"""Existing native route edits preserve unrelated work and filter before aggregation."""
import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'splunk/constellation/bin'))
from authoring_actions import compile_actions
from authoring_intent import validate_page_intent
from route_actions import validate_route_intent
from studio_contract import apply_changes
from provider_service import ProviderError
from scripts.authoring_benchmark import golden, PROFILE
from route_actions import focused_route, focused_button_route
from agent_service import AgentService
from test_reliability_journey import Provider,reply


def fixture():
    doc=golden();doc['layout']['future']={'preserve':True}
    doc['visualizations']['summary']['future']={'preserve':True}
    doc['dataSources']['summary_source']['options']['future']={'preserve':True}
    doc['defaults']={'tokens':{'default':{'device':{'value':'*','future':True}}}}
    actions=[]
    for name in ('details','coverage'):
        actions.extend([{'op':'search','id':name+'_source','pipeline':'| stats count AS rows'},
            {'op':'chart','id':name+'_count','chartType':'splunk.singlevalue','title':name+' observations','description':'',
             'sourceId':name+'_source','x':'','y':['rows']},
            {'op':'page','layoutId':name,'label':name.title(),'purpose':'Inspect fixture observations','moveItems':False,
             'width':1200,'height':800,'items':[{'id':name+'_count','kind':'block','x':20,'y':20,'w':570,'h':360}]}])
    actions.extend([{'op':'chart','id':'coverage_table','chartType':'splunk.table','title':'Coverage by device','description':'',
                     'sourceId':'summary_source','x':'','y':['device_name','avg_f','avg_rssi','valid_t','valid_wifi']},
                    {'op':'page','layoutId':'coverage','label':'Coverage','purpose':'Verify coverage','moveItems':False,
                     'width':1200,'height':800,'items':[{'id':'coverage_table','kind':'block','x':20,'y':400,'w':1160,'h':360}]},
                    {'op':'filter','sourceId':'details_source','field':'device_name','token':'device'},
                    {'op':'link','sourceId':'summary','pageId':'details','targetId':'','field':'device_name','token':'device'},
                    {'op':'button','id':'old_back','pageId':'details','targetPageId':'layout_main','targetId':'','label':'Back','x':20,'y':500,'w':300,'h':80}])
    return apply_changes(doc,compile_actions(doc,actions,PROFILE))


