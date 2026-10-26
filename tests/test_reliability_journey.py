"""Repeatable synthetic journey across orchestration, validation and durable drafts.

Provider replies are scripted, not live-model success measurements. These fixtures
exercise the real edit compiler, data guards, repair loop and persistence operations.
"""
import copy
import json
import unittest
from test_drafts_and_data import MemoryDrafts, blank, DataRuntime
from agent_service import AgentService
from studio_contract import apply_changes
from compatibility import feature_profile
from provider_service import ProviderError


class Provider:
    def __init__(self, replies): self.replies, self.requests = list(replies), []
    def configured(self): return {'model': 'synthetic-model'}
    def capabilities(self, config): return {'images': False, 'pdf': False}
    def complete(self, config, request):
        self.requests.append(copy.deepcopy(request))
        return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(self.replies.pop(0))}]}]}


class Runtime(DataRuntime):
    def environment(self): return {'version':'10.4.4','features':feature_profile('10.4.4',[])}


def reply(changes, message='Dashboard updated.'):
    return {'message':message,'changes':changes,'suggestions':[]}


class ReliabilityJourneyTests(unittest.TestCase):
    def test_imported_search_retains_its_supported_native_range_for_grounding(self):
        source = {'type': 'ds.search', 'options': {'query': 'search index="fixture_index" | stats count', 'queryParameters': {'earliest': '-1h', 'latest': 'now'}}}
        document = {'title': 'Imported', 'visualizations': {'metric': {'type': 'splunk.singlevalue', 'dataSources': {'primary': 'events'}}}, 'dataSources': {'events': source}, 'layout': {'type': 'absolute', 'structure': [{'item': 'metric'}]}}
        provider = Provider([reply([{'op': 'set', 'path': '/visualizations/metric/title', 'value': '"Events"'}])])
        result = AgentService(provider, Runtime()).assist({'prompt': 'Give this a clearer title', 'revision': 0, 'definition': document, 'selected': 'metric'})
        self.assertEqual(result['dataContext']['earliest'], '-1h')
        self.assertEqual(result['dataProfile']['scope'],result['dataContext'])
        self.assertNotIn('results',result['dataProfile'])
        self.assertNotIn('columns',result['dataProfile'])
        self.assertEqual(document['dataSources']['events'], source)
    def test_placement_feedback_uses_exact_ids_and_free_space_without_changing_the_candidate(self):
        from repair_hints import placement_hint
        candidate = {'visualizations': {'existing': {}, 'new_chart': {}}, 'layout': {'tabs': {'items': [{'layoutId': 'overview', 'label': 'Overview'}]}, 'layoutDefinitions': {'overview': {'type': 'absolute', 'options': {'width': 1200, 'height': 800}, 'structure': [{'item': 'existing', 'position': {'x': 20, 'y': 20, 'w': 1160, 'h': 400}}]}}}}
        before = copy.deepcopy(candidate)
        hint = placement_hint(candidate, 'overview')
        self.assertEqual(hint['unplacedVisualizations'], ['new_chart'])
        self.assertEqual(hint['layoutActionExample']['items'][0]['y'], 440)
        self.assertEqual(candidate, before)
    def test_repair_can_patch_the_uncommitted_candidate_without_repeating_creation(self):
        original = blank()['definition']
        initial = reply([
            {'op':'set','path':'/dataSources','value':json.dumps({'events':{'type':'ds.search','options':{'query':'search index="fixture_index" | stats count','queryParameters':{'earliest':'-1h','latest':'now'}}}})},
            {'op':'set','path':'/visualizations','value':json.dumps({'metric':{'type':'splunk.singlevalue','title':'Events','dataSources':{'primary':'events'}}})},
            {'op':'layout','layoutId':'overview','label':'Overview','width':1200,'height':600,'items':[{'id':'metric','kind':'block','x':20,'y':20,'w':400,'h':200}]},
        ])
        initial['suggestions'] = [{'label':'x'*61, 'prompt':'Inspect the result', 'reason':'', 'kind':'refine'}]
        patch = reply([{'op':'set','path':'/dataSources/events/options/queryParameters','value':'{"earliest":"-24h","latest":"now"}'}])
        provider = Provider([initial, patch])
        result = AgentService(provider, Runtime()).assist({'prompt':'Build from index=fixture_index','revision':0,'definition':original,'dataContext':blank()['dataContext']})
        self.assertEqual(result['recovery']['modelCalls'], 2)
        self.assertIn('Omitted invalid optional next-step suggestions', result['activity'])
        self.assertTrue(result['validationNotes'])  # The invalid query still requires repair.
        self.assertFalse(original['visualizations'])
        final = apply_changes(original, result['changes'])
        self.assertIn('metric', final['visualizations'])
        self.assertEqual(final['dataSources']['events']['options']['queryParameters']['earliest'], '-24h')
        feedback = json.loads(provider.requests[1]['input'][-1]['content'][0]['text'])['recoveryFeedback']
        self.assertEqual(feedback['editsApplyTo'], 'candidate')
        self.assertIn('metric', feedback['candidateDefinition']['visualizations'])
    def test_repair_create_focus_edit_navigation_switch_reopen_and_restore(self):
        store, runtime = MemoryDrafts(), Runtime()
        state = blank(); state['brief'] = {'purpose':'Understand real sensor activity', 'requirements':'Use Fahrenheit. Exclude readings over 150°F.'}
        record = store.operation({'action':'save','id':'a'*32,'version':0,'schemaVersion':3,'state':state})
        initial = copy.deepcopy(state['definition'])
        bad = reply([{'op':'set','path':'/visualizations','value':'{"metric":{"type":"splunk.singlevalue"}}'}])
        good = reply([
            {'op':'set','path':'/dataSources','value':json.dumps({'events':{'type':'ds.search','options':{'query':'search index="fixture_index" | stats count','queryParameters':{'earliest':'-24h','latest':'now'}}}})},
            {'op':'set','path':'/visualizations','value':json.dumps({'metric':{'type':'splunk.singlevalue','title':'Events','dataSources':{'primary':'events'}}})},
            {'op':'page','layoutId':'overview','label':'Overview','purpose':'A quick activity overview','moveItems':False,'width':1200,'height':600,'items':[{'id':'metric','kind':'block','x':20,'y':20,'w':400,'h':200}]},
            {'op':'page','layoutId':'details','label':'Details','purpose':'Inspect event details','moveItems':False,'width':1200,'height':600,'items':[]},
            {'op':'button','id':'open_details','label':'Details','pageId':'overview','targetPageId':'details','targetId':'','x':20,'y':260,'w':180,'h':80},
            {'op':'button','id':'return','label':'Overview','pageId':'details','targetPageId':'overview','targetId':'metric','x':20,'y':20,'w':180,'h':80},
        ])
        provider=Provider([bad,good]); agent=AgentService(provider,runtime)
        body={'prompt':'Create a two-page dashboard with navigation using index=fixture_index', 'revision':0,'definition':initial,'dataContext':state['dataContext'],'brief':state['brief']}
        result=agent.assist(body)
        self.assertEqual(result['recovery']['modelCalls'],2)
        self.assertEqual(state['definition'],initial)  # No failed intermediate edits escape.
        state['definition']=apply_changes(initial,result['changes']);state['pagePurposes']=result['pagePurposes'];state['brief']=result['brief']
        record=store.operation({'action':'save','id':record['id'],'version':record['version'],'schemaVersion':3,'state':state})
        created=copy.deepcopy(state['definition'])
        refine=Provider([reply([{'op':'set','path':'/visualizations/metric/title','value':'"Event arrivals"'}])])
        result=AgentService(refine,runtime).assist(dict(body, prompt='Give this a clearer title',revision=1,definition=created,selected='metric',pagePurposes=state['pagePurposes'],history=[]))
        self.assertIn('focus identifies the selected',refine.requests[0]['instructions'])
        self.assertLess(len(refine.requests[0]['instructions']),7000)
        context=json.loads(refine.requests[0]['input'][0]['content'][0]['text'])
        self.assertEqual(context['focus']['id'],'metric');self.assertIn('150°F',context['dashboardBrief']['requirements'])
        state['definition']=apply_changes(created,result['changes']);state['messages'].append({'id':2,'user':False,'text':'Refined the selected metric.'})
        record=store.operation({'action':'save','id':record['id'],'version':record['version'],'state':state})
        self.assertEqual(state['definition']['inputs'],created['inputs'])
        store.operation({'action':'save','id':'b'*32,'version':0,'state':blank()})
        reopened=MemoryDrafts(entries=store.entries).operation({'action':'open','id':record['id']})
        self.assertEqual(reopened['state'],state)
        history=store.operation({'action':'history','id':record['id']})['revisions']
        restored=store.operation({'action':'restore_revision','id':record['id'],'version':record['version'],'revision':history[0]['version']})
        self.assertEqual(restored['state']['definition'],created)
        self.assertEqual(restored['state']['messages'],state['messages'])
        self.assertEqual(restored['state']['brief'],state['brief'])
        self.assertEqual(store.listing()['activeId'],record['id'])

    def test_exhausted_recovery_leaves_the_saved_dashboard_and_conversation_intact(self):
        store=MemoryDrafts(); state=blank()
        record=store.operation({'action':'save','id':'a'*32,'version':0,'state':state})
        before=copy.deepcopy(store.entries)
        invalid=reply([{'op':'set','path':'/visualizations','value':'{"broken":{"type":"splunk.singlevalue"}}'}])
        provider=Provider([invalid,invalid,invalid])
        with self.assertRaises(ProviderError) as caught:AgentService(provider,Runtime()).assist({'prompt':'Build from index=fixture_index','revision':0,'definition':state['definition'],'dataContext':state['dataContext']})
        self.assertEqual(caught.exception.recovery['modelCalls'],3)
        self.assertLessEqual(caught.exception.recovery['queryChecks'],16)
        self.assertEqual(len(provider.requests),3); self.assertEqual(store.entries,before)
        self.assertEqual(store.read(record['id'])['state'],state)

    def test_history_does_not_copy_files_chat_or_transient_edits_and_is_bounded(self):
        store=MemoryDrafts();state=blank()
        record=store.operation({'action':'save','id':'a'*32,'version':0,'state':state})
        for i in range(15):
            state['definition']['title']='Dashboard '+str(i)
            record=store.operation({'action':'save','id':record['id'],'version':record['version'],'state':state})
        history=json.loads(store.entry(record['id'])['content']['history'])
        self.assertEqual(len(history),10)
        self.assertNotIn('messages',history[0]['state']);self.assertNotIn('attachments',history[0]['state'])
        state['prompt']='Typing without changing dashboard'
        record=store.operation({'action':'save','id':record['id'],'version':record['version'],'state':state})
        self.assertEqual(json.loads(store.entry(record['id'])['content']['history']),history)
        before=copy.deepcopy(store.entries)
        with self.assertRaises(ProviderError):store.operation({'action':'restore_revision','id':record['id'],'version':record['version']-1,'revision':history[0]['version']})
        self.assertEqual(store.entries,before)
        other=MemoryDrafts(user='bob',entries=store.entries)
        with self.assertRaises(ProviderError):other.operation({'action':'history','id':record['id']})

    def test_brief_migration_and_explicit_requirements_survive_short_history(self):
        from dashboard_brief import authoring_brief, validate_brief
        from draft_migrations import migrate_snapshot
        state=blank();state['messages'][0]['text']='Freezer temperatures in Fahrenheit; ignore spikes over 150 degrees.'
        migrated=migrate_snapshot(state,2)
        self.assertEqual(migrated['brief']['purpose'],state['messages'][0]['text']);self.assertNotIn('brief',state)
        updated=authoring_brief({'brief':migrated['brief'],'prompt':'Always keep Wi-Fi observations, even during temperature spikes.'})
        self.assertIn('keep Wi-Fi',updated['requirements'])
        self.assertEqual(authoring_brief({'brief':updated,'prompt':'Always keep Wi-Fi observations, even during temperature spikes.'}),updated)
        self.assertEqual(authoring_brief({'brief':updated,'prompt':'Make this an area chart titled Temperature (°F). Keep the existing data.'}),updated)
        self.assertEqual(authoring_brief({'brief':updated,'prompt':updated['purpose']}),updated)
        with self.assertRaises(ProviderError):validate_brief({'purpose':'x','secret':'bad'})
        with self.assertRaises(ProviderError):authoring_brief({'brief':[], 'prompt':'Create a dashboard'})

    def test_empty_partial_inspection_does_not_prove_an_empty_index(self):
        from data_service import DataService
        class Partial(Runtime):
            def execute(self,*args): return {'results':[],'fields':[],'state':'partial'}
            def preview(self,*args): return self.execute()
        with self.assertRaisesRegex(ProviderError,'not been proven empty'):DataService(Partial()).profile({'index':'fixture_index'})
        with self.assertRaisesRegex(ProviderError,'No absence'):DataService(Partial()).profile({'query':'index=fixture_index | stats count'})

    def test_scope_equivalence_accepts_formatting_but_never_extra_datasets(self):
        from search_scope import scoped_suffix
        profile={'baseQuery':'search index="fixture_index"','scope':{'index':'fixture_index','language':'spl'}}
        for query in ('index=fixture_index | stats count','SEARCH index = "fixture_index" | stats count','| search index="fixture_index" | stats count'):
            self.assertEqual(scoped_suffix(query,profile).strip(),'| stats count')
        for query in ('index=fixture_index OR index=other | stats count','index=fixture_index_extra | stats count','index=other | stats count','index=* | stats count'):
            self.assertIsNone(scoped_suffix(query,profile))
        profile={'baseQuery':'search index="fixture_index" sourcetype="events"','scope':{'index':'fixture_index','sourcetype':'events'}}
        self.assertEqual(scoped_suffix('index=fixture_index sourcetype=events | stats count',profile).strip(),'| stats count')
        self.assertIsNone(scoped_suffix('index=fixture_index | stats count',profile))
        exact={'baseQuery':'index=fixture_index | where duration>0','scope':{'query':'index=fixture_index | where duration>0'}}
        self.assertIsNone(scoped_suffix('index=fixture_index | stats count',exact))

    def test_named_row_drilldown_must_reach_the_requested_page(self):
        from authoring_intent import validate_page_intent
        doc={'layout':{'tabs':{'items':[{'layoutId':'overview','label':'Overview'},{'layoutId':'details','label':'Device details'}]}},
             'visualizations':{'table':{'type':'splunk.table','eventHandlers':[
                 {'type':'drilldown.setToken','options':{'fields':['device_name'],'tokens':[{'token':'device','key':'row.device_name.value'}]}},
                 {'type':'drilldown.switchToTab','options':{'fields':['device_name'],'tabId':'overview'}}]}}}
        prompt='Let a device row on Overview open and filter Device details, with a return button.'
        with self.assertRaisesRegex(ProviderError,'requested row drilldown'):validate_page_intent(prompt,'Created',doc,{}, {})
        doc['visualizations']['table']['eventHandlers'][1]['options']['tabId']='details'
        validate_page_intent(prompt,'Created',doc,{}, {})
        doc['visualizations']['table']['eventHandlers'][0]['options']['tokens'][0]['key']='row.invented.value'
        with self.assertRaises(ProviderError):validate_page_intent(prompt,'Created',doc,{}, {})
