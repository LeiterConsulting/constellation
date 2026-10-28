"""Compact native planning still compiles through every ordinary validator."""
import copy
import json
import unittest
from test_drafts_and_data import blank
from test_search_chart_actions import PROFILE
from agent_service import SCHEMA
from authoring_budget import AuthoringBudget
from authoring_actions import compile_actions
from studio_contract import apply_changes
from studio_features import validate_features
from native_creation import eligible, expand
from native_shapes import validate_shape
from provider_service import ProviderError

PROMPT='Create exactly two pages named Relationships and Timing with exactly three visualizations: a Sankey, parallel coordinates and a timeline. No extra panels or inputs.'
PLAN={'op':'nativeCompose','title':'Native chart example','description':'Authored synthetic qualification plan.','pages':[
 {'id':'relationships','label':'Relationships','purpose':'Relationships and axes','panels':[
  {'id':'flow','type':'splunk.sankey','title':'Flow','pipeline':'| stats sum(value) AS weight BY source target | table source target weight','bindings':[{'option':'linkValues','fields':['weight']}]},
  {'id':'axes','type':'splunk.parallelcoordinates','title':'Axes','pipeline':'| table category cpu latency','bindings':[]}]},
 {'id':'timing','label':'Timing','purpose':'Intervals','panels':[
  {'id':'intervals','type':'splunk.timeline','title':'Intervals','pipeline':'| table _time category duration_ms','bindings':[{'option':'x','fields':['_time']},{'option':'y','fields':['category']},{'option':'duration','fields':['duration_ms']}]}]}]}

