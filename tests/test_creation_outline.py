"""Synthetic flat-plan evidence; live model and native execution stay separate."""
import copy
import unittest
from test_compact_creation import compose
from test_drafts_and_data import blank
from test_search_chart_actions import PROFILE
from compact_creation import COMPOSE_ACTION, expand_compose, COMPACT_INSTRUCTIONS
from creation_outline import nested_outline, outline_schema, outline_instructions
from authoring_actions import compile_actions, validate_chart_placement
from studio_contract import apply_changes
from provider_service import ProviderError
from agent_service import AgentService
from test_reliability_journey import Provider, Runtime, reply


def outline():
    old=compose()
    return {**{k:v for k,v in old.items()if k not in ('pages','links')},
            'pages':[{k:p[k]for k in ('label','purpose','columns')}for p in old['pages']],
            'panels':[{**panel,'page':i}for i,page in enumerate(old['pages'])for panel in page['panels']],
            'links':[dict(link,to=1)for link in old['links']]}


class CreationOutlineTests(unittest.TestCase):
    def test_flat_recipe_plans_keep_membership_inputs_and_atomic_rejection(self):
        action=outline();action['panels']=[{k:v for k,v in p.items()if k not in ('pipeline','x','y')}for p in action['panels']]
        for p in action['panels']:
            metric=[{'function':'count','field':'','alias':'count'}]
            p['recipe']={'kind':'stats','metrics':metric,'groupBy':'device_name' if p['type']=='splunk.table' else ''} if p['type']in('splunk.table','splunk.singlevalue') else {'kind':'timechart','metrics':metric}
        before=copy.deepcopy(action);original=blank()['definition'];profile=dict(PROFILE,fields=[{'name':'device_name'}])
        compiled=expand_compose([nested_outline(action)],original,profile)
        final=apply_changes(original,compile_actions(original,compiled,profile));self.assertEqual(len(final['visualizations']),4)
        self.assertEqual(action,before);self.assertIn('search device_name=$select_page_1|s$',final['dataSources']['ds_detail']['options']['query'])
        mixed=copy.deepcopy(action);mixed['panels'][0]['pipeline']='| delete'
        with self.assertRaises(ProviderError):nested_outline(mixed)
    def test_linked_fixed_alias_trend_reaches_native_validation_without_a_model_repair(self):
        class Model(Provider):
            def configured(self):return {'provider':'ollama','model':'synthetic'}
            def capabilities(self,saved):return {'contextTokens':32768,'images':False,'pdf':False}
        class Searches(Runtime):
            def preview(self,body):
                if body.get('fieldDiscovery'):return super().preview(body)
                self.calls.append(body);query=body['query']
                if 'stats count BY host'in query:return {'fields':[{'name':'host'},{'name':'count'}],'results':[{'host':'fixture_alpha','count':'12'}],'state':'complete'}
                self.assert_no_split(query)
                return {'fields':[{'name':'_time'},{'name':'count'}],'results':[{'_time':'1000','count':'12'}],'state':'complete'}
            def assert_no_split(self,query):
                if 'timechart'in query and ' BY host'in query:raise ProviderError('Synthetic split columns do not include count',422,'preview_failed')
        action=outline();action['panels'][1].update(pipeline='| stats count BY host',y=['host','count']);action['links'][0]['field']='host'
        action['panels'][2]['pipeline']='| timechart bins=100 count AS count BY host'
        original=blank()['definition'];model=Model([reply([action])]);runtime=Searches()
        result=AgentService(model,runtime).assist({'prompt':'Build two pages of activity counts with a row-linked device detail trend.','revision':0,'definition':original,'dataContext':blank()['dataContext']})
        final=apply_changes(original,result['changes'])
        self.assertEqual(result['recovery']['modelCalls'],1);self.assertEqual(result['recovery']['queryChecks'],4);self.assertFalse(result['repaired'])
        self.assertNotIn('BY host',final['dataSources']['ds_detail']['options']['query'])
        self.assertIn('BY host',final['dataSources']['ds_devices']['options']['query'])
        self.assertFalse(original['visualizations'])
    def test_late_native_output_failure_replans_compactly_without_committing_the_candidate(self):
        import json
        class Model(Provider):
            def configured(self):return {'provider':'ollama','model':'synthetic'}
            def capabilities(self,saved):return {'contextTokens':32768,'images':False,'pdf':False}
        class Searches(Runtime):
            def preview(self,body):
                if body.get('fieldDiscovery'):return super().preview(body)
                self.calls.append(body);name='wrong' if 'AS wrong'in body['query'] else 'count'
                return {'fields':[{'name':name}],'results':[{name:'12'}],'state':'complete'}
        good=outline();good['pages']=good['pages'][:1];good['links']=[]
        good['panels']=[{'id':'count','page':0,'type':'splunk.table','title':'Observed rows','pipeline':'| stats count AS count','x':'','y':['count']}]
        bad=copy.deepcopy(good);bad['panels'][0]['pipeline']='| stats count AS wrong'
        original=blank()['definition'];original['futureSetting']={'keep':True};before=copy.deepcopy(original)
        model=Model([reply([bad]),reply([good])]);runtime=Searches()
        result=AgentService(model,runtime).assist({'prompt':'Build one page with a table of event counts.','revision':0,'definition':original,'dataContext':blank()['dataContext']})
        self.assertTrue(result['repaired']);self.assertEqual(result['recovery']['modelCalls'],2);self.assertEqual(result['recovery']['queryChecks'],2)
        second=model.requests[1];self.assertEqual(second['max_output_tokens'],3500)
        self.assertIn('panels',second['text']['format']['schema']['properties']['changes']['items']['properties'])
        feedback=json.loads(second['input'][-1]['content'][0]['text'])['recoveryFeedback']
        self.assertEqual(feedback['editsApplyTo'],'original');self.assertFalse(feedback['candidateDefinition']['visualizations'])
        final=apply_changes(original,result['changes']);self.assertEqual(len(final['visualizations']),1)
        self.assertIn('AS count',final['dataSources']['ds_count']['options']['query']);self.assertEqual(final['futureSetting'],{'keep':True});self.assertEqual(original,before)
    def test_flat_plan_still_requires_actual_output_validation_and_bounded_repair(self):
        class Model(Provider):
            def configured(self):return {'provider':'ollama','model':'synthetic'}
            def capabilities(self,saved):return {'contextTokens':32768,'images':False,'pdf':False}
        class Searches(Runtime):
            reject=False
            def preview(self,body):
                if self.reject and not body.get('fieldDiscovery'):raise ProviderError('Synthetic native failure',422,'preview_failed')
                return super().preview(body)
        action=outline();action['pages']=action['pages'][:1];action['links']=[]
        action['panels']=[{'id':'count','page':0,'type':'splunk.table','title':'Observed rows','pipeline':'| stats count AS count','x':'','y':['count']}]
        original=blank()['definition'];before=copy.deepcopy(original)
        body={'prompt':'Build one page with a table of event counts.','revision':0,'definition':original,'dataContext':blank()['dataContext']}
        runtime=Searches();model=Model([reply([action])]);result=AgentService(model,runtime).assist(body)
        self.assertEqual(result['recovery']['modelCalls'],1);self.assertEqual(result['recovery']['queryChecks'],1)
        self.assertIn('count',apply_changes(original,result['changes'])['visualizations'])
        runtime=Searches();runtime.reject=True;model=Model([reply([action])]*3)
        with self.assertRaises(ProviderError):AgentService(model,runtime).assist(body)
        self.assertEqual(len(model.requests),3);self.assertEqual(original,before)
    def test_all_charts_and_page_membership_compile_with_existing_guards(self):
        action=outline();before=copy.deepcopy(action);original=blank()['definition']
        nested=nested_outline(action);profile=dict(PROFILE,fields=[{'name':'device_name'}])
        result=apply_changes(original,compile_actions(original,expand_compose([nested],original,profile),profile))
        self.assertEqual(action,before);self.assertEqual(len(result['visualizations']),4)
        tabs=result['layout']['tabs']['items'];self.assertEqual([t['label']for t in tabs],['Overview','Device details'])
        self.assertEqual({item['item']for item in result['layout']['layoutDefinitions'][tabs[1]['layoutId']]['structure'] if item['type']=='block'},{'detail','detail_count'})
        self.assertTrue(any(h['type']=='drilldown.switchToTab'and h['options']['tabId']==tabs[1]['layoutId'] for h in result['visualizations']['devices']['eventHandlers']))
        validate_chart_placement(result,original)
        self.assertFalse(original['visualizations'])
    def test_no_balanced_distribution_is_assumed_and_nothing_is_truncated(self):
        action=outline();action['panels'][2]['page']=0
        nested=nested_outline(action)
        self.assertEqual([len(p['panels'])for p in nested['pages']],[3,1])
        self.assertEqual(sum(len(p['panels'])for p in nested['pages']),4)
    def test_invalid_membership_empty_pages_and_unknown_fields_fail_atomically(self):
        cases=[]
        for value in (True,-1,2,'1'):
            bad=outline();bad['panels'][0]['page']=value;cases.append(bad)
        bad=outline();bad['panels'][0]['extra']='unrequested';cases.append(bad)
        bad=outline();bad['pages'][0]['panels']=[];cases.append(bad)
        bad=outline();bad['panels']=[dict(p,page=0)for p in bad['panels']];cases.append(bad)
        bad=outline();bad['links'][0]['to']=True;cases.append(bad)
        for action in cases:
            before=copy.deepcopy(action)
            with self.subTest(action=action),self.assertRaises(ProviderError):nested_outline(action)
            self.assertEqual(action,before)
    def test_schema_bounds_global_count_and_uses_one_wire_shape(self):
        before=copy.deepcopy(COMPOSE_ACTION);schema=outline_schema(COMPOSE_ACTION,2,4)
        props=schema['properties'];self.assertEqual((props['panels']['minItems'],props['panels']['maxItems']),(4,4))
        self.assertNotIn('panels',props['pages']['items']['properties'])
        self.assertEqual(props['links']['items']['properties']['to']['enum'],[0,1])
        self.assertTrue(all(p['properties']['page']['enum']==[0,1]for p in props['panels']['items']['anyOf']))
        self.assertEqual(COMPOSE_ACTION,before)
        instructions=outline_instructions(COMPACT_INSTRUCTIONS)
        self.assertIn('Never nest panels in pages',instructions);self.assertNotIn('layout_PAGEID',instructions)
