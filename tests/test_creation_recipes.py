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
        for kind in ('aitk',):
            class CompactProvider(Provider):
                def configured(self):return {'provider':kind,'model':'fixture'}
                def capabilities(self,saved):return {'contextTokens':32768,'images':False,'pdf':False}
            action={'op':'compose','title':'Observed duration','description':'Selected real data.','pages':[{'id':'main','label':'Overview','purpose':'Observe duration','columns':1,
                    'panels':[{'id':'summary','type':'splunk.table','title':'Mean duration','recipe':recipe(group='')}]}],'links':[]}
            runtime=Outputs();provider=CompactProvider([reply([action])]);body={'prompt':'Build one page with one table of mean duration and observations.','revision':0,'definition':blank()['definition'],'dataContext':blank()['dataContext']}
            result=AgentService(provider,runtime).assist(body);self.assertEqual(result['recovery']['modelCalls'],1);self.assertEqual(result['recovery']['queryChecks'],1);self.assertFalse(result['repaired'])
            self.assertEqual(result['recovery']['recipePanels'],1)
            self.assertIn('avg(duration) AS mean_value',apply_changes(body['definition'],result['changes'])['dataSources']['ds_summary']['options']['query'])
            runtime=Outputs();runtime.missing=True;provider=CompactProvider([reply([action])]*3)
            with self.assertRaises(ProviderError):AgentService(provider,runtime).assist(body)

    def test_recipe_wire_strategy_is_enabled_only_for_the_qualified_provider_path(self):
        from authoring_budget import AuthoringBudget
        from agent_service import SCHEMA
        for provider in ('aitk','ollama'):
            context={'canvasState':'blank','request':'Build two pages with four charts.','dataProfile':PROFILE,
                     'modelLimits':{'contextTokens':32768},'history':[]}
            request={'instructions':'Initial instructions','text':{'format':{'schema':copy.deepcopy(SCHEMA)}},'input':[{'role':'user','content':[{'type':'input_text','text':'context'}]}]}
            budget=AuthoringBudget({'provider':provider},context);budget.prepare(request,blank()['definition'])
            panels=request['text']['format']['schema']['properties']['changes']['items']['properties']['pages']['items']['properties']['panels']['items']['anyOf']
            self.assertEqual(any('recipe'in variant.get('properties',{})for variant in panels),provider=='aitk')
            self.assertEqual('PREFERRED SEARCH FORM'in request['instructions'],provider=='aitk')

if __name__=='__main__':unittest.main()
