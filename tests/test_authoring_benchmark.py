"""Benchmark grading uses independent numeric answers and noncompensating gates."""
import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import authoring_benchmark as bench
from studio_contract import apply_changes
from authoring_actions import compile_actions
import row_navigation


class BenchmarkTests(unittest.TestCase):
    def records(self):
        result=[]
        for case in bench.cases():
            checks={'completion':True,'scope':True,'bindings':True}
            if case.get('population'):checks['population']=True
            if case.get('navigation'):checks.update(navigation=True,preservation=True)
            if case.get('format'):checks['preservation']=True
            result.append({'case':case['id'],'checks':checks,'modelCalls':1})
        return result
    def test_critical_failure_cannot_be_hidden_by_weighted_points_or_successful_big_batch(self):
        good=self.records();self.assertEqual(bench.score(good)['weightedScore'],100)
        bad=copy.deepcopy(good);bad[3]['checks']['navigation']=False
        score=bench.score(bad);self.assertGreater(score['weightedScore'],90)
        self.assertFalse(score['criticalGatesPassed']);self.assertFalse(score['productionQualified'])
        bad=copy.deepcopy(good);bad[0]['checks']['bindings']=False
        self.assertFalse(bench.score(bad)['criticalGatesPassed'])
        bad=copy.deepcopy(good);bad[1]['checks']['population']=False
        self.assertEqual(bench.score(bad)['candidateBatchPanels'],1)
        self.assertFalse(bench.score([{'case':'row_detail','checks':{'completion':True}}])['criticalGatesPassed'])
        with self.assertRaises(ValueError):bench.score([{'case':'invented','checks':{}}])
    def test_semantic_fixture_oracle_detects_dropped_wifi_and_boundary_temperature_errors(self):
        case=next(c for c in bench.cases()if c['id']=='focused_format');doc=case['body']['definition']
        query=doc['dataSources']['summary_source']['options']['query']+' | eval avg_f=round(avg_f,1), avg_rssi=round(avg_rssi,1)'
        reply={'changes':[{'op':'set','path':'/dataSources/summary_source/options/query','value':json.dumps(query)}]}
        rows=[{'device_name':'fixture_alpha','avg_f':91,'avg_rssi':-42.5,'valid_t':2,'valid_wifi':4},
              {'device_name':'fixture_beta','avg_f':5,'avg_rssi':-46,'valid_t':2,'valid_wifi':3}]
        def response(_action,_body):return {'fields':[{'name':k}for k in rows[0]],'results':rows}
        self.assertTrue(all(bench.grade(response,case,reply).values()))
        rows[0]['valid_wifi']=2
        self.assertFalse(bench.grade(response,case,reply)['population'])
        rows[0]['valid_wifi']=4;rows[0]['avg_f']=32  # Incorrectly excludes exactly 150 F.
        self.assertFalse(bench.grade(response,case,reply)['population'])
    def test_unscoped_output_is_never_executed_and_fixture_is_bounded_synthetic_only(self):
        doc=bench.golden();doc['dataSources']['summary_source']['options']['query']='search index=unselected | stats count'
        called=[]
        with self.assertRaises(ValueError):bench.checked_query(lambda *args:called.append(args),doc,'summary_source')
        self.assertFalse(called)
        for case in bench.cases():
            self.assertEqual(case['body']['dataContext']['query'],bench.BASE)
            self.assertNotIn('index=',bench.BASE)
        self.assertFalse(bench.score([])['criticalGatesPassed'])
    def test_row_grader_executes_both_concrete_native_token_values_and_preserves_original(self):
        case=next(c for c in bench.cases()if c['id']=='row_detail');doc=case['body']['definition'];receipt={'fields':[{'name':'device_name','numeric':False}]}
        plan=[{'op':'rowDetail','field':'device_name','label':'Details','purpose':'Inspect a device',
               'panels':[{'type':'splunk.table','title':'Readings','pipeline':'| stats count BY device_name','x':'','y':['device_name','count']}]}]
        actions=row_navigation.expand_plan(plan,doc,'summary',bench.PROFILE,receipt);reply={'changes':compile_actions(doc,actions,bench.PROFILE)};seen=[]
        def response(_action,body):
            query=body['query'];seen.append(query)
            entities=['fixture_alpha']if '| search device_name="fixture_alpha"'in query else ['fixture_beta']if '| search device_name="fixture_beta"'in query else ['fixture_alpha','fixture_beta']
            return {'fields':[{'name':k}for k in ('device_name','count','avg_f','avg_rssi','valid_t','valid_wifi')],
                    'results':[{'device_name':e,'count':1}for e in entities]}
        self.assertTrue(all(bench.grade(response,case,reply).values()))
        self.assertTrue(any('| search device_name="fixture_alpha"'in q for q in seen))
        self.assertTrue(any('| search device_name="fixture_beta"'in q for q in seen))


if __name__=='__main__':unittest.main()
