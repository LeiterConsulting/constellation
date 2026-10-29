"""Authored metadata and queries, without indexed values or provider access."""
import copy
import json
import unittest
from authoring_actions import compile_actions
from measurement_constraints import normalize_measurements, temperature_constraints, mask_command
from provider_service import ProviderError
from studio_contract import apply_changes
from population_guard import validate_populations, retain_source_rows, independent_measurements

PROFILE = {'scope': {'index': 'fixture_index', 'language': 'spl', 'earliest': '-24h'},
           'baseQuery': 'search index="fixture_index"',
           'fields': [{'name': 'temperature_f', 'numeric': True}, {'name': 'signal', 'numeric': True}]}
GOAL = 'Temperatures are Fahrenheit: exclude readings above 150 F from temperature calculations, but retain signal measurements independently.'


class MeasurementConstraintTests(unittest.TestCase):
    def test_explicit_all_row_requirement_keeps_temperature_only_trend_observations(self):
        profile=dict(self.profile(),retainSourceRows=True)
        query=PROFILE['baseQuery']+' | where temperature_f<=150 | timechart bins=100 avg(temperature_f) AS mean'
        doc={'dataSources':{'trend':{'type':'ds.search','options':{'query':query}}}}
        normalized=json.loads(normalize_measurements(doc,{},profile)[0]['value'])
        self.assertNotIn('where temperature_f',normalized);self.assertIn(mask_command(profile['measurementConstraints'][0]),normalized)
        self.assertIn('timechart bins=100 avg(temperature_f) AS mean',normalized)
        self.assertEqual(normalize_measurements(doc,copy.deepcopy(doc),profile),[])
        shared=json.loads(normalize_measurements(doc,{},self.profile())[0]['value'])
        self.assertIn('where temperature_f<=150',shared)
        for predicate in ('isnotnull(temperature_f)','temperature_f<=150 AND signal>-70'):
            bad={'dataSources':{'trend':{'type':'ds.search','options':{'query':PROFILE['baseQuery']+' | where '+predicate+' | stats avg(temperature_f) AS mean'}}}}
            with self.subTest(predicate=predicate),self.assertRaisesRegex(ProviderError,'Keep all source observations'):normalize_measurements(bad,{},profile)
    def test_all_row_retention_is_explicit_durable_and_can_be_revised(self):
        from dashboard_brief import authoring_brief
        prompt='Preserve independent Wi-Fi readings and all events.'
        brief=authoring_brief({'brief':{'purpose':'Understand readings','requirements':''},'prompt':prompt})
        self.assertTrue(retain_source_rows(prompt,{}));self.assertTrue(retain_source_rows('Rename the title.',brief))
        self.assertFalse(retain_source_rows('Use the same population.',brief))
        self.assertFalse(retain_source_rows('Do not preserve all source rows.',{}))
        revised=authoring_brief({'brief':brief,'prompt':'Stop preserving all events.'})
        self.assertFalse(retain_source_rows('Rename the title.',revised))
        self.assertTrue(retain_source_rows('Never replace missing with zero while keeping all source events.',{}))
        revised=authoring_brief({'brief':brief,'prompt':'Use a shared population.'})
        self.assertFalse(retain_source_rows('Rename the title.',revised));self.assertFalse(independent_measurements('Rename the title.',revised))
        again=authoring_brief({'brief':revised,'prompt':'Keep Wi-Fi measurements independent and keep all source events.'})
        self.assertTrue(retain_source_rows('Rename the title.',again));self.assertTrue(independent_measurements('Rename the title.',again))
    def profile(self, prompt=GOAL):
        return dict(PROFILE, measurementConstraints=temperature_constraints(prompt, {}, PROFILE))

    def test_exact_misplaced_raw_cutoff_is_supplied_at_the_boundary_without_filtering_other_measurements(self):
        profile=self.profile()
        for pipeline in ('| timechart bins=100 avg(temperature_f) AS mean WHERE temperature_f<=150',
                         '| stats avg(temperature_f) AS mean latest(signal) AS signal BY entity WHERE temperature_f<=150.0',
                         '| timechart bins=100 avg(signal) AS signal WHERE temperature_f<=150'):
            query=PROFILE['baseQuery']+' '+pipeline;doc={'dataSources':{'summary':{'type':'ds.search','options':{'query':query}}}}
            normalized=json.loads(normalize_measurements(doc,{},profile)[0]['value'])
            self.assertNotIn('WHERE',normalized)
            if 'avg(temperature_f)' in pipeline:self.assertIn(mask_command(profile['measurementConstraints'][0]),normalized)
            else:self.assertNotIn('temperature_f',normalized)
            self.assertEqual(normalize_measurements(doc,copy.deepcopy(doc),profile),[])

    def test_misplaced_repair_preserves_other_limits_compounds_literals_and_output_fields(self):
        from measurement_constraints import without_misplaced_cutoff
        rule=self.profile()['measurementConstraints'][0]
        for pipeline in ('| stats avg(temperature_f) AS mean WHERE temperature_f<=140',
                         '| stats avg(temperature_f) AS mean WHERE temperature_f<=150 AND signal>-80',
                         '| stats avg(temperature_f) AS mean WHERE temperature_f<=150 OR signal>-80',
                         '| stats avg(temperature_f) AS temperature_f WHERE temperature_f<=150',
                         '| stats avg(temperature_f) AS "temperature_f" WHERE temperature_f<=150',
                         '| stats count BY entity temperature_f WHERE temperature_f<=150',
                         '| stats values("WHERE temperature_f<=150") AS label',
                         '| timechart count BY entity WHERE count IN TOP10'):
            self.assertEqual(without_misplaced_cutoff(pipeline,rule),pipeline)

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

    def test_derived_classification_uses_masked_measurement_without_overwriting_source_fields(self):
        for expression in ('area=if(temperature_f<0,"cold","warm")',
                           'area=case(temperature_f<0,"cold",temperature_f<=150,"warm"), label=coalesce(area,"unknown")'):
            query=PROFILE['baseQuery']+' | eval '+expression+' | stats count(temperature_f) AS readings BY area'
            doc={'dataSources':{'summary':{'type':'ds.search','options':{'query':query}}}}
            normalized=json.loads(normalize_measurements(doc, {}, self.profile())[0]['value'])
            self.assertIn('| '+mask_command(self.profile()['measurementConstraints'][0])+' | eval '+expression, normalized)
        for expression in ('area=if(temperature_f<0,"cold","warm"), temperature_f=0',
                           'area=if(temperature_f<0,"cold","warm"), signal=temperature_f',
                           "'temperature_f'=0", '{target}=temperature_f'):
            doc['dataSources']['summary']['options']['query']=PROFILE['baseQuery']+' | eval '+expression+' | stats avg(temperature_f)'
            with self.subTest(expression=expression), self.assertRaisesRegex(ProviderError,'Do not overwrite'):
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

    def test_exact_coupled_cutoff_compiles_without_a_model_retry(self):
        profile = dict(self.profile(), independentMeasurements=True)
        profile['fields'] = PROFILE['fields'] + [{'name': 'entity', 'numeric': False}]
        for condition in ('where temperature_f<=150', 'search temperature_f <= 150.0', "where ('temperature_f'<=150)", 'where 150>=temperature_f'):
            query = PROFILE['baseQuery'] + ' | search entity=$entity|s$ | ' + condition + ' | stats avg(temperature_f) AS mean latest(signal) AS signal BY entity'
            doc = {'dataSources': {'summary': {'type': 'ds.search', 'options': {'query': query}}}}
            with self.subTest(condition=condition):
                normalized = json.loads(normalize_measurements(doc, {}, profile)[0]['value'])
                self.assertNotIn(condition, normalized)
                self.assertIn('temperature_f<=150,temperature_f,null()', normalized)
                self.assertIn('search entity=$entity|s$', normalized)
                self.assertIn('latest(signal) AS signal BY entity', normalized)
                validate_populations(normalized, profile)

    def test_unknown_predicates_unchanged_imports_and_shared_population_are_not_widened(self):
        for condition in ('where temperature_f<=140', 'where temperature_f<=150 AND signal>-80', 'where temperature_f<=150 OR signal>-80'):
            profile = dict(self.profile(), independentMeasurements=True)
            query = PROFILE['baseQuery'] + ' | ' + condition + ' | stats avg(temperature_f) latest(signal)'
            doc = {'dataSources': {'summary': {'type': 'ds.search', 'options': {'query': query}}}}
            normalized = json.loads(normalize_measurements(doc, {}, profile)[0]['value'])
            self.assertIn(condition, normalized)
            with self.assertRaises(ProviderError): validate_populations(normalized, profile)
            self.assertEqual(normalize_measurements(doc, copy.deepcopy(doc), profile), [])
        profile = dict(self.profile(), independentMeasurements=False)
        normalized = json.loads(normalize_measurements(doc, {}, profile)[0]['value'])
        self.assertIn(condition, normalized)

    def test_quoted_pipes_and_mask_text_stay_literal_and_cannot_hide_overwrites(self):
        literal = '| eval temperature_f=if(temperature_f<=150,temperature_f,null())'
        query = PROFILE['baseQuery'] + ' | eval note="' + literal + '" | stats latest(temperature_f) latest(signal)'
        doc = {'dataSources': {'summary': {'type': 'ds.search', 'options': {'query': query}}}}
        normalized = json.loads(normalize_measurements(doc, {}, self.profile())[0]['value'])
        self.assertIn('note="' + literal + '"', normalized)
        self.assertEqual(normalized.count(literal), 2)
        query = PROFILE['baseQuery'] + ' | eval note="| stats" | eval temperature_f=coalesce(temperature_f,0) | stats avg(temperature_f)'
        doc['dataSources']['summary']['options']['query'] = query
        with self.assertRaisesRegex(ProviderError, 'Do not overwrite'): normalize_measurements(doc, {}, self.profile())

    def test_quoted_verified_fields_and_no_space_fahrenheit_use_the_same_mask(self):
        profile = self.profile('Exclude temperatures over 150F.')
        query = PROFILE['baseQuery'] + " | stats avg(eval('temperature_f')) AS mean"
        doc = {'dataSources': {'summary': {'type': 'ds.search', 'options': {'query': query}}}}
        normalized = json.loads(normalize_measurements(doc, {}, profile)[0]['value'])
        self.assertIn('temperature_f<=150', normalized)
