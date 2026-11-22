"""Dedicated authenticated MCP pilot endpoints with caller-only Splunk access."""
import json
import os
from pathlib import Path
import sys
from urllib.parse import parse_qsl

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draft_service import DraftService, state_digest
from mcp_pilot_input import config, invalid, parse_brief, request_identity, strict_object
from mcp_pilot_ledger import PilotLedger
from mcp_pilot_service import PilotCreation
from provider_service import ProviderError
from search_service import SearchService


def mapping(pairs):
    result = {}
    if not isinstance(pairs, list):
        raise invalid()
    for pair in pairs:
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                or not all(isinstance(item, str) for item in pair)):
            raise invalid()
        key, value = pair
        if key in result:
            raise invalid()
        result[key] = value
    return result


def wire_arguments(request, create):
    if create:
        payload = request.get('payload', '')
        if not isinstance(payload, str) or len(payload) > 55000:
            raise invalid()
        if payload.lstrip().startswith('{'):
            # The outer JSON can expand the inner UTF-8 brief through escaping.
            return strict_object(payload, maximum=55000)
        try:
            return mapping(parse_qsl(payload, keep_blank_values=True, strict_parsing=True,
                                     encoding='utf-8', errors='strict', max_num_fields=4))
        except ValueError:
            raise invalid() from None
    arguments = mapping(request.get('query', []))
    if arguments.pop('output_mode', 'json') != 'json':
        raise invalid()
    return arguments


class PilotHandler(PersistentServerConnectionApplication):
    def __init__(self, _command_line=None, _command_arg=None):
        super(PersistentServerConnectionApplication, self).__init__()
        self.operation = os.environ.get('CONSTELLATION_MCP_PILOT')

    @staticmethod
    def response(status, payload):
        return {'status': status, 'payload': payload, 'headers': {'Cache-Control': 'no-store'}}

    def handle(self, raw):
        try:
            if self.operation not in ('create', 'status'):
                return self.response(503, {'error': 'The pilot endpoint is unavailable.', 'code': 'pilot_unconfirmed'})
            create = self.operation == 'create'
            request = json.loads(raw)
            if request.get('method', '').upper() != ('POST' if create else 'GET'):
                return self.response(405, {'error': 'Use the registered tool method.', 'code': 'method_not_allowed'})
            settings = config()
            if settings['mode'] == 'off':
                raise ProviderError('The dashboard pilot is disabled.', 403, 'feature_disabled')
            session = request.get('session') or {}
            user, token = session.get('user'), session.get('authtoken')
            arguments = wire_arguments(request, create)
            identifier, issued = request_identity(arguments, create)
            if not isinstance(user, str) or not token or user != arguments['expected_user'] or user not in settings['users']:
                raise ProviderError('The dashboard pilot is unavailable to this identity.', 403, 'identity_unavailable')
            runtime = SearchService(user, token)
            entries = runtime.request('/services/authentication/current-context').get('entry') or []
            context = entries[0].get('content', {}) if len(entries) == 1 else {}
            if context.get('username') != user or 'search' not in context.get('capabilities', []):
                raise ProviderError('The dashboard pilot is unavailable to this identity.', 403, 'identity_unavailable')
            brief = parse_brief(arguments['brief_json']) if create else None
            if settings['mode'] == 'probe':
                evidence = {'mode': 'probe', 'identity_verified': True}
                if create:
                    evidence['brief_digest'] = state_digest(brief)
                    return self.response(200, PilotCreation.reply(identifier, 'failed',
                                         code='pilot_probe_only', pilot=evidence))
                return self.response(200, PilotCreation.reply(identifier, 'not_found', pilot=evidence))
            root = Path(os.environ['SPLUNK_HOME']) / 'var' / 'lib' / 'splunk' / 'constellation_mcp_pilot'
            service = PilotCreation(runtime, DraftService(user, token), PilotLedger(root), settings)
            result = service.create(identifier, issued, brief) if create else service.status(identifier)
            return self.response(200, result)
        except ProviderError as error:
            # Only application-defined messages may cross the pilot boundary.
            code = error.code or 'pilot_request_failed'
            if code.startswith('splunk_') or code == 'pilot_request_failed':
                return self.response(error.status, {'error': 'The Splunk pilot request failed.', 'code': 'pilot_request_failed'})
            return self.response(error.status, {'error': str(error), 'code': code})
        except Exception:
            return self.response(503, {'error': 'The pilot response could not be confirmed. Check status.',
                                       'code': 'pilot_unconfirmed'})
