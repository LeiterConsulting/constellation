"""Focused pipeline edits retain scope/columns and reject schema-ignoring writes."""
import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'splunk/constellation/bin'))
from scripts import authoring_benchmark as bench
from table_projection import focused_calculation
from agent_service import AgentService
from authoring_actions import compile_actions
from studio_contract import apply_changes
from test_reliability_journey import Provider,reply


class Runtime:
    def environment(self):return {'version':'10.4.4','features':{}}
    def datasets(self):return {'indexes':[]}
    def preview(self,body):
        if body.get('fieldDiscovery'):return {'fields':[{'name':k}for k in ('device_name','temperature_f','wifi_rssi')],
            'results':[{'device_name':'PRIVATE_ROW_VALUE','temperature_f':32,'wifi_rssi':-42}],'state':'complete'}
        fields=['device_name','avg_f','avg_rssi','valid_t','valid_wifi']
        if 'AS peak_f'in body['query']:fields.append('peak_f')
        return {'fields':[{'name':f}for f in fields],'results':[{f:'PRIVATE_ROW_VALUE'if f=='device_name'else 2 for f in fields}],'state':'complete'}


class FocusedCalculationTests(unittest.TestCase):
    def test_wrong_actions_and_missing_alias_recover_in_one_scoped_pipeline_preserving_unknowns(self):
        case=next(c for c in bench.cases()if c['id']=='focused_metric');body=case['body'];old=copy.deepcopy(body['definition']);sid=old['visualizations'][body['selected']]['dataSources']['primary']
        pipeline=old['dataSources'][sid]['options']['query'][len(bench.BASE):]
        bad={'op':'set','path':'/title','value':'"Unrelated title"'}
        unchanged={'op':'search','id':sid,'pipeline':pipeline}
        correct={'op':'search','id':sid,'pipeline':pipeline.replace(' BY device_name',' max(temperature_f) AS peak_f BY device_name')}
        provider=Provider([reply([bad]),reply([unchanged]),reply([correct])])
        result=AgentService(provider,Runtime()).assist(body);doc=apply_changes(old,result['changes'])
        self.assertEqual(result['recovery']['modelCalls'],3);self.assertEqual(body['definition'],old)
        context=json.loads(provider.requests[0]['input'][0]['content'][0]['text'])
        self.assertNotIn('definition',context);self.assertEqual(context['calculationOnly']['sourceId'],sid)
        self.assertNotIn('PRIVATE_ROW_VALUE',json.dumps(provider.requests));self.assertEqual(provider.requests[0]['max_output_tokens'],3500)
        for item in provider.requests[1:]:
            feedback=json.loads(item['input'][-1]['content'][0]['text'])['recoveryFeedback']
            self.assertEqual(feedback['editsApplyTo'],'original');self.assertNotIn('candidateDefinition',feedback)
        expected=copy.deepcopy(old);expected['dataSources'][sid]=doc['dataSources'][sid];expected['visualizations'][body['selected']]['options']['table']=doc['visualizations'][body['selected']]['options']['table']
        self.assertEqual(doc,expected);self.assertIn('peak_f',doc['visualizations'][body['selected']]['options']['table'])
    def test_shared_sources_other_languages_files_and_unverified_fields_stay_general(self):
        case=next(c for c in bench.cases()if c['id']=='focused_metric');body=case['body'];doc=body['definition'];selected=body['selected'];receipt={'fields':[{'name':n}for n in ('device_name','avg_f','avg_rssi','valid_t','valid_wifi')]}
        self.assertIsNotNone(focused_calculation(body['prompt'],selected,doc,bench.PROFILE,receipt,[]))
        for profile,files in ((dict(bench.PROFILE,scope={'language':'spl2'}),[]),(bench.PROFILE,[{'file':'not sent'}]),(dict(bench.PROFILE,fields=[]),[])):
            self.assertIsNone(focused_calculation(body['prompt'],selected,doc,profile,receipt,files))
        shared=copy.deepcopy(doc);shared['visualizations']['another']=copy.deepcopy(shared['visualizations'][selected])
        self.assertIsNone(focused_calculation(body['prompt'],selected,shared,bench.PROFILE,receipt,[]))


if __name__=='__main__':unittest.main()
