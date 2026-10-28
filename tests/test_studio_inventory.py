"""Synthetic contracts; these do not qualify native rendering or provider skill."""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from studio_inventory import INVENTORY, authoring_contract, native_types
from knowledge_service import retrieve_guidance
from studio_features import validate_features
from studio_contract import apply_changes
from table_cells import array_kind, validate_sparkline_output
from table_format import formatting_only
from compact_creation import compact_goal
from provider_service import ProviderError
from test_drafts_and_data import blank, DataRuntime
from test_reliability_journey import Provider, Runtime, reply
from agent_service import AgentService
from data_service import DataService
from authoring_budget import AuthoringBudget


class StudioInventoryTests(unittest.TestCase):
    def test_inventory_has_each_embedded_asset_and_gates_newer_types(self):
        self.assertEqual(len(INVENTORY['visualizations']), 29)
        self.assertEqual(len(INVENTORY['inputs']), 6)
        self.assertEqual(len(INVENTORY['eventHandlers']), 6)
        self.assertNotIn('splunk.networkGraph', native_types({'version': '10.2.8'}))
        self.assertIn('splunk.networkGraph', native_types({'version': '10.4.4'}))
        self.assertIn('abslayout.line', native_types({'version': '10.2.8'}))
        self.assertNotIn('splunk.processtree', INVENTORY['visualizations'])

    def test_focus_and_durable_requirements_select_native_contracts(self):
        doc = {'visualizations': {'selected': {'type': 'splunk.table'}, 'other': {'type': 'splunk.line'}}}
        context = authoring_contract('Refine the selected element', doc, {'version': '10.4.4'},
                                     {'requirements': 'Use sparkline columns'}, {'id': 'selected'})
        options = context['relevantOptions']['splunk.table']
        self.assertIn('columnFormat', options['optionNames'])
        self.assertIn('SparklineCell', json.dumps(options['optionShapes']))
        self.assertLess(len(json.dumps(context)), 17000)
        old = authoring_contract('sparkline', doc, {'version': '10.2.8'}, focus={'id': 'selected'})
        self.assertNotIn('sparklineNullValueDisplay', json.dumps(old['relevantOptions']))
        found = retrieve_guidance('Refine it', doc, {'version': '10.2.8'}, brief={'requirements': 'Use sparkline columns'})
        self.assertIn('table-sparklines', [item['id'] for item in found])

    def test_compact_supports_native_sparkline_queries_but_not_advanced_cell_styling(self):
        self.assertTrue(compact_goal({'request': 'Build two pages with table sparklines'}))
        self.assertTrue(compact_goal({'request': 'Build two pages with native table sparkline gaps allowed to display zero.'}))
        self.assertTrue(compact_goal({'request': 'Build two pages', 'dashboardBrief': {'requirements': 'Use sparkline columns'}}))
        self.assertFalse(compact_goal({'request': 'Build two pages with area sparklines'}))
        self.assertFalse(compact_goal({'request': 'Build two pages', 'dashboardBrief': {'requirements': 'Use columnFormat custom cellTypes'}}))
        for prompt in ('Format only this selected table with sparklines.', 'Format only this selected table: columnFormat background colors.'):
            self.assertFalse(formatting_only(prompt, 't', {'visualizations': {'t': {'type': 'splunk.table'}}}))

    def test_every_registered_asset_round_trips_unknown_unrelated_properties(self):
        for kind in INVENTORY['visualizations']:
            original = blank()['definition']
            original['visualizations'] = {'target': {'type': kind, 'options': {}, 'future': {'keep': [1, 2]}}}
            original['layout'] = {'type': 'grid', 'structure': [{'item': 'target'}]}
            before = copy.deepcopy(original)
            candidate = apply_changes(original, [{'op': 'set', 'path': '/visualizations/target/title', 'value': '"Refined"'}])
            validate_features(candidate, original, {'version': '10.4.4'})
            self.assertEqual(candidate['visualizations']['target']['future'], original['visualizations']['target']['future'])
            self.assertEqual(original, before)

    def test_guidance_survives_all_specialized_budget_paths(self):
        from agent_service import SCHEMA
        for flag in ('formattingOnly', 'rowNavigationOnly', 'routeOnly', 'buttonRouteOnly', 'pageMetadataOnly', 'calculationOnly', 'tableSparklineOnly'):
            context = {'request': 'Refine this element', 'canvasState': 'dashboard', 'history': [],
                       'dashboardBrief': {'requirements': 'Keep the existing navigation'},
                       'retrievedGuidance': [{'id': 'native-interactions', 'text': 'Use native tokenNames arrays'}], flag: True}
            request = {'instructions': 'Fixture', 'text': {'format': {'schema': copy.deepcopy(SCHEMA)}}, 'input': [{'content': [{'type': 'input_text', 'text': 'Fixture'}]}]}
            AuthoringBudget({'provider': 'ollama'}, context).prepare(request, blank()['definition'])
            actual = json.loads(request['input'][0]['content'][0]['text'])
            self.assertEqual(actual['retrievedGuidance'], context['retrievedGuidance'])
            self.assertEqual(actual['dashboardBrief'], context['dashboardBrief'])

    def test_native_map_and_input_channels_validate_actual_output(self):
        data = DataService(DataRuntime()); profile = data.profile({'index': 'fixture_index'})
        source = {'type': 'ds.search', 'options': {'query': 'search index="fixture_index" | stats count', 'queryParameters': {'earliest': '-24h', 'latest': 'now'}}}
        for root, kind, options in [('visualizations', 'splunk.map', {'latitude': '> primary | seriesByName("absent")'}),
                                    ('inputs', 'input.dropdown', {'items': '> primary | frameBySeriesNames("absent")'})]:
            doc = blank()['definition']; doc['dataSources'] = {'source': source}
            doc[root] = {'item': {'type': kind, 'dataSources': {'primary': 'source'}, 'options': options}}
            doc['layout'] = {'type': 'grid', 'structure': [{'item': 'item'}]}
            with self.assertRaisesRegex(ProviderError, 'missing actual source fields'):
                data.validate_searches(doc, {}, profile)

    def test_decorative_connector_needs_placement_but_no_search(self):
        data = DataService(DataRuntime()); profile = data.profile({'index': 'fixture_index'})
        doc = blank()['definition']
        doc['visualizations']['connector'] = {'type': 'abslayout.line', 'options': {'toArrow': True}}
        doc['layout'] = {'type': 'grid', 'structure': [{'item': 'connector'}]}
        self.assertEqual(data.validate_searches(doc, {}, profile), [])
        doc['layout']['structure'] = []
        with self.assertRaisesRegex(ProviderError, 'Place each new visualization'): data.validate_searches(doc, {}, profile)

    def test_decorative_icon_keeps_metric_and_placement_guards(self):
        data = DataService(DataRuntime()); profile = data.profile({'index': 'fixture_index'})
        doc = blank()['definition']
        doc['visualizations']['icon'] = {'type': 'splunk.singlevalueicon', 'options': {'showValue': False, 'icon': 'splunk-enterprise-kvstore://fixture'}}
        doc['layout'] = {'type': 'absolute', 'structure': [{'item': 'icon'}]}
        self.assertEqual(data.validate_searches(doc, {}, profile), [])
        for show in (True, 'false', None):
            doc['visualizations']['icon']['options']['showValue'] = show
            with self.assertRaisesRegex(ProviderError, 'Bind visualization'): data.validate_searches(doc, {}, profile)
        doc['visualizations']['icon']['options']['showValue'] = False
        doc['layout']['structure'] = []
        with self.assertRaisesRegex(ProviderError, 'Place each new visualization'): data.validate_searches(doc, {}, profile)


