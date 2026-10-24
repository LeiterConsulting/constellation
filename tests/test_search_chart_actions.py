"""Provider-neutral builders retain native work and still use execution guards."""
import copy
import json
import unittest
from test_drafts_and_data import blank
from test_reliability_journey import Provider, Runtime, reply
from agent_service import AgentService
from authoring_actions import compile_actions
from studio_contract import apply_changes, validate_document
from provider_service import ProviderError

PROFILE={'baseQuery':'search index="fixture_index"','scope':{'index':'fixture_index','language':'spl','earliest':'-24h'}}
def chart(kind='splunk.line',x='_time',y=None):
    return {'op':'chart','id':'trend','chartType':kind,'title':'Activity','description':'Observed events', 'sourceId':'events','x':x,'y':['count'] if y is None else y}
def page():
    return {'op':'page','layoutId':'layout_main','label':'Overview','purpose':'Understand activity','moveItems':False,'width':1200,'height':600,'items':[{'id':'trend','kind':'block','x':20,'y':20,'w':1160,'h':400}]}

class SearchChartActionTests(unittest.TestCase):
    def test_raw_native_binding_text_is_encoded_and_still_checked_against_actual_fields(self):
        doc=apply_changes(blank()['definition'],compile_actions(blank()['definition'],[{'op':'search','id':'events','pipeline':'| stats count'},chart('splunk.table','',['count']),page()],PROFILE))
        raw={'op':'set','path':'/visualizations/trend/options/table','value':'> primary | frameBySeriesNames("count")'}
        title={'op':'set','path':'/visualizations/trend/title','value':'Event count'}
        provider=Provider([reply([raw,title])]);runtime=Runtime()
        result=AgentService(provider,runtime).assist({'prompt':'Polish only this selected table','revision':1,'definition':doc,'dataContext':blank()['dataContext'],'selected':'trend'})
        changed=apply_changes(doc,result['changes'])
        self.assertEqual(result['recovery']['modelCalls'],1)
        self.assertEqual(changed['visualizations']['trend']['options']['table'],raw['value'])
        self.assertEqual(changed['visualizations']['trend']['title'],'Event count')
        self.assertEqual(changed['dataSources'],doc['dataSources'])
        # JSON containers and malformed quoted strings are never treated as raw DOS.
        for value in ('"unfinished', '{unfinished'):
            with self.assertRaises(ProviderError):compile_actions(doc,[dict(raw,value=value)],PROFILE)
        bad=Provider([reply([dict(raw,value='> primary | frameBySeriesNames("missing")')])]*3)
        with self.assertRaises(ProviderError):AgentService(bad,Runtime()).assist({'prompt':'Polish only this table','revision':1,'definition':doc,'dataContext':blank()['dataContext'],'selected':'trend'})
    def test_new_row_filter_repair_requires_verified_native_intent_and_retains_other_fixes(self):
        from search_chart_actions import normalize_row_filters
        profile=dict(PROFILE,fields=[{'name':'device_name'}])
        doc=blank()['definition'];doc['defaults']={'tokens':{'default':{'device':{'value':'*'}}}}
        doc['layout']={'layoutDefinitions':{'layout_main':{'type':'absolute','structure':[]}},'tabs':{'items':[{'label':'Overview','layoutId':'layout_main'}]}}
        doc['visualizations']={'devices':{'type':'splunk.table','eventHandlers':[
            {'type':'drilldown.setToken','options':{'fields':['device_name'],'tokens':[{'token':'device','key':'row.device_name.value'}]}},
            {'type':'drilldown.switchToTab','options':{'fields':['device_name'],'tabId':'detail'}}]},
            'trend':{'type':'splunk.line','dataSources':{'primary':'events'}}}
        doc['layout']['layoutDefinitions']['detail']={'type':'absolute','structure':[{'item':'trend'}]}
        doc['layout']['tabs']['items'].append({'label':'Detail','layoutId':'detail'})
        doc['dataSources']={'events':{'type':'ds.search','future':'keep','options':{'query':'search index="fixture_index" | where device_name=$device|s$ AND value<=150 | stats count() AS reading_count'}}}
        before=copy.deepcopy(doc)
        result=apply_changes(doc,compile_actions(doc,[{'op':'set','path':'/description','value':'"Finished"'}],profile))
        # Untouched imported queries are preserved, including their old mistakes.
        self.assertEqual(result['dataSources'],doc['dataSources'])
        original=copy.deepcopy(doc);original['dataSources']['events']['options']['query']='search index="fixture_index" | stats count'
        result=apply_changes(original,compile_actions(original,[{'op':'set','path':'/dataSources/events/options/query','value':json.dumps(doc['dataSources']['events']['options']['query'])}],profile))
        self.assertEqual(result['dataSources']['events']['options']['query'],'search index="fixture_index" | search device_name=$device|s$ | where value<=150 | stats count AS reading_count')
        self.assertEqual(result['dataSources']['events']['future'],'keep')
        self.assertEqual(result['visualizations'],original['visualizations']);self.assertEqual(doc,before)
        self.assertEqual(normalize_row_filters(doc,{},dict(profile,fields=[])),[])
        no_link=copy.deepcopy(doc);no_link['visualizations']['devices']['eventHandlers']=[]
        self.assertEqual(normalize_row_filters(no_link,{},profile),[])
        self.assertEqual(normalize_row_filters(doc,doc,profile),[])
    def test_typed_filter_builds_safe_preaggregation_spl_and_preserves_native_work(self):
        from token_service import resolve_query_tokens
        profile=dict(PROFILE,fields=[{'name':'device_name'},{'name':'temperature_f'}])
        original=blank()['definition']
        original['dataSources']={'untouched':{'type':'ds.search','options':{'query':'search index=other | stats count'}}}
        original['future']={'keep':True};before=copy.deepcopy(original)
        actions=[{'op':'search','id':'events','pipeline':'| where temperature_f<=150 | stats avg(temperature_f) AS temperature'},
                 {'op':'token','name':'device','value':'*'}, {'op':'filter','sourceId':'events','field':'device_name','token':'device'},
                 {'op':'dashboard','title':'Sensor health','description':'A completed sensor view.'}]
        result=apply_changes(original,compile_actions(original,actions,profile))
        query=result['dataSources']['events']['options']['query']
        self.assertEqual(query,'search index="fixture_index" | search device_name=$device|s$ | where temperature_f<=150 | stats avg(temperature_f) AS temperature')
        self.assertIn('device_name="*"',resolve_query_tokens(query,result))
        self.assertIn('device_name="fixture_A"',resolve_query_tokens(query,result,{'default':{'device':'fixture_A'}}))
        again=apply_changes(result,compile_actions(result,[actions[2]],profile))
        self.assertEqual(again,result)
        self.assertEqual(result['dataSources']['untouched'],original['dataSources']['untouched'])
        self.assertEqual(result['future'],{'keep':True});self.assertEqual(original,before)
        for change in ({'field':'invented'},{'field':'device_name | delete'},{'token':'device|s$'},{'sourceId':'untouched'}):
            with self.subTest(change=change),self.assertRaises(ProviderError):
                compile_actions(result,[dict(actions[2],**change)],profile)
        with self.assertRaisesRegex(ProviderError,'SPL2/chain'):
            compile_actions(result,[actions[2]],dict(profile,scope=dict(profile['scope'],language='spl2')))
    def test_real_authoring_journey_compiles_source_bindings_and_scope_without_encoded_objects(self):
        class TimeRuntime(Runtime):
            def preview(self, body):
                self.calls.append(body)
                return {'fields':[{'name':'_time'},{'name':'count'}],'results':[{'_time':'2026-01-01T00:00:00Z','count':'12'}],'state':'complete'}
        original=blank()['definition'];provider=Provider([reply([{'op':'search','id':'events','pipeline':'| timechart bins=100 count'},chart(),page()])])
        result=AgentService(provider,TimeRuntime()).assist({'prompt':'Build with index=fixture_index','revision':0,'definition':original,'dataContext':blank()['dataContext']})
        doc=apply_changes(original,result['changes'])
        self.assertFalse(original['visualizations'])
        self.assertEqual(doc['dataSources']['events']['options']['query'],'search index="fixture_index" | timechart bins=100 count')
        self.assertEqual(doc['dataSources']['events']['options']['queryParameters'],{'earliest':'-24h','latest':'now'})
        self.assertEqual(doc['visualizations']['trend']['dataSources'],{'primary':'events'})
        self.assertEqual(doc['visualizations']['trend']['options']['x'],'> primary | seriesByName("_time")')
        self.assertEqual(doc['visualizations']['trend']['options']['y'],'> primary | frameBySeriesNames("count")')
        self.assertEqual(result['recovery']['modelCalls'],1)
        self.assertTrue(result['searchReceipts'])
    def test_builders_preserve_unrelated_sources_native_properties_and_handlers(self):
        doc=blank()['definition'];doc['dataSources']={'events':{'type':'ds.search','custom':'keep','options':{'query':'old','refresh':'5m','queryParameters':{'earliest':'-1h','latest':'now','custom':'keep'}}},'unrelated':{'type':'ds.search','options':{'query':'keep'}}}
        doc['visualizations']['trend']={'type':'splunk.line','options':{'legendDisplay':'right'},'eventHandlers':[{'type':'custom.existing'}],'unknown':'keep','dataSources':{'primary':'events'}}
        result=apply_changes(doc,compile_actions(doc,[{'op':'search','id':'events','pipeline':'| stats count'},chart()],PROFILE))
        self.assertEqual(result['dataSources']['unrelated'],doc['dataSources']['unrelated'])
        self.assertEqual(result['dataSources']['events']['custom'],'keep')
        self.assertEqual(result['dataSources']['events']['options']['queryParameters']['custom'],'keep')
        self.assertEqual(result['dataSources']['events']['options']['refresh'],'5m')
        self.assertEqual(result['visualizations']['trend']['eventHandlers'],doc['visualizations']['trend']['eventHandlers'])
        self.assertEqual(result['visualizations']['trend']['options']['legendDisplay'],'right')
        self.assertEqual(result['visualizations']['trend']['unknown'],'keep')
    def test_search_cannot_choose_another_scope_or_native_range(self):
        with self.assertRaises(ProviderError):compile_actions(blank()['definition'],[{'op':'search','id':'events','pipeline':'| stats count'}])
        action={'op':'search','id':'events','pipeline':'| stats count','index':'other'}
        with self.assertRaises(ProviderError):compile_actions(blank()['definition'],[action],PROFILE)
        provider=Provider([reply([{'op':'search','id':'events','pipeline':'| makeresults count=1'},chart(),page()])]*3)
        with self.assertRaises(ProviderError):AgentService(provider,Runtime()).assist({'prompt':'Build with index=fixture_index','revision':0,'definition':blank()['definition'],'dataContext':blank()['dataContext']})
    def test_single_value_table_and_spl2_preserve_native_types(self):
        doc=blank()['definition'];profile=copy.deepcopy(PROFILE);profile['scope']['language']='spl2'
        result=apply_changes(doc,compile_actions(doc,[{'op':'search','id':'events','pipeline':'| stats count'},chart('splunk.singlevalue','',['count'])],profile))
        self.assertEqual(result['dataSources']['events']['type'],'ds.spl2')
        self.assertEqual(result['visualizations']['trend']['options']['majorValue'],'> primary | seriesByName("count") | lastPoint()')
        result=apply_changes(result,compile_actions(result,[chart('splunk.table','',[])],profile))
        self.assertNotIn('majorValue',result['visualizations']['trend']['options'])
    def test_invalid_fields_ids_and_channel_shapes_rejected(self):
        for action in [chart('splunk.line','',[]),chart('splunk.singlevalue','',['a','b']),dict(chart(),id='__proto__'),dict(chart(),y=['field\nvalue']),dict(chart(),sourceId='../bad')]:
            with self.subTest(action=action),self.assertRaises(ProviderError):compile_actions(blank()['definition'],[action],PROFILE)
    def test_feedback_identifies_actual_missing_binding_and_available_source_ids(self):
        doc=blank()['definition'];doc['dataSources']={'events':{'type':'ds.search'}};doc['visualizations']={'trend':{'type':'splunk.line','dataSources':{'primary':'wrong'}}}
        with self.assertRaisesRegex(ProviderError,'trend.*wrong.*events'):validate_document(doc)
    def test_table_column_selection_uses_native_frame_and_missing_output_is_rejected(self):
        actions=[{'op':'search','id':'events','pipeline':'| stats count'},chart('splunk.table','',['count']),page()]
        provider=Provider([reply(actions)])
        result=AgentService(provider,Runtime()).assist({'prompt':'Build with index=fixture_index','revision':0,'definition':blank()['definition'],'dataContext':blank()['dataContext']})
        doc=apply_changes(blank()['definition'],result['changes'])
        self.assertEqual(doc['visualizations']['trend']['options']['table'],'> primary | frameBySeriesNames("count")')
        actions[1]['y']=['missing_field'];provider=Provider([reply(actions)]*3)
        with self.assertRaisesRegex(ProviderError,'recovery limit'):AgentService(provider,Runtime()).assist({'prompt':'Build with index=fixture_index','revision':0,'definition':blank()['definition'],'dataContext':blank()['dataContext']})
    def test_multiple_typed_tokens_preserve_existing_metadata_and_reject_mixed_defaults(self):
        doc=blank()['definition'];doc['defaults']={'unknown':'keep','tokens':{'default':{'selected':{'value':'old','unknown':'keep'},'untouched':{'value':'keep'}}}}
        actions=[{'op':'token','name':'selected','value':'*'},{'op':'token','name':'other','value':'all'}]
        result=apply_changes(doc,compile_actions(doc,actions))
        self.assertEqual(result['defaults']['tokens']['default']['selected'],{'value':'*','unknown':'keep'})
        self.assertEqual(result['defaults']['tokens']['default']['other'],{'value':'all'})
        self.assertEqual(result['defaults']['tokens']['default']['untouched'],{'value':'keep'})
        self.assertEqual(result['defaults']['unknown'],'keep')
        with self.assertRaises(ProviderError):compile_actions(doc,actions+[{'op':'set','path':'/defaults','value':'{}'}])
    def test_raw_query_patch_is_typed_text_but_malformed_objects_are_not_repaired(self):
        doc=blank()['definition'];doc['dataSources']={'events':{'type':'ds.search','options':{'query':'search index="fixture_index" | stats count'}}}
        query='search index="fixture_index" | stats count AS observations'
        result=apply_changes(doc,compile_actions(doc,[{'op':'set','path':'/dataSources/events/options/query','value':query}]))
        self.assertEqual(result['dataSources']['events']['options']['query'],query)
        with self.assertRaises(ProviderError):compile_actions(doc,[{'op':'set','path':'/dataSources/events/options/query','value':'{"query": broken'}])
    def test_changed_spl_event_count_shorthand_is_compiled_without_touching_other_meanings(self):
        pipeline='| eval label="count() AS literal" | stats count() AS observations count(host) AS populated count() AS *'
        doc=blank()['definition']
        result=apply_changes(doc,compile_actions(doc,[{'op':'search','id':'events','pipeline':pipeline}],PROFILE))
        query=result['dataSources']['events']['options']['query']
        self.assertIn('count AS observations',query);self.assertIn('"count() AS literal"',query)
        self.assertIn('count(host)',query);self.assertIn('count() AS *',query)
        spl2=copy.deepcopy(PROFILE);spl2['scope']['language']='spl2'
        other=apply_changes(doc,compile_actions(doc,[{'op':'search','id':'events','pipeline':'| stats count() AS observations'}],spl2))
        self.assertIn('count() AS observations',other['dataSources']['events']['options']['query'])
        self.assertEqual(compile_actions(result,[],PROFILE),[])
