"""Caller-token bridge to owner-only OpenAI custody; keys never cross this API."""
import json
from provider_service import ProviderError


def request(runtime, action, body=None):
    import splunk.rest
    if action not in ('connection', 'models', 'responses'): raise ProviderError('Unsupported OpenAI operation.')
    try:
        response, raw = splunk.rest.simpleRequest('/servicesNS/nobody/constellation/constellation/openai/' + action,
            sessionKey=runtime.token, method='POST' if body is not None else 'GET',
            getargs={'output_mode': 'json'}, postargs={'request': json.dumps(body)} if body is not None else None,
            timeout=105, raiseAllErrors=False)
        result = json.loads(raw)
    except Exception:
        raise ProviderError('The private OpenAI connection is unavailable. Reopen Settings or ask an administrator to check the app installation.', 503, 'openai_connection_unavailable') from None
    status = int(response.get('status', 200))
    if status >= 400:
        # Only app-owned, fixed errors are returned by the dedicated handler.
        raise ProviderError(result.get('error', 'The private OpenAI request failed.'), status, result.get('code', 'openai_connection_failed'))
    return result


class OpenAIStoreProxy:
    def __init__(self, runtime): self.runtime = runtime
    def read(self): return request(self.runtime, 'connection')['config']
    def write(self, config): request(self.runtime, 'connection', config)
    def key_access(self): return {'canWrite': True}


class OpenAIClientProxy:
    def __init__(self, runtime): self.runtime = runtime
    def call(self, _unused_key, resource, body=None): return request(self.runtime, resource, body)
