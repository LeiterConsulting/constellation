"""Owner-restricted encrypted connection records; used only by the key handler."""
import hashlib
import json
from urllib.parse import quote
import splunk.rest
from provider_service import ProviderError


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
                getargs={'output_mode': 'json'}, postargs=fields, raiseAllErrors=True, timeout=10)
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
