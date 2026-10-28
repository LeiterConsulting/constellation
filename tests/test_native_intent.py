"""Explicit native intent stays separate from schema validity and rendering."""
import copy
import json
import unittest
from test_drafts_and_data import blank
from agent_service import SCHEMA
from authoring_budget import AuthoringBudget
from native_intent import requested_types, validate_native_intent
from provider_service import ProviderError
from studio_inventory import authoring_contract
from test_search_chart_actions import PROFILE


class NativeIntentTests(unittest.TestCase):
    def test_positive_creation_list_requires_native_types_without_table_substitution(self):
        prompt='Create two pages with three visualizations: a Sankey diagram, parallel coordinates and a timeline. Not a table substitute.'
        self.assertEqual(requested_types(prompt), {'splunk.sankey', 'splunk.parallelcoordinates', 'splunk.timeline'})
        self.assertEqual(requested_types('Create splunk.sankey and splunk.timeline charts.'), {'splunk.sankey', 'splunk.timeline'})
        old=blank()['definition'];new=copy.deepcopy(old);new['visualizations']={'v':{'type':'splunk.table'}}
        with self.assertRaisesRegex(ProviderError, 'Tables or promises'): validate_native_intent(prompt,new,old,{})
        for kind in requested_types(prompt):new['visualizations'][kind]={'type':kind}
        validate_native_intent(prompt,new,old,{})

    def test_references_negations_titles_choices_and_unchanged_answers_do_not_force_charts(self):
        for prompt in ('Explain a Sankey diagram.', 'Create a table, not a Sankey.', 'Build a pie or Sankey chart.',
                       'Create a chart titled "Timeline".', 'Do not create a Sankey.', 'Build a table without a timeline.'):
            self.assertEqual(requested_types(prompt),set(),prompt)
        old=blank()['definition'];validate_native_intent('Create a timeline',old,old,{})
        old['visualizations']['s']={'type':'splunk.sankey'};new=copy.deepcopy(old);new['title']='Changed'
        validate_native_intent('Add a description to the Sankey',new,old,{})

    def test_selected_explicit_conversion_retains_identity(self):
        old=blank()['definition'];old['visualizations']['v']={'type':'splunk.table'};new=copy.deepcopy(old);new['title']='Changed'
        with self.assertRaises(ProviderError):validate_native_intent('Convert this to a Sankey diagram',new,old,{'kind':'visualization','id':'v'})
        new['visualizations']['v']['type']='splunk.sankey';validate_native_intent('Convert this to a Sankey diagram',new,old,{'kind':'visualization','id':'v'})

    def test_native_creation_schema_omits_existing_target_helpers_and_basic_chart_substitutes(self):
        goal='Create two pages with a Sankey, parallel coordinates and a timeline.'
        context={'request':goal,'canvasState':'blank','history':[],'dataProfile':PROFILE,
                 'nativeAuthoring':authoring_contract(goal,{}, {'version':'10.4.4'}),'modelLimits':{'contextTokens':32768}}
        self.assertIn('splunk.parallelcoordinates',context['nativeAuthoring']['relevantOptions'])
        for provider in ('openai','aitk','ollama'):
            with self.subTest(provider=provider):
                request={'instructions':'Fixture','text':{'format':{'schema':copy.deepcopy(SCHEMA)}},'input':[{'content':[{'type':'input_text','text':'Fixture'}]}]}
                budget=AuthoringBudget({'provider':provider},context);budget.prepare(request,blank()['definition'])
                actions={op for item in request['text']['format']['schema']['properties']['changes']['items']['anyOf']for op in item['properties']['op']['enum']}
                self.assertTrue({'set','search','page'}<=actions)
                self.assertFalse(actions & {'chart','pageMeta','buttonRoute','route','formatTable','tableSparkline'})
                self.assertIn('native chart types required',request['instructions'])

    def test_semicolon_list_retains_all_requested_families(self):
        prompt='Create two pages with exactly three visualizations: a Sankey on Relationships using source and target; parallel coordinates on Relationships with category first; a timeline on Timing with intervals. No extra inputs.'
        self.assertEqual(requested_types(prompt),{'splunk.sankey','splunk.parallelcoordinates','splunk.timeline'})
        old=blank()['definition'];new=copy.deepcopy(old);new['visualizations']={str(i):{'type':'splunk.sankey'}for i in range(3)}
        with self.assertRaisesRegex(ProviderError,'parallelcoordinates'):validate_native_intent(prompt,new,old,{})
