"""Separate owner-only key custody entry; no general elevated REST interface."""
import json
import os
import sys
from urllib.parse import parse_qs
from splunk.persistconn.application import PersistentServerConnectionApplication
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from provider_service import ProviderError
from search_service import SearchService


class OpenAIPrivateHandler(PersistentServerConnectionApplication):
    def __init__(self, _command_line=None, _command_arg=None):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, raw):
        try:
            request = json.loads(raw); session = request.get('session', {})
            if not session.get('user') or not session.get('authtoken'): raise ProviderError('Sign in to Splunk first.', 401)
            token = request.get('system_authtoken')
            if not isinstance(token, str) or not token: raise ProviderError('Private OpenAI storage is unavailable.', 503)
            action, method = request.get('path_info', '').strip('/'), request.get('method', 'GET').upper()
            if (method, action) not in (('GET', 'connection'), ('POST', 'connection'), ('GET', 'models'), ('POST', 'responses')):
                raise ProviderError('This private OpenAI endpoint or method is unavailable.', 404)
            payload = request.get('payload', '')
            if not isinstance(payload, str) or len(payload.encode()) > 36_000_000: raise ProviderError('This request is too large.', 413)
            body = None
            if payload:
                values = parse_qs(payload, keep_blank_values=True, strict_parsing=True, max_num_fields=1)
                if set(values) != {'request'} or len(values['request']) != 1: raise ProviderError('Provide one private request.')
                encoded = values['request'][0]
                if len(encoded.encode()) > 12_000_000: raise ProviderError('This request is too large.', 413)
                body = json.loads(encoded)
            if method == 'GET' and body is not None: raise ProviderError('This operation does not accept a body.')
            if method == 'POST' and not isinstance(body, dict): raise ProviderError('Provide a JSON object.')
            from openai_private import execute
            result = execute(SearchService(session['user'], session['authtoken'], request_timeout=10), SearchService('nobody', token, request_timeout=10), action, body)
            return {'status': 200, 'payload': result, 'headers': {'Cache-Control': 'no-store'}}
        except ProviderError as error:
            return {'status': error.status, 'payload': {'error': str(error), 'code': error.code or 'openai_connection_failed'}, 'headers': {'Cache-Control': 'no-store'}}
        except Exception:
            return {'status': 500, 'payload': {'error': 'The private OpenAI request could not be completed.', 'code': 'openai_connection_failed'}, 'headers': {'Cache-Control': 'no-store'}}
