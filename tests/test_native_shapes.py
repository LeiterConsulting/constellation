"""Authored shape/permission fixtures; no live results or provider credentials."""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from native_shapes import direct_fields, validate_shape
from studio_features import validate_features
from studio_inventory import authoring_contract, native_types
from data_service import DataService
from provider_service import ProviderError


def frame(names, rows):
    return {'state': 'complete', 'fields': [{'name': name} for name in names], 'results': [dict(zip(names, row)) for row in rows]}


def viz(kind, options=None, aliases=None):
    return {'type': 'splunk.' + kind, 'dataSources': aliases or {'primary': 's'}, 'options': options or {}}


class NativeShapeTests(unittest.TestCase):
    def test_portable_synthetic_native_cases_satisfy_shape_and_version_contracts(self):
        cases = json.loads((Path(__file__).parent / 'fixtures/native_chart_shapes.json').read_text())['cases']
        self.assertEqual(len(cases), 7)
        for case in cases:
            with self.subTest(case=case['id']):
                outputs = {name: frame(source['fields'], source['rows']) for name, source in case['sources'].items()}
                item = {'type': case['type'], 'options': case['options'], 'dataSources': {name: name for name in outputs}}
                validate_shape(item, outputs)
                validate_features({'layout': {}, 'visualizations': {'v': item}}, {}, {'version': case['minimumEnterprise']})

    def test_selector_provenance_handles_order_types_and_auxiliary_sources(self):
        outputs = {'s': frame(['from', 'to', 'weight'], [['A', 'B', '3']]), 'nodes': frame(['id', 'size'], [['A', '8']])}
        aliases = {'primary': 's', 'nodeSource': 'nodes'}
        for binding, expected in [('> primary | seriesByName("weight")', ('s', ['weight'])),
                                  ('> primary | frameBySeriesTypes("string") | seriesByIndex(1)', ('s', ['to'])),
                                  ('> primary | frameBySeriesIndexRange(1) | getField()', ('s', ['to', 'weight'])),
                                  ('> nodeSource | seriesByType("number")', ('nodes', ['size']))]:
            self.assertEqual(direct_fields(binding, aliases, outputs), expected)
        for binding in ('> primary | customDerived("renamed")', '> context | seriesByName("future")', 'weight'):
            self.assertIsNone(direct_fields(binding, aliases, outputs))

    def test_sankey_requires_native_relationship_names_and_numeric_nonnegative_weights(self):
        good = frame(['source', 'target', 'value'], [['A', 'B', 2], ['B', 'C', None], ['C', 'D', 0]])
        validate_shape(viz('sankey'), {'s': good})
        for bad in (frame(['from', 'to', 'value'], [['A', 'B', 2]]), frame(['source', 'target', 'value'], [['A', 'B', -1]]),
                    frame(['source', 'target', 'value'], [['A', 'B', 'not-numeric']]), frame(['source', 'target', 'value'], [[['A'], 'B', 2]])):
            with self.assertRaises(ProviderError): validate_shape(viz('sankey'), {'s': bad})
        validate_shape(viz('sankey', {'linkValues': '> primary | seriesByName("amount")'}), {'s': frame(['source', 'target', 'amount'], [['A', 'B', 3]])})

    def test_parallel_axes_preserve_nulls_and_reject_an_accidental_text_dimension(self):
        good = frame(['category', 'latency', 'load'], [['A', 3, 0], ['B', None, 2]])
        before = copy.deepcopy(good); validate_shape(viz('parallelcoordinates'), {'s': good}); self.assertEqual(good, before)
        with self.assertRaisesRegex(ProviderError, 'numeric'):
            validate_shape(viz('parallelcoordinates'), {'s': frame(['category', 'region', 'load'], [['A', 'north', 2]])})

    def test_pie_and_punchcard_scalar_numeric_roles(self):
        validate_shape(viz('pie'), {'s': frame(['label', 'value'], [['A', 2], ['B', None]])})
        validate_shape(viz('punchcard'), {'s': frame(['x', 'y', 'size'], [['A', 'B', 0]])})
        for kind, result in [('pie', frame(['label', 'value'], [['A', 'invalid']])), ('punchcard', frame(['x', 'y', 'size'], [['A', 'B', -2]]))]:
            with self.assertRaises(ProviderError): validate_shape(viz(kind), {'s': result})

    def test_timeline_custom_epoch_numbers_need_explicit_timestamp_conversion(self):
        item=viz('timeline', {'x': '> primary | seriesByName("start_ms")', 'y': '> primary | seriesByName("lane")', 'duration': '> primary | seriesByName("duration_ms")'})
        with self.assertRaisesRegex(ProviderError, 'ISO timestamp'):
            validate_shape(item, {'s': frame(['start_ms','lane','duration_ms'], [[1700000000000,'A',60000]])})
        item['options']['x']='> primary | seriesByName("start_iso")'
        validate_shape(item, {'s': frame(['start_iso','lane','duration_ms'], [['2023-11-14T22:13:20.000+00:00','A',60000]])})

    def test_network_auxiliary_node_source_is_not_confused_with_link_source(self):
        item = viz('networkGraph', {'source': '> primary | seriesByName("from")', 'target': '> primary | seriesByName("to")',
                                   'nodeValues': '> nodeSource | seriesByName("magnitude")'}, {'primary': 'links', 'nodeSource': 'nodes'})
        outputs = {'links': frame(['from', 'to'], [['A', 'B']]), 'nodes': frame(['id', 'magnitude'], [['A', 8]])}
        validate_shape(item, outputs)
        outputs['nodes'] = frame(['id', 'magnitude'], [['A', 'SECRET_SYNTHETIC_VALUE']])
        with self.assertRaises(ProviderError) as raised: validate_shape(item, outputs)
        self.assertNotIn('SECRET_SYNTHETIC_VALUE', str(raised.exception))

    def test_timeline_requires_native_time_or_iso_and_nonnegative_duration(self):
        item = viz('timeline', {'x': '> primary | seriesByName("_time")', 'y': '> primary | seriesByName("lane")', 'duration': '> primary | seriesByName("duration_ms")'})
        validate_shape(item, {'s': frame(['_time', 'lane', 'duration_ms'], [[1700000000000, 'A', 1000]])})
        with self.assertRaises(ProviderError): validate_shape(item, {'s': frame(['_time', 'lane', 'duration_ms'], [[1700000000000, 'A', -1]])})

    def test_link_order_excludes_unrequested_columns_but_cannot_invent_them(self):
        output = {'s': frame(['stage', 'service', 'region'], [['A', 'B', 'C']])}
        validate_shape(viz('linkgraph', {'fieldOrder': ['region', 'stage']}), output)
        for order in (['stage', 'missing'], ['stage', 'stage'], ['stage']):
            with self.assertRaises(ProviderError): validate_shape(viz('linkgraph', {'fieldOrder': order}), output)

    def test_empty_filtered_outputs_and_unproven_derived_bindings_are_not_invented(self):
        for kind in ('sankey', 'parallelcoordinates', 'pie', 'punchcard', 'timeline', 'networkGraph'):
            validate_shape(viz(kind), {'s': frame([], [])})
        validate_shape(viz('pie', {'value': '> context | derivedValue()'}), {'s': frame(['label', 'value'], [['A', 2]])})

    def test_type_change_revalidates_an_existing_source_and_repairs_atomically(self):
        class Runtime:
            def preview(self, body): return frame(['category', 'region', 'load'], [['A', 'north', 2]])
        old = {'visualizations': {'v': viz('table')}, 'dataSources': {'s': {'type': 'ds.search', 'options': {'query': 'search index=fixture | table category region load', 'queryParameters': {'earliest': '-24h', 'latest': 'now'}}}},
               'layout': {'type': 'absolute', 'structure': [{'item': 'v'}]}}
        candidate = copy.deepcopy(old); candidate['visualizations']['v']['type'] = 'splunk.parallelcoordinates'
        before = copy.deepcopy(candidate)
        with self.assertRaisesRegex(ProviderError, 'numeric'):
            DataService(Runtime()).validate_searches(candidate, old, {'baseQuery': 'search index=fixture', 'scope': {'earliest': '-24h'}, 'fields': []})
        self.assertEqual(candidate, before)


