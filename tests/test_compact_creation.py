"""Compact proposals keep native compilation, search guards and atomic recovery."""
import copy
import json
import unittest
from test_drafts_and_data import blank
from test_reliability_journey import Provider, Runtime, reply
from test_search_chart_actions import PROFILE
from compact_creation import expand_compose, COMPOSE_ACTION, compact_goal, without_redundant_input_casts, detail_timechart
from authoring_actions import compile_actions, validate_chart_placement
from authoring_budget import AuthoringBudget
from agent_service import AgentService, SCHEMA
from studio_contract import apply_changes
from provider_service import ProviderError
from page_service import proposed_purposes
from token_service import resolve_query_tokens


def panel(identifier='volume', kind='splunk.line', pipeline='| timechart bins=100 count AS count', x='_time', y=None):
    return {'id': identifier, 'type': kind, 'title': 'Recorded observations', 'pipeline': pipeline, 'x': x, 'y': ['count'] if y is None else y}


def compose():
    return {'op': 'compose', 'title': 'Observed activity', 'description': 'Real selected data.',
            'pages': [{'id': 'main', 'label': 'Overview', 'purpose': 'Summarize observations', 'columns': 1,
                       'panels': [panel(), panel('devices', 'splunk.table', '| stats count BY device_name', '', ['device_name', 'count'])]},
                      {'id': 'details', 'label': 'Device details', 'purpose': 'Investigate one device', 'columns': 2,
                       'panels': [panel('detail'), panel('detail_count', 'splunk.singlevalue', '| stats count', '')]}],
            'links': [{'from': 'devices', 'to': 'details', 'field': 'device_name'}]}


