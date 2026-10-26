"""Verified formatting and lossless native output, with synthetic fixtures."""
import copy
import json
import unittest
from authoring_actions import compile_actions
from data_service import DataService
from provider_service import ProviderError
from studio_contract import apply_changes
from test_measurement_constraints import PROFILE
from table_format import formatting_only
from test_drafts_and_data import profile_fixture


def document():
    return {'title': 'Sensors', 'visualizations': {'table': {'type': 'splunk.table', 'title': 'Devices',
        'dataSources': {'primary': 'summary'}, 'options': {'table': '> primary | frameBySeriesNames("entity", "mean", "signal", "seen")'},
        'eventHandlers': [{'type': 'drilldown.setToken', 'options': {'fields': ['entity'], 'tokens': [{'token': 'entity', 'key': 'row.entity.value'}]}}]}},
        'dataSources': {'summary': {'type': 'ds.search', 'future': {'keep': True}, 'options': {'query': PROFILE['baseQuery'] + ' | stats avg(temperature_f) AS mean latest(signal) AS signal latest(_time) AS seen BY entity', 'queryParameters': {'earliest': '-24h', 'latest': 'now'}}}},
        'layout': {'type': 'grid', 'structure': [{'item': 'table'}]}}


class Runtime:
    def preview(self, body):
        if body.get('fieldDiscovery'): return profile_fixture(self,body)
        return {'state': 'complete', 'fields': [{'name': f} for f in ('entity', 'mean', 'signal', 'seen')],
                'results': [{'entity': 'fixture_A', 'mean': '20.123', 'signal': '-60.25', 'seen': '1700000000'}]}


