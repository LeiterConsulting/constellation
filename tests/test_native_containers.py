import copy
import json
import unittest
from authoring_actions import compile_actions
from studio_contract import apply_changes
from provider_service import ProviderError
from test_drafts_and_data import blank
from table_sparkline import focused_schema, compile_sparkline


class NativeContainersTests(unittest.TestCase):
    def document(self):
        doc = blank()['definition']
        doc['visualizations'] = {'t': {'type': 'splunk.table', 'future': {'keep': 1}}}
        doc['layout'] = {'type': 'grid', 'structure': [{'item': 't'}]}
        return doc

    def test_known_option_parents_are_explicit_and_browser_can_apply_them(self):
        doc = self.document(); before = copy.deepcopy(doc)
        changes = compile_actions(doc, [{'op': 'set', 'path': '/visualizations/t/options/columnFormat/reading~1trend/sparklineTypes', 'value': '["area"]'}])
        result = apply_changes(doc, changes)
        self.assertEqual(result['visualizations']['t']['options']['columnFormat']['reading/trend']['sparklineTypes'], ['area'])
        self.assertEqual(result['visualizations']['t']['future'], before['visualizations']['t']['future'])
        self.assertEqual(doc, before)

    def test_never_guesses_arrays_assets_unknown_nested_maps_or_replaces_scalars(self):
        doc = self.document(); doc['visualizations']['t']['options'] = {'columnFormat': 'future expression'}
        for path in ('/visualizations/t/options/columnFormat/trend/width', '/visualizations/missing/options/width',
                     '/visualizations/t/options/unknown/0/width', '/visualizations/t/eventHandlers/0/options/token',
                     '/visualizations/t/context/mapping/0/value', '/visualizations/t/options/__proto__/width'):
            with self.subTest(path=path), self.assertRaises(ProviderError): compile_actions(doc, [{'op': 'set', 'path': path, 'value': '180'}])
        self.assertEqual(doc['visualizations']['t']['options']['columnFormat'], 'future expression')

    def test_sequential_new_objects_and_existing_context_are_preserved(self):
        doc = self.document(); doc['visualizations']['t']['context'] = {'unrelated': [{'match': 'old', 'value': 'keep'}]}
        actions = [{'op': 'set', 'path': '/visualizations/t/context/newMap', 'value': '[{"match":"sparkline","value":"area"}]'},
                   {'op': 'set', 'path': '/visualizations/t/options/tableFormat/cellTypes', 'value': '[["SparklineCell"]]'}]
        result = apply_changes(doc, compile_actions(doc, actions))
        self.assertEqual(result['visualizations']['t']['context']['unrelated'], doc['visualizations']['t']['context']['unrelated'])
        self.assertIn('newMap', result['visualizations']['t']['context'])


class SparklineCompilerTests(unittest.TestCase):
    def setUp(self):
        self.doc = NativeContainersTests().document()
        self.doc['dataSources'] = {'s': {'type': 'ds.search', 'options': {'query': 'search index="fixture" | stats sparkline(avg(value),1h) AS trend'}}}
        self.doc['visualizations']['t'].update(dataSources={'primary': 's'}, options={'table': '> primary', 'columnFormat': {'other': {'width': 120}}})
        self.receipt = {'table': 't', 'source': 's', 'status': 'complete', 'fields': [{'name': 'trend', 'cellKind': 'sparkline'}]}
        self.action = {'op': 'tableSparkline', 'id': 't', 'field': 'trend', 'sparklineType': 'area', 'width': 180}

    def test_styling_is_a_native_mapping_for_all_rows_and_preserves_other_work(self):
        before = copy.deepcopy(self.doc)
        changed = apply_changes(self.doc, compile_sparkline(self.action, self.doc, self.receipt))
        column = changed['visualizations']['t']['options']['columnFormat']['trend']
        self.assertTrue(column['sparklineTypes'].startswith('> table | seriesByName("trend") | type() | matchValue('))
        self.assertTrue(column['cellTypes'].startswith('> table |'))
        self.assertEqual(column['width'], 180)
        maps = list(changed['visualizations']['t']['context'].values())
        self.assertIn([{'match': 'sparkline', 'value': 'area'}, {'match': 'array', 'value': 'area'}], maps)
        self.assertEqual(changed['dataSources'], before['dataSources'])
        self.assertEqual(changed['layout'], before['layout'])
        self.assertEqual(changed['visualizations']['t']['options']['columnFormat']['other'], {'width': 120})
        self.assertEqual(self.doc, before)

    def test_unverified_scalar_wrong_target_and_invalid_width_fail(self):
        for action in (dict(self.action, id='other'), dict(self.action, field='other'), dict(self.action, width=10), dict(self.action, width=True)):
            with self.assertRaises(ProviderError): compile_sparkline(action, self.doc, self.receipt)
        scalar = dict(self.receipt, fields=[{'name': 'trend', 'numeric': True}])
        with self.assertRaises(ProviderError): compile_sparkline(self.action, self.doc, scalar)

    def test_focused_schema_pins_explicit_intent_and_leaves_broader_edits_native(self):
        prompt = 'For only this selected table, make trend a sparkline using area styling, with column width to 180 pixels. Do not change any search or filter.'
        schema = focused_schema(prompt, 't', self.doc, self.receipt, [])
        self.assertEqual(schema['properties']['sparklineType']['enum'], ['area'])
        self.assertEqual(schema['properties']['width']['enum'], [180])
        for suffix in (' Also add another column.', ' Rename this table.', ' Add a color threshold.'):
            self.assertIsNone(focused_schema(prompt + suffix, 't', self.doc, self.receipt, []))
        self.assertIsNone(focused_schema(prompt, 't', self.doc, self.receipt, [{'type': 'input_image'}]))


if __name__ == '__main__': unittest.main()
