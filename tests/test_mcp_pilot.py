"""Exercise the pilot workflow against synthetic Splunk data and an on-disk receipt store."""
from concurrent.futures import ThreadPoolExecutor
import importlib
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from test_drafts_and_data import DataRuntime, MemoryDrafts
from compatibility import feature_profile
from dashboard_library import parse_view
from mcp_pilot_authoring import require_provider
from mcp_pilot_input import parse_brief, request_identity, web_base
from mcp_pilot_ledger import ADMISSION_SECONDS, CLAIM_SECONDS, PilotLedger, RETAIN_SECONDS
from mcp_pilot_service import PilotCreation, build_fixture
from provider_service import ProviderError

NOW = 1795186800  # Synthetic time for request-window checks.
IDENTIFIER = '20261120T150000Z-' + 'a' * 32
BASE = 'https://splunk.example.com/splunk/en-US'


def brief():
    return {'title': 'Pilot "events" · café $ and \\', 'purpose': 'Operator event counts.',
            'source': {'kind': 'index', 'index': 'fixture_index'}, 'time_range': {'earliest': '-24h', 'latest': 'now'},
            'pages': [{'name': 'Overview', 'panels': ['Event count', 'Event arrivals over time']},
                      {'name': 'Coverage', 'panels': ['Event counts by sourcetype']}],
            'provenance': {'kind': 'conversation', 'label': 'Synthetic context'}}


class FixtureRuntime(DataRuntime):
    def __init__(self, user='alice'):
        super().__init__()
        self.user = user

    def environment(self):
        return {'version': '10.4.4', 'features': feature_profile('10.4.4', ['search'])}

    def preview(self, body):
        query = body['query']
        self.calls.append(query)
        if body.get('fieldDiscovery'):
            row = {'_time': '1000', 'sourcetype': 'fixture:events', '_raw': 'PRIVATE FIXTURE ROW'}
        elif '| timechart' in query:
            row = {'_time': '1000', 'events': '20'}
        elif 'BY sourcetype' in query:
            row = {'sourcetype': 'fixture:events', 'events': '20'}
        else:
            row = {'events': '20'}
        return {'fields': [{'name': field} for field in row], 'results': [row], 'state': 'complete'}


