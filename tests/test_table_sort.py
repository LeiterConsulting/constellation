"""Literal sort compilation stays scoped, private and fully validated."""
import copy
import json
import unittest
from test_drafts_and_data import blank
from test_reliability_journey import Provider, Runtime
from test_search_chart_actions import chart, page, PROFILE
from agent_service import AgentService
from authoring_actions import compile_actions
from studio_contract import apply_changes
from table_sort import exact_table_sort
from provider_service import ProviderError


class TableSortTests(unittest.TestCase):
    def document(self):
        return apply_changes(blank()['definition'], compile_actions(blank()['definition'], [
            {'op': 'search', 'id': 'events', 'pipeline': '| stats count'}, chart('splunk.table', '', ['count']), page()], PROFILE))

    def receipt(self):
        return {'table': 'trend', 'source': 'events', 'status': 'complete', 'fields': [{'name': 'count', 'numeric': True}]}

    def test_exact_sort_changes_only_exclusive_source_query_and_never_mutates_input(self):
        doc = self.document(); before = copy.deepcopy(doc)
        for direction, sign in [('descending', '-'), ('ascending', '+')]:
            plan = exact_table_sort('Sort only this selected summary table by count in ' + direction + ' order. Preserve every column, row link and other element.', 'trend', doc, PROFILE, self.receipt(), [])
            expected = copy.deepcopy(doc); expected['dataSources']['events']['options']['query'] += ' | sort 0 ' + sign + 'count'
            self.assertEqual(apply_changes(doc, plan['changes']), expected)
        self.assertEqual(doc, before)

    def test_ambiguous_compound_unverified_shared_and_non_spl_requests_keep_model_path(self):
        doc = self.document(); receipt = self.receipt()
        for prompt in ['Sort this table.', 'Sort only this table by missing descending.', 'Do not sort only this table by count descending.',
                       'Sort only this table by count descending. Also add a column.', 'Sort only this table by count ascending or descending.',
                       'Sort only this table by count descending. Preserve count but filter missing rows.']:
            self.assertIsNone(exact_table_sort(prompt, 'trend', doc, PROFILE, receipt, []))
        prompt = 'Sort only this table by count descending.'
        for variant in ('shared', 'chain', 'input', 'spl2'):
            changed = copy.deepcopy(doc)
            if variant == 'shared': changed['visualizations']['other'] = copy.deepcopy(changed['visualizations']['trend'])
            if variant == 'chain': changed['dataSources']['child'] = {'type': 'ds.chain', 'options': {'extend': 'events'}}
            if variant == 'input': changed.setdefault('inputs', {})['filter'] = {'dataSources': {'primary': 'events'}}
            if variant == 'spl2': changed['dataSources']['events']['type'] = 'ds.spl2'
            self.assertIsNone(exact_table_sort(prompt, 'trend', changed, PROFILE, receipt, []))
        self.assertIsNone(exact_table_sort(prompt, 'trend', doc, PROFILE, receipt, [{}]))
        self.assertIsNone(exact_table_sort(prompt, 'trend', doc, PROFILE, dict(receipt, status='failed'), []))
        long_compound = 'Sort only this table by count descending. ' + 'Preserve ' * 800 + 'all columns. Add a panel.'
        self.assertIsNone(exact_table_sort(long_compound, 'trend', doc, PROFILE, receipt, []))

    def test_agent_uses_no_inference_but_runs_actual_search_validation(self):
        provider = Provider([]); doc = self.document()
        result = AgentService(provider, Runtime()).assist({'prompt': 'Sort only this selected table by count descending. Preserve every other element.',
                    'selected': 'trend', 'revision': 3, 'definition': doc, 'dataContext': blank()['dataContext']})
        self.assertEqual(provider.requests, []); self.assertEqual(result['recovery']['modelCalls'], 0)
        self.assertTrue(result['searchReceipts']); self.assertGreater(result['recovery']['queryChecks'], 0)
        changed = apply_changes(doc, result['changes']); expected = copy.deepcopy(doc)
        expected['dataSources']['events']['options']['query'] += ' | sort 0 -count'
        self.assertEqual(changed, expected)

    def test_local_plan_does_not_swallow_service_failure_or_invoke_model(self):
        class Interrupted(Runtime):
            def preview(self, body):
                if '| sort 0' in body['query']: raise ProviderError('Interrupted', 503, 'splunk_transport')
                return super().preview(body)
        provider = Provider([])
        with self.assertRaises(ProviderError) as caught:
            AgentService(provider, Interrupted()).assist({'prompt': 'Sort only this selected table by count descending.',
                        'selected': 'trend', 'revision': 0, 'definition': self.document(), 'dataContext': blank()['dataContext']})
        self.assertEqual(caught.exception.code, 'splunk_transport'); self.assertEqual(provider.requests, [])
