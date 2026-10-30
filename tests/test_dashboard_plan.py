"""Synthetic large-board proposals exercise real compilers and validation."""
import copy
import json
import unittest
from test_drafts_and_data import blank
from test_reliability_journey import Provider, Runtime, reply
from test_native_shapes import frame, viz
from agent_service import AgentService, SCHEMA
from authoring_actions import compile_actions, validate_chart_placement
from authoring_budget import AuthoringBudget
from compatibility import feature_profile
from dashboard_plan import counts, eligible, expand, page_names, schema_for
from native_builders import native_options, verified_precision
from native_shapes import validate_shape
from studio_contract import apply_changes
from provider_service import ProviderError
from board_batches import source_schema, source_actions, layout_schema, pool_context, expand_layout, normalize_plan, recipe_goal

PROFILE = {'baseQuery':'search index="fixture_index"','scope':{'index':'fixture_index','earliest':'-24h','language':'spl'},
           'fields':[{'name':'host'},{'name':'temperature_f','numeric':True},{'name':'_time','numeric':False}]}
GOAL = 'Create exactly eight pages with exactly 24 charts. Give each page a purpose and use shared real-data summaries, temperature trends and host tables.'


def plan():
    sources = [{'id':'metrics','recipe':{'kind':'stats','metrics':[{'function':'avg','field':'temperature_f','alias':'mean_f'},{'function':'count','field':'','alias':'observations'}],'groupBy':''}},
               {'id':'trend','recipe':{'kind':'timechart','metrics':[{'function':'avg','field':'temperature_f','alias':'mean_f'}]}},
               {'id':'summary','recipe':{'kind':'stats','metrics':[{'function':'count','field':'','alias':'observations'}],'groupBy':'host'}}]
    return {'op':'boardPlan','title':'Observed telemetry','description':'Shared observations across eight pages',
            'pages':[{'label':'Page '+str(p+1),'purpose':'Inspect observed telemetry '+str(p+1),'columns':2}for p in range(8)],
            'sources':sources,'panels':[{'id':'panel_'+str(p)+'_'+str(k),'page':p,'type':kind,'title':title,'source':source,'bindings':binding}
             for p in range(8) for k,(kind,title,source,binding)in enumerate([
              ('splunk.singlevalue','Mean temperature (°F)','metrics',{'value':'mean_f'}),
              ('splunk.line','Temperature over time (°F)','trend',{'x':'_time','y':['mean_f']}),
              ('splunk.table','Host observations','summary',{'columns':['host','observations']})])], 'links':[]}


def compile_plan(action, goal=GOAL):
    original=blank()['definition'];original['futureSetting']={'keep':True}
    raw=expand([action],original,PROFILE,goal)
    result=apply_changes(original,compile_actions(original,raw,PROFILE))
    return original,result,raw