class NativeVersionTests(unittest.TestCase):
    def test_catalog_and_retrieval_use_documented_type_boundaries(self):
        self.assertNotIn('splunk.timeline', native_types({'version': '10.0.4'}))
        self.assertIn('splunk.timeline', native_types({'version': '10.2.8'}))
        self.assertNotIn('splunk.treemap', native_types({'version': '10.4.4'}))
        self.assertIn('splunk.treemap', native_types({'version': '10.6.0'}))
        context = authoring_contract('Create a Sankey and timeline', {}, {'version': '10.4.4'})
        self.assertIn('dataContract', context['relevantOptions']['splunk.sankey'])
        self.assertNotIn('durationUnit', context['relevantOptions']['splunk.timeline']['optionNames'])
        self.assertLess(len(json.dumps(context)), 17000)

    def test_new_future_features_rejected_but_unchanged_imports_survive(self):
        doc = {'layout': {}, 'visualizations': {'v': viz('treemap')}}
        with self.assertRaisesRegex(ProviderError, '10.6'): validate_features(doc, {}, {'version': '10.4.4'})
        imported = copy.deepcopy(doc); doc['visualizations']['v']['title'] = 'New title'
        validate_features(doc, imported, {'version': '10.4.4'})
        for kind, option, minimum in [('timeline', 'durationUnit', '10.6'), ('line', 'trellisSortBy', '10.6'), ('pie', 'legendDisplay', '10.4')]:
            item = {'layout': {}, 'visualizations': {'v': viz(kind, {option: 'seconds' if kind == 'timeline' else 'name' if kind == 'line' else 'right'})}}
            with self.assertRaisesRegex(ProviderError, minimum): validate_features(item, {}, {'version': '10.2.8'})
            validate_features(item, copy.deepcopy(item), {'version': '10.2.8'})

    def test_unsupported_interactions_and_event_names_receive_native_feedback(self):
        for kind, events in [('parallelcoordinates', []), ('sankey', ['cell.click'])]:
            doc = {'layout': {}, 'visualizations': {'v': viz(kind)}}
            doc['visualizations']['v']['eventHandlers'] = [{'type': 'drilldown.setToken', 'options': {'tokens': [{'token': 'chosen', 'value': 'A'}], 'events': events}}]
            with self.assertRaises(ProviderError): validate_features(doc, {}, {'version': '10.4.4'})
            validate_features(doc, copy.deepcopy(doc), {'version': '10.4.4'})


if __name__ == '__main__': unittest.main()