class FixtureDrafts(MemoryDrafts):
    def __init__(self, owner='alice', native_fault=None):
        super().__init__(owner)
        self.views = {}
        self.native_fault = native_fault
        self.writes = 0

    def request(self, path, method='GET', fields=None, projection=False):
        if '/data/ui/views' not in path:
            return super().request(path, method, fields, projection)
        if method == 'POST':
            if self.native_fault == 'denied':
                raise ProviderError('Native failure', 403)
            name = fields['name']
            self.assert_new_view(name)
            self.writes += 1
            self.views[name] = {'name': name, 'acl': {'owner': self.user, 'app': 'constellation', 'sharing': 'user'},
                                'content': {'eai:data': fields['eai:data']}}
            if self.native_fault == 'lost':
                raise ProviderError('Native response lost', 503)
        view = self.views.get(path.rsplit('/', 1)[-1])
        return {'entry': [view]} if view else None

    def assert_new_view(self, name):
        if name in self.views:
            raise AssertionError('A native create was replayed.')


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.root = TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.clock = NOW
        self.ledger = PilotLedger(Path(self.root.name) / 'ledger', clock=lambda: self.clock)
        self.runtime = FixtureRuntime()
        self.drafts = FixtureDrafts()
        self.settings = {'mode': 'fixture', 'index': 'fixture_index', 'web_base': web_base(BASE)}

    def service(self):
        return PilotCreation(self.runtime, self.drafts, self.ledger, self.settings)

    def test_native_round_trip_duplicate_and_new_session_status(self):
        first = self.service().create(IDENTIFIER, NOW, brief())
        self.assertEqual(first['status'], 'created')
        self.assertEqual(first['edit_url'], BASE + '/app/constellation/workspace?draft=' + first['draft_id'])
        self.assertEqual(first['view_url'], BASE + '/app/constellation/' + first['dashboard_id'])
        self.assertEqual(first['title'], brief()['title'])
        state = self.drafts.read(first['draft_id'])['state']
        native = parse_view(self.drafts.views[first['dashboard_id']]['content']['eai:data'])[1]
        self.assertEqual(native, state['definition'])
        self.assertEqual(len(native['layout']['tabs']['items']), 2)
        self.assertEqual(len(native['visualizations']), 3)
        self.assertNotIn('PRIVATE FIXTURE ROW', json.dumps(state))
        self.assertNotIn('fixture-session', self.ledger.path.read_bytes().decode(errors='replace'))
        self.assertNotIn('Operator event counts', self.ledger.path.read_bytes().decode(errors='replace'))
        before = len(self.runtime.calls)
        self.assertEqual(self.service().create(IDENTIFIER, NOW, dict(reversed(list(brief().items())))), first)
        self.ledger = PilotLedger(self.ledger.root, clock=lambda: self.clock)
        self.assertEqual(self.service().status(IDENTIFIER), first)
        self.assertEqual(len(self.runtime.calls), before)
        self.assertEqual(self.drafts.writes, 1)
        self.assertEqual(len(self.drafts.entries), 1)
        with self.assertRaises(ProviderError) as changed:
            self.service().create(IDENTIFIER, NOW, dict(brief(), title='another'))
        self.assertEqual(changed.exception.code, 'request_conflict')

    def test_peer_and_changed_view_acl_never_receive_links(self):
        result = self.service().create(IDENTIFIER, NOW, brief())
        foreign = PilotCreation(FixtureRuntime('bob'), FixtureDrafts('bob'), self.ledger, self.settings)
        self.assertEqual(foreign.status(IDENTIFIER)['status'], 'not_found')
        self.drafts.views[result['dashboard_id']]['acl']['sharing'] = 'app'
        reread = self.service().status(IDENTIFIER)
        self.assertNotIn('view_url', reread)
        self.assertNotIn('dashboard_id', reread)
        self.assertIn('edit_url', reread)

    def test_uncertain_native_write_recovers_and_denial_keeps_draft(self):
        self.drafts.native_fault = 'lost'
        result = self.service().create(IDENTIFIER, NOW, brief())
        self.assertEqual(result['status'], 'created')
        self.assertEqual(self.service().status(IDENTIFIER), result)
        self.assertEqual(self.drafts.writes, 1)
        self.drafts.native_fault = 'denied'
        result = self.service().create(IDENTIFIER[:-1] + 'b', NOW, brief())
        self.assertEqual(result['status'], 'draft_only')
        self.assertIn('edit_url', result)
        self.assertNotIn('view_url', result)
        self.assertEqual(self.drafts.writes, 1)

    def test_claims_are_atomic_and_expired_ids_cannot_restart(self):
        def claim(_):
            return self.ledger.claim('alice', IDENTIFIER, NOW, 'fixture-digest')[1]

        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(claim, range(4))), 1)
        self.assertEqual(self.service().status(IDENTIFIER)['status'], 'running')
        self.clock += CLAIM_SECONDS + 1
        self.assertEqual(self.service().status(IDENTIFIER)['code'], 'operation_interrupted')
        with self.assertRaises(ProviderError):
            self.ledger.advance('alice', IDENTIFIER, 'accepted', 'saving_draft')
        self.clock = NOW + RETAIN_SECONDS + ADMISSION_SECONDS
        self.assertEqual(self.service().status(IDENTIFIER)['status'], 'not_found')
        with self.assertRaises(ProviderError) as old:
            claim(0)
        self.assertEqual(old.exception.code, 'request_expired')

    def test_out_of_scope_requests_do_not_search_or_write(self):
        for n, incoming in enumerate((dict(brief(), requirements='Use seconds.'), dict(brief(), source={
                'kind': 'spl', 'query': 'search index=fixture_index'})), 1):
            result = self.service().create(IDENTIFIER[:-1] + str(n), NOW, incoming)
            self.assertEqual(result['status'], 'needs_input')
        self.assertEqual(self.runtime.calls, [])
        self.assertFalse(self.drafts.entries)

    def test_authoring_preserves_reviewed_context_and_uses_the_caller_private_save_path(self):
        incoming = dict(brief(), requirements='Label all panels.', findings=['The gap starts at noon.'])
        snapshot, _ = build_fixture(self.runtime, incoming)
        changes = [{'op': 'set', 'path': '/' + key, 'value': json.dumps(value)}
                   for key, value in snapshot['definition'].items()]
        approved = ('openai', 'https://api.openai.com/v1', 'fixture-model')
        self.settings.update(mode='authoring', provider_route=approved)
        with patch('mcp_pilot_authoring.AgentService') as agent, patch('mcp_pilot_authoring.user_provider'):
            def assist(body, check_provider):
                check_provider({'provider': 'openai', 'model': 'fixture-model'})
                self.assertNotIn('Synthetic context', body['prompt'])
                self.assertIn('The gap starts at noon.', body['prompt'])
                self.assertEqual(body['dataContext'], {'index': 'fixture_index', 'earliest': '-24h'})
                return {'changes': changes, 'searchReceipts': [{'status': 'results'}],
                        'dataContext': snapshot['dataContext'], 'pagePurposes': snapshot['pagePurposes'],
                        'message': 'Created the dashboard.'}

            agent.return_value.assist.side_effect = assist
            reply = self.service().create(IDENTIFIER, NOW, incoming)
            self.assertEqual(reply['status'], 'created')
            self.assertEqual(self.service().create(IDENTIFIER, NOW, incoming), reply)
            self.assertEqual(agent.return_value.assist.call_count, 1)
        saved = self.drafts.read(reply['draft_id'])['state']
        self.assertEqual(saved['brief']['requirements'], incoming['requirements'])
        self.assertIn('Synthetic context', saved['messages'][0]['text'])
        self.assertEqual(self.drafts.writes, 1)

    def test_authoring_provider_route_must_match_before_inference(self):
        approved = ('ollama', 'https://models.example.com', 'fixture-model')
        require_provider({'provider': 'ollama', 'base_url': approved[1], 'model': approved[2]}, approved)
        with self.assertRaises(ProviderError) as error:
            require_provider({'provider': 'ollama', 'base_url': 'https://other.example.com',
                              'model': approved[2]}, approved)
        self.assertEqual(error.exception.code, 'authoring_input')

    def test_exact_envelope_and_restricted_url(self):
        self.assertEqual(parse_brief(json.dumps(brief())), brief())
        parsed_id, _ = request_identity({'schema_version': '1', 'request_id': IDENTIFIER, 'expected_user': 'alice'}, False)
        self.assertEqual(parsed_id, IDENTIFIER)
        for value in ('{"title":"a","title":"b"}', json.dumps(dict(brief(), owner='peer')),
                      json.dumps(dict(brief(), time_range={'earliest': [], 'latest': 'now'}))):
            with self.assertRaises(ProviderError):
                parse_brief(value)
        for value in ('http://splunk.example.com/en-US', BASE + '?x=1', BASE + '/../en-US',
                      'https://user@splunk.example.com/en-US'):
            with self.assertRaises(ProviderError):
                web_base(value)


