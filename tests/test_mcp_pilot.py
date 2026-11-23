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
from mcp_pilot_input import parse_brief, parse_inspection, request_identity, web_base
from mcp_pilot_inspection import inspect_source
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

    def test_missing_status_reports_mode_for_the_verified_caller_without_writing(self):
        handler = self.load_handler()
        wire = {'method': 'GET', 'session': {'user': 'alice', 'authtoken': 'fixture-session'},
                'query': [('schema_version', '1'), ('request_id', IDENTIFIER), ('expected_user', 'alice')]}
        with TemporaryDirectory() as root, patch.dict('os.environ', {
            'CONSTELLATION_MCP_PILOT': 'status', 'SPLUNK_HOME': root,
        }), patch.object(handler, 'SearchService') as runtime, patch.object(handler, 'DraftService') as drafts:
            runtime.return_value.user = drafts.return_value.user = 'alice'
            runtime.return_value.request.return_value = {'entry': [
                {'content': {'username': 'alice', 'capabilities': ['search']}}]}
            status = handler.PilotHandler()
            for mode in ('fixture', 'authoring'):
                with self.subTest(mode=mode), patch.object(handler, 'config', return_value={
                    'mode': mode, 'users': {'alice'},
                }):
                    runtime.return_value.request.reset_mock()
                    reply = status.handle(json.dumps(wire))
                    self.assertEqual(reply['status'], 200)
                    self.assertEqual(reply['payload'], {
                        'schema_version': '1', 'request_id': IDENTIFIER, 'status': 'not_found', 'warnings': [],
                        'pilot': {'mode': mode, 'identity_verified': True},
                    })
                    runtime.return_value.request.assert_called_once_with('/services/authentication/current-context')
            drafts.return_value.request.assert_not_called()
            self.assertFalse((Path(root) / 'var').exists())

    def test_inspection_uses_the_same_caller_session_and_never_opens_save_paths(self):
        handler = self.load_handler()
        scope = {'source': {'kind': 'spl', 'query': 'search index=fixture_index service="café & test"'},
                 'time_range': {'earliest': '-1h', 'latest': 'now'}}
        arguments = {'schema_version': '1', 'expected_user': 'alice',
                     'scope_json': json.dumps(scope, ensure_ascii=False)}
        wire = {'method': 'POST', 'session': {'user': 'alice', 'authtoken': 'fixture-session'}}
        with patch.dict('os.environ', {'CONSTELLATION_MCP_PILOT': 'inspect'}), \
                patch.object(handler, 'config', return_value={'mode': 'authoring', 'users': {'alice'}}) as settings, \
                patch.object(handler, 'SearchService') as runtime, patch.object(handler, 'inspect_source') as inspect_call, \
                patch.object(handler, 'PilotLedger') as ledger, patch.object(handler, 'DraftService') as drafts:
            context = {'username': 'alice', 'capabilities': ['search']}
            runtime.return_value.request.return_value = {'entry': [{'content': context}]}
            inspect_call.return_value = {'schema_version': '1', 'status': 'observed'}
            app = handler.PilotHandler()
            for encoder in (urlencode, json.dumps):
                with self.subTest(encoder=encoder.__name__):
                    reply = app.handle(json.dumps(dict(wire, payload=encoder(arguments))))
                    self.assertEqual(reply, {'status': 200, 'payload': inspect_call.return_value,
                                             'headers': {'Cache-Control': 'no-store'}})
                    runtime.assert_called_with('alice', 'fixture-session')
                    inspect_call.assert_called_with(runtime.return_value, scope)
            wire['payload'] = urlencode(arguments)
            inspect_call.reset_mock()
            for mode, code in (('off', 'feature_disabled'), ('fixture', 'feature_disabled'), ('probe', 'pilot_probe_only')):
                with self.subTest(mode=mode):
                    settings.return_value['mode'] = mode
                    self.assertEqual(app.handle(json.dumps(wire))['payload']['code'], code)
            settings.return_value['mode'] = 'authoring'
            self.assertEqual(app.handle(json.dumps(dict(wire, method='GET')))['status'], 405)
            switched = dict(wire, payload=urlencode(dict(arguments, expected_user='peer')))
            self.assertEqual(app.handle(json.dumps(switched))['payload']['code'], 'identity_unavailable')
            context['capabilities'] = []
            self.assertEqual(app.handle(json.dumps(wire))['payload']['code'], 'identity_unavailable')
            inspect_call.assert_not_called()
            ledger.assert_not_called()
            drafts.assert_not_called()

    def test_registration_routes_and_schema_are_aligned(self):
        from configparser import ConfigParser
        app = Path(__file__).resolve().parents[1] / 'splunk/constellation'
        tools, routes = ConfigParser(), ConfigParser()
        tools.read(app / 'default/tools.conf')
        routes.read(app / 'default/restmap.conf')
        schemas = json.loads((app / 'static/tool_input_payload_signatures.json').read_text())
        operations = {'create_dashboard': ('create', 'post'), 'get_creation_status': ('status', 'get'),
                      'inspect_dashboard_source': ('inspect', 'post')}
        self.assertEqual(set(schemas), set(operations))
        for name in schemas:
            operation, method = operations[name]
            tool = tools['restmap:' + name]
            route = routes['script:' + tool['endpoint_name']]
            self.assertEqual(route['passSystemAuth'], 'false')
            self.assertEqual(route['passSession'], 'true')
            self.assertEqual(route['requireAuthentication'], 'true')
            self.assertEqual(route['handler'], 'mcp_pilot_handler.PilotHandler')
            self.assertEqual(route['driver.env.constellation_mcp_pilot'], operation)
            self.assertEqual(route['match'], '/constellation/mcp/v1/' + operation)
            self.assertEqual(route['passPayload'], 'true' if method == 'post' else 'false')
            self.assertEqual(tool['method'], method)
            self.assertEqual(set(schemas[name]['required']), set(schemas[name]['properties']))
            self.assertTrue(all(p['required'] == 'true' for p in schemas[name]['properties'].values()))
            if method == 'post':
                self.assertEqual(schemas[name]['body_template'],
                                 {key: '$' + key + '$' for key in schemas[name]['required']})


