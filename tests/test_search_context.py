"""Synthetic app-qualified replay, field profiles, scope and ownership boundaries."""
import copy
import json
import sys
import types
import unittest
from pathlib import Path
from urllib.parse import unquote
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from search_context import namespace, results_namespace, report_reference, source_report
from source_service import SourceResolver, preview_query
from search_service import SearchService
from data_service import DataService
from agent_service import AgentService
from studio_contract import apply_changes
from compatibility import feature_profile
from provider_service import ProviderError
from test_reliability_journey import Provider, reply


class ContextRuntime(SearchService):
    def __init__(self):
        super().__init__('fixture_author', 'fixture-session')
        self.calls, self.jobs = [], {}
        self.objects = {}
        for app in ('constellation', 'search'):
            self.objects[(app, 'saved/searches', 'Fixture report')] = {'search': '| makeresults | eval device="a" | lookup rooms device OUTPUT value'}
            self.objects[(app, 'data/transforms/lookups', 'rooms')] = {'type': 'file', 'filename': 'rooms.csv'}
            self.objects[(app, 'configs/conf-macros', 'measure')] = {'definition': 'eval context="'+app+'"'}
        self.rows = {'search': [{'device': 'PRIVATE_SEARCH_VALUE', 'value': '12'}],
                     'constellation': [{'device': 'PRIVATE_LOCAL_VALUE', 'value': '99'}]}
        self.readable = True
    def datasets(self): return {'indexes': [{'name': 'fixture'}]}
    def environment(self): return {'version': '10.4.4', 'features': feature_profile('10.4.4', [])}
    def request(self, path, method='GET', fields=None, optional=False):
        self.calls.append((path, method, fields))
        parts = path.split('/');app = parts[3] if len(parts) > 3 else 'constellation'
        if '/search/v2/jobs' in path:
            if path.endswith('/jobs'):
                sid = 'fixture_'+str(len(self.jobs));self.jobs[sid] = {'app': app, 'query': fields['search']}
                return {'sid': sid}
            if path.endswith('/control'): return {}
            sid = parts[-2] if path.endswith('/results') else parts[-1]
            job = self.jobs[sid]
            if path.endswith('/results'):
                rows = copy.deepcopy(self.rows[job['app']]);return {'fields': [{'name': 'device'}, {'name': 'value'}], 'results': rows}
            return {'entry': [{'acl': {'owner': self.user, 'app': job['app']}, 'content': {'isDone': True, 'isFinalized': False, 'resultCount': '1'}}]}
        resource, _, name = '/'.join(parts[4:]).rpartition('/')
        content = self.objects.get((app, resource, unquote(name))) if self.readable else None
        return {'entry': [] if content is None else [{'name': unquote(name), 'acl': {'app': app}, 'content': copy.deepcopy(content)}]}


def document():
    return {'title': 'Report fixture', 'future': {'keep': True},
            'visualizations': {'metric': {'type': 'splunk.table', 'title': 'Original', 'options': {}, 'dataSources': {'primary': 'chain'}}},
            'dataSources': {'report': {'type': 'ds.savedSearch', 'options': {'ref': 'Fixture report', 'app': 'search'}},
                            'chain': {'type': 'ds.chain', 'options': {'extend': 'report', 'query': '| `measure` | table device value'}}},
            'layout': {'type': 'absolute', 'structure': [{'item': 'metric'}]}}


