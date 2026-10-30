"""Aggregate sharing changes neither populations, expressions nor projections."""
import copy
import unittest
from planning_sources import shared_stats
from creation_recipes import compile_recipe

PROFILE={'scope':{'language':'spl'},'fields':[{'name':'host'},{'name':'temperature_f','numeric':True},{'name':'wifi_rssi','numeric':True}]}
def source(key,field,alias,group=''):
    return {'id':key,'recipe':{'kind':'stats','groupBy':group,'metrics':[{'function':'avg','field':field,'alias':alias}]}}
def panel(key,kind='splunk.singlevalue',bindings=None):
    return {'source':key,'type':kind,'bindings':bindings or {'value':key}}
def pipelines(specs):return {s['id']:compile_recipe(s['recipe'],'splunk.table',PROFILE,format_values=False)[0]for s in specs}

class PlanningSourceTests(unittest.TestCase):
    def test_timecharts_share_only_identical_buckets_without_changing_populations(self):
        specs=[{'id':'a','recipe':{'kind':'timechart','metrics':[{'function':'avg','field':'temperature_f','alias':'temperature_mean'}]}},{'id':'b','recipe':{'kind':'timechart','metrics':[{'function':'avg','field':'wifi_rssi','alias':'wifi_mean'},{'function':'count','field':'','alias':'all_observations'}]}}]
        before={s['id']:compile_recipe(s['recipe'],'splunk.line',PROFILE,format_values=False)[0]for s in specs};result=shared_stats(specs,before,[],PROFILE,unbound_pool=True)
        self.assertEqual(result['a'],result['b']);self.assertTrue(result['a'].startswith('| timechart bins=100 '));self.assertIn('avg(wifi_rssi) AS wifi_mean',result['a']);self.assertIn('count AS all_observations',result['a']);self.assertNotIn('where',result['a'])
        raw=[{'id':k,'pipeline':v}for k,v in before.items()]
        self.assertEqual(shared_stats(raw,before,[],PROFILE,unbound_pool=True),result)
        for query in ('| timechart span=1h avg(wifi_rssi) AS wifi_mean','| timechart bins=50 avg(wifi_rssi) AS wifi_mean','| timechart bins=100 avg(wifi_rssi) AS wifi_mean BY host','| timechart bins=100 avg(wifi_rssi) AS wifi_mean | fillnull value=0'):
            raw[1]['pipeline']=query;original={'a':before['a'],'b':query};self.assertEqual(shared_stats(raw,original,[],PROFILE,unbound_pool=True),original)
        consumers=[panel('a','splunk.line',{'x':'_time','y':['temperature_mean']}),panel('b','splunk.line',{'x':'_time','y':[]})]
        self.assertEqual(shared_stats(specs,before,consumers,PROFILE),before)
    def test_compatible_aggregates_share_exact_expressions_and_leave_inputs_unchanged(self):
        specs=[source('temp','temperature_f','temp'),source('wifi','wifi_rssi','wifi')];old=copy.deepcopy(specs);original=pipelines(specs)
        result=shared_stats(specs,original,[panel('temp'),panel('wifi')],PROFILE)
        self.assertEqual(result['temp'],result['wifi']);self.assertIn('avg(temperature_f) AS temp',result['temp']);self.assertIn('avg(wifi_rssi) AS wifi',result['temp'])
        self.assertNotIn('round',result['temp']);self.assertNotIn('where',result['temp']);self.assertEqual(specs,old);self.assertEqual(original,pipelines(specs))
    def test_conflicting_alias_group_and_unprojected_consumers_remain_separate(self):
        variants=[
            ([source('a','temperature_f','same'),source('b','wifi_rssi','same')],[panel('a'),panel('b')]),
            ([source('a','temperature_f','a'),source('b','wifi_rssi','b','host')],[panel('a'),panel('b')]),
            ([source('a','temperature_f','a'),source('b','wifi_rssi','b')],[panel('a','splunk.table',{'columns':[]}),panel('b')]),
            ([source('a','temperature_f','a'),source('b','wifi_rssi','b')],[panel('a','splunk.line',{'x':'host','y':[]}),panel('b')]),
        ]
        for specs,consumers in variants:
            before=pipelines(specs);self.assertEqual(shared_stats(specs,before,consumers,PROFILE),before)
    def test_shared_wide_aggregates_keep_every_validated_metric_and_input_bound(self):
        specs=[];consumers=[]
        for index in range(3):
            s=source('s'+str(index),'temperature_f','m'+str(index));s['recipe']['metrics']=[{'function':'avg','field':'temperature_f','alias':'m'+str(index*5+i)}for i in range(5)];specs.append(s);consumers.append(panel(s['id']))
        result=shared_stats(specs,pipelines(specs),consumers,PROFILE)
        self.assertEqual(len(set(result.values())),1)
        self.assertIn(' AS m0',result['s0'])
        for i in range(1,15):self.assertIn('m'+str(i)+'=m0',result['s0'])
        self.assertEqual(result['s0'].count('avg(temperature_f)'),1)
    def test_duplicate_timechart_specifiers_preserve_aliases_with_value_copies(self):
        specs=[{'id':'a','recipe':{'kind':'timechart','metrics':[{'function':'count','field':'','alias':'all_readings'}]}},{'id':'b','recipe':{'kind':'timechart','metrics':[{'function':'count','field':'','alias':'history_observations'}]}}]
        before={s['id']:compile_recipe(s['recipe'],'splunk.line',PROFILE,format_values=False)[0]for s in specs};result=shared_stats(specs,before,[],PROFILE,unbound_pool=True)
        self.assertEqual(result['a'],result['b']);self.assertEqual(result['a'],'| timechart bins=100 count AS all_readings | eval history_observations=all_readings')
        raw=[{'id':'a','pipeline':'| timechart bins=100 count AS a count AS b'}]
        result=shared_stats(raw,{'a':raw[0]['pipeline']},[],PROFILE,unbound_pool=True)
        self.assertEqual(result['a'],'| timechart bins=100 count AS a | eval b=a')
    def test_raw_pipelines_are_never_rewritten_or_merged_speculatively(self):
        specs=[source('a','temperature_f','a'),{'id':'b','pipeline':'| where temperature_f<0 | stats avg(wifi_rssi) AS b'}]
        before={'a':compile_recipe(specs[0]['recipe'],'splunk.table',PROFILE,format_values=False)[0],'b':specs[1]['pipeline']}
        self.assertEqual(shared_stats(specs,before,[panel('a'),panel('b')],PROFILE),before)
    def test_exact_literal_stats_can_share_but_complex_expressions_cannot(self):
        specs=[{'id':'a','pipeline':'| stats avg(temperature_f) AS a'}, {'id':'b','pipeline':'| stats count AS b'}]
        before={s['id']:s['pipeline']for s in specs};result=shared_stats(specs,before,[panel('a'),panel('b')],PROFILE)
        self.assertEqual(result['a'],result['b']);self.assertIn('avg(temperature_f) AS a',result['a']);self.assertIn('count AS b',result['a'])
        for unsupported in ('| stats avg(temperature_f+1) AS b','| stats avg(temperature_f) AS b | eval b=round(b,2)','| stats avg(unknown) AS b','| stats sum() AS b','| stats avg(temperature_f) AS b BY host location'):
            specs[1]['pipeline']=unsupported;before={s['id']:s['pipeline']for s in specs}
            self.assertEqual(shared_stats(specs,before,[panel('a'),panel('b')],PROFILE),before)
