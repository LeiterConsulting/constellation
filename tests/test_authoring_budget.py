"""Staged authoring remains atomic, bounded and grounded in verified queries."""
import copy
import json
import unittest
from test_drafts_and_data import blank
from test_reliability_journey import Provider, Runtime, reply
from test_search_chart_actions import chart, page, PROFILE
from agent_service import AgentService
from authoring_actions import compile_actions
from studio_contract import apply_changes
from provider_service import ProviderError
from authoring_budget import AuthoringBudget

class AuthoringBudgetTests(unittest.TestCase):
    def test_two_internal_stages_complete_before_any_changes_are_returned(self):
        first=[{'op':'search','id':'events','pipeline':'| stats count'},chart('splunk.table','',['count']),page()]
        second=dict(page(),layoutId='details',label='Details',purpose='Investigate counts')
        class StagedProvider(Provider):
            def configured(self):return {'provider':'aitk','model':'fixture'}
        original=blank()['definition'];runtime=Runtime();provider=StagedProvider([reply(first),reply([second])])
        result=AgentService(provider,runtime).assist({'prompt':'Build two pages with index=fixture_index','revision':0,'definition':original,'dataContext':blank()['dataContext']})
        self.assertFalse(original['visualizations']);self.assertEqual(result['recovery']['modelCalls'],2)
        self.assertEqual(result['recovery']['queryChecks'],1)
        doc=apply_changes(original,result['changes']);self.assertEqual(len(doc['layout']['tabs']['items']),2)
        context=json.loads(provider.requests[1]['input'][0]['content'][0]['text'])
        self.assertIn('COMPLETE THE ORIGINAL',context['authoringStage']);self.assertIn('trend',context['definition']['visualizations'])
        self.assertIn('internal stages',json.dumps(result['activity']))
    def test_failed_completion_does_not_publish_foundation_or_change_original(self):
        first=[{'op':'search','id':'events','pipeline':'| stats count'},chart('splunk.table','',['count']),page()]
        class StagedProvider(Provider):
            def configured(self):return {'provider':'ollama','model':'fixture'}
        original=blank()['definition'];before=copy.deepcopy(original)
        provider=StagedProvider([reply(first),reply([]),reply([])])
        with self.assertRaises(ProviderError):AgentService(provider,Runtime()).assist({'prompt':'Build two pages with index=fixture_index','revision':0,'definition':original,'dataContext':blank()['dataContext']})
        self.assertEqual(original,before);self.assertEqual(len(provider.requests),3)
    def test_new_foundation_page_ids_are_reused_without_renaming_existing_user_pages(self):
        context={'request':'Build two pages','canvasState':'blank','history':[]}
        budget=AuthoringBudget({'provider':'aitk'},context);budget.stages=1;budget.phase='complete'
        base=blank()['definition']
        doc=apply_changes(base,compile_actions(base,[{'op':'search','id':'events','pipeline':'| stats count'},chart('splunk.table','',['count']),page()],PROFILE))
        actions=[dict(page(),layoutId='another_overview'),{'op':'button','pageId':'details','targetPageId':'another_overview'}, {'op':'link','pageId':'another_overview'}]
        result=budget.actions(actions,doc)
        self.assertEqual(result[0]['layoutId'],'layout_main');self.assertEqual(result[1]['targetPageId'],'layout_main');self.assertEqual(result[2]['pageId'],'layout_main')
        self.assertEqual(actions[0]['layoutId'],'another_overview')
        budget.creation=False;self.assertEqual(budget.actions(actions,doc),actions)
    def test_foundation_does_not_publish_provisional_dashboard_description(self):
        budget=AuthoringBudget({'provider':'aitk'},{'request':'Build two pages','canvasState':'blank','history':[],'dataProfile':PROFILE})
        actions=[{'op':'set','path':'/description','value':'"More will be added in the next stage."'}, {'op':'set','path':'/title','value':'"A useful dashboard"'}]
        self.assertEqual(budget.actions(actions,blank()['definition']),actions[1:])
    def test_reference_only_creation_keeps_full_native_schema_without_a_real_profile(self):
        budget=AuthoringBudget({'provider':'aitk'},{'request':'Build two pages from this illustrative reference','canvasState':'blank','history':[]})
        self.assertEqual(budget.phase,'complete')
        schema={'properties':{'changes':{'items':{'anyOf':[{'native':'unchanged'}]}}}}
        request={'instructions':'Fixture','text':{'format':{'schema':schema}},'input':[{'content':[{'type':'input_text','text':'Fixture'}]}]}
        budget.prepare(request,blank()['definition'])
        self.assertEqual(request['text']['format']['schema'],schema)
    def test_native_field_repair_compiles_but_missing_output_still_fails(self):
        doc=apply_changes(blank()['definition'],compile_actions(blank()['definition'],[{'op':'search','id':'events','pipeline':'| stats count'},chart('splunk.table','',['count']),page()],PROFILE))
        doc['visualizations']['trend']['options']['unknown']={'preserve':True}
        changes=compile_actions(doc,[{'op':'set','path':'/visualizations/trend/options/table','value':json.dumps({'field':'count'})}],PROFILE)
        result=apply_changes(doc,changes)
        self.assertEqual(result['visualizations']['trend']['options']['table'],'> primary | frameBySeriesNames("count")')
        self.assertEqual(result['visualizations']['trend']['options']['unknown'],{'preserve':True})
        provider=Provider([reply([{'op':'set','path':'/visualizations/trend/options/table','value':json.dumps({'field':'missing'})}])]*3)
        with self.assertRaises(ProviderError):AgentService(provider,Runtime()).assist({'prompt':'Change the table','revision':0,'definition':doc,'dataContext':blank()['dataContext']})
    def test_oversized_context_fails_before_provider_and_preserves_brief(self):
        context={'request':'Build two pages','canvasState':'blank','definition':{},'history':[{'text':'old'*4000}],'dashboardBrief':{'purpose':'keep'}}
        budget=AuthoringBudget({'provider':'ollama'},context)
        request={'instructions':'small','text':{'format':{'schema':{'properties':{'changes':{}}}}},'input':[{'content':[{'type':'input_text','text':'context'}]}]}
        budget.prepare(request,blank()['definition'])
        self.assertEqual(json.loads(request['input'][0]['content'][0]['text'])['dashboardBrief'],{'purpose':'keep'})
        budget.context['dashboardBrief']['purpose']='large'*100000
        with self.assertRaises(ProviderError) as caught:budget.prepare(request,blank()['definition'])
        self.assertEqual(caught.exception.code,'model_context_budget')
    def test_latest_feedback_replaces_repeated_failed_output_and_preserves_candidate(self):
        budget=AuthoringBudget({'provider':'ollama'},{'request':'Build','canvasState':'blank','history':[]})
        request={'instructions':'Fixture','text':{},'max_output_tokens':8500,'input':[{'role':'user','content':[{'type':'input_text','text':'original goal'}]}]}
        envelope={'rejectedOutput':'x'*100000,'recoveryFeedback':{'candidateDefinition':{'title':'working candidate'},'validationError':'Fix x'}}
        budget.feedback(request,envelope);budget.feedback(request,dict(envelope,rejectedOutput='latest'))
        self.assertEqual(len(request['input']),2)
        value=json.loads(request['input'][-1]['content'][0]['text'])
        self.assertEqual(value['rejectedOutput'],'latest');self.assertEqual(value['recoveryFeedback']['candidateDefinition']['title'],'working candidate')
