"""User-scoped REST bridge; never requests system authentication."""
import json
import os
import sys
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
from credential_store import CredentialStore
from openai_connection import OpenAIStoreProxy, OpenAIClientProxy


def author(service, runtime, body):
    control = AuthoringProgress(runtime.user, runtime.token) if body.get('runHandle') else None
    progress = control.claim(body['runHandle']) if control else lambda *args: None
    runtime.check_cancel = lambda: progress()
    runtime.aitk_run_handle = body.get('runHandle')
    try:
        result = AgentService(service, runtime, progress=progress).assist(body)
        if control: control.complete(body['runHandle'], result)
        else: progress('complete')
        return result
    except Exception:
        progress('failed')
        raise
    finally:
        if control: control.release(body['runHandle'])


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
            store = ConnectionStore(OpenAIStoreProxy(runtime), ConnectionPreferences(session['user'], session['authtoken']))
            service = ProviderService(store, client=OpenAIClientProxy(runtime), runtime=runtime)
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
