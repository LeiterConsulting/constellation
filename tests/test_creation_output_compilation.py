"""Explicit raw columns are compiled narrowly and still checked against output."""
import copy,json,unittest
from test_creation_page_scope import fixture
from test_creation_recipes import PROFILE
from test_drafts_and_data import blank
from test_reliability_journey import Runtime,Provider,reply
from table_projection import compile_creation_columns,validate_creation_columns
from creation_page_scope import normalize_creation_page_scope
from studio_contract import apply_changes
from agent_service import AgentService
from provider_service import ProviderError

PROMPT='Build two pages. Click a device to investigate it. Add a raw reading table with _time, device_name, duration.'

class CreationColumnTests(unittest.TestCase):
    def fixture(self):
        doc=fixture();doc['dataSources']['raw']['options']['query']=PROFILE['baseQuery']+' | search device_name=$selected_device|s$ | table device_name duration'
        doc['visualizations']['raw']['options']['table']='> primary | frameBySeriesNames("device_name", "duration")'
        return doc
    def test_missing_time_is_restored_in_the_query_and_display_preserving_other_work(self):
        doc=self.fixture();before=copy.deepcopy(doc);result=apply_changes(doc,compile_creation_columns(PROMPT,doc,{},PROFILE))
        self.assertEqual(doc,before);self.assertEqual(result['dataSources']['raw']['options']['query'],doc['dataSources']['raw']['options']['query']+' _time')
        self.assertEqual(result['visualizations']['raw']['options']['table'],'> primary | frameBySeriesNames("_time", "device_name", "duration")')
        result['dataSources']['raw']['options']['query']=doc['dataSources']['raw']['options']['query'];result['visualizations']['raw']=doc['visualizations']['raw'];self.assertEqual(result,doc)
    def test_unknown_removed_computed_shared_and_advanced_fields_are_not_invented(self):
        doc=self.fixture()
        for suffix in ('| fields - _time | table device_name duration', '| eval _time=unknown | table device_name duration', '| table device_name duration | where _time>1', '| stats count BY device_name'):
            bad=copy.deepcopy(doc);bad['dataSources']['raw']['options']['query']=PROFILE['baseQuery']+' '+suffix
            self.assertEqual(compile_creation_columns(PROMPT,bad,{},PROFILE),[])
        bad=copy.deepcopy(doc);bad['visualizations']['other_raw']=copy.deepcopy(bad['visualizations']['raw']);self.assertEqual(compile_creation_columns(PROMPT,bad,{},PROFILE),[])
        bad=copy.deepcopy(doc);bad['visualizations']['raw']['options']['table']='> primary | frameBySeriesNames("device_name") | filter(foo)';self.assertEqual(compile_creation_columns(PROMPT,bad,{},PROFILE),[])
        self.assertEqual(compile_creation_columns(PROMPT,doc,doc,PROFILE),[])
        self.assertEqual(compile_creation_columns(PROMPT+' Add another raw table with duration.',doc,{},PROFILE),[])
    def test_native_missing_output_still_rejects_the_compiled_projection(self):
        doc=apply_changes(self.fixture(),compile_creation_columns(PROMPT,self.fixture(),{},PROFILE))
        with self.assertRaisesRegex(ProviderError,'_time'):
            validate_creation_columns(PROMPT,doc,{},PROFILE,[{'source':'raw','fields':['device_name','duration']}])
    def test_complete_service_compiles_scope_and_columns_with_one_model_call(self):
        class Outputs(Runtime):
            def preview(self,body):
                self.calls.append(body)
                if body.get('fieldDiscovery'):
                    return {'state':'complete','fields':[{'name':n}for n in ('_time','device_name','duration')], 'results':[{'_time':'1700000000','device_name':'fixture_A','duration':'12'}]}
                fields=['_time','device_name','duration']if'| table'in body['query']else ['_time','device_name','mean']
                return {'state':'complete','fields':[{'name':n}for n in fields], 'results':[{f:'12'for f in fields}]}
        doc=self.fixture();changes=[{'op':'set','path':'/'+k,'value':json.dumps(v)}for k,v in doc.items()if k!='future']
        provider=Provider([reply(changes)]);runtime=Outputs();original=blank()['definition'];before=copy.deepcopy(original)
        result=AgentService(provider,runtime).assist({'prompt':PROMPT,'revision':0,'definition':original,'dataContext':blank()['dataContext']});final=apply_changes(original,result['changes'])
        self.assertFalse(result['repaired']);self.assertEqual(result['recovery']['modelCalls'],1);self.assertEqual(result['recovery']['queryChecks'],4)
        self.assertNotIn('$selected_device',final['dataSources']['trend']['options']['query']);self.assertIn('_time',final['dataSources']['raw']['options']['query']);self.assertEqual(original,before)
        self.assertTrue(all('fixture_A'not in json.dumps(r)for r in provider.requests))

if __name__=='__main__':unittest.main()
