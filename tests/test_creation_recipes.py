"""Synthetic search recipes retain native validation, aliases and populations."""
import copy
import unittest
from test_drafts_and_data import blank
from creation_recipes import compile_recipe
from provider_service import ProviderError
from compact_creation import expand_compose
from agent_service import AgentService
from studio_contract import apply_changes
from test_reliability_journey import Provider, Runtime, reply

PROFILE = {'baseQuery':'search index="fixture_index"', 'scope':{'index':'fixture_index','language':'spl','earliest':'-24h'},
           'fields':[{'name':n,'numeric':n!='device_name'} for n in ('_time','device_name','duration','temperature_f','wifi_rssi')]}
def recipe(kind='stats', metrics=None, group='device_name', columns=None):
    return {'kind':kind,'metrics':metrics if metrics is not None else [{'function':'avg','field':'duration','alias':'mean_value'}, {'function':'count','field':'','alias':'observations'}],
            'groupBy':group,'columns':columns or []}

class RecipeTests(unittest.TestCase):
    def test_repeated_aggregate_uses_one_native_specifier_and_keeps_every_alias(self):
        metrics=[{'function':'count','field':'','alias':'readings'},{'function':'count','field':'','alias':'history_count'},{'function':'avg','field':'temperature_f','alias':'mean_f'},{'function':'avg','field':'temperature_f','alias':'temperature_mean'}]
        original=copy.deepcopy(metrics);query,x,y=compile_recipe({'kind':'timechart','metrics':metrics},'splunk.line',PROFILE,format_values=False)
        self.assertEqual(query,'| timechart bins=100 count AS readings avg(temperature_f) AS mean_f | eval history_count=readings, temperature_mean=mean_f')
        self.assertEqual(y,['readings','history_count','mean_f','temperature_mean']);self.assertEqual(x,'_time');self.assertEqual(metrics,original)
    def test_kind_specific_plans_compile_without_irrelevant_fields_and_preserve_legacy(self):
        for modern, legacy, chart in (
            ({'kind':'stats','metrics':recipe()['metrics'],'groupBy':'device_name'},recipe(),'splunk.table'),
            ({'kind':'timechart','metrics':recipe()['metrics']},recipe('timechart',group=''),'splunk.line'),
            ({'kind':'table','columns':['_time','device_name','duration']},recipe('table',[], '',['_time','device_name','duration']),'splunk.table')):
            before=copy.deepcopy(modern)
            self.assertEqual(compile_recipe(modern,chart,PROFILE),compile_recipe(legacy,chart,PROFILE))
            self.assertEqual(modern,before)
        for bad in ({'kind':'stats','metrics':[]}, {'kind':'timechart','metrics':recipe()['metrics'],'columns':['mean_value']},
                    {'kind':'table','columns':['duration'],'metrics':recipe()['metrics']},
                    {'kind':'table','columns':['duration'],'extra':True}, {'kind':[], 'columns':[]}):
            with self.subTest(bad=bad),self.assertRaises(ProviderError):compile_recipe(bad,'splunk.table',PROFILE)

    def test_invalid_recipe_shape_feedback_identifies_the_correction_without_accepting_it(self):
        recipe={'kind':'timechart','metrics':[{'function':'count','field':'','alias':'events'}],'groupBy':'','columns':[]}
        for changed,message in ((dict(recipe,columns=['events']),'Only raw table'),(dict(recipe,metrics=[]),'1–8 metrics'),(dict(recipe,groupBy='device_name'),'groupBy:""')):
            with self.subTest(changed=changed),self.assertRaisesRegex(ProviderError,message):compile_recipe(changed,'splunk.line',PROFILE)
    def test_aggregate_and_raw_bindings_come_from_one_verified_plan(self):
        self.assertEqual(compile_recipe(recipe(), 'splunk.table', PROFILE), ('| stats avg(duration) AS mean_value count AS observations BY device_name | eval mean_value=round(mean_value,2)','','device_name mean_value observations'.split()))
        q,x,y = compile_recipe(recipe('timechart', group=''), 'splunk.line', PROFILE)
        self.assertEqual((q,x,y), ('| timechart bins=100 avg(duration) AS mean_value count AS observations','_time',['mean_value','observations']))
        self.assertEqual(compile_recipe(recipe('table', [], '', ['_time','device_name','duration']), 'splunk.table', PROFILE), ('| table _time device_name duration','',['_time','device_name','duration']))
        self.assertEqual(compile_recipe(recipe(metrics=[{'function':'max','field':'duration','alias':'peak'}],group=''), 'splunk.singlevalue', PROFILE), ('| stats max(duration) AS peak','',['peak']))

    def test_unknown_inputs_sql_expressions_and_alias_collisions_are_rejected(self):
        bad=[]
        for update in ({'field':'duratoin'}, {'field':'eval(duration<=150)'}, {'field':'device_name'}, {'alias':'device_name'}, {'function':'delete'}):
            r=recipe();r['metrics'][0].update(update);bad.append(r)
        r=recipe();r['metrics'][1]['alias']='mean_value';bad.append(r)
        bad.extend([recipe('timechart'), recipe('table', [], '', ['duration','duration']), recipe('table', [], '', ['invented']),dict(recipe(),extra='ignore')])
        for r in bad:
            with self.subTest(r=r),self.assertRaises(ProviderError): compile_recipe(r,'splunk.table',PROFILE)
        with self.assertRaises(ProviderError):compile_recipe(recipe(),'splunk.table',dict(PROFILE,scope={'language':'spl2'}))
        with self.assertRaises(ProviderError):compile_recipe(recipe(),'splunk.singlevalue',PROFILE)

    def test_native_time_type_is_not_inferred_from_its_sample_serialization(self):
        profile=copy.deepcopy(PROFILE);profile['fields'][0]['numeric']=False
        r=recipe(metrics=[{'function':'max','field':'_time','alias':'last_seen'}])
        self.assertIn('max(_time) AS last_seen',compile_recipe(r,'splunk.table',profile)[0])
        profile['scope']={'query':'search index="fixture_index" | eval _time="changed"','language':'spl'}
        with self.assertRaises(ProviderError):compile_recipe(r,'splunk.table',profile)

    def test_cutoff_is_left_to_the_source_mask_and_independent_counts_stay_independent(self):
        metrics=[{'function':f,'field':v,'alias':a}for f,v,a in [('avg','temperature_f','mean_f'),('count','','events'),('count','temperature_f','valid_t'),('avg','wifi_rssi','wifi_mean'),('max','_time','seen')]]
        action={'op':'compose','title':'Recorded readings','description':'Real readings.','pages':[{'id':'main','label':'Overview','purpose':'Inspect readings','columns':1,
                  'panels':[{'id':'summary','type':'splunk.table','title':'Temperature and Wi-Fi','recipe':recipe(metrics=metrics)}]}],'links':[]}
        original=blank()['definition'];before=copy.deepcopy(action)
        expanded=expand_compose([action],original,PROFILE);q=next(a['pipeline']for a in expanded if a['op']=='search')
        self.assertEqual(q,'| stats avg(temperature_f) AS mean_f count AS events count(temperature_f) AS valid_t avg(wifi_rssi) AS wifi_mean max(_time) AS seen BY device_name | eval mean_f=round(mean_f,2), wifi_mean=round(wifi_mean,2), seen=strftime(seen,"%Y-%m-%d %H:%M:%S")')
        self.assertEqual(action,before);self.assertEqual(next(a['y']for a in expanded if a['op']=='chart'),['device_name','mean_f','events','valid_t','wifi_mean','seen'])

    def test_recipe_is_accepted_only_after_actual_output_checks_with_one_model_call(self):
        class Outputs(Runtime):
            missing=False
            def preview(self,body):
                if body.get('fieldDiscovery'):return super().preview(body)
                self.calls.append(body)
                return {'state':'complete','fields':[{'name':n}for n in (['observations']if self.missing else['mean_value','observations'])], 'results':[{'mean_value':'12','observations':'3'}]}
        for kind in ('aitk','ollama'):
            class CompactProvider(Provider):
                def configured(self):return {'provider':kind,'model':'fixture'}
                def capabilities(self,saved):return {'contextTokens':32768,'images':False,'pdf':False}
            action={'op':'compose','title':'Observed duration','description':'Selected real data.','pages':[{'id':'main','label':'Overview','purpose':'Observe duration','columns':1,
                    'panels':[{'id':'summary','type':'splunk.table','title':'Mean duration','recipe':{k:v for k,v in recipe(group='').items()if k!='columns'}}]}],'links':[]}
            if kind=='ollama':
                action=dict(action,pages=[{k:v for k,v in action['pages'][0].items()if k not in('id','panels')}],
                            panels=[dict(action['pages'][0]['panels'][0],page=0)])
            runtime=Outputs();provider=CompactProvider([reply([action])]);body={'prompt':'Build one page with one table of mean duration and observations.','revision':0,'definition':blank()['definition'],'dataContext':blank()['dataContext']}
            result=AgentService(provider,runtime).assist(body);self.assertEqual(result['recovery']['modelCalls'],1);self.assertEqual(result['recovery']['queryChecks'],1);self.assertFalse(result['repaired'])
            self.assertEqual(result['recovery']['recipePanels'],1)
            self.assertIn('avg(duration) AS mean_value',apply_changes(body['definition'],result['changes'])['dataSources']['ds_summary']['options']['query'])
            runtime=Outputs();runtime.missing=True;provider=CompactProvider([reply([action])]*3)
            with self.assertRaises(ProviderError):AgentService(provider,runtime).assist(body)

    def test_recipe_wire_strategy_excludes_irrelevant_kind_fields_and_keeps_advanced_pipeline(self):
        from authoring_budget import AuthoringBudget
        from agent_service import SCHEMA
        for provider in ('aitk','ollama'):
            context={'canvasState':'blank','request':'Build two pages with four charts.','dataProfile':PROFILE,
                     'modelLimits':{'contextTokens':32768},'history':[]}
            request={'instructions':'Initial instructions','text':{'format':{'schema':copy.deepcopy(SCHEMA)}},'input':[{'role':'user','content':[{'type':'input_text','text':'context'}]}]}
            budget=AuthoringBudget({'provider':provider},context);budget.prepare(request,blank()['definition'])
            props=request['text']['format']['schema']['properties']['changes']['items']['properties']
            panels=(props['panels'] if provider=='ollama' else props['pages']['items']['properties']['panels'])['items']['anyOf']
            recipes=next(variant['properties']['recipe']['anyOf']for variant in panels if 'recipe'in variant.get('properties',{}))
            self.assertEqual([set(r['properties'])for r in recipes],[{'kind','metrics','groupBy'},{'kind','metrics'},{'kind','columns'}])
            self.assertTrue(all(r['additionalProperties']is False and set(r['required'])==set(r['properties'])for r in recipes))
            self.assertTrue(any('pipeline'in variant.get('properties',{})for variant in panels))
            self.assertIn('PREFERRED SEARCH FORM',request['instructions'])
            if provider=='ollama':
                self.assertIn('panels:[{id,page:0,type,title,recipe:{kind,...}}]',request['instructions'])
                self.assertNotIn('panels:[\n',request['instructions'])

if __name__=='__main__':unittest.main()
