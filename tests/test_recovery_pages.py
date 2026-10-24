import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from agent_service import AgentService
from provider_service import ProviderService, ProviderError
from recovery_service import RecoverySession, MAX_QUERY_CHECKS
from token_service import resolve_query_tokens, validate_wildcard_filters, without_entity_equality
from page_service import focus_context, proposed_purposes
from authoring_actions import compile_actions
from studio_contract import apply_changes
from draft_migrations import migrate_snapshot
from search_service import search_feedback
from test_agent_service import Client, Store, change
import test_agent_service as fixtures


class Runtime:
    def __init__(self): self.queries=[];self.profiles=0
    def environment(self): return {'version':'10.2.8','features':{'networkGraph':False}}
    def datasets(self): return {'indexes':[{'name':'esp32'}]}
    def execute(self,query,earliest):
        self.profiles+=1
        return {'results':[{'field':'temperature_f','count':'200','numeric_count':'200'}]}
    def preview(self,body):
        self.queries.append(copy.deepcopy(body))
        if 'broken' in body['query']: raise ProviderError('Correct query syntax and parentheses.',422,'fixture_syntax')
        return {'fields':[{'name':'average_f'}], 'results':[{'average_f':'PRIVATE EVENT VALUE'}]}


class RecoveryTests(unittest.TestCase):
    def test_literal_all_value_filter_is_repaired_before_search_execution(self):
        original=fixtures.NewDashboardTests().blank()
        bad=self.proposal('search index="esp32" | where device_name=$entity|s$ | stats avg(temperature_f) AS average_f','average_f')
        bad['changes'].append({'op':'token','name':'entity','value':'*'})
        good={'message':'Updated the device filter.','suggestions':[],'changes':[
            change('/dataSources/temperature/options/query','search index="esp32" | search device_name=$entity|s$ | stats avg(temperature_f) AS average_f')]}
        client=Client([bad,good]);runtime=Runtime()
        result=AgentService(ProviderService(Store(),client),runtime).assist({'prompt':'Build a device-filtered temperature chart','revision':0,'definition':original,'dataContext':{'index':'esp32','earliest':'-24h'}})
        self.assertEqual(result['recovery']['modelCalls'],2)
        self.assertEqual(len(runtime.queries),1)
        feedback=json.loads(client.calls[1]['input'][-1]['content'][0]['text'])['recoveryFeedback']
        self.assertIn('literal',feedback['validationError'])
        self.assertEqual(feedback['editsApplyTo'],'candidate')
        doc=apply_changes(original,result['changes'])
        self.assertIn('| search device_name=',doc['dataSources']['temperature']['options']['query'])
        self.assertEqual(original['visualizations'],{})
    def proposal(self, query, field):
        return {'message':'Freezer temperature with readings above 150°F excluded.', 'suggestions':[], 'changes':[
            change('/dataSources/temperature',{'type':'ds.search','options':{'query':query,'queryParameters':{'earliest':'-24h','latest':'now'}}}),
            change('/visualizations/temperature',{'type':'splunk.singlevalue','title':'Average °F','dataSources':{'primary':'temperature'},'options':{'majorValue':"> primary | seriesByName('"+field+"') | lastPoint()"}}),
            {'op':'page','layoutId':'layout_main','label':'Freezer','purpose':'Keep food frozen','moveItems':False,'width':1200,'height':800,'items':[{'id':'temperature','kind':'block','x':20,'y':20,'w':400,'h':200}]}]}
    def test_real_query_failure_then_binding_failure_recover_in_same_request(self):
        query='search index="esp32" | where temperature_f<=150 | stats avg(temperature_f) AS average_f'
        client=Client([self.proposal(query+' broken','average_f'), self.proposal(query,'invented'),self.proposal(query,'average_f')]);runtime=Runtime();original=fixtures.NewDashboardTests().blank()
        reply=AgentService(ProviderService(Store(),client),runtime).assist({'prompt':'Build freezer average, excluding readings above 150 Fahrenheit.','revision':3,'definition':original,'dataContext':{'index':'esp32','earliest':'-24h'},'tokens':{'default':{'event_value':'NEVER SEND'}}})
        self.assertEqual(reply['recovery']['modelCalls'],3);self.assertEqual(reply['recovery']['queryChecks'],2)
        self.assertEqual(len(runtime.queries),2);self.assertEqual(runtime.profiles,2)
        second=json.loads(client.calls[1]['input'][-1]['content'][0]['text'])['recoveryFeedback']
        self.assertEqual(second['searchReceipts'][0]['status'],'failed');self.assertEqual(second['dataProfile']['sampledRows'],200)
        third=json.loads(client.calls[2]['input'][-1]['content'][0]['text'])['recoveryFeedback']
        self.assertIn('average_f',third['validationError']);self.assertEqual(third['searchReceipts'][0]['status'],'results')
        self.assertNotIn('PRIVATE EVENT VALUE',json.dumps(client.calls));self.assertNotIn('NEVER SEND',json.dumps(client.calls))
        self.assertEqual(original['visualizations'],{});self.assertEqual(reply['pagePurposes'],{'layout_main':'Keep food frozen'})
        candidate=apply_changes(original,reply['changes']);self.assertEqual(candidate['dataSources']['temperature']['options']['query'],query.replace(' | where', ' | eval temperature_f=if(temperature_f<=150,temperature_f,null()) | where'))
    def test_cached_results_are_isolated_and_budgets_stop_additional_work(self):
        runtime=Runtime();clock=[0];session=RecoverySession(runtime,clock=lambda:clock[0]);body={'query':'valid'}
        first=session.preview(body);first['results'].clear();self.assertEqual(len(session.preview(body)['results']),1)
        for number in range(3):session.model_call()
        with self.assertRaisesRegex(ProviderError,'attempt budget'):session.model_call()
        clock[0]=121
        with self.assertRaisesRegex(ProviderError,'time budget'):session.preview({'query':'different'})
        self.assertEqual(len(runtime.queries),1)
        session=RecoverySession(runtime)
        for number in range(MAX_QUERY_CHECKS):session.preview({'query':str(number)})
        with self.assertRaisesRegex(ProviderError,'search budget'):session.preview({'query':'one more'})
    def test_safe_native_diagnostic_categories_do_not_echo_error_body(self):
        diagnostic=search_feedback('Unknown search command x PRIVATE-TOKEN | index=secret')
        self.assertIn('unknown search command',diagnostic);self.assertNotIn('PRIVATE',diagnostic);self.assertNotIn('secret',diagnostic)


