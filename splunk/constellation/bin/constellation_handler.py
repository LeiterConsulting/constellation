"""User-scoped REST bridge; never requests system authentication."""
import hashlib
import json
import os
import sys
from urllib.parse import quote
from splunk.persistconn.application import PersistentServerConnectionApplication
import splunk.rest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from provider_service import ProviderService, ProviderError
from search_service import SearchService
from agent_service import AgentService
from draft_service import DraftService
from data_service import DataService
from dashboard_library import DashboardLibrary
from authoring_progress import AuthoringProgress


def author(service, runtime, body):
    control = AuthoringProgress(runtime.user, runtime.token) if body.get('runHandle') else None
    progress = control.claim(body['runHandle']) if control else lambda *args: None
    runtime.check_cancel = lambda: progress()
    try:
        result = AgentService(service, runtime, progress=progress).assist(body)
        progress('complete')
        return result
    except Exception:
        progress('failed')
        raise
    finally:
        if control: control.release(body['runHandle'])


class CredentialStore:
    def __init__(self, user, token):
        self.user, self.token = user, token
        self.base = '/servicesNS/' + quote(user, safe='') + '/constellation/storage/passwords'
        # storage/passwords reads app/global credentials, even in a user namespace.
        # Distinct IDs prevent one user's connection from shadowing another's.
        self.name = 'connection-' + hashlib.sha256(user.encode('utf-8')).hexdigest()
        self.entry = self.base + '/' + quote('constellation.openai:' + self.name + ':', safe='')
        self.legacy_entry = self.base + '/' + quote('constellation.openai:connection:', safe='')

    def request(self, path, method='GET', fields=None):
        try:
            _, raw = splunk.rest.simpleRequest(path, sessionKey=self.token, method=method,
                getargs={'output_mode': 'json'}, postargs=fields, raiseAllErrors=True)
            return json.loads(raw)
        except Exception as error:
            if str(getattr(error, 'statusCode', '')) == '404':
                return None
            raise ProviderError('Splunk credential storage is unavailable to this user. The connection requires storage-password permissions.', 403) from None

    def verify_acl(self, acl):
        perms = acl.get('perms', {})
        roles = [perms.get('read'), perms.get('write')]
        if (acl.get('owner') != self.user or acl.get('app') != 'constellation'
                or acl.get('sharing') != 'app'
                or any(not isinstance(value, list) or any(role != '' for role in value) for value in roles)):
            raise ProviderError('The saved connection permissions are not restricted to its owner. Ask a Splunk administrator to repair this credential.', 403)

    def locate(self):
        for path in (self.entry, self.legacy_entry):
            result = self.request(path + '/acl')
            if not result:
                continue
            acl = result['entry'][0].get('acl', {})
            if path == self.legacy_entry and acl.get('owner') != self.user:
                # An older shared ID may belong to another user. Never read it.
                continue
            self.verify_acl(acl)
            return path
        return None

    def read(self):
        path = self.locate()
        if path is None:
            return None
        result = self.request(path)
        if not result:
            raise ProviderError('The saved connection changed. Reopen Settings and retry.', 409)
        entry = result['entry'][0]
        self.verify_acl(entry.get('acl', {}))
        return json.loads(entry['content']['clear_password'])

    def write(self, config):
        path = self.locate()
        fields = {'password': json.dumps(config)}
        if path:
            self.request(path, 'POST', fields)
        else:
            path = self.entry
            # Never put a real key in the initially inherited ACL: create an
            # empty placeholder, restrict it, verify, then write the secret.
            self.request(self.base, 'POST', {'password': '{}', 'name': self.name, 'realm': 'constellation.openai'})
            self.request(path + '/acl', 'POST', {'sharing': 'app', 'owner': self.user,
                                               'perms.read': '', 'perms.write': ''})
            acl = self.request(path + '/acl')
            if not acl or not acl.get('entry'):
                raise ProviderError('The private credential permissions could not be verified. No key was stored.', 503)
            self.verify_acl(acl['entry'][0].get('acl', {}))
            self.request(path, 'POST', fields)
        # Retain the endpoint's supported scope and deny every read/write role.
        self.request(path + '/acl', 'POST', {'sharing': 'app', 'owner': self.user,
                                           'perms.read': '', 'perms.write': ''})
        if self.read() != config:
            raise ProviderError('The saved connection could not be verified.', 500)

    def key_access(self):
        context = self.request('/services/authentication/current-context')['entry'][0]['content']
        caps = set(context.get('capabilities', []))
        return {'canWrite': bool(caps.intersection({'admin_all_objects', 'edit_storage_passwords'}))}