class NativeCreationTests(unittest.TestCase):
    def context(self,prompt=PROMPT):return {'request':prompt,'canvasState':'blank','history':[],'dataProfile':PROFILE,'modelLimits':{'contextTokens':32768}}
    def test_eligibility_keeps_advanced_requests_on_full_native_path(self):
        self.assertTrue(eligible(self.context(),blank()['definition']))
        for suffix in (' Add a return button.',' Use a network graph.',' Set line opacity.',' Position the flow above the axes.',' Use nodeSource for styling.',' Without fake data, add navigation.'):
            self.assertFalse(eligible(self.context(PROMPT+suffix),blank()['definition']),suffix)
        self.assertFalse(eligible(self.context(),dict(blank()['definition'],visualizations={'v':{'type':'splunk.table'}})))
        self.assertFalse(eligible(dict(self.context(),dataProfile={'scope':{'language':'spl2'}}),blank()['definition']))

    def test_plan_compiles_searches_bindings_pages_without_replacing_original(self):
        old=blank()['definition'];before=copy.deepcopy(old);actions=expand([PLAN],old,PROFILE,PROMPT)
        doc=apply_changes(old,compile_actions(old,actions,PROFILE));validate_features(doc,old,{'version':'10.4.4'})
        self.assertEqual(old,before);self.assertEqual(len(doc['visualizations']),3)
        self.assertEqual(doc['visualizations']['flow']['options']['linkValues'],'> primary | seriesByName("weight")')
        self.assertEqual([x['label']for x in doc['layout']['tabs']['items']],['Relationships','Timing'])
        self.assertTrue(all(source['options']['query'].startswith(PROFILE['baseQuery'])for source in doc['dataSources'].values()))
        bad=copy.deepcopy(doc['visualizations']['axes'])
        output={'fields':[{'name':'category'},{'name':'accidental_text'},{'name':'cpu'}],'results':[{'category':'A','accidental_text':'synthetic','cpu':2}]}
        with self.assertRaises(ProviderError):validate_shape(bad,{'ds_axes':output})

    def test_schema_ignoring_plans_cannot_bypass_types_bindings_counts_or_ids(self):
        for edit in ('type','binding','duplicate','count'):
            bad=copy.deepcopy(PLAN)
            if edit=='type':bad['pages'][0]['panels'][0]['type']='splunk.table'
            elif edit=='binding':bad['pages'][0]['panels'][0]['bindings'][0]['fields']=['weight','other']
            elif edit=='duplicate':bad['pages'][0]['panels'][1]['id']='flow'
            else:bad['pages'][1]['panels']=[]
            with self.assertRaises(ProviderError):expand([bad],blank()['definition'],PROFILE,PROMPT)
        with self.assertRaises(ProviderError):expand([{'op':'set','path':'/title','value':'"Wrong"'}],blank()['definition'],PROFILE,PROMPT)

    def test_every_provider_uses_bounded_plan_and_recovers_against_original(self):
        for provider in ('openai','ollama','aitk'):
            budget=AuthoringBudget({'provider':provider},self.context())
            request={'instructions':'Fixture','text':{'format':{'schema':copy.deepcopy(SCHEMA)}},'input':[{'content':[{'type':'input_text','text':'Fixture'}]}]}
            budget.prepare(request,blank()['definition']);self.assertTrue(budget.native_plan)
            self.assertEqual(request['text']['format']['schema']['properties']['changes']['items']['properties']['op']['enum'],['nativeCompose'])
            self.assertLess(request['max_output_tokens'],5000)
            budget.feedback(request,{'recoveryFeedback':{'editsApplyTo':'original','candidateDefinition':blank()['definition'],'validationError':'Wrong data shape'},'rejectedOutput':'Untrusted failed output'})
            self.assertNotIn('Untrusted failed output',json.dumps(request));self.assertIn('ONE complete corrected nativeCompose',json.dumps(request))
            self.assertEqual(budget.actions([PLAN],blank()['definition']),expand([PLAN],blank()['definition'],PROFILE,PROMPT))

    def test_event_filter_cannot_be_saved_at_wrong_native_level(self):
        old=blank()['definition'];old['visualizations']['s']={'type':'splunk.sankey','options':{}}
        new=copy.deepcopy(old);new['visualizations']['s']['options']['events']=['node.click']
        with self.assertRaisesRegex(ProviderError,'eventHandlers'):validate_features(new,old,{'version':'10.4.4'})
        validate_features(new,new,{'version':'10.4.4'}) # Existing unknown import is preserved.

    def test_type_conversion_rechecks_inherited_native_events(self):
        old=blank()['definition'];old['visualizations']['v']={'type':'splunk.sankey','eventHandlers':[{'type':'drilldown.setToken','options':{'events':['node.click'],'tokens':[{'token':'picked','value':'yes'}]}}]}
        new=copy.deepcopy(old);new['visualizations']['v']['type']='splunk.parallelcoordinates'
        with self.assertRaisesRegex(ProviderError,'does not support interactions'):validate_features(new,old,{'version':'10.4.4'})

    def test_flat_native_outline_has_exact_total_and_explicit_page_membership(self):
        from native_creation import schema_for,nested,instructions
        schema=schema_for(PROMPT,True);props=schema['properties']
        self.assertEqual(props['panels']['minItems'],3);self.assertEqual(props['panels']['maxItems'],3)
        self.assertEqual(props['pages']['minItems'],2);self.assertEqual(props['pages']['maxItems'],2)
        self.assertNotIn('panels',props['pages']['items']['properties'])
        flat={key:copy.deepcopy(value)for key,value in PLAN.items()if key!='pages'};flat['pages']=[];flat['panels']=[]
        for index,page in enumerate(PLAN['pages']):
            flat['pages'].append({key:value for key,value in page.items()if key!='panels'})
            flat['panels'].extend(dict(copy.deepcopy(panel),page=index)for panel in page['panels'])
        before=copy.deepcopy(flat);self.assertEqual(nested(flat),PLAN);self.assertEqual(flat,before)
        self.assertEqual(expand([flat],blank()['definition'],PROFILE,PROMPT),expand([PLAN],blank()['definition'],PROFILE,PROMPT))
        self.assertIn('Never put panels inside pages',instructions(True))
        for value in (-1,2,True,'1'):
            bad=copy.deepcopy(flat);bad['panels'][0]['page']=value
            with self.assertRaises(ProviderError):expand([bad],blank()['definition'],PROFILE,PROMPT)
        bad=copy.deepcopy(flat);bad['panels'][0]['unknown']='retained error'
        with self.assertRaises(ProviderError):expand([bad],blank()['definition'],PROFILE,PROMPT)

    def test_native_schema_uses_family_specific_binding_keys(self):
        from native_creation import schema_for
        schema=schema_for(PROMPT,True);variants=schema['properties']['panels']['items']['anyOf']
        sankey=next(v for v in variants if v['properties']['type']['enum']==['splunk.sankey'])
        self.assertEqual(sankey['properties']['bindings']['required'],['linkValues'])
        self.assertFalse(sankey['properties']['bindings']['additionalProperties'])
        plan=copy.deepcopy(PLAN)
        for page in plan['pages']:
            for panel in page['panels']:
                panel['bindings']={b['option']:b['fields'] if b['option']=='fieldOrder' else b['fields'][0] for b in panel['bindings']}
        self.assertEqual(expand([plan],blank()['definition'],PROFILE,PROMPT),expand([PLAN],blank()['definition'],PROFILE,PROMPT))
        bad=copy.deepcopy(plan);bad['pages'][0]['panels'][0]['bindings']['unknown']='bad'
        with self.assertRaises(ProviderError):expand([bad],blank()['definition'],PROFILE,PROMPT)

    def test_partial_family_list_cannot_restrict_other_requested_charts(self):
        prompt='Create two pages with exactly three visualizations: a Sankey and other useful charts.'
        self.assertFalse(eligible(self.context(prompt),blank()['definition']))
        prompt='Create two pages with exactly three visualizations: a Sankey; parallel coordinates; a timeline.'
        self.assertTrue(eligible(self.context(prompt),blank()['definition']))
        from native_creation import schema_for
        types={v['properties']['type']['enum'][0]for v in schema_for(prompt,True)['properties']['panels']['items']['anyOf']}
        self.assertEqual(types,{'splunk.sankey','splunk.parallelcoordinates','splunk.timeline'})

    def test_new_native_board_uses_single_chart_space_and_replaces_only_unrequested_default_title(self):
        plan=copy.deepcopy(PLAN);plan['title']='New dashboard'
        actions=expand([plan],blank()['definition'],PROFILE,PROMPT)
        self.assertEqual(actions[0]['title'],'Relationships / Timing')
        page=next(action for action in actions if action.get('layoutId')=='layout_timing')
        self.assertEqual(len(page['items']),1);self.assertGreater(page['items'][0]['w'],1000)
        self.assertLessEqual(page['items'][0]['x']+page['items'][0]['w'],page['width'])
        explicit=PROMPT+' Use the title "New dashboard".'
        self.assertEqual(expand([plan],blank()['definition'],PROFILE,explicit)[0]['title'],'New dashboard')
        self.assertEqual(expand([plan],blank()['definition'],PROFILE,PROMPT+' Use the title New dashboard.')[0]['title'],'New dashboard')
