"""One repair receives all bounded source/binding failures and reuses good checks."""
import json
import unittest
from test_drafts_and_data import blank
from test_reliability_journey import Provider, Runtime, reply
from agent_service import AgentService
from studio_contract import apply_changes

class ValidationFeedbackTests(unittest.TestCase):
    def test_spl_formatting_in_dos_is_rejected_with_actionable_feedback(self):
        from test_search_chart_actions import chart, page
        original=blank()['definition']
        initial=[{'op':'search','id':'events','pipeline':'| stats count'},chart('splunk.table','',['count']),page(),
                 {'op':'set','path':'/visualizations/trend/options/table','value':json.dumps('> primary | eval count=round(count) | frameBySeriesNames("count")')}]
        repair=[{'op':'set','path':'/visualizations/trend/options/table','value':json.dumps('> primary | frameBySeriesNames("count")')}]
        provider=Provider([reply(initial),reply(repair)])
        result=AgentService(provider,Runtime()).assist({'prompt':'Build with index=fixture_index','revision':0,'definition':original,'dataContext':blank()['dataContext']})
        feedback=json.loads(provider.requests[1]['input'][-1]['content'][0]['text'])
        self.assertIn('SPL eval is not a native DOS',feedback['validationError'])
        self.assertEqual(result['recovery']['modelCalls'],2);self.assertFalse(original['visualizations'])
    def test_one_repair_gets_unsafe_token_and_all_populated_field_errors(self):
        original=blank()['definition']
        sources={'filtered':{'type':'ds.search','options':{'query':'search index="fixture_index" | search host=$chosen$ | stats count','queryParameters':{'earliest':'-24h','latest':'now'}}},
                 'good':{'type':'ds.search','options':{'query':'search index="fixture_index" | stats count','queryParameters':{'earliest':'-24h','latest':'now'}}}}
        charts={'metric':{'type':'splunk.singlevalue','dataSources':{'primary':'good'},'options':{'majorValue':'> primary | seriesByName("missing") | lastPoint()'}},
                'table':{'type':'splunk.table','dataSources':{'primary':'good'},'options':{'table':'> primary | frameBySeriesNames("also_missing")'}}}
        initial=[{'op':'set','path':'/dataSources','value':json.dumps(sources)},
                 {'op':'set','path':'/visualizations','value':json.dumps(charts)},
                 {'op':'token','name':'chosen','value':'*'},
                 {'op':'layout','layoutId':'overview','label':'Overview','width':1200,'height':600,'items':[{'id':'metric','kind':'block','x':20,'y':20,'w':400,'h':200},{'id':'table','kind':'block','x':440,'y':20,'w':700,'h':400}]}]
        patch=[{'op':'set','path':'/dataSources/filtered/options/query','value':json.dumps(sources['filtered']['options']['query'].replace('$chosen$','$chosen|s$'))},
               {'op':'set','path':'/visualizations/metric/options/majorValue','value':json.dumps('> primary | seriesByName("count") | lastPoint()')},
               {'op':'set','path':'/visualizations/table/options/table','value':json.dumps('> primary | frameBySeriesNames("count")')}]
        provider=Provider([reply(initial),reply(patch)]);result=AgentService(provider,Runtime()).assist({'prompt':'Build a board with index=fixture_index','definition':original,'revision':0,'dataContext':blank()['dataContext']})
        feedback=json.loads(provider.requests[1]['input'][-1]['content'][0]['text'])['recoveryFeedback']
        self.assertIn('Source filtered',feedback['validationError']);self.assertIn('|s',feedback['validationError'])
        self.assertIn('Visualization metric',feedback['validationError']);self.assertIn('Visualization table',feedback['validationError'])
        self.assertNotIn('PRIVATE EVENT VALUE',json.dumps(feedback))
        self.assertEqual(result['recovery']['modelCalls'],2);self.assertEqual(result['recovery']['queryChecks'],2)
        self.assertFalse(original['visualizations']);self.assertEqual(len(apply_changes(original,result['changes'])['visualizations']),2)
