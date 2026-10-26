"""Synthetic sparse samples and incomplete metadata, independent of providers/labs."""
import copy,json,unittest
from test_drafts_and_data import DataRuntime,blank
from test_preview_jobs import JobRuntime
from test_reliability_journey import Runtime,Provider,reply
from data_service import DataService
from agent_service import AgentService
from agent_feedback import validate_blank_claim
from provider_service import ProviderError
from search_evidence import sample_completion

class SparseDataTests(unittest.TestCase):
    def fixture(self, rows=None, fields=None):
        class Sample(DataRuntime):
            def preview(self,body):
                self.calls.append(body)
                return {'state':'complete','fields':[{'name':x}for x in (fields or ['entity','mean','readings'])],
                        'results':copy.deepcopy(rows if rows is not None else [{'entity':'fixture_A','readings':'3'}])}
        runtime=Sample();profile=DataService(runtime).profile({'index':'fixture_index'})
        doc={'dataSources':{'s':{'type':'ds.search','options':{'query':'search index="fixture_index" | stats avg(duration) AS mean count AS readings BY entity','queryParameters':{'earliest':'-24h','latest':'now'}}}},
             'visualizations':{'table':{'type':'splunk.table','dataSources':{'primary':'s'},'options':{'table':'> primary | frameBySeriesNames("entity", "mean", "readings")'}}},
             'layout':{'type':'absolute','structure':[{'item':'table'}]}}
        return DataService(runtime),profile,doc
    def test_returned_all_null_column_remains_a_valid_binding_without_filling_values(self):
        service,profile,doc=self.fixture();before=copy.deepcopy(doc)
        receipts=service.validate_searches(doc,{},profile)
        self.assertEqual(receipts[0]['emptyFields'],['mean']);self.assertEqual(doc,before)
        self.assertEqual(receipts[0]['fields'],['entity','mean','readings'])
        self.assertNotIn('fixture_A',json.dumps(receipts))
    def test_missing_schema_alias_still_rejected_with_null_or_partial_values(self):
        service,profile,doc=self.fixture();doc['visualizations']['table']['options']['table']='> primary | frameBySeriesNames("invented")'
        with self.assertRaisesRegex(ProviderError,'missing output fields invented'):service.validate_searches(doc,{},profile)
        service,profile,doc=self.fixture(rows=[],fields=['entity','readings'])
        with self.assertRaisesRegex(ProviderError,'missing output fields mean'):service.validate_searches(doc,{},profile)
    def test_empty_alias_does_not_verify_misspelled_inputs_or_invented_nulls(self):
        service,profile,doc=self.fixture()
        for suffix in ('stats avg(duratoin) AS mean count AS readings BY entity',
                       'eval duration=duratoin | stats avg(duration) AS mean count AS readings BY entity',
                       "stats avg('duratoin') AS mean count AS readings BY entity",
                       'stats count AS readings BY entity | eval mean=null()'):
            candidate=copy.deepcopy(doc);candidate['dataSources']['s']['options']['query']='search index="fixture_index" | '+suffix
            with self.subTest(suffix=suffix),self.assertRaisesRegex(ProviderError,'missing output fields mean'):
                service.validate_searches(candidate,{},profile)
    def test_verified_nullable_aggregation_survives_mask_and_postaggregate_formatting(self):
        service,profile,doc=self.fixture();doc['dataSources']['s']['options']['query']='search index="fixture_index" | eval duration=if(duration<=150,duration,null()) | stats avg(duration) AS mean count AS readings BY entity | eval mean=round(mean,1)'
        result=service.validate_searches(doc,{},profile);self.assertIn('mean',result[0]['emptyFields'])
    def test_nullable_conditional_aggregate_requires_the_same_verified_measurement(self):
        service,profile,doc=self.fixture()
        for function in ('avg','max'):
            doc['dataSources']['s']['options']['query']='search index="fixture_index" | stats '+function+'(eval(if(duration<=150,duration,null()))) AS mean count AS readings BY entity | eval mean=round(mean,1)'
            with self.subTest(function=function): self.assertIn('mean',service.validate_searches(doc,{},profile)[0]['emptyFields'])
        for condition,value in (('duratoin<=150','duration'),('duration<=150','duratoin'),('duration<=150','entity'),('duration<=missing','duration')):
            doc['dataSources']['s']['options']['query']='search index="fixture_index" | stats avg(eval(if('+condition+','+value+',null()))) AS mean count AS readings BY entity'
            with self.subTest(condition=condition,value=value),self.assertRaisesRegex(ProviderError,'missing output fields mean'):
                service.validate_searches(doc,{},profile)
    def test_partial_profile_keeps_completion_and_values_stay_out_of_context(self):
        class Partial(DataRuntime):
            def preview(self,body):
                self.calls.append(body)
                return {'state':'partial','fields':[{'name':'duration'},{'name':'_raw'}],
                        'results':[{'duration':'8','_raw':'PRIVATE EVENT'}],
                        'evidence':{'state':'partial','reasons':['Only the first 200 result rows are shown.','PRIVATE DIAGNOSTIC']}}
        runtime=Partial();profile=DataService(runtime).profile({'query':'search index="fixture_index"','earliest':'-1h'})
        self.assertTrue(runtime.calls[0]['fieldDiscovery']);self.assertEqual(profile['sampledRows'],1)
        self.assertEqual(profile['completion'],{'state':'partial','reasons':['Only the first 200 result rows are shown.']})
        self.assertEqual([x['name']for x in profile['fields']],['duration']);self.assertNotIn('PRIVATE',json.dumps(profile))
        self.assertNotIn('"8"',json.dumps(profile))
    def test_partial_index_profile_is_not_claimed_complete_or_empty(self):
        class Partial(DataRuntime):
            def execute(self,*args):
                r=super().execute(*args);r.update(state='partial',evidence={'reasons':['Search stopped at a resource limit.']});return r
        p=DataService(Partial()).profile({'index':'fixture_index'})
        self.assertEqual(p['completion']['state'],'partial');self.assertEqual(p['sampledRows'],20)
        class Empty(Partial):
            def execute(self,*args):return {'state':'partial','results':[]}
        with self.assertRaises(ProviderError)as caught:DataService(Empty()).profile({'index':'fixture_index'})
        self.assertEqual(caught.exception.code,'profile_partial')
    def test_verbose_profile_search_retains_limits_scope_and_cleanup(self):
        runtime=JobRuntime(rows=201);query='search index="fixture_index"'
        result=runtime.preview({'query':query,'earliest':'-1h','fieldDiscovery':True,'max_time':999})
        params=runtime.calls[0][2]
        self.assertEqual(params['search'].lstrip('| ').strip(),query);self.assertEqual(params['adhoc_search_level'],'verbose')
        self.assertEqual(params['max_time'],'5');self.assertEqual(params['max_count'],'201');self.assertEqual(result['state'],'partial')
        self.assertEqual(runtime.calls[-1][2],{'action':'cancel'})
        runtime=JobRuntime();runtime.preview({'query':query})
        self.assertEqual(runtime.calls[0][2]['adhoc_search_level'],'fast')
    def test_unknown_evidence_does_not_become_complete_or_forward_diagnostics(self):
        self.assertEqual(sample_completion({}),{'state':'unknown','reasons':[]})
        self.assertEqual(sample_completion({'state':'PRIVATE','evidence':{'reasons':[{},'PRIVATE']}}),{'state':'unknown','reasons':[]})
    def test_blank_canvas_does_not_accept_fictional_completion_but_allows_questions(self):
        doc=blank()['definition'];profile={'sampledRows':3}
        for message in ('The dashboard has an Overview with charts.','I created the dashboard.','Completed your dashboard.','Overview shows the readings.'):
            with self.assertRaises(ProviderError):validate_blank_claim(message,doc,doc,profile)
        for message in ('Which field identifies the device?','I have not created it yet. Which unit should I use?','The dashboard has no charts yet.'):
            validate_blank_claim(message,doc,doc,profile)
        provider=Provider([reply([], 'The dashboard has an Overview with charts.'),reply([], 'Which field identifies the device?')])
        result=AgentService(provider,Runtime()).assist({'prompt':'Build from index=fixture_index','revision':0,'definition':doc})
        self.assertTrue(result['repaired']);self.assertEqual(result['recovery']['modelCalls'],2)
        self.assertIn('canvas is still blank',result['validationNotes'][0]);self.assertEqual(result['changes'],[])
