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
    def test_focused_repair_keeps_one_exact_large_candidate_without_losing_original_receipt(self):
        original={'title':'Original','visualizations':{'table':{'future':'fixture'*7000}}};candidate=copy.deepcopy(original);candidate['title']='Uncommitted'
        context={'request':'Add two columns to this selected table','canvasState':'dashboard','focus':{'kind':'visualization','id':'table'},'history':[],'definition':original,'focusedSourceReceipt':{'originalQuery':'verified fixture'}}
        budget=AuthoringBudget({'provider':'ollama'},context);request={'instructions':'Fixture','text':{},'max_output_tokens':8500,'input':[{'role':'user','content':[{'type':'input_text','text':json.dumps(context)}]}]}
        envelope={'rejectedOutput':'old wire proposal','recoveryFeedback':{'candidateDefinition':candidate,'editsApplyTo':'candidate','placementHint':{'unneeded':'layout'},'validationError':'Fix one field'}}
        budget.feedback(request,envelope);first=json.loads(request['input'][0]['content'][0]['text']);feedback=json.loads(request['input'][1]['content'][0]['text'])
        self.assertEqual(first['definition'],candidate);self.assertEqual(first['focusedSourceReceipt'],context['focusedSourceReceipt']);self.assertNotIn('candidateDefinition',feedback['recoveryFeedback']);self.assertNotIn('placementHint',feedback['recoveryFeedback']);self.assertEqual(feedback['rejectedOutput'],'')
        self.assertEqual(budget.context['definition'],original);self.assertEqual(envelope['recoveryFeedback']['candidateDefinition'],candidate)
        envelope['recoveryFeedback']['editsApplyTo']='original';budget.feedback(request,envelope)
        self.assertEqual(json.loads(request['input'][0]['content'][0]['text'])['definition'],original);self.assertNotIn('candidateDefinition',json.loads(request['input'][1]['content'][0]['text'])['recoveryFeedback'])
    def test_schema_ignoring_compact_reply_keeps_small_plan_repair_against_original(self):
        from agent_service import SCHEMA
        context={'request':'Build three pages with exactly six charts','canvasState':'blank','history':[],'dataProfile':PROFILE,'modelLimits':{'contextTokens':32768}}
        budget=AuthoringBudget({'provider':'ollama'},context)
        request={'instructions':'Fixture','text':{'format':{'schema':copy.deepcopy(SCHEMA)}},'input':[{'content':[{'type':'input_text','text':'Fixture'}]}]}
        budget.prepare(request,blank()['definition']);schema=copy.deepcopy(request['text']['format']['schema'])
        with self.assertRaisesRegex(ProviderError,'ONE complete compose'):
            budget.actions([{'op':'search','id':'events','pipeline':'| stats count'}],blank()['definition'])
        envelope={'rejectedOutput':'Rejected native proposal','recoveryFeedback':{'editsApplyTo':'original','candidateDefinition':blank()['definition'],'validationError':'Use compose'}}
        budget.feedback(request,envelope)
        self.assertTrue(budget.compact);self.assertEqual(request['text']['format']['schema'],schema)
        self.assertNotIn('Rejected native proposal',json.dumps(request));self.assertIn('ONE complete corrected compose',json.dumps(request))
        self.assertEqual(request['max_output_tokens'],5500)
    def test_bounded_aitk_workload_does_not_infer_capacity_or_stage_every_two_page_request(self):
        base={'request':'Build two pages','canvasState':'blank','history':[],'dataProfile':PROFILE}
        self.assertEqual(AuthoringBudget({'provider':'aitk'},base).phase,'complete')
        for context in (dict(base,request='Build three pages'), dict(base,request='Build two pages with 12 charts'), dict(base,dashboardBrief={'purpose':'x'*40000})):
            self.assertEqual(AuthoringBudget({'provider':'aitk'},context).phase,'foundation')
        for goal in ('Build three pages with exactly six charts','Build four pages with exactly eight charts'):
            self.assertEqual(AuthoringBudget({'provider':'aitk'},dict(base,request=goal)).phase,'complete')
        for goal in ('Build four pages with 12 charts','Build five pages with eight charts','Build three pages with two charts'):
            self.assertEqual(AuthoringBudget({'provider':'aitk'},dict(base,request=goal)).phase,'foundation')

    def test_concise_creation_keeps_full_context_schema_actions_and_budgets(self):
        from agent_service import SCHEMA
        context={'request':'Build two pages','canvasState':'blank','history':[], 'dataProfile':PROFILE,
                 'dashboardBrief':{'purpose':'Keep the exact requirements'},'nativeFeatures':{'future':'preserved'}}
        schema=copy.deepcopy(SCHEMA)
        request={'instructions':'Keep validators','text':{'format':{'schema':schema}},'input':[{'content':[{'type':'input_text','text':'context'}]}]}
        budget=AuthoringBudget({'provider':'aitk'},context);budget.prepare(request,blank()['definition'])
        decoded=json.loads(request['input'][0]['content'][0]['text'])
        self.assertEqual(decoded['dashboardBrief'],context['dashboardBrief'])
        self.assertNotIn('nativeFeatures',decoded)
        self.assertNotIn('catalog',decoded)
        self.assertEqual(decoded['definition'],blank()['definition'])
        from compact_creation import COMPOSE_ACTION, RECIPE_COMPOSE_ACTION
        expected=copy.deepcopy(RECIPE_COMPOSE_ACTION)
        expected['properties']['pages'].update(minItems=2,maxItems=2)
        self.assertEqual(request['text']['format']['schema']['properties']['changes']['items'],expected)
        self.assertEqual(COMPOSE_ACTION['properties']['pages']['minItems'],1)
        self.assertEqual(SCHEMA,schema)
        self.assertEqual(request['text']['format']['schema']['properties']['suggestions']['maxItems'],1)
        self.assertIn('Never omit requested work',request['instructions'])
        self.assertIn('NEXT QUESTIONS',request['instructions'])
        self.assertIn('inspected schema',request['instructions'])
    def test_verified_ollama_capacity_reserves_repairs_without_guessing_aitk_limits(self):
        context={'request':'Build two pages','canvasState':'blank','history':[],'dataProfile':PROFILE}
        for provider,capacity,phase in [('ollama',32768,'complete'),('ollama',262144,'complete'),('ollama',16384,'foundation'),('ollama',None,'foundation'),('aitk',32768,'complete'),('aitk',None,'complete')]:
            with self.subTest(provider=provider,capacity=capacity):
                value=dict(context,modelLimits={'contextTokens':capacity})
                self.assertEqual(AuthoringBudget({'provider':provider},value).phase,phase)

    def test_two_internal_stages_complete_before_any_changes_are_returned(self):
        first=[{'op':'search','id':'events','pipeline':'| stats count'},chart('splunk.table','',['count']),page()]
        second=dict(page(),layoutId='details',label='Details',purpose='Investigate counts')
        class StagedProvider(Provider):
            def configured(self):return {'provider':'aitk','model':'fixture'}
        original=blank()['definition'];runtime=Runtime();provider=StagedProvider([reply(first),reply([second,dict(second,layoutId='third',label='Third')])])
        result=AgentService(provider,runtime).assist({'prompt':'Build three pages with index=fixture_index','revision':0,'definition':original,'dataContext':blank()['dataContext']})
        self.assertFalse(original['visualizations']);self.assertEqual(result['recovery']['modelCalls'],2)
        self.assertEqual(result['recovery']['queryChecks'],1)
        doc=apply_changes(original,result['changes']);self.assertEqual(len(doc['layout']['tabs']['items']),3)
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
        budget=AuthoringBudget({'provider':'aitk'},{'request':'Build three pages','canvasState':'blank','history':[],'dataProfile':PROFILE})
        actions=[{'op':'set','path':'/description','value':'"More will be added in the next stage."'}, {'op':'set','path':'/title','value':'"A useful dashboard"'}]
        self.assertEqual(budget.actions(actions,blank()['definition']),actions[1:])
        metadata={'op':'dashboard','title':'A useful dashboard','description':'More will be added in the next stage.'}
        self.assertEqual(budget.actions([metadata],blank()['definition']),[{'op':'set','path':'/title','value':'"A useful dashboard"'}])
        with self.assertRaises(ProviderError):budget.actions([dict(metadata,unknown='reject')],blank()['definition'])
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

    def test_valid_staged_document_replaces_duplicate_wire_proposal_only_after_staging(self):
        from provider_messages import conversation_entries
        budget=AuthoringBudget({'provider':'aitk'},{'request':'Build','canvasState':'blank','history':[]})
        request={'instructions':'Fixture','text':{},'max_output_tokens':8500,'input':[{'role':'user','content':[{'type':'input_text','text':'original goal'}]}]}
        candidate={'title':'Keep me','visualizations':{'existing':{'future':{'keep':True}}}}
        envelope={'rejectedOutput':'previous verbose proposal','recoveryFeedback':{'candidateDefinition':candidate,'editsApplyTo':'candidate','validationError':'Fix one binding'}}
        budget.feedback(request,envelope)
        feedback=json.loads(request['input'][-1]['content'][0]['text'])
        self.assertEqual(feedback['rejectedOutput'],'');self.assertEqual(feedback['recoveryFeedback']['candidateDefinition'],candidate)
        self.assertNotIn('assistant',[entry['role'] for entry in conversation_entries(request)])
        envelope['recoveryFeedback']['editsApplyTo']='original';budget.feedback(request,envelope)
        self.assertIn('previous verbose proposal',json.dumps(request))