class RouteTests(unittest.TestCase):
    def action(self):return {'op':'route','sourceId':'summary','pageId':'coverage','field':'device_name','returnLabel':'Back to Overview'}
    def test_retarget_filters_all_destination_sources_clones_shared_search_and_is_idempotent(self):
        doc=fixture();before=copy.deepcopy(doc)
        result=apply_changes(doc,compile_actions(doc,[self.action()],PROFILE))
        self.assertEqual(doc,before)
        self.assertEqual(result['dataSources']['summary_source'],doc['dataSources']['summary_source'])
        self.assertEqual(result['dataSources']['details_source'],doc['dataSources']['details_source'])
        self.assertEqual(result['visualizations']['details_count'],doc['visualizations']['details_count'])
        self.assertEqual(result['inputs']['old_back'],doc['inputs']['old_back'])
        self.assertEqual(result['layout']['layoutDefinitions']['details'],doc['layout']['layoutDefinitions']['details'])
        self.assertEqual(result['layout']['future'],{'preserve':True})
        for key in ('coverage_count','coverage_table'):
            sid=result['visualizations'][key]['dataSources']['primary']
            query=result['dataSources'][sid]['options']['query']
            self.assertIn('| search device_name=$device|s$ |',query)
            self.assertLess(query.index('search device_name='),query.index('| stats'))
        clone=result['visualizations']['coverage_table']['dataSources']['primary']
        self.assertNotEqual(clone,'summary_source')
        self.assertEqual(result['dataSources'][clone]['options']['future'],{'preserve':True})
        self.assertEqual(result['defaults'],doc['defaults'])
        validate_route_intent('Retarget this row and filter both destination charts. Add a Back button.',result,doc,PROFILE,{'kind':'visualization','id':'summary'})
        self.assertEqual(apply_changes(result,compile_actions(result,[self.action()],PROFILE)),result)
    def test_unknown_field_source_type_and_reused_chart_are_rejected_atomically(self):
        doc=fixture();before=copy.deepcopy(doc)
        for update in ({'field':'invented'},{'pageId':'missing'},{'pageId':'layout_main'},{'sourceId':'coverage_count'}):
            with self.subTest(update=update),self.assertRaises(ProviderError):compile_actions(doc,[dict(self.action(),**update)],PROFILE)
        for source_type in ('ds.chain','ds.spl2'):
            bad=copy.deepcopy(doc);bad['dataSources']['coverage_source']['type']=source_type
            with self.assertRaises(ProviderError):compile_actions(bad,[self.action()],PROFILE)
        bad=copy.deepcopy(doc);bad['layout']['layoutDefinitions']['details']['structure'].append(copy.deepcopy(bad['layout']['layoutDefinitions']['coverage']['structure'][0]))
        with self.assertRaisesRegex(ProviderError,'reused'):compile_actions(bad,[self.action()],PROFILE)
        self.assertEqual(doc,before)
    def test_revised_route_cannot_pass_with_one_unfiltered_source_or_return_on_wrong_page(self):
        doc=fixture();result=apply_changes(doc,compile_actions(doc,[self.action()],PROFILE))
        prompt='Change the table row route and filter every destination chart. Add a Back button.'
        bad=copy.deepcopy(result);bad['dataSources']['coverage_source']=doc['dataSources']['coverage_source']
        with self.assertRaisesRegex(ProviderError,'before aggregation'):validate_route_intent(prompt,bad,doc,PROFILE,{'kind':'visualization'})
        bad=copy.deepcopy(result);sid=bad['visualizations']['coverage_count']['dataSources']['primary']
        bad['dataSources'][sid]['options']['query']=PROFILE['baseQuery']+' | stats count | search device_name=$device|s$'
        with self.assertRaises(ProviderError):validate_route_intent(prompt,bad,doc,PROFILE,{'kind':'visualization'})
        bad=copy.deepcopy(result);bad['inputs']={'old_back':bad['inputs']['old_back']}
        with self.assertRaisesRegex(ProviderError,'return navigation'):validate_route_intent(prompt,bad,doc,PROFILE,{'kind':'visualization'})
        validate_route_intent(prompt,doc,doc,PROFILE,{'kind':'visualization'})
    def test_button_edit_is_direct_navigation_and_still_checks_selected_destination(self):
        doc=fixture();result=apply_changes(doc,compile_actions(doc,[self.action()],PROFILE))
        key=next(key for key in result['inputs']if key!='old_back')
        prompt='Change only this selected Back button: rename it "Open Details" and make it open Details instead of Overview. Preserve the current device filter.'
        focus={'kind':'input','id':key}
        with self.assertRaisesRegex(ProviderError,'selected navigation button'):validate_page_intent(prompt,'Updated',result,result,focus)
        changed=apply_changes(result,compile_actions(result,[{'op':'buttonRoute','id':key,'pageId':'details','label':'Open Details'}],PROFILE))
        validate_page_intent(prompt,'Updated the button.',changed,result,focus)
        self.assertEqual(changed['visualizations'],result['visualizations'])
        expected=copy.deepcopy(result);expected['inputs'][key]=changed['inputs'][key]
        self.assertEqual(changed,expected)
        self.assertIsNotNone(focused_button_route(prompt,result,key,[]))
        for text in (prompt+' Add a chart.',prompt+' Move it below the chart.'):
            self.assertIsNone(focused_button_route(text,result,key,[]))
        with self.assertRaisesRegex(ProviderError,'existing rectangle'):
            compile_actions(result,[{'op':'buttonRoute','id':key,'pageId':'details','label':'Too long '*10}],PROFILE)
    def test_focused_reroute_needs_evidence_unambiguous_destination_and_no_other_edit_goal(self):
        doc=fixture();receipt={'fields':[{'name':'device_name','numeric':False},{'name':'numeric_id','numeric':True}]}
        prompt='Retarget this existing table row drilldown to open Coverage. Filter every Coverage chart and add a Back button.'
        schema=focused_route(prompt,doc,'summary',PROFILE,receipt,[])
        self.assertEqual(schema['properties']['pageId']['enum'],['coverage'])
        self.assertEqual(schema['properties']['field']['enum'],['device_name'])
        for text in (prompt+' Add a new chart.',prompt+' Rename the Details page.',prompt.replace('Filter every','Preserve the')):
            self.assertIsNone(focused_route(text,doc,'summary',PROFILE,receipt,[]))
        self.assertIsNone(focused_route(prompt,doc,'summary',PROFILE,{'fields':[]},[]))
        self.assertIsNone(focused_route(prompt,doc,'summary',PROFILE,receipt,[{'file':'not sent'}]))
        bad=copy.deepcopy(doc);bad['layout']['tabs']['items'][1]['label']='Coverage'
        self.assertIsNone(focused_route(prompt,bad,'summary',PROFILE,receipt,[]))
    def test_schema_ignoring_provider_cannot_retarget_another_page_or_edit_existing_queries(self):
        class Runtime:
            def environment(self):return {'version':'10.4.4','features':{}}
            def datasets(self):return {'indexes':[]}
            def preview(self,body):
                if body.get('fieldDiscovery'):
                    return {'fields':[{'name':k}for k in ('device_name','temperature_f','wifi_rssi','_time')],
                            'results':[{'device_name':'PRIVATE_ROW_VALUE','temperature_f':32,'wifi_rssi':-42,'_time':1234}],'state':'complete'}
                names=('device_name','avg_f','avg_rssi','valid_t','valid_wifi','rows')
                return {'fields':[{'name':k}for k in names],'results':[dict(zip(names,('PRIVATE_ROW_VALUE',32,-42,1,1,1)))],'state':'complete'}
        from scripts.authoring_benchmark import SCOPE
        doc=fixture();before=copy.deepcopy(doc)
        prompt='Retarget this existing table row drilldown to open Coverage. Filter every Coverage chart and add a Back to Overview button.'
        bad={'op':'set','path':'/title','value':'"Unrelated change"'}
        provider=Provider([reply([bad]),reply([self.action()])])
        result=AgentService(provider,Runtime()).assist({'prompt':prompt,'revision':0,'definition':doc,'selected':'summary','dataContext':SCOPE,
            'history':[{'role':'user','text':'Previously edit a different button.'}]})
        context=json.loads(provider.requests[0]['input'][0]['content'][0]['text'])
        self.assertNotIn('definition',context);self.assertEqual(list(context)[-1],'request')
        self.assertEqual(context['routeOnly']['pageId'],['coverage'])
        self.assertNotIn('PRIVATE_ROW_VALUE',json.dumps(provider.requests))
        self.assertEqual(provider.requests[0]['max_output_tokens'],1500)
        self.assertEqual(result['recovery']['modelCalls'],2)
        self.assertEqual(doc,before)
        feedback=json.loads(provider.requests[1]['input'][-1]['content'][0]['text'])['recoveryFeedback']
        self.assertEqual(feedback['editsApplyTo'],'original');self.assertNotIn('candidateDefinition',feedback)
    def test_stale_button_reply_cannot_satisfy_selected_page_rename(self):
        doc=fixture();focus={'kind':'page','id':'coverage'}
        prompt='Rename only this selected page from Coverage to Data quality. Its purpose is to explain completeness. Preserve navigation.'
        with self.assertRaisesRegex(ProviderError,'Rename the focused'):validate_page_intent(prompt,'Updated the previous button.',doc,doc,focus)
        changed=copy.deepcopy(doc);next(t for t in changed['layout']['tabs']['items']if t['layoutId']=='coverage')['label']='Data quality'
        validate_page_intent(prompt,'Renamed the page.',changed,doc,focus)
    def test_page_metadata_plan_preserves_native_work_and_cannot_write_native_purpose_paths(self):
        from page_service import proposed_purposes,focused_page_meta
        doc=fixture();before=copy.deepcopy(doc)
        action={'op':'pageMeta','layoutId':'coverage','label':'Data quality','purpose':'Explain measurement coverage'}
        result=apply_changes(doc,compile_actions(doc,[action],PROFILE))
        expected=copy.deepcopy(doc);next(t for t in expected['layout']['tabs']['items']if t['layoutId']=='coverage')['label']='Data quality'
        self.assertEqual(result,expected);self.assertEqual(doc,before)
        purposes=proposed_purposes([action],{'details':'Keep this purpose'},result)
        self.assertEqual(purposes,{'details':'Keep this purpose','coverage':'Explain measurement coverage'})
        focus={'kind':'page','id':'coverage'}
        schema=focused_page_meta('Rename only this selected page from Coverage to Data quality.',doc,focus,[])
        self.assertEqual(schema['properties']['layoutId']['enum'],['coverage'])
        self.assertIsNone(focused_page_meta('Rename this page and add a chart.',doc,focus,[]))
        with self.assertRaises(ProviderError):compile_actions(doc,[dict(action,layoutId='missing')],PROFILE)


if __name__=='__main__':unittest.main()