class PilotInspectionTests(unittest.TestCase):
    def setUp(self):
        self.scope = {'source': {'kind': 'index', 'index': 'fixture_index', 'sourcetype': 'fixture:events'},
                      'time_range': {'earliest': '-1h', 'latest': 'now'}}
        self.runtime = FixtureRuntime()

    def test_index_inspection_returns_one_bounded_metadata_sample(self):
        rows = [{'latency_ms': '0', '_raw': 'PRIVATE CELL', 'broken\nfield': '1'},
                {'latency_ms': ['1', '2']}, {}]
        fields = [dict(name=name) for name in ('latency_ms', '_raw', 'broken\nfield')]
        fields.extend({'name': 'field_' + str(i)} for i in range(20))
        with patch.object(self.runtime, 'preview', return_value={
            'results': rows, 'fields': fields, 'state': 'partial',
            'evidence': {'reasons': ['Search stopped at a resource limit.', 'PRIVATE DIAGNOSTIC']},
        }) as preview:
            reply = inspect_source(self.runtime, parse_inspection(json.dumps(self.scope)))
        preview.assert_called_once_with({'query': 'search index="fixture_index" sourcetype="fixture:events" | head 201',
                                         'language': 'spl', 'earliest': '-1h', 'fieldDiscovery': True})
        self.assertEqual(reply['status'], 'observed')
        self.assertEqual(reply['source'], dict(self.scope['source'], language='spl'))
        self.assertEqual(reply['time_range'], self.scope['time_range'])
        self.assertEqual(reply['sample'], {'rows': 3, 'row_limit': 200, 'grain': 'indexed_observations',
                                          'completion': 'partial', 'reasons': ['resource_limit']})
        self.assertEqual(len(reply['fields']), 12)
        self.assertEqual(reply['fields'][0], {'name': 'latency_ms', 'present': 2, 'missing': 1,
                                             'numeric': 1, 'multivalue': 1, 'role': 'measurement',
                                             'unit': 'ms', 'basis': 'field_name'})
        self.assertNotRegex(json.dumps(reply), r'PRIVATE|broken|_raw')

    def test_spl_returns_aggregate_grain_and_suppresses_dynamic_column_names(self):
        for pipeline, expected_fields in (
            ('stats count AS events', [{'name': 'events', 'present': 1, 'missing': 0,
                                        'numeric': 1, 'multivalue': 0, 'role': 'unknown', 'basis': 'unknown'}]),
            ('timechart count BY host', []),
            ('eval {host}=count', []),
            ('xyseries _time host count', []),
        ):
            with self.subTest(pipeline=pipeline):
                query = 'search index=fixture_index service="café | xyseries" | ' + pipeline
                scope = dict(self.scope, source={'kind': 'spl', 'query': query})
                column = 'events' if expected_fields else 'private_value_as_field_name'
                with patch.object(self.runtime, 'preview', return_value={
                    'results': [{column: '0'}], 'fields': [{'name': column}], 'state': 'complete',
                }) as preview:
                    result = inspect_source(self.runtime, scope)
                preview.assert_called_once_with({'query': query + ' | head 201', 'language': 'spl',
                                                 'earliest': '-1h', 'fieldDiscovery': True})
                self.assertEqual(result['status'], 'observed')
                self.assertEqual(result['source'], {'kind': 'spl', 'language': 'spl'})
                self.assertEqual(result['sample']['grain'], 'existing_search_output')
                self.assertEqual(result['fields'], expected_fields)
                self.assertEqual(result['sample']['reasons'], [] if expected_fields else ['dynamic_field_names'])
                self.assertNotRegex(json.dumps(result), r'fixture_index|private_value')

    def test_zero_rows_are_empty_only_after_verified_completion(self):
        for completion, status, reasons in (
            ('complete', 'empty', []),
            ('partial', 'inconclusive', ['unverified_completion']),
            ('unknown', 'inconclusive', []),
            ('timeout', 'inconclusive', ['preview_timeout']),
        ):
            with self.subTest(completion=completion), patch.object(self.runtime, 'preview', return_value={
                'results': [], 'fields': [{'name': 'latency_ms'}], 'state': completion,
            }) as preview:
                if completion == 'timeout':
                    preview.side_effect = ProviderError('PRIVATE MESSAGE', 422, 'preview_timeout')
                result = inspect_source(self.runtime, self.scope)
                self.assertEqual(result['status'], status)
                self.assertEqual(result['fields'], [])
                state = 'unknown' if completion == 'timeout' else completion
                self.assertEqual(result['sample'], {'rows': 0, 'row_limit': 200, 'grain': 'indexed_observations',
                                                     'completion': state, 'reasons': reasons})

    def test_scope_rejects_unavailable_forms_and_keeps_upstream_errors_private(self):
        for invalid_scope in (
            dict(self.scope, source={'kind': 'saved_report', 'app': 'search', 'name': 'fixture'}),
            dict(self.scope, time_range={'earliest': '-30d', 'latest': 'now'}),
            dict(self.scope, time_range={'earliest': '-1h', 'latest': '2026-01-01'}),
            dict(self.scope, source=dict(self.scope['source'], app='search')),
            dict(self.scope, profile={}),
        ):
            with self.assertRaises(ProviderError) as error:
                parse_inspection(json.dumps(invalid_scope))
            self.assertEqual(error.exception.code, 'invalid_request')
        malformed_search = dict(self.scope, source={'kind': 'spl', 'query': 'search index=fixture_index earliest=-3h'})
        inaccessible_index = dict(self.scope, source={'kind': 'index', 'index': 'unavailable'})
        for scope in (malformed_search, inaccessible_index):
            with patch.object(self.runtime, 'preview') as preview, self.assertRaises(ProviderError) as error:
                inspect_source(self.runtime, scope)
            self.assertEqual(error.exception.code, 'inspection_failed')
            preview.assert_not_called()
        with patch.object(self.runtime, 'preview', side_effect=ProviderError('PRIVATE MESSAGE', 503, 'splunk_transport')), \
                self.assertRaises(ProviderError) as error:
            inspect_source(self.runtime, self.scope)
        self.assertEqual(error.exception.code, 'inspection_unavailable')
        self.assertNotIn('PRIVATE', str(error.exception))
