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
            checks={key:True for key in bench.required_checks(case)}
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
            if 'AS probe_rows'in query:
                return {'fields':[{'name':k}for k in ('device_name','probe_rows','probe_t','probe_wifi')],
                        'results':[{'device_name':e,'probe_rows':4 if e=='fixture_alpha'else 3,'probe_t':2,'probe_wifi':4 if e=='fixture_alpha'else 3}for e in entities]}
            return {'fields':[{'name':k}for k in ('device_name','count','avg_f','avg_rssi','valid_t','valid_wifi')],
                    'results':[{'device_name':e,'count':1}for e in entities]}
        self.assertTrue(all(bench.grade(response,case,reply).values()))
        self.assertTrue(any('| search device_name="fixture_alpha"'in q for q in seen))
        self.assertTrue(any('| search device_name="fixture_beta"'in q for q in seen))
    def test_raw_detail_projection_does_not_remove_the_key_from_the_independent_row_probe(self):
        case=next(c for c in bench.cases()if c['id']=='row_detail');doc=case['body']['definition'];seen=[]
        plan=[{'op':'rowDetail','field':'device_name','label':'Details','purpose':'Inspect readings','panels':[
            {'type':'splunk.table','title':'Readings','pipeline':'| eval temperature_f=if(temperature_f<=150,temperature_f,null()) | table _time temperature_f wifi_rssi | sort - _time','x':'','y':['_time','temperature_f','wifi_rssi']}]}]
        actions=row_navigation.expand_plan(plan,doc,'summary',bench.PROFILE,{'fields':[{'name':'device_name','numeric':False}]})
        doc=apply_changes(doc,compile_actions(doc,actions,bench.PROFILE))
        def call(_action,body):
            query=body['query'];seen.append(query)
            self.assertNotIn('| table',query)
            entities=['fixture_alpha']if 'device_name="fixture_alpha"'in query else ['fixture_beta']if 'device_name="fixture_beta"'in query else ['fixture_alpha','fixture_beta']
            return {'results':[{'device_name':e,'probe_rows':4 if e=='fixture_alpha'else 3,'probe_t':2,'probe_wifi':4 if e=='fixture_alpha'else 3}for e in entities]}
        self.assertTrue(bench.navigation_checks(call,case,doc));self.assertEqual(len(seen),3)
    def test_larger_tasks_are_bounded_and_failed_large_route_is_not_compensated(self):
        cases={c['id']:c for c in bench.cases()}
        self.assertEqual(len(cases),12)
        self.assertEqual(cases['create_8']['batch'],8)
        for name in ('large_route','large_format'):
            doc=cases[name]['body']['definition'];self.assertEqual(len(doc['visualizations']),32)
            self.assertEqual(len(doc['layout']['tabs']['items']),4)
            self.assertLessEqual(len(doc['dataSources']),8)
        good=self.records();self.assertEqual(bench.score(good)['candidateBatchPanels'],8)
        good[-3]['checks']['preservation']=False
        self.assertFalse(bench.score(good)['criticalGatesPassed'])
    def test_existing_route_grader_preserves_unknowns_shared_sources_and_query_transformations(self):
        case=next(c for c in bench.cases()if c['id']=='large_route');old=case['body']['definition']
        actions=[{'op':'route','sourceId':'summary','pageId':'coverage','field':'device_name','returnLabel':'Back to Overview'}]
        doc=apply_changes(old,compile_actions(old,actions,bench.PROFILE))
        self.assertTrue(bench.preserved_route(old,doc,'coverage'))
        bad=copy.deepcopy(doc);bad['visualizations']['summary'].pop('futureFixture')
        self.assertFalse(bench.preserved_route(old,bad,'coverage'))
        bad=copy.deepcopy(doc);bad['dataSources']['summary_source']['options']['query']+=' | head 1'
        self.assertFalse(bench.preserved_route(old,bad,'coverage'))
        bad=copy.deepcopy(doc);sid=bad['visualizations']['coverage_count']['dataSources']['primary'];bad['dataSources'][sid]['options']['query']+=' | eval source_rows=0'
        self.assertFalse(bench.preserved_route(old,bad,'coverage'))
    def test_concrete_route_probe_accepts_temperature_subset_but_rejects_lost_independent_wifi(self):
        case=next(c for c in bench.cases()if c['id']=='row_detail');old=case['body']['definition']
        for metric,accepted in (('temperature_f',True),('wifi_rssi',False)):
            plan=[{'op':'rowDetail','field':'device_name','label':'Details','purpose':'Inspect readings','panels':[
                {'type':'splunk.singlevalue','title':'Average','pipeline':'| eval temperature_f=if(temperature_f<=150,temperature_f,null()) | where temperature_f<=150 | stats avg('+metric+') AS average','x':'','y':['average']}]}]
            actions=row_navigation.expand_plan(plan,old,'summary',bench.PROFILE,{'fields':[{'name':'device_name','numeric':False}]})
            doc=apply_changes(old,compile_actions(old,actions,bench.PROFILE))
            def call(_action,body):
                query=body['query'];entities=['fixture_alpha']if 'device_name="fixture_alpha"'in query else ['fixture_beta']if 'device_name="fixture_beta"'in query else ['fixture_alpha','fixture_beta']
                return {'results':[{'device_name':e,'probe_rows':2,'probe_t':2,'probe_wifi':2}for e in entities]}
            self.assertEqual(bench.navigation_checks(call,case,doc),accepted)


if __name__=='__main__':unittest.main()