class PageTests(unittest.TestCase):
    def document(self):
        document=fixtures.NewDashboardTests().blank()
        document['visualizations']={'table':{'type':'splunk.table'},'detail':{'type':'splunk.markdown','title':'Detail','options':{'markdown':'Detail'}}}
        document['layout']['layoutDefinitions']['layout_main']['structure']=[{'item':'table','type':'block','position':{'x':0,'y':0,'w':500,'h':300}},{'item':'detail','type':'block','position':{'x':600,'y':0,'w':500,'h':300}}]
        document['layout']['future']={'keep':True}
        return document
    def actions(self):
        return [{'op':'page','layoutId':'details','label':'Reading details','purpose':'Investigate a selected device','moveItems':True,'width':1200,'height':800,'items':[{'id':'detail','kind':'block','x':20,'y':20,'w':1160,'h':400}]},
            {'op':'link','sourceId':'table','pageId':'details','targetId':'detail','field':'device','token':'selected_device'}]
    def test_pages_move_and_link_atomically_preserving_original_and_unknowns(self):
        original=self.document();before=copy.deepcopy(original);actions=self.actions();result=apply_changes(original,compile_actions(original,actions))
        self.assertEqual(original,before);self.assertEqual(result['layout']['future'],{'keep':True})
        self.assertEqual([item['item'] for item in result['layout']['layoutDefinitions']['layout_main']['structure']],['table'])
        handlers=result['visualizations']['table']['eventHandlers']
        self.assertEqual(handlers[-1],{'type':'drilldown.switchToTab','options':{'fields':['device'],'tabId':'details'}})
        self.assertEqual(handlers[-2]['options']['tokens'][0],{'token':'selected_device','key':'row.device.value'})
        self.assertEqual(proposed_purposes(actions,{},result),{'details':'Investigate a selected device'})
        self.assertEqual(focus_context(result,'page:details','details',{'details':'Investigate'})['purpose'],'Investigate')
        result['inputs']={'filter':{'type':'input.dropdown','options':{'label':'Device'}}}
        self.assertEqual(focus_context(result,'filter','details',{})['kind'],'input')
    def test_invalid_destination_and_non_table_field_link_are_rejected(self):
        for updates in ({'targetId':'missing'},{'pageId':'missing'},{'sourceId':'detail'},{'token':'bad token'}):
            actions=self.actions();actions[-1].update(updates)
            with self.subTest(updates=updates),self.assertRaises(ProviderError):compile_actions(self.document(),actions)
    def test_schema_one_migration_preserves_conversation_and_definition(self):
        original={'definition':self.document(),'messages':[{'id':7,'text':'Retain this discussion','user':True}]}
        migrated=migrate_snapshot(original,1)
        self.assertEqual(migrated['messages'],original['messages']);self.assertEqual(migrated['definition'],original['definition']);self.assertEqual(migrated['pagePurposes'],{})
        self.assertNotIn('pagePurposes',original)