class NativeTableCellTests(unittest.TestCase):
    def document(self, config):
        doc = blank()['definition']
        doc['visualizations']['table'] = {'type': 'splunk.table', 'options': config}
        doc['layout'] = {'type': 'grid', 'structure': [{'item': 'table'}]}
        return doc

    def test_dimension_enum_and_version_feedback_preserves_untouched_imports(self):
        for config in ({'columnFormat': {'trend': {'cellTypes': 'SparklineCell'}}},
                       {'tableFormat': {'cellTypes': ['SparklineCell']}},
                       {'columnFormat': {'trend': {'cellTypes': ['sparkline']}}},
                       {'columnFormat': {'trend': {'sparklineTypes': ['bar']}}}):
            doc = self.document(config)
            with self.assertRaises(ProviderError): validate_features(doc, {}, {'version': '10.4.4'})
            validate_features(doc, copy.deepcopy(doc), {'version': '10.2.8'})
        for config in ({'columnFormat': {'trend': {'cellTypes': ['SparklineCell'], 'sparklineTypes': ['area']}}},
                       {'tableFormat': {'cellTypes': [['SparklineCell']]}}):
            validate_features(self.document(config), {}, {'version': '10.2.8'})
        doc = self.document({'columnFormat': {'trend': {'sparklineNullValueDisplay': 'connect'}}})
        with self.assertRaisesRegex(ProviderError, '10.4'): validate_features(doc, {}, {'version': '10.2.8'})
        validate_features(doc, {}, {'version': '10.4.4'})

    def test_actual_arrays_not_scalar_statistics_and_no_values_in_receipts(self):
        self.assertEqual(array_kind([['##__SPARKLINE__##', '1', None, '2']]), 'sparkline')
        self.assertEqual(array_kind([[1, None, 2]]), 'numericArray')
        self.assertEqual(array_kind([['label', 'other']]), 'array')
        self.assertIsNone(array_kind(['12', '13']))
        table = {'options': {'columnFormat': {'trend': {'cellTypes': ['SparklineCell']}}}}
        validate_sparkline_output(table, ['trend'], [{'trend': ['##__SPARKLINE__##', '1', None, '2']}])
        validate_sparkline_output(table, ['trend'], [{'trend': None}])
        for fields, rows in [(['trend'], [{'trend': 2}]), (['trend'], [{'trend': ['text']}]), (['other'], [{'other': 2}])]:
            with self.assertRaises(ProviderError): validate_sparkline_output(table, fields, rows)

    def test_agent_repairs_native_cell_shape_without_losing_columns_or_navigation(self):
        class Arrays(Runtime):
            def preview(self, body):
                if body.get('fieldDiscovery'): return super().preview(body)
                self.calls.append(body)
                return {'state': 'complete', 'fields': [{'name': name} for name in ('host', 'mean', 'trend')],
                        'results': [{'host': 'SYNTHETIC_HOST', 'mean': '2', 'trend': ['##__SPARKLINE__##', '1', None, '3']}]}
        original = blank()['definition']
        original['dataSources'] = {'source': {'type': 'ds.search', 'options': {'query': 'search index="fixture_index" | stats avg(duration) AS mean sparkline(avg(duration),1h) AS trend BY host', 'queryParameters': {'earliest': '-24h', 'latest': 'now'}}}}
        original['visualizations'] = {'table': {'type': 'splunk.table', 'title': 'Hosts', 'dataSources': {'primary': 'source'}, 'options': {'table': '> primary | frameBySeriesNames("host", "mean", "trend")'}, 'future': {'keep': True}}}
        original['layout'] = {'type': 'grid', 'structure': [{'item': 'table'}]}
        first = {'op': 'set', 'path': '/visualizations/table/options/columnFormat', 'value': json.dumps({'trend': {'cellTypes': 'SparklineCell'}})}
        second = dict(first, value=json.dumps({'trend': {'cellTypes': ['SparklineCell'], 'sparklineTypes': ['area']}}))
        provider = Provider([reply([first]), reply([second])])
        result = AgentService(provider, Arrays()).assist({'prompt': 'Format only this selected table with a native sparkline in trend.', 'revision': 0, 'definition': original, 'selected': 'table', 'dataContext': blank()['dataContext']})
        candidate = apply_changes(original, result['changes'])
        self.assertEqual(result['recovery']['modelCalls'], 2)
        self.assertEqual(candidate['dataSources'], original['dataSources'])
        self.assertEqual(candidate['layout'], original['layout'])
        self.assertEqual(candidate['visualizations']['table']['options']['table'], original['visualizations']['table']['options']['table'])
        context = json.loads(provider.requests[0]['input'][0]['content'][0]['text'])
        self.assertEqual(next(f for f in context['focusedSourceReceipt']['fields'] if f['name'] == 'trend')['cellKind'], 'sparkline')
        self.assertNotIn('SYNTHETIC_HOST', json.dumps(provider.requests))
        self.assertIn('table-sparklines', [item['id'] for item in context['retrievedGuidance']])


if __name__ == '__main__': unittest.main()