class DashboardPlanTests(unittest.TestCase):
    def test_batch_composition_uses_verified_outputs_and_keeps_pool_immutable(self):
        context={'request':GOAL,'dataProfile':PROFILE};sources=plan()['sources'];before=copy.deepcopy(sources)
        receipts=[{'source':'ds_plan_metrics','fields':['mean_f','observations']},{'source':'ds_plan_trend','fields':['_time','mean_f']},{'source':'ds_plan_summary','fields':['host','observations']}]
        schema=layout_schema(context,sources,receipts);self.assertNotIn('sources',schema['properties'])
        variants=schema['properties']['panels']['items']['anyOf']
        for v in variants:
            if v['properties']['type']['enum']==['splunk.singlevalue']:self.assertEqual(v['properties']['source']['enum'],['metrics'])
            if v['properties']['source']['enum']==['trend']and v['properties']['type']['enum']==['splunk.line']:
                self.assertEqual(v['properties']['bindings']['properties']['y']['items']['enum'],['mean_f'])
        pool=pool_context(sources,receipts);self.assertTrue(all('fields'in s and 'results'not in s for s in pool))
        layout=plan();layout.pop('sources');layout['op']='boardLayout'
        self.assertEqual(expand_layout([layout],blank()['definition'],context,sources),expand([plan()],blank()['definition'],PROFILE,GOAL));self.assertEqual(sources,before)
        layout['sources']=[]
        with self.assertRaises(ProviderError):expand_layout([layout],blank()['definition'],context,sources)
    def test_source_batch_rejects_invalid_scope_inputs_before_composition(self):
        context={'request':GOAL,'dataProfile':PROFILE};action={'op':'boardSources','sources':plan()['sources']}
        compiled=source_actions([action],context);self.assertEqual(len(compiled),3);self.assertTrue(all(c['id'].startswith('ds_plan_')for c in compiled))
        for invalid in (None,{'kind':'stats','metrics':[{'function':'avg','field':'unverified','alias':'mean'}],'groupBy':''}):
            bad=copy.deepcopy(action);bad['sources'][0]['recipe']=invalid
            with self.assertRaises(ProviderError):source_actions([bad],context)
    def test_failed_batch_promotion_returns_to_source_planning(self):
        from unittest.mock import patch
        budget=AuthoringBudget({'provider':'ollama'},{'request':GOAL,'canvasState':'blank','dataProfile':PROFILE})
        calls=[]
        def prepare(request,document):
            calls.append(hasattr(budget,'verified_pool'))
            if calls[-1]:raise ProviderError('Synthetic composition admission failure.',413)
        with patch.object(budget,'prepare',side_effect=prepare),self.assertRaises(ProviderError):
            budget.advance_sources({},blank()['definition'],[{'sources':plan()['sources']}],[])
        self.assertEqual(calls,[True,False]);self.assertFalse(hasattr(budget,'verified_pool'));self.assertEqual(budget.stages,0)
    def test_pool_fragments_are_coalesced_before_actual_searches_and_bindings(self):
        sources=[]
        for n in range(5):sources.append({'id':'metric'+str(n),'recipe':{'kind':'stats','metrics':[{'function':'avg','field':'temperature_f','alias':'metric'+str(n)}],'groupBy':''}})
        sources.extend(plan()['sources'][1:]);sources.append({'id':'raw','recipe':{'kind':'table','columns':['host','temperature_f']}})
        self.assertEqual(len(sources),8);original=copy.deepcopy(sources);result=normalize_plan([{'op':'boardSources','sources':sources}],{'dataProfile':PROFILE})[0]['sources']
        self.assertEqual(len(result),4);self.assertEqual(sources,original)
        self.assertIn(' AS metric0',result[0]['pipeline'])
        for n in range(1,5):self.assertIn('metric'+str(n)+'=metric0',result[0]['pipeline'])
        self.assertTrue(any('timechart'in s['pipeline']for s in result));self.assertTrue(any('BY host'in s['pipeline']for s in result));self.assertTrue(any('table host temperature_f'in s['pipeline']for s in result))
    def test_complex_requests_keep_native_authoring_and_batch_bindings_are_checked_early(self):
        context={'request':GOAL,'dataProfile':PROFILE};self.assertTrue(recipe_goal(context))
        for goal in ('Add a native Sankey','Show p95 and outliers','Add table sparklines','Create a ratio','Use timechart count by host'):
            self.assertFalse(recipe_goal(dict(context,request=GOAL+' '+goal)))
        self.assertFalse(eligible(dict(context,request=GOAL+' Add table sparklines.'),blank()['definition']))
        self.assertNotIn('pipeline',json.dumps(source_schema(context)))
        with self.assertRaisesRegex(ProviderError,'not raw pipelines'):source_actions([{'op':'boardSources','sources':[{'id':'raw','pipeline':'| stats count'}]}],context)
        layout=plan();sources=layout.pop('sources');layout['op']='boardLayout';layout['panels'][1]['source']='summary'
        receipts=[{'source':'ds_plan_metrics','fields':['mean_f','observations']},{'source':'ds_plan_trend','fields':['_time','mean_f']},{'source':'ds_plan_summary','fields':['host','observations']}]
        with self.assertRaisesRegex(ProviderError,'without _time'):expand_layout([layout],blank()['definition'],context,sources,receipts)
    def test_larger_shared_plan_keeps_all_membership_precision_and_unknown_native_work(self):
        action=plan();before=copy.deepcopy(action);original,result,raw=compile_plan(action)
        self.assertEqual(action,before);self.assertFalse(original['visualizations'])
        self.assertEqual(result['futureSetting'],{'keep':True});self.assertEqual(len(result['visualizations']),24)
        self.assertEqual(len(result['dataSources']),3);self.assertEqual(len(result['layout']['tabs']['items']),8)
        self.assertTrue(all(len(p['structure'])==3 for p in result['layout']['layoutDefinitions'].values()))
        self.assertNotIn('round(',result['dataSources']['ds_plan_metrics']['options']['query'])
        self.assertEqual(result['visualizations']['panel_0_0']['options']['sparklineDisplay'],'off')
        self.assertEqual(result['visualizations']['panel_0_0']['options']['trendDisplay'],'off')
        validate_chart_placement(result,original)
    def test_counts_admission_and_names_never_guess_or_truncate(self):
        self.assertEqual(counts(GOAL),(8,24,None));self.assertEqual(counts('Build eight pages with 3 charts per page.'),(8,24,3))
        self.assertIsNone(counts('Build eight pages with exactly 20 charts and 3 charts per page.'))
        self.assertIsNone(counts('Build nine pages with exactly 24 charts.'))
        names='Build five pages named "Overview", "Inputs", "Details", "Signals", "Confidence" with exactly 10 charts.'
        self.assertEqual(page_names(names,5),['Overview','Inputs','Details','Signals','Confidence'])
        context={'request':GOAL,'dataProfile':PROFILE};self.assertTrue(eligible(context,blank()['definition']))
        self.assertTrue(eligible(dict(context,request=GOAL+' No invented health/SLA thresholds. No dropdowns or custom colors.'),blank()['definition']))
        self.assertFalse(eligible(dict(context,request=GOAL+' No dropdowns; add a gauge.'),blank()['definition']))
        for suffix in (' Add a dropdown.', ' Place an image.', ' Set custom colors.', ' Add a scatter chart.', ' Include splunk.singlevalueicon.'):
            self.assertFalse(eligible(dict(context,request=GOAL+suffix),blank()['definition']))
        self.assertFalse(eligible(context,dict(blank()['definition'],visualizations={'existing':{'type':'splunk.table'}})))
        malformed=plan();malformed['panels'].pop()
        with self.assertRaises(ProviderError):compile_plan(malformed)
        named_goal=GOAL+'\nOn "Page 2", include a Sankey chart.'
        with self.assertRaisesRegex(ProviderError,'Page 2 still needs'):compile_plan(plan(),named_goal)
    def test_schema_and_compact_repair_are_provider_neutral_and_keep_limits(self):
        for provider in ('openai','ollama','aitk'):
            context={'request':GOAL,'canvasState':'blank','history':[],'dataProfile':PROFILE,'modelLimits':{'contextTokens':32768},'nativeAuthoring':{'unneeded':'extra'}}
            budget=AuthoringBudget({'provider':provider},context);request={'instructions':'Fixture','text':{'format':{'schema':copy.deepcopy(SCHEMA)}},'input':[{'content':[{'type':'input_text','text':'Fixture'}]}]}
            budget.prepare(request,blank()['definition']);self.assertTrue(budget.board_plan);self.assertEqual(budget.phase,'complete')
            self.assertEqual(request['text']['format']['schema']['properties']['changes']['items'],source_schema(context)if provider in ('ollama','aitk')else schema_for(context))
            recipe=schema_for(context)['properties']['sources']['items']['anyOf'][1]['properties']['recipe']
            fields=recipe['anyOf'][0]['properties']['metrics']['items']['anyOf'][0]['properties']['field']['enum']
            self.assertEqual(set(fields),{''}|{f['name']for f in PROFILE['fields']})
            current=json.loads(request['input'][0]['content'][0]['text']);self.assertNotIn('nativeAuthoring',current)
            self.assertNotIn('baseQuery',current['dataProfile']);self.assertEqual(current['creationRequirements']['panels'],24)
            budget.feedback(request,{'recoveryFeedback':{'validationError':'Bad binding','candidateDefinition':{'sensitive':'do not repeat'},'dataProfile':PROFILE},'rejectedOutput':'old failed text','request':'repair'})
            feedback=json.loads(request['input'][-1]['content'][0]['text']);self.assertEqual(feedback['recoveryFeedback']['editsApplyTo'],'original')
            self.assertNotIn('candidateDefinition',feedback['recoveryFeedback']);self.assertNotIn('baseQuery',feedback['recoveryFeedback']['dataProfile'])
            self.assertNotIn('old failed text',json.dumps(request))
    def test_route_isolates_shared_destination_sources_and_keeps_overview_unfiltered(self):
        action=plan();action['links']=[{'from':'panel_0_2','to':1,'field':'host'}]
        _,result,_=compile_plan(action)
        for pid in ('panel_0_0','panel_0_1','panel_0_2'):
            self.assertNotIn('$select_page_1',result['dataSources'][result['visualizations'][pid]['dataSources']['primary']]['options']['query'])
        for pid in ('panel_1_0','panel_1_1','panel_1_2'):
            query=result['dataSources'][result['visualizations'][pid]['dataSources']['primary']]['options']['query']
            self.assertIn('search host=$select_page_1|s$',query)
        self.assertEqual(len(result['dataSources']),6)
        self.assertTrue(any(h['type']=='drilldown.switchToTab' and h['options']['tabId']=='layout_board_0' for h in result['inputs']['back_board_1']['eventHandlers']))
    def test_row_routes_do_not_overwrite_unknown_existing_token_work(self):
        original=blank()['definition'];original['defaults']={'tokens':{'default':{'select_page_1':{'value':'keep','future':True}}}};original['expressions']={'select_page_1_2':{'future':True}}
        action=plan();action['links']=[{'from':'panel_0_2','to':1,'field':'host'}]
        changes=expand([action],original,PROFILE,GOAL);result=apply_changes(original,compile_actions(original,changes,PROFILE))
        self.assertEqual(result['defaults']['tokens']['default']['select_page_1'],original['defaults']['tokens']['default']['select_page_1']);self.assertEqual(result['expressions'],original['expressions'])
        self.assertEqual(result['defaults']['tokens']['default']['select_page_1_3']['value'],'*')
    def test_full_closure_includes_network_nodes_and_filtered_clones(self):
        action=plan();action['panels'][0].update(type='splunk.networkGraph',source='edges',bindings={'source':'from_node','target':'to_node'})
        action['sources'].append({'id':'edges','pipeline':'| stats count BY host | eval from_node=host, to_node="observed" | table from_node to_node count'})
        _,result,_=compile_plan(action);graph=result['visualizations']['panel_0_0'];self.assertIn('nodeSource',graph['dataSources'])
        nodes=result['dataSources'][graph['dataSources']['nodeSource']];self.assertEqual(nodes['type'],'ds.chain')
        self.assertIn('mvappend(from_node,to_node)',nodes['options']['query']);self.assertIn('nodeSource',graph['options']['nodeIds'])
        closure=result['dataSources'][graph['dataSources']['primary']];self.assertEqual(closure['type'],'ds.chain');self.assertIn('mvappend("edge","node")',closure['options']['query']);self.assertIn('to_node,null()',closure['options']['query']);self.assertEqual(closure['options']['extend'],nodes['options']['extend'])
        action['links']=[{'from':'panel_0_2','to':i,'field':'host'}for i in (1,2,3)]
        # Duplicate source routes also stay unambiguous; use distinct origin tables.
        for i,link in enumerate(action['links']):link['from']='panel_'+str((0,4,6)[i])+'_2'
        with self.assertRaisesRegex(ProviderError,'limit is eight'):compile_plan(action)
    def test_overall_kpi_cannot_silently_display_last_grouped_row(self):
        action=plan();action['sources'][0]['recipe']['groupBy']='host'
        with self.assertRaisesRegex(ProviderError,'ungrouped'):compile_plan(action)
    def test_unused_model_declarations_never_compile_or_change_the_board(self):
        expected=compile_plan(plan())[1];action=plan();before=copy.deepcopy(action)
        action['sources'].append({'id':'unused','recipe':{'kind':'stats','metrics':[{'function':'avg','field':'missing_input','alias':'unused'}],'groupBy':''}})
        self.assertEqual(compile_plan(action)[1],expected);self.assertEqual(action['sources'][:3],before['sources'])
    def test_invalid_unknown_duplicate_or_wrong_membership_is_atomic(self):
        cases=[]
        bad=plan();bad['panels'][0]['extra']='unknown';cases.append(bad)
        bad=plan();bad['panels'][0]['id']=bad['panels'][1]['id'];cases.append(bad)
        bad=plan();bad['panels'][0]['page']=True;cases.append(bad)
        bad=plan();bad['sources'][0]['recipe']=None;cases.append(bad)
        bad=plan();bad['panels']=[dict(p,page=0)for p in bad['panels']];cases.append(bad)
        for action in cases:
            before=copy.deepcopy(action)
            with self.subTest(action=action),self.assertRaises(ProviderError):compile_plan(action)
            self.assertEqual(action,before)
    def test_dynamic_split_series_are_actual_numeric_columns_not_guessed_categories(self):
        options=native_options('splunk.area',{'x':'_time','y':[]},'| timechart bins=100 count BY host')
        item=viz('area',options)
        validate_shape(item,{'s':frame(['_time','fixture_a','fixture_b'],[[1000,3,7]])})
        for fields,values in [(['_time','fixture_a'],[1000,'text']),(['fixture_a','_time'],[3,1000])]:
            with self.assertRaises(ProviderError):validate_shape(item,{'s':frame(fields,[values])})
        with self.assertRaises(ProviderError):native_options('splunk.line',{'x':'_time','y':[]},'| timechart count AS observed')
    def test_network_endpoint_coverage_and_alignment_have_payload_free_feedback(self):
        outputs={'links':frame(['from_node','to_node'],[['fixture_private_a','fixture_private_b']]),'nodes':frame(['id','size'],[['fixture_private_a',3]])}
        item=viz('networkGraph',{'source':'> primary | seriesByName("from_node")','target':'> primary | seriesByName("to_node")'}, {'primary':'links','nodeSource':'nodes'})
        with self.assertRaisesRegex(ProviderError,'endpoint')as raised:validate_shape(item,outputs)
        self.assertNotIn('fixture_private_b',str(raised.exception))
        item['options']['nodeIds']='> nodeSource | seriesByName("id")';outputs['nodes']=frame(['id','size'],[['fixture_private_a',2],['fixture_private_b',1]])
        with self.assertRaisesRegex(ProviderError,'membership'):validate_shape(item,outputs)
        outputs['links']=frame(['from_node','to_node'],[['fixture_private_a','fixture_private_b'],['fixture_private_b',None]])
        validate_shape(item,outputs)
        outputs['nodes']=frame(['id','size'],[['fixture_private_a',2],['fixture_private_b',1],['fixture_private_c',1]])
        bad=copy.deepcopy(item);bad['options']['target']='> nodeSource | seriesByName("id")'
        with self.assertRaisesRegex(ProviderError,'align one endpoint'):validate_shape(bad,outputs)
        item['options']['nodeValues']='> primary | seriesByIndex(0)'
        with self.assertRaisesRegex(ProviderError,'align'):validate_shape(item,outputs)
    def test_fractional_precision_does_not_modify_measurements_or_explicit_user_work(self):
        original,result,_=compile_plan(plan());before=copy.deepcopy(result)
        outputs={'ds_plan_metrics':frame(['mean_f'],[[.003125]])}
        changes=verified_precision(result,original,outputs);self.assertEqual(len(changes),8)
        self.assertTrue(all(c['value']=='4'for c in changes));self.assertEqual(result,before)
        self.assertEqual(verified_precision(result,result,outputs),[])
        for item in result['visualizations'].values():item.setdefault('options',{})['numberPrecision']=0
        self.assertEqual(verified_precision(result,original,outputs),[])
        general=copy.deepcopy(before)
        for item in general['visualizations'].values():
            item.get('options',{}).pop('sparklineDisplay',None);item.get('options',{}).pop('trendDisplay',None)
        defaults=verified_precision(general,original,outputs)
        self.assertEqual(sum(c['path'].endswith('/sparklineDisplay')for c in defaults),8)
        self.assertEqual(sum(c['path'].endswith('/trendDisplay')for c in defaults),8)
    def test_larger_plan_executes_real_orchestration_once_and_recovers_without_losing_requirements(self):
        class Model(Provider):
            def __init__(self,provider,replies):super().__init__(replies);self.kind=provider
            def configured(self):return {'provider':self.kind,'model':'synthetic'}
            def capabilities(self,saved):return {'contextTokens':32768,'images':False,'pdf':False}
        class Searches(Runtime):
            def preview(self,body):
                if body.get('fieldDiscovery'):return dict(frame(['_time','host','temperature_f'],[[1000,'fixture_a',.003125]]),evidence={'state':'complete'})
                self.calls.append(body)
                if 'timechart'in body['query']:return frame(['_time','mean_f'],[[1000,.003125]])
                if 'BY host'in body['query']:return frame(['host','observations'],[['fixture_a',1]])
                return frame(['mean_f','observations'],[[.003125,1]])
        for provider in ('openai','ollama','aitk'):
            layout=plan();pool=layout.pop('sources');layout['op']='boardLayout'
            replies=[reply([{'op':'boardSources','sources':pool}]),reply([layout])]if provider in ('ollama','aitk')else[reply([plan()])]
            runtime=Searches();model=Model(provider,replies);original=blank()['definition']
            result=AgentService(model,runtime).assist({'prompt':GOAL,'revision':0,'definition':original,'dataContext':blank()['dataContext']})
            final=apply_changes(original,result['changes']);self.assertEqual(len(final['visualizations']),24);self.assertEqual(len(final['dataSources']),3)
            self.assertEqual(result['recovery']['modelCalls'],2 if provider in ('ollama','aitk')else 1);self.assertEqual(result['recovery']['queryChecks'],3);self.assertFalse(result['repaired'])
            self.assertEqual(final['visualizations']['panel_0_0']['options']['numberPrecision'],4)
            self.assertFalse(original['visualizations'])
        bad=copy.deepcopy(layout);bad['panels'].pop();runtime=Searches();model=Model('ollama',[reply([{'op':'boardSources','sources':pool}]),reply([bad]),reply([layout])])
        result=AgentService(model,runtime).assist({'prompt':GOAL,'revision':0,'definition':original,'dataContext':blank()['dataContext']})
        self.assertTrue(result['repaired']);self.assertEqual(result['recovery']['modelCalls'],3)
        feedback=json.loads(model.requests[-1]['input'][-1]['content'][0]['text']);self.assertEqual(feedback['recoveryFeedback']['editsApplyTo'],'original')
        runtime=Searches();model=Model('ollama',[reply([{'op':'boardSources','sources':pool}]),reply([bad]),reply([bad])])
        untouched=copy.deepcopy(original)
        with self.assertRaises(ProviderError):AgentService(model,runtime).assist({'prompt':GOAL,'revision':0,'definition':original,'dataContext':blank()['dataContext']})
        self.assertEqual(original,untouched);self.assertEqual(len(runtime.calls),3);self.assertEqual(len(model.requests),3)
    def test_unavailable_exact_family_is_negotiated_before_model_or_profile(self):
        class Older(Runtime):
            def environment(self):return {'version':'10.2.8','features':feature_profile('10.2.8',[]),'visualizations':['splunk.linkgraph']}
            def preview(self,body):raise AssertionError('Unavailable-feature preflight dispatched data search')
        model=Provider([]);result=AgentService(model,Older()).assist({'prompt':'Create one page with one network graph.','revision':0,'definition':blank()['definition'],'dataContext':blank()['dataContext'],'suggestionFormat':'cards'})
        self.assertEqual(result['changes'],[]);self.assertEqual(result['recovery']['modelCalls'],0);self.assertEqual(result['recovery']['queryChecks'],0)
        self.assertIn('link graph',result['suggestions'][0]['prompt']);self.assertFalse(model.requests)

    def test_changed_parent_validates_unchanged_chain_consumers_and_retains_source_budget(self):
        from data_service import DataService
        from test_search_chart_actions import chart, page
        actions=[{'op':'search','id':'events','pipeline':'| stats count AS old'},
                 {'op':'set','path':'/dataSources/child','value':json.dumps({'type':'ds.chain','options':{'extend':'events','query':'| eval derived=old*2'}})},
                 dict(chart('splunk.table','',['derived']),sourceId='child'),page()]
        old=apply_changes(blank()['definition'],compile_actions(blank()['definition'],actions,PROFILE));new=copy.deepcopy(old)
        new['dataSources']['events']['options']['query']=PROFILE['baseQuery']+' | stats count AS changed'
        class Searches:
            def __init__(self):self.calls=[]
            def preview(self,body):
                self.calls.append(body)
                if 'eval derived'in body['query']:raise ProviderError('Synthetic missing old alias',422,'preview_failed')
                return frame(['changed'],[[2]])
        runtime=Searches()
        with self.assertRaisesRegex(ProviderError,'child'):DataService(runtime).validate_searches(new,old,PROFILE)
        self.assertEqual(len(runtime.calls),2)
        for i in range(8):
            item={'type':'ds.chain','options':{'extend':'events','query':'| eval derived=old*2'}}
            old['dataSources']['extra_'+str(i)]=copy.deepcopy(item);new['dataSources']['extra_'+str(i)]=item
        runtime=Searches()
        with self.assertRaisesRegex(ProviderError,'eight affected'):DataService(runtime).validate_searches(new,old,PROFILE)
        self.assertFalse(runtime.calls)
