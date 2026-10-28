"""Synthetic report references; no native credentials or provider calls."""
import copy
import unittest
from unittest.mock import patch
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from source_service import SourceResolver, preview_query, REPORT_WARNING
from search_service import SearchService
from provider_service import ProviderError
from data_service import DataService


class Reports(SearchService):
    def __init__(self):
        super().__init__('ordinary_author', 'synthetic-session')
        self.calls = []
        self.query = 'search index="fixture" | stats count AS total'
        self.entry = {'name': 'Fixture / report', 'acl': {'app': 'search', 'owner': 'another_author'}, 'content': {'is_scheduled': '1', 'dispatchAs': 'owner'}}
    def request(self, path, method='GET', fields=None, optional=False):
        self.calls.append((path, method, fields))
        result = copy.deepcopy(self.entry)
        result['content']['search'] = self.query
        return {'entry': [result]}
    def execute(self, query, earliest='-15m'):
        self.calls.append(('bounded-current-user', query, earliest))
        return {'warning': '', 'results': []}


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Reports()
        self.sources = {'report': {'type': 'ds.savedSearch', 'options': {'ref': 'Fixture / report', 'app': 'search'}},
                        'chain': {'type': 'ds.chain', 'options': {'extend': 'report', 'query': '| eval total=total+1'}}}

    def test_current_user_read_exact_reference_and_chain_without_owner_dispatch(self):
        resolver = SourceResolver(self.runtime)
        query, language = resolver.resolve(self.sources, 'chain')
        self.assertTrue(query.endswith('| eval total=total+1')); self.assertEqual(language, 'spl')
        self.assertEqual(self.runtime.calls, [('/servicesNS/ordinary_author/search/saved/searches/Fixture%20%2F%20report', 'GET', None)])
        resolver.resolve(self.sources, 'report'); self.assertEqual(len(self.runtime.calls), 1)
        SourceResolver(self.runtime).resolve(self.sources, 'report'); self.assertEqual(len(self.runtime.calls), 2)

    def test_replay_is_guarded_and_labelled_not_a_cached_report_result(self):
        body = {'sourceRequest': {'sources': self.sources, 'id': 'chain', 'tokens': {'default': {}}}, 'earliest': '-1h'}
        result = self.runtime.preview(body)
        self.assertEqual(result['warning'], REPORT_WARNING)
        self.assertEqual(self.runtime.calls[-1][0], 'bounded-current-user')
        self.assertEqual(self.runtime.calls[-1][2], '-1h')
        for unsafe in ('| collect index=fixture', '| savedsearch privileged', '| delete', '| inputlookup fixture'):
            self.runtime.query = unsafe
            with self.assertRaises(ProviderError): self.runtime.preview(body)
            self.assertEqual(self.runtime.calls[-1][1], 'GET')

    def test_job_start_uses_same_guards_and_cancellation_contract(self):
        with patch('preview_jobs.PreviewJobs.start', return_value={'state': 'running', 'handle': 'synthetic'}) as start:
            result = self.runtime.job({'action': 'start', 'sourceRequest': {'sources': self.sources, 'id': 'report'}, 'earliest': '-24h'})
            self.assertEqual(result['sourceWarning'], REPORT_WARNING)
            self.assertEqual(start.call_args.args[1], '-24h')
            self.assertIn('index="fixture"', start.call_args.args[0])

    def test_denied_mismatched_disabled_and_invalid_references_fail_closed(self):
        for mutation in ({'name': 'wrong'}, {'acl': {'app': 'other'}}, {'content': {'disabled': '1'}}):
            self.runtime.entry.update(mutation)
            with self.assertRaises(ProviderError): SourceResolver(self.runtime).resolve(self.sources, 'report')
        for app in ('../search', 'search?owner=admin', 'https://example.com', 'a/b'):
            sources = copy.deepcopy(self.sources); sources['report']['options']['app'] = app
            with self.assertRaises(ProviderError): SourceResolver(self.runtime).resolve(sources, 'report')
        with self.assertRaises(ProviderError): preview_query(self.runtime, {'sourceRequest': {'sources': self.sources, 'id': 'report', 'owner': 'admin'}})

    def test_tokens_resolved_after_report_read_and_injection_guarded(self):
        self.runtime.query = 'search index="fixture" entity=$entity|s$'
        query, _, _ = preview_query(self.runtime, {'sourceRequest': {'sources': self.sources, 'id': 'report', 'tokens': {'default': {'entity': 'x" | collect index=bad'}}}})
        self.assertIn('entity="x\\" | collect index=bad"', query)
        self.runtime.preview({'sourceRequest': {'sources': self.sources, 'id': 'report', 'tokens': {'default': {'entity': 'A'}}}})
        self.assertIn('entity="A"', self.runtime.calls[-1][1])
        self.runtime.query = 'search index="fixture" entity=$entity$'
        with self.assertRaises(ProviderError): self.runtime.preview({'sourceRequest': {'sources': self.sources, 'id': 'report', 'tokens': {'default': {'entity': 'A | delete'}}}})
        with self.assertRaises(ProviderError) as missing:
            self.runtime.preview({'sourceRequest': {'sources': self.sources, 'id': 'report', 'tokens': {'default': {'entity': None}}}})
        self.assertEqual(missing.exception.code, 'preview_token_unset')

    def test_data_validation_resolves_reports_without_modifying_native_definition(self):
        doc = {'dataSources': copy.deepcopy(self.sources)}; before = copy.deepcopy(doc)
        data = DataService(self.runtime)
        self.assertIn('stats count', data.resolve_query(doc, 'report')[0])
        self.assertEqual(doc, before)
        self.sources['chain']['options']['extend'] = 'chain'
        with self.assertRaises(ProviderError): SourceResolver(self.runtime).resolve(self.sources, 'chain')

    def test_changed_report_reference_checks_resolved_population_and_wildcards(self):
        self.runtime.query = 'search index="fixture" | stats count AS total'
        self.runtime.preview = lambda body: {'fields': [{'name': 'total'}], 'results': [{'total': '2'}], 'state': 'complete'}
        doc = {'layout': {'type': 'grid', 'structure': [{'item': 'table'}]}, 'dataSources': {'report': self.sources['report']},
               'visualizations': {'table': {'type': 'splunk.table', 'dataSources': {'primary': 'report'}, 'options': {'table': '> primary'}}}}
        old = copy.deepcopy(doc); old['dataSources']['report']['options']['ref'] = 'Previous fixture'
        profile = {'baseQuery': 'search index="fixture"', 'scope': {'earliest': '-24h'}, 'fields': []}
        with patch('data_service.validate_populations') as populations, patch('data_service.validate_wildcard_filters') as wildcard:
            DataService(self.runtime, independent_populations=True).validate_searches(doc, old, profile)
            populations.assert_called_once_with(self.runtime.query, profile)
            wildcard.assert_called_once_with(self.runtime.query, doc)

    def test_imported_report_can_be_profiled_from_selection_without_manual_spl(self):
        from test_reliability_journey import Provider, Runtime, reply
        from agent_service import AgentService
        class Imported(Runtime):
            user = 'fixture_author'
            def request(self, path, optional=False):
                self.report_path = path
                return {'entry': [{'name': 'Fixture report', 'acl': {'app': 'search'}, 'content': {'search': 'search index="fixture_index" | stats count'}}]}
        doc = {'title': 'Imported report', 'visualizations': {'metric': {'type': 'splunk.singlevalue', 'dataSources': {'primary': 'report'}}},
               'dataSources': {'report': {'type': 'ds.savedSearch', 'options': {'app': 'search', 'ref': 'Fixture report'}}},
               'layout': {'type': 'absolute', 'structure': [{'item': 'metric'}]}}
        before = copy.deepcopy(doc)
        provider = Provider([reply([{'op': 'set', 'path': '/visualizations/metric/title', 'value': '"Events"'}])])
        runtime = Imported(); result = AgentService(provider, runtime).assist({'prompt': 'Give this a clearer title', 'revision': 0, 'definition': doc, 'selected': 'metric'})
        self.assertEqual(result['dataContext']['query'], 'search index="fixture_index" | stats count')
        self.assertIn('Report preview reruns', result['dataProfile']['note'])
        self.assertIn('/servicesNS/fixture_author/search/saved/searches/', runtime.report_path)
        self.assertEqual(doc, before)