class ContextTests(unittest.TestCase):
    def test_namespace_and_results_recognition_never_select_another_user(self):
        self.assertEqual(namespace('fixture author', 'search'), '/servicesNS/fixture%20author/search')
        path = namespace('fixture author', 'search')+'/search/v2/jobs/fixture.1/results'
        self.assertEqual(results_namespace('fixture author', path), namespace('fixture author', 'search'))
        for invalid in (path.replace('fixture%20author', 'other'), path+'/control', path.replace('/search/search/', '/../search/'), path.replace('fixture.1', '../fixture')):
            self.assertIsNone(results_namespace('fixture author', invalid))
        for invalid in ('../search', '-', '', None, 'a'*101):
            with self.assertRaises(ProviderError): namespace('fixture_author', invalid)
        for value in ({'ref': 'Fixture', 'app': 'search', 'owner': 'admin'}, {'ref': '', 'app': 'search'}, {'ref': 'x\n'}):
            with self.assertRaises(ProviderError): report_reference(value)
    def test_report_and_chain_run_in_original_app_while_plain_queries_keep_default(self):
        runtime = ContextRuntime();doc = document()
        report = runtime.preview({'sourceRequest': {'sources': doc['dataSources'], 'id': 'chain'}, 'earliest': '-1h'})
        plain = runtime.preview({'query': '| makeresults', 'app': 'search', 'earliest': '-1h'})
        self.assertEqual(report['results'], runtime.rows['search']);self.assertEqual(plain['results'], runtime.rows['constellation'])
        foreign = next(x for x in runtime.jobs.values() if x['app'] == 'search')
        self.assertIn('context="search"', foreign['query']);self.assertNotIn('context="constellation"', foreign['query'])
        self.assertEqual(runtime.namespace, '/servicesNS/fixture_author/constellation')
    def test_scope_reference_is_re_read_and_wrong_prefix_or_language_never_dispatches(self):
        runtime = ContextRuntime();ref = {'ref': 'Fixture report', 'app': 'search'}
        base = runtime.objects[('search', 'saved/searches', 'Fixture report')]['search']
        result = runtime.preview({'report': ref, 'query': base+' | stats count', 'earliest': '-1h'})
        self.assertEqual(result['results'], runtime.rows['search'])
        for extra in ({'query': '| makeresults'}, {'query': base+'oops'}, {'query': base, 'language': 'spl2'}, {'query': base, 'report': dict(ref, owner='admin')}):
            before = len(runtime.jobs)
            with self.assertRaises(ProviderError): runtime.preview(dict({'report': ref}, **extra))
            self.assertEqual(len(runtime.jobs), before)
        runtime.objects[('search', 'saved/searches', 'Fixture report')]['search'] += ' | where value>0'
        with self.assertRaises(ProviderError) as stale: runtime.preview({'report': ref, 'query': base})
        self.assertEqual(stale.exception.code, 'report_scope')
    def test_field_profile_keeps_report_context_but_excludes_returned_values(self):
        runtime = ContextRuntime();ref = {'ref': 'Fixture report', 'app': 'search'}
        profile = DataService(runtime).profile({'report': ref, 'earliest': '-1h'})
        self.assertEqual(profile['scope']['report'], ref);self.assertEqual(profile['sampledRows'], 1)
        self.assertNotIn('PRIVATE_', json.dumps(profile))
        created = next(iter(runtime.jobs.values()));self.assertEqual(created['app'], 'search')
        self.assertTrue(created['query'].endswith('| head 201'))
        self.assertEqual(next(x for x in profile['fields']if x['name']=='value')['coverage']['numeric'], 1)
    def test_inspection_route_derives_selected_report_scope_and_keeps_current_token_values_local(self):
        runtime = ContextRuntime();doc = document()
        runtime.objects[('search', 'saved/searches', 'Fixture report')]['search'] = '| makeresults | eval device=$device|s$'
        doc['defaults'] = {'tokens': {'default': {'device': {'value': 'default-device'}}}}
        request = {'sourceId': 'report', 'definition': doc, 'tokens': {'default': {'device': 'current-device'}},
                   'earliest': '-1h', 'query': 'wrong-global-query', 'report': {'ref': 'wrong', 'app': 'constellation'}}
        before = copy.deepcopy(request);profile = DataService.inspect_request(runtime, request)
        self.assertEqual(request, before);self.assertEqual(profile['scope']['report'], {'ref': 'Fixture report', 'app': 'search'})
        self.assertIn('$device|s$', profile['baseQuery']);self.assertNotIn('current-device', json.dumps(profile))
        self.assertNotIn('definition', profile['scope']);self.assertNotIn('tokens', profile['scope'])
        self.assertTrue(all(job['app'] == 'search' and 'current-device' in job['query'] for job in runtime.jobs.values()))
        runtime.jobs.clear();DataService.inspect_request(runtime, dict(request, tokens=None))
        self.assertTrue(all('default-device' in job['query'] for job in runtime.jobs.values()))
    def test_inspection_rejects_missing_source_document_or_tokens_before_dispatch(self):
        runtime = ContextRuntime();doc = document()
        runtime.objects[('search', 'saved/searches', 'Fixture report')]['search'] = '| makeresults | eval device=$missing|s$'
        for body in ({'sourceId': 'report'}, {'sourceId': 'absent', 'definition': doc}, {'sourceId': 'report', 'definition': doc}, {'definition': [], 'query': '| makeresults'}, {'query': '| makeresults', 'tokens': 'bad'}):
            with self.assertRaises(ProviderError): DataService.inspect_request(runtime, body)
        self.assertEqual(runtime.jobs, {})

    def test_report_backed_table_receipt_uses_resolved_query_and_actual_metadata(self):
        runtime = ContextRuntime();doc = document();data = DataService(runtime, document=doc)
        query, _ = data.resolve_query(doc, 'chain')
        profile = data.profile({'query': query, 'report': {'ref': 'Fixture report', 'app': 'search'}, 'earliest': '-1h'})
        receipt = data.focused_table_receipt(doc, 'metric', profile)
        self.assertEqual(receipt['status'], 'complete');self.assertEqual(receipt['query'], query)
        self.assertEqual({f['name'] for f in receipt['fields']}, {'device', 'value'})
        self.assertNotIn('PRIVATE_', json.dumps(receipt))
        self.assertTrue(all(job['app'] == 'search' for job in runtime.jobs.values()))

    def test_actual_output_validation_rejects_silent_app_context_loss(self):
        runtime = ContextRuntime();doc = document();data = DataService(runtime, document=doc)
        query, language = data.resolve_query(doc, 'chain');profile = data.profile({'query': query, 'report': {'ref': 'Fixture report', 'app': 'search'}, 'earliest': '-1h'})
        self.assertEqual(data.inspect_source(doc, 'chain', doc['dataSources']['chain'], profile)[1]['results'], runtime.rows['search'])
        lost = copy.deepcopy(doc);lost['dataSources']['chain'] = {'type': 'ds.search', 'options': {'query': query, 'queryParameters': {'earliest': '-1h', 'latest': 'now'}}}
        before = len(runtime.jobs)
        with self.assertRaises(ProviderError) as denied: data.inspect_source(lost, 'chain', lost['dataSources']['chain'], profile)
        self.assertEqual(denied.exception.code, 'report_context');self.assertEqual(len(runtime.jobs), before)
    def test_selected_agent_edit_rehydrates_report_scope_and_preserves_unrelated_work(self):
        runtime = ContextRuntime();doc = document();before = copy.deepcopy(doc)
        provider = Provider([reply([{'op': 'set', 'path': '/visualizations/metric/title', 'value': '"Verified"'}])])
        result = AgentService(provider, runtime).assist({'prompt': 'Change only this selected table title to Verified. Preserve its searches and everything else.', 'revision': 0, 'definition': doc, 'selected': 'metric',
            'dataContext': {'query': 'stale local query', 'earliest': '-1h', 'report': {'ref': 'Fixture report', 'app': 'constellation'}}})
        edited = apply_changes(doc, result['changes']);expected = copy.deepcopy(doc);expected['visualizations']['metric']['title'] = 'Verified'
        self.assertEqual(edited, expected);self.assertEqual(doc, before)
        self.assertEqual(result['dataContext']['report']['app'], 'search')
        model_context = json.loads(provider.requests[0]['input'][0]['content'][0]['text'])
        self.assertNotIn('PRIVATE_', json.dumps(model_context));self.assertIn('REPORT SCOPE', provider.requests[0]['instructions'])
        self.assertTrue(all(job['app'] == 'search' for job in runtime.jobs.values()))
        actions = provider.requests[0]['text']['format']['schema']['properties']['changes']['items']['anyOf']
        operations = {op for action in actions for op in action.get('properties', {}).get('op', {}).get('enum', [])}
        self.assertIn('set', operations);self.assertFalse(operations & {'search', 'filter', 'compose', 'menu'})
    def test_tokens_and_scope_checks_precede_dispatch_and_denied_reports_have_no_job(self):
        runtime = ContextRuntime();ref = {'ref': 'Fixture report', 'app': 'search'}
        runtime.objects[('search', 'saved/searches', 'Fixture report')]['search'] = '| makeresults | eval device=$device|s$'
        doc = document();doc['defaults'] = {'tokens': {'default': {'device': {'value': 'safe value'}}}}
        profile = DataService(runtime, document=doc).profile({'report': ref, 'earliest': '-15m'})
        self.assertEqual(profile['scope']['report'], ref)
        self.assertIn('device="safe value"', next(iter(runtime.jobs.values()))['query'])
        runtime.readable = False;before = len(runtime.jobs)
        with self.assertRaises(ProviderError): runtime.preview({'report': ref})
        self.assertEqual(len(runtime.jobs), before)
    def test_report_ancestry_is_bounded_and_does_not_retain_previous_context(self):
        doc = document();runtime = ContextRuntime();resolver = SourceResolver(runtime)
        self.assertEqual(source_report(doc['dataSources'], 'chain')['app'], 'search')
        resolver.resolve(doc['dataSources'], 'chain')
        resolver.resolve({'plain': {'type': 'ds.search', 'options': {'query': '| makeresults'}}}, 'plain')
        self.assertIsNone(resolver.report_reference);self.assertEqual(resolver.report_app, 'constellation')
        doc['dataSources']['chain']['options']['extend'] = 'chain'
        with self.assertRaises(ProviderError): source_report(doc['dataSources'], 'chain')


