import copy
import unittest
from sparkline_queries import gap_limit, normalize_sparklines, preserve_gaps
from table_cells import validate_sparkline_request, array_kind
from studio_contract import apply_changes
from provider_service import ProviderError
from test_drafts_and_data import blank
from test_reliability_journey import Provider, Runtime, reply
from agent_service import AgentService
from creation_recipes import compile_recipe


class SparklineQueryTests(unittest.TestCase):
    def setUp(self):
        self.doc = blank()['definition']
        self.query = 'search index="fixture" | stats avg(value) AS mean sparkline(avg(value),1h) AS trend BY device | eval mean=round(mean,2)'
        self.doc['dataSources'] = {'s': {'type': 'ds.search', 'options': {'query': self.query}}}
        self.doc['visualizations'] = {'t': {'type': 'splunk.table', 'dataSources': {'primary': 's'}, 'options': {'table': '> primary | frameBySeriesNames("device","mean","trend")'}}}
        self.doc['layout'] = {'type': 'grid', 'structure': [{'item': 't'}]}
        self.profile = {'preserveSparklineGaps': True, 'nativeTableSparklineGaps': True, 'fields': [{'name': 'value', 'numeric': True}]}

    def test_count_mask_retains_zero_marker_and_bucket_alignment(self):
        result = apply_changes(self.doc, normalize_sparklines(self.doc, {}, self.profile))
        query = result['dataSources']['s']['options']['query']
        self.assertIn('sparkline(count(value),1h) AS ctSpk_', query)
        self.assertIn('>0,mvindex(', query)
        self.assertIn('true(),"null"', query)
        self.assertIn('"##__SPARKLINE__##","##__SPARKLINE__##"', query)
        self.assertIn('| fields - ctSpk_', query)
        self.assertTrue(query.endswith('| eval mean=round(mean,2)'))
        self.assertEqual(normalize_sparklines(result, {}, self.profile), [])
        self.assertEqual(result['visualizations'], self.doc['visualizations'])
        self.assertEqual(self.doc['dataSources']['s']['options']['query'], self.query)
        self.assertEqual(array_kind([['##__SPARKLINE__##', 'null', '0', '12']]), 'sparkline')

    def test_existing_queries_and_older_renderer_preserved(self):
        self.assertEqual(normalize_sparklines(self.doc, copy.deepcopy(self.doc), self.profile), [])
        self.assertEqual(normalize_sparklines(self.doc, {}, dict(self.profile, nativeTableSparklineGaps=False)), [])
        self.assertTrue(gap_limit('Create a table with sparklines', blank()['definition'], {'version': '10.2.8'}, {}))
        for prompt in ('Omit table sparklines', 'Create sparkline(count(value),1h)', 'Allow native sparkline gaps to display zero.'):
            self.assertFalse(gap_limit(prompt, blank()['definition'], {'version': '10.2.8'}, {}))

    def test_deliberate_zero_fill_gets_a_visible_note(self):
        self.assertFalse(preserve_gaps('Allow native sparkline gaps to display zero.', {'requirements': 'Other missing values stay unknown.'}))
        old = {'requirements': 'Native sparkline gaps may display zero.'}
        self.assertTrue(preserve_gaps('Do not fill sparkline gaps with zero.', old))
        self.assertTrue(preserve_gaps('Keep missing sparkline buckets unknown.', old))
        result = apply_changes(self.doc, normalize_sparklines(self.doc, {}, dict(self.profile, preserveSparklineGaps=False)))
        self.assertEqual(result['dataSources'], self.doc['dataSources'])
        self.assertIn('appear as zero', result['visualizations']['t']['description'])

    def test_explicit_sparkline_cannot_disappear_be_hidden_or_become_scalar(self):
        prompt = 'Include sparkline(avg(value),1h) AS trend in the table.'
        receipts = [{'source': 's', 'fields': ['device', 'mean', 'trend'], 'arrayFields': {'trend': 'sparkline'}}]
        validate_sparkline_request(prompt, self.doc, receipts)
        with self.assertRaises(ProviderError): validate_sparkline_request(prompt, self.doc, [dict(receipts[0], arrayFields={})])
        hidden = copy.deepcopy(self.doc);hidden['visualizations']['t']['options']['table'] = '> primary | frameBySeriesNames("device","mean")'
        with self.assertRaises(ProviderError): validate_sparkline_request(prompt, hidden, receipts)
        validate_sparkline_request(prompt, self.doc, [dict(receipts[0], arrayFields={}, status='empty')])
        validate_sparkline_request('Do not include sparkline(avg(value),1h) AS trend.', self.doc, [])

    def test_older_native_gap_limit_needs_no_inference_or_changes(self):
        class Older(Runtime):
            def environment(self): return dict(super().environment(), version='10.2.8')
        provider = Provider([])
        result = AgentService(provider, Older()).assist({'prompt': 'Build two pages with table sparklines.', 'revision': 0, 'definition': blank()['definition'], 'dataContext': blank()['dataContext'], 'suggestionFormat': 'cards'})
        self.assertEqual(result['changes'], [])
        self.assertEqual(result['recovery']['modelCalls'], 0)
        self.assertEqual(len(result['suggestions']), 2)
        self.assertIn('plots missing', result['message'])
        self.assertNotIn('temperature', ' '.join(card['prompt'] for card in result['suggestions']))

    def test_compact_recipe_keeps_array_metric_out_of_scalar_formatting(self):
        recipe = {'kind': 'stats', 'groupBy': 'device', 'metrics': [
            {'function': 'avg', 'field': 'value', 'alias': 'mean'},
            {'function': 'sparkline', 'aggregation': 'avg', 'field': 'value', 'alias': 'trend', 'span': '1h'}]}
        profile = dict(self.profile, scope={'language': 'spl', 'earliest': '-24h'}, fields=self.profile['fields'] + [{'name': 'device', 'numeric': False}])
        query, x, columns = compile_recipe(recipe, 'splunk.table', profile)
        self.assertIn('sparkline(avg(value),1h) AS trend', query)
        self.assertNotIn('round(trend', query)
        self.assertEqual(columns, ['device', 'mean', 'trend'])
        for chart in ('splunk.line', 'splunk.singlevalue'):
            with self.assertRaises(ProviderError): compile_recipe(recipe, chart, profile)
        recipe['metrics'][1]['span'] = '1s'
        with self.assertRaises(ProviderError): compile_recipe(recipe, 'splunk.table', profile)

    def test_repair_profile_refresh_keeps_native_missing_value_policy(self):
        import json
        class Arrays(Runtime):
            def preview(self, body):
                if body.get('fieldDiscovery'): return super().preview(body)
                self.calls.append(body)
                fields, row = ['mean'], {'mean': '3'}
                if 'sparkline(' in body['query']:
                    fields += ['trend'];row['trend'] = ['##__SPARKLINE__##', 'null', '0', '3']
                return {'state': 'complete', 'fields': [{'name': name} for name in fields], 'results': [row]}
        doc = blank()['definition']
        doc['dataSources'] = {}
        source = {'type': 'ds.search', 'options': {'query': 'search index="fixture_index" | stats avg(duration) AS mean', 'queryParameters': {'earliest': '-24h', 'latest': 'now'}}}
        table = {'type': 'splunk.table', 'dataSources': {'primary': 's'}, 'options': {'table': '> primary'}}
        first = [{'op': 'set', 'path': '/dataSources/s', 'value': json.dumps(source)},
                 {'op': 'set', 'path': '/visualizations/t', 'value': json.dumps(table)},
                 {'op': 'set', 'path': '/layout', 'value': '{"type":"grid","structure":[{"item":"t"}]}'}]
        second = [{'op': 'set', 'path': '/dataSources/s/options/query', 'value': json.dumps(source['options']['query'] + ' sparkline(avg(duration),1h) AS trend')}]
        provider = Provider([reply(first), reply(second)])
        result = AgentService(provider, Arrays()).assist({'prompt': 'Build a table including sparkline(avg(duration),1h) AS trend.', 'revision': 0, 'definition': doc, 'dataContext': blank()['dataContext']})
        candidate = apply_changes(doc, result['changes'])
        self.assertEqual(result['recovery']['modelCalls'], 2)
        self.assertTrue(result['dataProfile']['preserveSparklineGaps'])
        self.assertTrue(result['dataProfile']['nativeTableSparklineGaps'])
        self.assertIn('sparkline(count(duration),1h)', candidate['dataSources']['s']['options']['query'])


if __name__ == '__main__': unittest.main()
