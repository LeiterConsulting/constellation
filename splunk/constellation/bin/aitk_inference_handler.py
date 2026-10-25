"""Dedicated Splunk persistconn entry; main/control never receive system authentication."""
import json
import os
import sys
from splunk.persistconn.application import PersistentServerConnectionApplication
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from provider_service import ProviderError
from search_service import SearchService


class AitkInferenceHandler(PersistentServerConnectionApplication):
    """Separate opt-in privileged boundary; never a general Splunk REST proxy."""
    def __init__(self, _command_line=None, _command_arg=None):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, raw):
        try:
            request = json.loads(raw)
            session = request.get('session', {})
            if not session.get('user') or not session.get('authtoken'):
                raise ProviderError('Sign in to Splunk first.', 401)
            token = request.get('system_authtoken')
            if not isinstance(token, str) or not token:
                raise ProviderError('Shared AITK system authentication is unavailable.', 503, 'aitk_system_unavailable')
            from aitk_inference import execute, form_body
            action = request.get('path_info', '').strip('/')
            method = request.get('method', 'GET').upper()
            if (method, action) == ('GET', 'status'): body = {'action': 'status'}
            elif (method, action) == ('POST', 'infer'): body = form_body(request)
            else: raise ProviderError('This inference endpoint or method is unavailable.', 404)
            caller = SearchService(session['user'], session['authtoken'])
            privileged = SearchService('nobody', token)
            result = execute(caller, privileged, body)
            return {'status': 200, 'payload': result, 'headers': {'Cache-Control': 'no-store'}}
        except ProviderError as error:
            return {'status': error.status, 'payload': {'error': str(error), 'status': error.status,
                    'code': error.code or 'aitk_inference_failed'}, 'headers': {'Cache-Control': 'no-store'}}
        except Exception:
            return {'status': 500, 'payload': {'error': 'Shared AITK inference could not be completed.',
                    'status': 500, 'code': 'aitk_inference_failed'}, 'headers': {'Cache-Control': 'no-store'}}