class ConstellationHandler(PersistentServerConnectionApplication):
    def __init__(self, _command_line=None, _command_arg=None):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, raw):
        try:
            request = json.loads(raw)
            session = request.get('session', {})
            if not session.get('user') or not session.get('authtoken'):
                raise ProviderError('Sign in to Splunk first.', 401)
            action = request.get('path_info', '').strip('/')
            if not action:
                action = request.get('rest_path', '').rstrip('/').rsplit('/', 1)[-1]
            method = request.get('method', 'GET').upper()
            payload = request.get('payload', '')
            if len(payload) > 12_000_000:
                raise ProviderError('This request exceeds the allowed size.', 413)
            body = json.loads(payload) if payload else {}
            if not isinstance(body, dict):
                raise ProviderError('Expected a JSON object.')
            runtime = SearchService(session['user'], session['authtoken'])
            from connection_store import ConnectionStore, ConnectionPreferences
            store = ConnectionStore(CredentialStore(session['user'], session['authtoken']), ConnectionPreferences(session['user'], session['authtoken']))
            service = ProviderService(store, runtime=runtime)
            routes = {('GET','settings'): service.settings, ('POST','settings'): lambda: service.save(body),
                      ('POST','models'): service.models, ('POST','test'): service.test,
                      ('POST','assist'): lambda: service.assist(body),
                      ('POST','author'): lambda: author(service, runtime, body),
                      ('POST','run'): lambda: AuthoringProgress(session['user'], session['authtoken']).operation(body),
                      ('GET','environment'): runtime.environment,
                      ('POST','environment'): lambda: runtime.environment(body.get('probe') is True),
                      ('GET','datasets'): runtime.datasets,
                      ('GET','discovery'): lambda: DataService(runtime).discovery(),
                      ('POST','profile'): lambda: DataService(runtime).profile(body),
                      ('GET','drafts'): lambda: DraftService(session['user'], session['authtoken']).listing(),
                      ('POST','drafts'): lambda: DraftService(session['user'], session['authtoken']).operation(body),
                      ('POST','library'): lambda: DashboardLibrary(DraftService(session['user'], session['authtoken'])).operation(body),
                      ('POST','preview_job'): lambda: runtime.job(body),
                      ('POST','preview'): lambda: runtime.preview(body)}
            operation = routes.get((method, action))
            if operation is None:
                raise ProviderError('This endpoint or method is unavailable.', 404)
            return {'status': 200, 'payload': operation(), 'headers': {'Cache-Control': 'no-store'}}
        except ProviderError as error:
            payload = {'error': str(error)}
            if error.code:
                payload['code'] = error.code
            if getattr(error, 'validation_error', None):
                payload['validationError'] = error.validation_error
            if getattr(error, 'recovery', None):
                payload['recovery'] = error.recovery
            return {'status': error.status, 'payload': payload, 'headers': {'Cache-Control': 'no-store'}}
        except Exception as error:
            # Framework/transport exceptions can contain secrets. Never echo or log them.
            return {'status': 500, 'payload': {'error': 'The connection request could not be completed. No dashboard changes were applied.', 'code': type(error).__name__}, 'headers': {'Cache-Control': 'no-store'}}