class PilotHandlerTests(unittest.TestCase):
    def load_handler(self):
        module = ModuleType('splunk.persistconn.application')
        module.PersistentServerConnectionApplication = type('Persistent', (), {})
        with patch.dict(sys.modules, {'splunk.persistconn.application': module}):
            handler = importlib.import_module('mcp_pilot_handler')
        self.addCleanup(sys.modules.pop, 'mcp_pilot_handler', None)
        return handler

    def test_splunk_can_load_the_single_persistent_application_class(self):
        handler = self.load_handler()
        base = handler.PersistentServerConnectionApplication
        classes = [name for name, candidate in inspect.getmembers(handler, inspect.isclass)
                   if candidate is not base and issubclass(candidate, base)]
        self.assertEqual(classes, ['PilotHandler'])
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(handler.PilotHandler().handle('{}')['status'], 503)

    def test_identity_probe_checks_forwarded_session_and_never_opens_ledger(self):
        handler = self.load_handler()
        with patch.dict('os.environ', {'CONSTELLATION_MCP_PILOT': 'create'}):
            create = handler.PilotHandler()
        with patch.dict('os.environ', {'CONSTELLATION_MCP_PILOT': 'status'}):
            status = handler.PilotHandler()
        arguments = {'schema_version': '1', 'request_id': IDENTIFIER, 'expected_user': 'alice',
                     'brief_json': json.dumps(brief(), ensure_ascii=False)}
        wire = {'method': 'POST', 'session': {'user': 'alice', 'authtoken': 'fixture-session'},
                'payload': json.dumps(arguments, ensure_ascii=False)}
        with patch.object(handler, 'config', return_value={'mode': 'probe', 'users': {'alice'}}), \
                patch.object(handler, 'SearchService') as runtime, patch.object(handler, 'PilotLedger') as ledger:
            runtime.return_value.request.return_value = {'entry': [{'content': {'username': 'alice', 'capabilities': ['search']}}]}
            first = create.handle(json.dumps(wire))
            wire['payload'] = urlencode(arguments)
            self.assertEqual(create.handle(json.dumps(wire)), first)
            self.assertEqual(first['payload']['code'], 'pilot_probe_only')
            self.assertTrue(first['payload']['pilot']['identity_verified'])
            self.assertNotIn(brief()['title'], json.dumps(first))
            self.assertEqual(status.handle(json.dumps(wire))['status'], 405)
            status_wire = {'method': 'GET', 'session': wire['session'],
                           'query': [(key, value) for key, value in arguments.items() if key != 'brief_json']}
            checked = status.handle(json.dumps(status_wire))
            self.assertEqual(checked['payload']['status'], 'not_found')
            self.assertTrue(checked['payload']['pilot']['identity_verified'])
            runtime.return_value.request.return_value['entry'][0]['content']['username'] = 'someone-else'
            failure = create.handle(json.dumps(wire))
            self.assertEqual(failure['payload']['code'], 'identity_unavailable')
            ledger.assert_not_called()

    def test_registration_routes_and_schema_are_aligned(self):
        from configparser import ConfigParser
        app = Path(__file__).resolve().parents[1] / 'splunk/constellation'
        tools, routes = ConfigParser(), ConfigParser()
        tools.read(app / 'default/tools.conf')
        routes.read(app / 'default/restmap.conf')
        schemas = json.loads((app / 'static/tool_input_payload_signatures.json').read_text())
        self.assertEqual(set(schemas), {'create_dashboard', 'get_creation_status'})
        for name in schemas:
            tool = tools['restmap:' + name]
            route = routes['script:' + tool['endpoint_name']]
            self.assertEqual(route['passSystemAuth'], 'false')
            self.assertEqual(route['passSession'], 'true')
            self.assertEqual(route['requireAuthentication'], 'true')
            self.assertEqual(route['handler'], 'mcp_pilot_handler.PilotHandler')
            self.assertEqual(route['driver.env.constellation_mcp_pilot'], 'create' if name == 'create_dashboard' else 'status')
            self.assertEqual(tool['method'], 'post' if name == 'create_dashboard' else 'get')
            self.assertEqual(set(schemas[name]['required']), set(schemas[name]['properties']))
            self.assertTrue(all(p['required'] == 'true' for p in schemas[name]['properties'].values()))