class ContextTransportTests(unittest.TestCase):
    def test_owned_foreign_results_keep_pending_and_read_only_retry_contract(self):
        rest = types.ModuleType('splunk.rest');rest.simpleRequest = Mock(side_effect=[ConnectionResetError('PRIVATE'), ({'status': 204}, b'')])
        splunk = types.ModuleType('splunk');splunk.rest = rest
        runtime = SearchService('fixture_author', 'fixture-session');path = namespace(runtime.user, 'search')+'/search/v2/jobs/fixture.1/results'
        with patch.dict(sys.modules, {'splunk': splunk, 'splunk.rest': rest}):
            self.assertEqual(runtime.request(path, 'POST', {'count': '201'}), {'resultsPending': True})
        self.assertEqual(rest.simpleRequest.call_count, 2)
        self.assertTrue(all(x.kwargs['sessionKey'] == 'fixture-session' for x in rest.simpleRequest.call_args_list))
        for target in (path.replace('fixture_author', 'other'), path.removesuffix('/fixture.1/results'), path.removesuffix('/results')+'/control'):
            rest.simpleRequest = Mock(side_effect=ConnectionResetError('PRIVATE'))
            with patch.dict(sys.modules, {'splunk': splunk, 'splunk.rest': rest}):
                with self.assertRaises(ProviderError): runtime.request(target, 'POST', {})
            self.assertEqual(rest.simpleRequest.call_count, 1)


if __name__ == '__main__': unittest.main()