class TokenTests(unittest.TestCase):
    def test_explicit_filter_removes_only_exact_entity_equality_and_preserves_conditions(self):
        for predicate in ('device=$entity|s$', '$entity|s$=device', '(device=$entity$)'):
            pipeline='| where '+predicate+' AND temperature<=150 | stats count'
            self.assertEqual(without_entity_equality(pipeline,'device','entity'),'| where temperature<=150 | stats count')
        pipeline='| where device=$entity|s$ | stats count'
        self.assertEqual(without_entity_equality(pipeline,'device','entity'),'| stats count')
        for pipeline in ('| where device=$entity|s$ OR other=1 | stats count',
                         '| eval note="| where device=$entity|s$" | stats count',
                         '| where (device=$entity|s$ AND value<=150) | stats count',
                         '| where other_device=$entity|s$ | stats count'):
            self.assertEqual(without_entity_equality(pipeline,'device','entity'),pipeline)
    def test_all_entity_defaults_require_wildcard_aware_filters(self):
        document={'defaults':{'tokens':{'default':{'entity':{'value':'*'}}}}}
        for query in ('search index=fixture | where device=$entity|s$',
                      'search index=fixture | where device==$entity|s$ AND value<=150',
                      "search index=fixture | where 'device name'=$entity|s$",
                      'search index=fixture | where device=$entity|s$ AND $entity|s$="*"',
                      'search index=fixture | where $entity|s$=device'):
            with self.subTest(query=query),self.assertRaisesRegex(ProviderError,'literal'):
                validate_wildcard_filters(query,document)
        for query in ('search index=fixture | search device=$entity|s$ | where value<=150',
                      'search index=fixture | where $entity|s$="*" OR device=$entity|s$',
                      'search index=fixture | where ("*"==$entity|s$ OR device=$entity|s$) AND value<=150',
                      'search index=fixture | eval note="| where device=$entity|s$"'):
            validate_wildcard_filters(query,document)
        validate_wildcard_filters('search index=fixture | where device=$entity|s$', {'inputs':{'entity_input':{'options':{'token':'entity','defaultValue':'fixture_A'}}}})
    def test_current_values_override_defaults_without_enabling_query_injection(self):
        document={'defaults':{'tokens':{'default':{'device':{'value':'*'}}}},'inputs':{'x':{'options':{'token':'room','defaultValue':'kitchen'}}}}
        self.assertEqual(resolve_query_tokens('search device=$device|s$ room=$room|s$',document),'search device="*" room="kitchen"')
        value='freezer" | outputlookup private.csv'
        query=resolve_query_tokens('search device=$device|s$',document,{'default':{'device':value}})
        self.assertEqual(query,'search device='+json.dumps(value))
        with self.assertRaisesRegex(ProviderError,'safe query'):resolve_query_tokens('search device=$device$',document,{'default':{'device':value}})
        with self.assertRaisesRegex(ProviderError,'already adds'):resolve_query_tokens('search device="$device|s$"',document)
        with self.assertRaisesRegex(ProviderError,'define an input'):resolve_query_tokens('search device=$missing|s$',document)

if __name__=='__main__':unittest.main()

