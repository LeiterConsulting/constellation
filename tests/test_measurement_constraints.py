"""Authored metadata and queries, without indexed values or provider access."""
import copy
import json
import unittest
from authoring_actions import compile_actions
from measurement_constraints import normalize_measurements, temperature_constraints, mask_command
from provider_service import ProviderError
from studio_contract import apply_changes

PROFILE = {'scope': {'index': 'fixture_index', 'language': 'spl', 'earliest': '-24h'},
           'baseQuery': 'search index="fixture_index"',
           'fields': [{'name': 'temperature_f', 'numeric': True}, {'name': 'signal', 'numeric': True}]}
GOAL = 'Temperatures are Fahrenheit: exclude readings above 150 F from temperature calculations, but retain signal measurements independently.'


class MeasurementConstraintTests(unittest.TestCase):
    def profile(self, prompt=GOAL):
        return dict(PROFILE, measurementConstraints=temperature_constraints(prompt, {}, PROFILE))

    def test_explicit_units_verified_fields_and_latest_requirement(self):
        brief = {'purpose': GOAL, 'requirements': ''}
        self.assertEqual(temperature_constraints('Round this table', brief, PROFILE), [{'field': 'temperature_f', 'maximum': 150, 'unit': 'F'}])
        self.assertEqual(temperature_constraints('Exclude temperatures over 140.5°F.', brief, PROFILE)[0]['maximum'], 140.5)
        self.assertEqual(temperature_constraints('Remove the temperature cutoff.', brief, PROFILE), [])
        self.assertEqual(temperature_constraints('Exclude readings above 150', {}, PROFILE), [])
        self.assertEqual(temperature_constraints(GOAL, {}, dict(PROFILE, fields=[{'name': 'temperature_f', 'numeric': False}])), [])
        self.assertEqual(temperature_constraints(GOAL, {}, dict(PROFILE, scope={'language': 'spl2'})), [])
        self.assertEqual(temperature_constraints('Do not exclude temperatures over 150 F.', {}, PROFILE), [])

    def test_mask_precedes_every_aggregate_and_retains_other_events(self):
        for aggregate in ('avg', 'latest', 'earliest', 'min', 'max', 'sum', 'median', 'stdev', 'count'):
            with self.subTest(aggregate=aggregate):
                query = PROFILE['baseQuery'] + ' | stats ' + aggregate + '(temperature_f) AS result latest(signal) AS signal BY entity'
                doc = {'dataSources': {'summary': {'type': 'ds.search', 'options': {'query': query, 'future': 'retained'}}}}
                changes = normalize_measurements(doc, {}, self.profile())
                normalized = json.loads(changes[0]['value'])
                self.assertIn('| eval temperature_f=if(temperature_f<=150,temperature_f,null()) | stats', normalized)
                self.assertIn('latest(signal)', normalized)
                self.assertNotIn('| where', normalized)
                self.assertIn(aggregate + '(temperature_f)', normalized)

    def test_stable_mask_unrelated_sources_and_untouched_imports(self):
        mask = mask_command(self.profile()['measurementConstraints'][0])
        query = PROFILE['baseQuery'] + ' | search entity=$entity|s$ | ' + mask + ' | timechart bins=100 avg(temperature_f) AS mean'
        doc = {'dataSources': {'trend': {'type': 'ds.search', 'options': {'query': query}}, 'radio': {'type': 'ds.search', 'options': {'query': PROFILE['baseQuery'] + ' | stats latest(signal)'}}}}
        before = copy.deepcopy(doc)
        changed = normalize_measurements(doc, {}, self.profile())
        self.assertEqual(len(changed), 1)
        normalized = json.loads(changed[0]['value'])
        self.assertEqual(normalized.count(mask), 1)
        self.assertIn('search entity=$entity|s$', normalized)
        self.assertEqual(normalize_measurements(doc, before, self.profile()), [])
        self.assertEqual(doc, before)

    def test_reextract_fill_and_preaggregate_overwrite_are_not_silently_rewritten(self):
        for pipe in ('eval temperature_f=coalesce(temperature_f,0)', 'fillnull value=0 temperature_f', 'rex field=temperature_f "x"'):
            doc = {'dataSources': {'summary': {'type': 'ds.search', 'options': {'query': PROFILE['baseQuery'] + ' | ' + pipe + ' | stats avg(temperature_f)'}}}}
            with self.subTest(pipe=pipe), self.assertRaisesRegex(ProviderError, 'Do not overwrite'):
                normalize_measurements(doc, {}, self.profile())

    def test_compiler_keeps_query_parameters_unknown_properties_and_native_formatting(self):
        doc = {'visualizations': {}, 'dataSources': {'summary': {'type': 'ds.search', 'future': {'retained': True}, 'options': {'query': PROFILE['baseQuery'] + ' | stats avg(temperature_f) AS mean', 'future': 17}}}, 'layout': {'type': 'grid'}}
        before = copy.deepcopy(doc)
        actions = [{'op': 'search', 'id': 'summary', 'pipeline': '| stats latest(temperature_f) AS latest_temperature avg(temperature_f) AS mean latest(signal) AS signal | eval mean=round(mean,1)'}]
        changed = apply_changes(doc, compile_actions(doc, actions, self.profile()))
        self.assertIn('temperature_f<=150', changed['dataSources']['summary']['options']['query'])
        self.assertEqual(changed['dataSources']['summary']['future'], {'retained': True})
        self.assertEqual(changed['dataSources']['summary']['options']['future'], 17)
        self.assertEqual(doc, before)