class TableFormatTests(unittest.TestCase):
    def test_generation_schema_contains_only_the_verified_selected_numeric_fields(self):
        from table_format import verified_format_action, TABLE_FORMAT_ACTION
        receipt={'table':'table','fields':[{'name':'mean','numeric':True},{'name':'entity','numeric':True},{'name':'seen','numeric':False},{'name':'unverified'},{'name':'bad name','numeric':True}]}
        original=copy.deepcopy(TABLE_FORMAT_ACTION)
        action=verified_format_action(receipt,document())
        self.assertEqual(action['properties']['id']['enum'],['table'])
        self.assertEqual(action['properties']['columns']['items']['properties']['field']['enum'],['mean'])
        self.assertEqual(TABLE_FORMAT_ACTION,original)
        receipt['fields']=[{'name':'seen','numeric':False}]
        with self.assertRaises(ProviderError) as error:verified_format_action(receipt,document())
        self.assertEqual(error.exception.code,'table_output_unverified')
    def test_narrow_formatting_scope_does_not_capture_broader_edits(self):
        self.assertTrue(formatting_only('Polish only this selected summary table: round temperatures to one decimal.', 'table', document()))
        self.assertFalse(formatting_only('Round only this selected table and add the maximum.', 'table', document()))
        self.assertFalse(formatting_only('Create a formatted sensor table.', 'table', document()))

    def test_preservation_clauses_do_not_hide_later_positive_calculations(self):
        prefix = 'Format only this selected summary table: round counts. '
        for clause in ('Do not add absent columns.', "Don't add new fields.", 'Never delete existing columns.'):
            self.assertTrue(formatting_only(prefix + clause, 'table', document()))
            for active in (' Add max(signal) AS peak.', ' But calculate a maximum.', ' Sort by count.'):
                self.assertFalse(formatting_only(prefix + clause + active, 'table', document()))

    def test_misplaced_action_is_rejected_without_rewriting_imported_unknown_options(self):
        from studio_features import validate_features
        doc = document(); changed = copy.deepcopy(doc)
        changed['visualizations']['table']['options']['formatTable'] = {'columns': []}
        with self.assertRaisesRegex(ProviderError, 'not a native table option'):
            validate_features(changed, doc, {})
        imported = copy.deepcopy(changed)
        changed['visualizations']['table']['title'] = 'A new title'
        changed['visualizations']['table']['options']['futureOption'] = {'preserve': True}
        validate_features(changed, imported, {})
        changed['visualizations']['table']['options']['formatTable'] = None
        with self.assertRaisesRegex(ProviderError, 'not a native table option'):
            validate_features(changed, imported, {})

    def test_output_metadata_has_types_and_no_values_and_compiler_preserves_upstream(self):
        doc = document(); before = copy.deepcopy(doc)
        service = DataService(Runtime())
        receipt = service.focused_table_receipt(doc, 'table', PROFILE)
        self.assertNotIn('fixture_A', json.dumps(receipt)); self.assertNotIn('20.123', json.dumps(receipt))
        action = {'op': 'formatTable', 'id': 'table', 'columns': [
            {'field': 'mean', 'kind': 'number', 'precision': 1}, {'field': 'signal', 'kind': 'number', 'precision': 0}, {'field': 'seen', 'kind': 'datetime', 'precision': 0}]}
        changed = apply_changes(doc, compile_actions(doc, [action], PROFILE, receipt))
        self.assertEqual(changed['visualizations'], doc['visualizations'])
        self.assertEqual(changed['layout'], doc['layout'])
        source = changed['dataSources']['summary']; query = source['options'].pop('query')
        original = copy.deepcopy(doc['dataSources']['summary']); original['options'].pop('query')
        self.assertEqual(source, original)
        self.assertTrue(query.startswith(doc['dataSources']['summary']['options']['query'] + ' | eval '))
        self.assertIn('mean=round(mean,1), signal=round(signal,0), seen=strftime(seen,', query)
        self.assertEqual(doc, before)

    def test_absent_nonnumeric_navigation_fields_and_rebuilt_queries_are_rejected(self):
        doc = document(); receipt = DataService(Runtime()).focused_table_receipt(doc, 'table', PROFILE)
        for field in ('missing', 'entity', 'mean | stats count'):
            with self.subTest(field=field), self.assertRaises(ProviderError):
                compile_actions(doc, [{'op': 'formatTable', 'id': 'table', 'columns': [{'field': field, 'kind': 'number', 'precision': 1}]}], PROFILE, receipt)
        changed = copy.deepcopy(doc); changed['dataSources']['summary']['options']['query'] += ' | stats count'
        with self.assertRaisesRegex(ProviderError, 'Do not rebuild'):
            compile_actions(changed, [{'op': 'formatTable', 'id': 'table', 'columns': [{'field': 'mean', 'kind': 'number', 'precision': 1}]}], PROFILE, receipt)

    def test_changed_search_revalidates_unchanged_bindings_and_names_only_missing_fields(self):
        doc = document(); previous = copy.deepcopy(doc)
        doc['dataSources']['summary']['options']['query'] += ' | fields - mean'
        class Missing(Runtime):
            def preview(self, body):
                if body.get('fieldDiscovery'): return super().preview(body)
                result = super().preview(body)
                result['fields'] = [f for f in result['fields'] if f['name'] != 'mean']
                for row in result['results']: row.pop('mean')
                return result
        with self.assertRaisesRegex(ProviderError, 'missing output fields mean\\.') as caught:
            DataService(Missing()).validate_searches(doc, previous, PROFILE)
        self.assertNotIn('missing output fields entity', str(caught.exception))
        self.assertIn('preserve the verified aggregation and aliases', str(caught.exception))
        self.assertIn('NEW metric, add its calculation', str(caught.exception))
        self.assertNotIn('Use formatTable', str(caught.exception))

    def test_invalid_format_proposal_recovers_with_verified_columns_without_rebuilding_query(self):
        from agent_service import AgentService
        from test_reliability_journey import Provider, reply
        from compatibility import feature_profile
        from test_measurement_constraints import GOAL
        class FullRuntime(Runtime):
            def environment(self): return {'version': '10.2.8', 'features': feature_profile('10.2.8', [])}
            def datasets(self): return {'indexes': [{'name': 'fixture_index'}]}
            def execute(self, query, earliest):
                return {'results': [{'field': f, 'count': '20', 'numeric_count': '20'} for f in ('temperature_f', 'signal')]}
        doc = document(); before = copy.deepcopy(doc)
        provider = Provider([reply([{'op': 'set', 'path': '/visualizations/table/options/formatTable',
                                    'value': json.dumps({'id': 'table', 'columns': [{'field': 'seen', 'kind': 'datetime', 'precision': 0}]})}]),
                             reply([{'op': 'formatTable', 'id': 'table', 'columns': [{'field': 'mean', 'kind': 'number', 'precision': 1}, {'field': 'seen', 'kind': 'datetime', 'precision': 0}]}])])
        result = AgentService(provider, FullRuntime()).assist({'prompt': 'Polish only this selected summary table: round temperatures to one decimal and format last seen as a date. Do not add absent columns.',
            'revision': 0, 'definition': doc, 'selected': 'table', 'brief': {'purpose': GOAL}, 'dataContext': PROFILE['scope']})
        self.assertEqual(result['recovery']['modelCalls'], 2)
        context = json.loads(provider.requests[0]['input'][0]['content'][0]['text'])
        self.assertEqual(provider.requests[0]['text']['format']['schema']['properties']['changes']['items']['properties']['op']['enum'], ['formatTable'])
        self.assertEqual(provider.requests[0]['text']['format']['schema']['properties']['changes']['items']['properties']['columns']['items']['properties']['field']['enum'], ['mean','seen','signal'])
        self.assertTrue(context['focusedSourceReceipt']['fields'][1]['numeric'])
        self.assertEqual(context['focus']['id'], 'table')
        self.assertIn('150', json.dumps(context['dashboardBrief']))
        self.assertFalse(set(context).intersection({'definition', 'catalog', 'nativeFeatures', 'retrievedGuidance'}))
        self.assertLess(len(provider.requests[0]['instructions']), 2000)
        self.assertNotIn('COMPLETE THE ORIGINAL GOAL', provider.requests[0]['instructions'])
        self.assertNotIn('20.123', json.dumps(provider.requests))
        self.assertIn('formatTable', result['validationNotes'][0])
        changed = apply_changes(doc, result['changes'])
        self.assertEqual(changed['visualizations'], doc['visualizations'])
        self.assertIn('seen=strftime(seen,', changed['dataSources']['summary']['options']['query'])
        self.assertIn('stats avg(temperature_f) AS mean latest(signal) AS signal latest(_time) AS seen BY entity', changed['dataSources']['summary']['options']['query'])
        self.assertIn('temperature_f<=150', changed['dataSources']['summary']['options']['query'])
        self.assertEqual(doc, before)

    def test_creation_does_not_offer_an_existing_table_only_action(self):
        from agent_service import AgentService
        from test_reliability_journey import Provider, Runtime, reply
        from test_drafts_and_data import blank
        provider = Provider([reply([{'op': 'dashboard', 'title': 'Sensors', 'description': 'Sensor readings'}])])
        AgentService(provider, Runtime()).assist({'prompt': 'Build a sensor dashboard', 'revision': 0,
            'definition': blank()['definition'], 'dataContext': blank()['dataContext']})
        actions = provider.requests[0]['text']['format']['schema']['properties']['changes']['items']['anyOf']
        self.assertFalse(any(action['properties']['op']['enum'] == ['formatTable'] for action in actions))


    def test_broader_selected_table_edit_does_not_offer_format_action_and_repairs_ignored_schema(self):
        from agent_service import AgentService
        from test_reliability_journey import Provider, reply
        from compatibility import feature_profile
        class FullRuntime(Runtime):
            def environment(self): return {'version': '10.2.8', 'features': feature_profile('10.2.8', [])}
            def datasets(self): return {'indexes': [{'name': 'fixture_index'}]}
            def execute(self, query, earliest):
                return {'results': [{'field': f, 'count': '20', 'numeric_count': '20'} for f in ('temperature_f', 'signal')]}
        provider = Provider([reply([{'op': 'formatTable', 'id': 'table', 'columns': [{'field': 'mean', 'kind': 'number', 'precision': 1}]}]), reply([])])
        result = AgentService(provider, FullRuntime()).assist({'prompt': 'Add a new peak metric to this selected table.', 'revision': 0,
            'definition': document(), 'selected': 'table', 'dataContext': PROFILE['scope']})
        actions = provider.requests[0]['text']['format']['schema']['properties']['changes']['items']['anyOf']
        self.assertFalse(any(action['properties']['op']['enum'] == ['formatTable'] for action in actions))
        context = json.loads(provider.requests[0]['input'][0]['content'][0]['text'])
        self.assertIn('unavailable', context['tableEditing'])
        self.assertEqual(result['recovery']['modelCalls'], 2)
        self.assertIn('broader edit', result['validationNotes'][0])