class CompactCreationTests(unittest.TestCase):
    def test_fixed_alias_detail_trend_removes_only_its_redundant_verified_entity_group(self):
        profile=dict(PROFILE,fields=[{'name':'host'},{'name':'duration','numeric':True}])
        chart={'chartType':'splunk.line','x':'_time','y':['mean']}
        query='| where duration>=0 | timechart bins=100 avg(duration) AS mean BY host'
        self.assertEqual(detail_timechart(query,chart,'host',profile),query.removesuffix(' BY host'))
        for changed in (query+' | fields _time mean host',query.replace('BY host','BY other'),
                        query.replace('avg(duration)','avg(eval(duration+1))'),query.replace('bins=100','bins=100 limit=0'),
                        query.replace('avg(duration)',"avg('duration')")):
            self.assertEqual(detail_timechart(changed,chart,'host',profile),changed)
        self.assertEqual(detail_timechart(query,dict(chart,y=['different']),'host',profile),query)
        self.assertEqual(detail_timechart(query,chart,'host',dict(profile,scope={'query':'search index=fixture','language':'spl'})),query)
        self.assertEqual(detail_timechart(query,chart,'host',dict(profile,scope={'index':'fixture','language':'spl2'})),query)
        action=compose();action['links'][0]['field']='host';action['pages'][0]['panels'][1]['pipeline']='| stats count BY host';action['pages'][0]['panels'][1]['y']=['host','count']
        action['pages'][1]['panels'][0]['pipeline']='| timechart bins=100 count AS count BY host'
        before=copy.deepcopy(action)
        expanded=expand_compose([action],blank()['definition'],profile,'Build two pages with a row-linked detail trend.')
        detail=next(x for x in expanded if x.get('id')=='ds_detail')
        self.assertNotIn('BY host',detail['pipeline']);self.assertEqual(action,before)
        explicit='Build two pages with separate series by host.'
        self.assertFalse(compact_goal({'request':explicit}))
        self.assertTrue(compact_goal({'request':'Build two pages with a trend followed by a summary table.'}))
        expanded=expand_compose([action],blank()['definition'],profile,explicit)
        self.assertIn('BY host',next(x for x in expanded if x.get('id')=='ds_detail')['pipeline'])
    def test_fresh_table_separators_preserve_expressions_scope_and_other_panels(self):
        action=compose();action['links']=[]
        query='| stats avg(duration) AS mean max(duration) AS peak latest(_time) AS seen BY device_name | eval mean=round(mean,2) peak=round(peak,1) seen=strftime(seen,"%Y|%m,%d %H:%M:%S")'
        action['pages'][0]['panels'][1].update(pipeline=query,y=['device_name','mean','peak','seen'])
        before=copy.deepcopy(action);original=blank()['definition'];original['future']={'keep':True}
        expanded=expand_compose([action],original,PROFILE)
        searches={a['id']:a['pipeline']for a in expanded if a['op']=='search'}
        self.assertEqual(searches['ds_devices'],query.replace(') peak=', '), peak=').replace(') seen=', '), seen='))
        self.assertEqual(searches['ds_volume'],action['pages'][0]['panels'][0]['pipeline'])
        self.assertEqual(action,before);self.assertEqual(original['future'],{'keep':True})

    def test_fresh_table_unknown_expressions_and_raw_stages_are_not_rewritten(self):
        for query in ('| eval mean=round(mean,2) peak=round(peak,1) | stats avg(mean) AS mean',
                      '| stats count AS mean | eval mean=round(other,2) peak=round(peak,1)',
                      '| stats count AS mean | eval mean=round(mean,2) AND peak=round(peak,1)',
                      '| stats count AS mean | eval mean=round(mean,2) peak=coalesce(peak,0)'):
            action=compose();action['pages'][0]['panels'][1]['pipeline']=query
            self.assertEqual(next(a['pipeline']for a in expand_compose([action],blank()['definition'],PROFILE)if a.get('id')=='ds_devices'),query)
        action=compose();action['pages'][0]['panels'][0]['pipeline']='| stats count AS mean | eval mean=round(mean,2) peak=round(peak,1)'
        self.assertEqual(next(a['pipeline']for a in expand_compose([action],blank()['definition'],PROFILE)if a.get('id')=='ds_volume'),action['pages'][0]['panels'][0]['pipeline'])

    def test_new_table_eval_is_validated_with_one_model_call_across_compact_providers(self):
        class Outputs(Runtime):
            def preview(self,body):
                if body.get('fieldDiscovery'):return super().preview(body)
                self.calls.append(body)
                if ') peak='in body['query']:raise ProviderError('Malformed eval',422,'preview_failed')
                return {'state':'complete','fields':[{'name':n}for n in ('mean','peak')],'results':[{'mean':'12','peak':'42'}]}
        for kind in ('aitk','ollama'):
            class CompactProvider(Provider):
                def configured(self):return {'provider':kind,'model':'fixture'}
                def capabilities(self,saved):return {'contextTokens':32768,'images':False,'pdf':False}
            action=compose();action['links']=[];action['pages']=[dict(action['pages'][0],panels=[panel('metrics','splunk.table','| stats avg(duration) AS mean max(duration) AS peak | eval mean=round(mean,2) peak=round(peak,1)','',['mean','peak'])])]
            original=blank()['definition'];before=copy.deepcopy(original);provider=CompactProvider([reply([action])]);runtime=Outputs()
            result=AgentService(provider,runtime).assist({'prompt':'Build one page with one table of mean and peak duration.','revision':0,'definition':original,'dataContext':blank()['dataContext']})
            query=apply_changes(original,result['changes'])['dataSources']['ds_metrics']['options']['query']
            self.assertIn('), peak=',query);self.assertEqual(result['recovery']['modelCalls'],1);self.assertEqual(result['recovery']['queryChecks'],1)
            self.assertFalse(result['repaired']);self.assertEqual(original,before);self.assertTrue(any(query==c.get('query')for c in runtime.calls if isinstance(c,dict)))

    def test_named_page_count_keeps_ordinary_phrasing_on_the_bounded_plan_path(self):
        from creation_strategy import explicit_page_count
        for noun in ('named','distinct','separate'):
            request='Build exactly two '+noun+' pages with exactly four charts and row navigation.'
            self.assertEqual(explicit_page_count(request),2);self.assertTrue(compact_goal({'request':request}))
        self.assertIsNone(explicit_page_count('Build two named pages or three separate pages.'))
        self.assertIsNone(explicit_page_count('Build two pages, then five named pages.'))
    def test_wide_tables_occupy_a_clear_full_row_without_clipping_or_reordering_other_panels(self):
        original=blank()['definition'];action=compose();action['links']=[]
        wide=panel('wide','splunk.table','| stats count AS observations count AS expected count AS seen count AS total BY device_name','',['device_name','observations','expected','seen','total'])
        action['pages']=[dict(action['pages'][0],columns=2,panels=[panel('first'),wide,panel('last')])]
        result=apply_changes(original,compile_actions(original,[action],dict(PROFILE,fields=[{'name':'device_name'}])))
        page=result['layout']['layoutDefinitions']['layout_main'];positions={i['item']:i['position']for i in page['structure']}
        self.assertEqual(positions['wide']['w'],1160);self.assertEqual(positions['wide']['x'],20)
        self.assertGreaterEqual(positions['wide']['y'],positions['first']['y']+positions['first']['h'])
        self.assertGreaterEqual(positions['last']['y'],positions['wide']['y']+positions['wide']['h'])
        validate_chart_placement(result,original)

    def test_selective_navigation_and_explicit_button_constraints_keep_native_actions(self):
        for suffix in ('Do not add a return button.','No back buttons.','Add a return button labelled "Home".','Use a named token.','Filter only one destination chart.','Put the summary table to the left of the trend.','Make the trend span both columns.'):
            self.assertFalse(compact_goal({'request':'Build two pages. '+suffix}))
        self.assertTrue(compact_goal({'request':'Build two pages with row navigation and a return button.'}))

    def test_links_accept_only_unambiguous_declared_references(self):
        original=blank()['definition'];profile=dict(PROFILE,fields=[{'name':'device_name'}]);action=compose()
        action['links'][0].update(**{'from':'ds_devices','to':'layout_details'})
        self.assertTrue(any(a['op']=='button' for a in expand_compose([action],original,profile)))
        action['links'][0].update(to='Device details')
        self.assertTrue(any(a['op']=='filter' for a in expand_compose([action],original,profile)))
        action['links'][0].update(**{'from':'Recorded observations'})
        with self.assertRaises(ProviderError):expand_compose([action],original,profile)

    def test_link_containment_uses_only_a_unique_declared_table_and_parent_page(self):
        original=blank()['definition'];profile=dict(PROFILE,fields=[{'name':'device_name'}]);action=compose()
        action['links'][0].update(**{'from':'Overview','to':'ds_detail'})
        result=apply_changes(original,compile_actions(original,[action],profile))
        self.assertTrue(any(h['type']=='drilldown.switchToTab' and h['options']['tabId']=='layout_details' for h in result['visualizations']['devices']['eventHandlers']))
        action['pages'][0]['panels'].append(panel('another','splunk.table','| stats count BY device_name','',['device_name','count']))
        with self.assertRaises(ProviderError):expand_compose([action],original,profile)
        action=compose();action['links'][0].update(to='missing_panel')
        with self.assertRaises(ProviderError):expand_compose([action],original,profile)
        action=compose();action['pages'][1]['label']='Recorded observations';action['links'][0].update(**{'from':'Recorded observations'})
        with self.assertRaises(ProviderError):expand_compose([action],original,profile)

    def test_numeric_identity_cast_repair_keeps_the_cutoff_guard_and_other_expressions(self):
        profile=dict(PROFILE,fields=[{'name':'temperature_f','numeric':True},{'name':'wifi_rssi','numeric':True}],measurementConstraints=[{'field':'temperature_f','maximum':150,'unit':'F'}])
        suffix='| eval temperature_f=tonumber(temperature_f), wifi_rssi=tonumber(wifi_rssi) | stats avg(temperature_f) AS temperature'
        self.assertEqual(without_redundant_input_casts(suffix,profile),'| stats avg(temperature_f) AS temperature')
        for expression in ('temperature_f=tonumber(temperature_f,16)','temperature_f=coalesce(tonumber(temperature_f),0)','temperature_f=tonumber(other)','temperature_f=tonumber(TEMPERATURE_F)','temperature_f=tonumber(temperature_f)+1','temperature_f=tonumber(temperature_f),wifi_rssi=unknown'):
            query='| eval '+expression+' | stats avg(temperature_f) AS temperature'
            self.assertEqual(without_redundant_input_casts(query,profile),query)
        after='| stats avg(temperature_f) AS temperature_f | eval temperature_f=tonumber(temperature_f)'
        self.assertEqual(without_redundant_input_casts(after,profile),after)
        action=compose();action['links']=[];action['pages']=[dict(action['pages'][0],panels=[panel('temp','splunk.singlevalue',suffix,'',['temperature'])])]
        result=apply_changes(blank()['definition'],compile_actions(blank()['definition'],[action],profile))
        self.assertIn('temperature_f=if(temperature_f<=150,temperature_f,null())',result['dataSources']['ds_temp']['options']['query'])
        action['pages'][0]['panels'][0]['pipeline']='| eval temperature_f=coalesce(temperature_f,0) | stats avg(temperature_f) AS temperature'
        with self.assertRaises(ProviderError):compile_actions(blank()['definition'],[action],profile)

    def test_expands_to_native_pages_filtered_sources_and_readable_buttons(self):
        original = blank()['definition']; original['future'] = {'keep': True}; before = copy.deepcopy(original)
        profile = dict(PROFILE, fields=[{'name': 'device_name'}])
        actions = expand_compose([compose()], original, profile)
        self.assertLess(len(json.dumps(compose())), len(json.dumps(actions)))
        result = apply_changes(original, compile_actions(original, [compose()], profile))
        self.assertEqual(result['future'], before['future']); self.assertEqual(original, before)
        self.assertEqual([t['label'] for t in result['layout']['tabs']['items']], ['Overview', 'Device details'])
        self.assertEqual(len(result['visualizations']), 4)
        self.assertEqual(proposed_purposes(actions, {}, result)['layout_details'], 'Investigate one device')
        for source in ('ds_detail', 'ds_detail_count'):
            query = result['dataSources'][source]['options']['query']
            self.assertIn('| search device_name=$select_details|s$', query)
            self.assertIn('device_name="*"', resolve_query_tokens(query, result))
            self.assertEqual(result['dataSources'][source]['options']['queryParameters'], {'earliest': '-24h', 'latest': 'now'})
        self.assertTrue(any(h['type'] == 'drilldown.switchToTab' and h['options']['tabId'] == 'layout_main' for h in result['inputs']['back_0']['eventHandlers']))
        validate_chart_placement(result, original)

    def test_never_replaces_existing_user_content_or_non_spl(self):
        original = blank()['definition']
        for key in ('visualizations', 'dataSources', 'inputs'):
            doc = copy.deepcopy(original); doc[key] = {'user_owned': {'future': True}}; before = copy.deepcopy(doc)
            with self.assertRaises(ProviderError): compile_actions(doc, [compose()], PROFILE)
            self.assertEqual(doc, before)
        with self.assertRaises(ProviderError): expand_compose([compose()], original, dict(PROFILE, scope=dict(PROFILE['scope'], language='spl2')))
        with self.assertRaises(ProviderError): expand_compose([compose(), {'op': 'remove', 'path': '/title', 'value': ''}], original, PROFILE)

    def test_rejects_duplicates_wrong_destinations_and_unknown_fields_atomically(self):
        mutations = [lambda a: a['pages'][1].update(id='main'),
                     lambda a: a['pages'][1]['panels'][0].update(id='volume'),
                     lambda a: a['pages'][0].update(columns=True),
                     lambda a: a['pages'][0]['panels'][0].update(id='../unsafe'),
                     lambda a: a['pages'][0]['panels'][0].update(url='https://example.invalid'),
                     lambda a: a['links'][0].update(to='main'),
                     lambda a: a['links'][0].update(**{'from': 'volume'}),
                     lambda a: a.update(owner='another_user')]
        original = blank()['definition']; before = copy.deepcopy(original)
        for mutation in mutations:
            action = compose(); mutation(action)
            with self.subTest(action=action), self.assertRaises(ProviderError): compile_actions(original, [action], PROFILE)
        self.assertEqual(original, before)

    def test_expansion_keeps_preview_and_edit_bounds(self):
        action = compose(); action['pages'][0]['panels'] = [panel('p' + str(i)) for i in range(8)]
        with self.assertRaises(ProviderError): expand_compose([action], blank()['definition'], PROFILE)
        action = compose(); action['links'][0]['field'] = 'unverified'
        with self.assertRaises(ProviderError): compile_actions(blank()['definition'], [action], dict(PROFILE, fields=[{'name': 'device_name'}]))

    def test_agent_still_runs_actual_output_binding_and_recovery_checks(self):
        action = compose(); action['pages'] = [dict(action['pages'][0], panels=[panel('volume', 'splunk.table', '| stats count', '', ['missing'])]),
            dict(action['pages'][1], panels=[panel('detail', 'splunk.table', '| stats count', '', ['count'])])]; action['links'] = []
        fix = copy.deepcopy(action); fix['pages'][0]['panels'][0]['y'] = ['count']
        class CompactProvider(Provider):
            def configured(self): return {'provider':'aitk','model':'fixture'}
        original = blank()['definition']; provider = CompactProvider([reply([action]), reply([fix])]); runtime = Runtime()
        result = AgentService(provider, runtime).assist({'prompt': 'Build two pages of activity counts', 'revision': 0, 'definition': original, 'dataContext': blank()['dataContext']})
        self.assertEqual(result['recovery']['modelCalls'], 2); self.assertEqual(result['recovery']['queryChecks'], 1)
        self.assertTrue(result['validationNotes']); self.assertFalse(original['visualizations'])
        self.assertEqual(result['pagePurposes']['layout_main'], action['pages'][0]['purpose'])
        self.assertEqual(provider.requests[0]['text']['format']['schema']['properties']['changes']['items']['properties']['pages']['minItems'], 2)
        schema = provider.requests[1]['text']['format']['schema']['properties']['changes']['items']
        self.assertEqual(schema['properties']['op']['enum'], ['compose'])
        self.assertEqual(json.loads(provider.requests[1]['input'][-1]['content'][0]['text'])['recoveryFeedback']['editsApplyTo'], 'original')
        self.assertIn('volume', apply_changes(original, result['changes'])['visualizations'])

    def test_explicit_one_page_creation_keeps_the_same_execution_and_binding_checks(self):
        action=compose();action['pages']=[dict(action['pages'][0],panels=[panel('count','splunk.singlevalue','| stats count AS readings','',['readings'])])];action['links']=[]
        class CompactProvider(Provider):
            def configured(self):return {'provider':'ollama','model':'fixture'}
            def capabilities(self,saved):return {'contextTokens':32768,'images':False,'pdf':False}
        original=blank()['definition'];runtime=Runtime();provider=CompactProvider([reply([action])])
        # The fixture runtime returns count; use that exact observed output.
        action['pages'][0]['panels'][0].update(pipeline='| stats count',y=['count'])
        result=AgentService(provider,runtime).assist({'prompt':'Create a one-page dashboard of activity counts','revision':0,'definition':original,'dataContext':blank()['dataContext']})
        schema=provider.requests[0]['text']['format']['schema']['properties']['changes']['items']
        self.assertEqual(schema['properties']['pages']['minItems'],1);self.assertEqual(schema['properties']['pages']['maxItems'],1)
        self.assertEqual(result['recovery']['queryChecks'],1);self.assertEqual(result['recovery']['modelCalls'],1)
        self.assertEqual(len(apply_changes(original,result['changes'])['layout']['tabs']['items']),1)
        self.assertEqual(original['visualizations'],{})
        from creation_strategy import explicit_page_count
        self.assertIsNone(explicit_page_count('Build one page and two pages'))
        self.assertIsNone(explicit_page_count('Build a multi-page dashboard'))
        self.assertFalse(compact_goal({'request':'Build one page with a map and dropdown'}))

    def test_advanced_actions_remain_available_and_staged_candidates_cannot_compose(self):
        context = {'request': 'Build two pages', 'canvasState': 'blank', 'history': [], 'dataProfile': PROFILE}
        request = {'instructions': 'Preserve native features', 'text': {'format': {'schema': copy.deepcopy(SCHEMA)}}, 'input': [{'content': []}]}
        budget = AuthoringBudget({'provider': 'aitk'}, context); budget.prepare(request, blank()['definition'])
        self.assertEqual(request['text']['format']['schema']['properties']['changes']['items']['properties']['pages']['maxItems'], 2)
        candidate = copy.deepcopy(blank()['definition']); candidate['visualizations']['user_chart'] = {'type': 'splunk.markdown'}
        budget.prepare(request, candidate)
        choices = request['text']['format']['schema']['properties']['changes']['items']['anyOf']
        self.assertNotIn(COMPOSE_ACTION, choices); self.assertTrue(any(c['properties']['op']['enum'] == ['set', 'remove'] for c in choices))
        advanced = AuthoringBudget({'provider':'aitk'},dict(context,request='Build two pages with a map and dropdown'))
        advanced.prepare(request, blank()['definition'])
        self.assertIn('anyOf', request['text']['format']['schema']['properties']['changes']['items'])

    def test_ollama_full_repair_restores_the_existing_output_allowance(self):
        context={'request':'Build two pages','canvasState':'blank','history':[],'dataProfile':PROFILE,'modelLimits':{'contextTokens':32768,'outputTokens':8500}}
        request={'instructions':'Preserve native features','text':{'format':{'schema':copy.deepcopy(SCHEMA)}},'input':[{'content':[]}]}
        budget=AuthoringBudget({'provider':'ollama'},context);budget.prepare(request,blank()['definition'])
        self.assertEqual(request['max_output_tokens'],3500)
        self.assertEqual(json.loads(request['input'][0]['content'][0]['text'])['modelLimits']['outputTokens'],3500)
        self.assertEqual(context['modelLimits']['outputTokens'],8500)
        candidate=blank()['definition'];candidate['visualizations']={'new_chart':{'type':'splunk.table'}}
        budget.feedback(request,{'recoveryFeedback':{'candidateDefinition':candidate,'editsApplyTo':'candidate'},'rejectedOutput':'{}'})
        self.assertEqual(request['max_output_tokens'],8500)
        self.assertEqual(json.loads(request['input'][0]['content'][0]['text'])['modelLimits']['outputTokens'],8500)
        self.assertNotIn(COMPOSE_ACTION,request['text']['format']['schema']['properties']['changes']['items']['anyOf'])

    def test_compact_page_requirement_also_applies_to_schema_ignoring_adapters(self):
        context={'request':'Build two pages','canvasState':'blank','history':[],'dataProfile':PROFILE}
        budget=AuthoringBudget({'provider':'aitk'},context)
        request={'instructions':'Preserve','text':{'format':{'schema':copy.deepcopy(SCHEMA)}},'input':[{'content':[]}]}
        budget.prepare(request,blank()['definition'])
        action=compose();action['pages']=action['pages'][:1];action['links']=[]
        original=copy.deepcopy(blank()['definition'])
        with self.assertRaises(ProviderError):budget.actions([action],original)
        self.assertEqual(original,blank()['definition'])