class PageOutcomeTests(unittest.TestCase):
    def test_explicit_move_and_navigation_cannot_be_claimed_without_visible_results(self):
        from authoring_intent import validate_page_intent
        document=PageTests().document();document=apply_changes(document,compile_actions(document,[PageTests().actions()[0]]))
        # A duplicated chart and absent navigation must return both specific issues.
        document['layout']['layoutDefinitions']['layout_main']['structure'].append(copy.deepcopy(document['layout']['layoutDefinitions']['details']['structure'][0]))
        with self.assertRaises(ProviderError) as error:
            validate_page_intent('Move Detail here. Add a return button and matching navigation button.','Added navigation buttons.',document,PageTests().document(),{'kind':'page','id':'details'})
        self.assertIn('moveItems:true',str(error.exception));self.assertIn('op:button',str(error.exception))
        validate_page_intent('Add a Show notes toggle button.','Added a toggle.',document,document,{'kind':'page','id':'details'})
    def test_typed_buttons_create_place_and_link_without_duplicate_owned_handlers(self):
        document=PageTests().document();actions=PageTests().actions()[:1]
        action={'op':'button','id':'back','label':'Back to overview','pageId':'details','targetPageId':'layout_main','targetId':'table','x':20,'y':500,'w':250,'h':50}
        result=apply_changes(document,compile_actions(document,actions+[action]));again=apply_changes(result,compile_actions(result,[action]))
        self.assertEqual(result,again);self.assertEqual(again['inputs']['back']['type'],'input.button')
        self.assertEqual(len(again['inputs']['back']['eventHandlers']),2)
        self.assertEqual(again['layout']['layoutDefinitions']['details']['structure'][-1]['item'],'back')
        self.assertEqual(again['layout']['layoutDefinitions']['details']['structure'][-1]['position']['h'],80)
        result['visualizations']['detail']['type']='splunk.table'
        placed=apply_changes(result,compile_actions(result,[dict(action,y=30)]))
        self.assertEqual(placed['layout']['layoutDefinitions']['details']['structure'][-1]['position']['y'],440)
        result['layout']['layoutDefinitions']['details']['structure'][0]['position'].update(y=0,h=800)
        grown=apply_changes(result,compile_actions(result,[dict(action,y=30)]))
        self.assertEqual(grown['layout']['layoutDefinitions']['details']['options']['height'],920)
    def test_linking_another_table_field_preserves_its_existing_field_handlers(self):
        document=PageTests().document();actions=PageTests().actions();result=apply_changes(document,compile_actions(document,actions))
        original=copy.deepcopy(result['visualizations']['table']['eventHandlers'])
        link=dict(actions[1],field='other_field',token='other_token')
        result=apply_changes(result,compile_actions(result,[link]))
        self.assertEqual(result['visualizations']['table']['eventHandlers'][:2],original)

class AgentPresentationTests(unittest.TestCase):
    def test_recovery_copy_keeps_visible_outcomes_and_units(self):
        from agent_feedback import presentation_message
        raw='Corrected filters after the supplied ESP32 base query. Temperatures over 150°F are excluded; Wi-Fi readings are retained.'
        self.assertEqual(presentation_message(raw,'Build a freezer dashboard',True),'Temperatures over 150°F are excluded; Wi-Fi readings are retained.')
        self.assertEqual(presentation_message('Moved the chart and added buttons, using typed layout actions as required.','Move this chart',True),'Moved the chart and added buttons.')
        self.assertEqual(presentation_message(raw,'Explain the query validation errors',True),raw)
        self.assertEqual(presentation_message(raw,'Build this dashboard',False),raw)

class ScopeIntentTests(unittest.TestCase):
    def test_supported_explicit_creation_windows_and_ambiguous_comparisons(self):
        from scope_intent import inferred_range
        for phrase,expected in [('last hour','-1h'),('past 1 hour','-1h'),('last 15 minutes','-15m'),('past day','-24h'),('last 7 days','-7d'),('last week','-7d'),('compare last hour and last day',None),('last month',None)]:
            with self.subTest(phrase=phrase): self.assertEqual(inferred_range(phrase),expected)
    def test_direct_creation_profiles_requested_hour_but_explicit_ui_scope_wins(self):
        class TimedRuntime(Runtime):
            def __init__(self):super().__init__();self.windows=[]
            def execute(self,query,earliest):self.windows.append(earliest);return super().execute(query,earliest)
        for explicit,expected in [(None,'-1h'),({'index':'esp32','earliest':'-24h'},'-24h')]:
            runtime=TimedRuntime();client=Client([{'message':'Ready','changes':[],'suggestions':[]}])
            body={'prompt':'Create event count from index=esp32 during the last hour','revision':0,'definition':fixtures.NewDashboardTests().blank()}
            if explicit: body['dataContext']=explicit
            reply=AgentService(ProviderService(Store(),client),runtime).assist(body)
            self.assertEqual(runtime.windows,[expected]);self.assertEqual(reply['dataContext']['earliest'],expected)
