"""Private secretless provider preferences, separated from encrypted credentials."""
import hashlib
import json
from urllib.parse import quote
from draft_service import DraftService
from provider_service import ProviderError


def secretless(config):
    if not isinstance(config, dict) or set(config) - {'active_provider', 'model', 'connections'}:
        raise ProviderError('Secrets cannot be saved in connection preferences.')
    connections = config.get('connections', {})
    if not isinstance(connections, dict) or set(connections) - {'ollama', 'aitk'}:
        raise ProviderError('This connection preference is unsupported.')
    for provider, value in connections.items():
        allowed = {'model', 'base_url'} if provider == 'ollama' else {'model', 'connection'}
        if not isinstance(value, dict) or set(value) - allowed or any(not isinstance(item, str) for item in value.values()):
            raise ProviderError('Secrets cannot be saved in connection preferences.')
    return config


class ConnectionPreferences(DraftService):
    def __init__(self, user, token):
        super().__init__(user, token)
        self.base = '/servicesNS/' + quote(user, safe='') + '/constellation/configs/conf-constellation_connections'
        self.name = 'connection_' + hashlib.sha256(user.encode()).hexdigest()
        self.path = self.base + '/' + self.name

    def read(self):
        result = self.request(self.path)
        if not result or not result.get('entry'): return None
        self.verify(result['entry'][0])
        return secretless(json.loads(result['entry'][0]['content']['config']))

    def write(self, config):
        fields = {'config': json.dumps(secretless(config))}
        existing = self.read()
        self.request(self.path if existing is not None else self.base, 'POST', fields if existing is not None else dict(fields, name=self.name))
        if self.read() != config: raise ProviderError('The saved connection preferences could not be verified.', 503)

    def clear(self):
        if self.read() is not None: self.request(self.path, 'DELETE')
        if self.read() is not None: raise ProviderError('Reopen Settings to finish switching connections.', 503)


class ConnectionStore:
    def __init__(self, encrypted, preferences):
        self.encrypted, self.preferences = encrypted, preferences

    def read(self):
        preferences = self.preferences.read()
        return preferences if preferences is not None else self.encrypted.read()

    def key_access(self):
        return self.encrypted.key_access()

    def write(self, config):
        if config.get('api_key'):
            self.encrypted.write(config)
            self.preferences.clear()
        else:
            self.preferences.write(config)
