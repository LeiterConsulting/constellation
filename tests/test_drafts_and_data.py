import base64
import copy
from contextlib import nullcontext
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from draft_service import DraftService, validate_snapshot
from data_service import DataService
from dashboard_library import DashboardLibrary
from draft_migrations import migrate_snapshot
from compatibility import feature_profile
from knowledge_service import retrieve_guidance
from agent_service import AgentService
from provider_service import ProviderError


def blank():
    return {'definition': {'title': 'Real data draft', 'visualizations': {}, 'layout': {'type': 'absolute', 'structure': []}},
            'messages': [{'id': 1, 'user': True, 'text': 'Understand event arrivals'}], 'prompt': 'Compare hosts',
            'attachments': [], 'selected': '', 'suggestions': [], 'activity': [], 'searchesEnabled': True,
            'dataContext': {'index': 'fixture_index', 'earliest': '-24h'}}


class MemoryDrafts(DraftService):
    def __init__(self, user='alice', entries=None):
        super().__init__(user, 'fixture-session')
        self.entries = entries if entries is not None else {}
    def locked(self): return nullcontext()
    def request(self, path, method='GET', fields=None, projection=False):
        if path.endswith('/acl'):
            name = path.rsplit('/', 2)[1]
            self.entries[name]['acl'].update(owner=fields['owner'], sharing=fields['sharing'])
            return {'entry': [copy.deepcopy(self.entries[name])]}
        if path == self.base:
            if method == 'GET': return {'entry': copy.deepcopy(list(self.entries.values()))}
            name = fields['name']
            self.entries[name] = {'name': name, 'content': {}, 'acl': {'owner': self.user, 'app': 'constellation', 'sharing': 'user'}}
        else: name = path.rsplit('/', 1)[-1]
        if name not in self.entries: return None
        if method == 'POST': self.entries[name]['content'].update({k: v for k, v in fields.items() if k != 'name'})
        return {'entry': [copy.deepcopy(self.entries[name])]}


class DraftTests(unittest.TestCase):
    identifier = 'a' * 32
    def test_roundtrip_includes_conversation_prompt_tokens_context_and_pending_files(self):
        store, state = MemoryDrafts(), blank()
        state['attachments'] = [{'name': 'reference.png', 'data': 'data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode()}]
        state['tokens'] = {'default': {'host': {'value': 'fixture-host'}}}
        result = store.operation({'action': 'save', 'id': self.identifier, 'version': 0, 'state': state})
        reopened = MemoryDrafts(entries=store.entries).operation({'action': 'read', 'id': self.identifier})
        self.assertEqual(result['state'], reopened['state']); self.assertEqual(reopened['state'], state)
        self.assertEqual(store.listing()['activeId'], self.identifier)
        self.assertNotIn('state', store.listing()['drafts'][0])
    def test_stale_write_cannot_replace_other_sessions_work_and_identical_retry_is_idempotent(self):
        store = MemoryDrafts()
        first = store.operation({'action': 'save', 'id': self.identifier, 'version': 0, 'state': blank()})
        retry = store.operation({'action': 'save', 'id': self.identifier, 'version': 0, 'state': blank()})
        self.assertEqual(first['version'], retry['version'])
        changed = blank(); changed['prompt'] = 'Other session work'
        store.operation({'action': 'save', 'id': self.identifier, 'version': 1, 'state': changed})
        with self.assertRaisesRegex(ProviderError, 'another session'):
            store.operation({'action': 'save', 'id': self.identifier, 'version': 1, 'state': blank()})
        self.assertEqual(store.read(self.identifier)['state']['prompt'], 'Other session work')
    def test_crud_retains_conversation_and_deleted_drafts_are_recoverable(self):
        store = MemoryDrafts(); item = store.operation({'action':'save','id':self.identifier,'version':0,'state':blank()})
        item = store.operation({'action':'rename','id':self.identifier,'version':item['version'],'title':'Event arrivals'})
        duplicate = store.operation({'action':'duplicate','id':self.identifier,'version':item['version']})
        self.assertNotEqual(duplicate['id'], self.identifier)
        self.assertEqual(duplicate['state']['messages'], item['state']['messages'])
        deleted = store.operation({'action':'delete','id':self.identifier,'version':item['version']})
        self.assertEqual(len(store.listing()['trash']), 1)
        with self.assertRaises(ProviderError): store.read(self.identifier)
        with self.assertRaises(ProviderError): store.operation({'action':'save','id':self.identifier,'version':deleted['version'],'state':blank()})
        restored = store.operation({'action':'restore','id':self.identifier,'version':deleted['version']})
        self.assertIsNone(restored['deletedAt']); self.assertEqual(restored['state'], item['state'])
    def test_owner_checks_and_unknown_session_properties_fail_closed(self):
        store = MemoryDrafts(); store.operation({'action':'save','id':self.identifier,'version':0,'state':blank()})
        store.entries[store.key(self.identifier)]['acl']['owner'] = 'bob'
        with self.assertRaises(ProviderError): store.read(self.identifier)
        with self.assertRaises(ProviderError): store.listing()
        for identifier in ('../escape', 'b'*33, None):
            with self.assertRaises(ProviderError): store.key(identifier)
        with self.assertRaises(ProviderError): validate_snapshot(dict(blank(), apiKey='fixture-secret'))


class DataRuntime:
    def __init__(self): self.calls = []
    def datasets(self): return {'indexes': [{'name':'fixture_index'}], 'status':'available'}
    def execute(self, query, earliest):
        self.calls.append((query, earliest))
        if 'tstats' in query: return {'results':[{'index':'fixture_index','sourcetype':'events','count':'20'}, {'index':'not_visible','count':'90'}]}
        return {'results':[{'field':'duration','count':'20','numeric_count':'20','values':'PRIVATE EVENT VALUE'},
                           {'field':'host','count':'20','numeric_count':'0'}, {'field':'_raw','count':'20','numeric_count':'0'}]}
    def preview(self, body):
        self.calls.append(body)
        return {'fields':[{'name':'count'}], 'results':[{'count':'12'}]}


class DataGroundingTests(unittest.TestCase):
    def test_empty_filtered_subset_is_valid_and_does_not_remove_other_panels(self):
        class Runtime(DataRuntime):
            def preview(self, body):
                return {'fields': [], 'results': []} if 'where' in body['query'] else super().preview(body)
        service = DataService(Runtime()); profile = service.profile({'index':'fixture_index'})
        sources = {name:{'type':'ds.search','options':{'query':query,'queryParameters':{'earliest':'-24h','latest':'now'}}} for name,query in {
            'all':'search index="fixture_index" | stats count',
            'outliers':'search index="fixture_index" | where duration > 99999 | table duration'}.items()}
        document = {'dataSources':sources,'visualizations':{'subset':{'type':'splunk.table','dataSources':{'primary':'outliers'}}},
                    'layout':{'type':'absolute','structure':[{'item':'subset'}]}}
        receipts = service.validate_searches(document,{},profile)
        self.assertEqual([(r['source'],r['status']) for r in receipts],[('all','results'),('outliers','empty')])
        document['visualizations']['subset'] = {'type':'splunk.singlevalue','dataSources':{'primary':'outliers'},'options':{'majorValue':42}}
        with self.assertRaisesRegex(ProviderError,'constant sample'): service.validate_searches(document,{},profile)

    def test_timechart_must_cover_the_selected_window_within_the_row_budget(self):
        service = DataService(DataRuntime())
        for earliest,span,valid in [('-24h','5m',False),('-24h','15m',True),('-7d','15m',False),('-7d','1h',True),('-1h','1m',True)]:
            with self.subTest(earliest=earliest,span=span):
                profile=service.profile({'index':'fixture_index','earliest':earliest})
                source={'type':'ds.search','options':{'query':'search index="fixture_index" | timechart span='+span+' count',
                          'queryParameters':{'earliest':earliest,'latest':'now'}}}
                if valid: service.validate_searches({'dataSources':{'trend':source}}, {}, profile)
                else:
                    with self.assertRaisesRegex(ProviderError,'200-row'): service.validate_searches({'dataSources':{'trend':source}}, {}, profile)
    def test_discovery_only_promotes_catalog_visible_activity(self):
        result = DataService(DataRuntime()).discovery()
        self.assertEqual([row['index'] for row in result['activity']], ['fixture_index'])
    def test_profile_uses_selected_scope_and_excludes_event_values(self):
        runtime = DataRuntime(); service = DataService(runtime)
        result = service.profile({'index':'fixture_index','sourcetype':'events" | rest /unsafe','earliest':'-24h'})
        self.assertEqual(result['fields'], [{'name':'_time','numeric':True,'present':20},{'name':'duration','numeric':True,'present':20},{'name':'host','numeric':False,'present':20}])
        self.assertNotIn('PRIVATE EVENT VALUE', json.dumps(result))
        self.assertIn('maxvals=1', runtime.calls[0][0]); self.assertIn('\\"', runtime.calls[0][0])
        with self.assertRaises(ProviderError): service.profile({'index':'not_visible'})
        with self.assertRaises(ProviderError): service.profile({'index':'fixture_index','earliest':'0'})
    def test_real_data_edits_are_executed_and_synthetic_or_out_of_scope_sources_are_rejected(self):
        runtime = DataRuntime(); service = DataService(runtime)
        profile = service.profile({'index':'fixture_index'})
        before={'dataSources':{}}; source={'type':'ds.search','options':{'query':'search index="fixture_index" | stats count','queryParameters':{'earliest':'-24h','latest':'now'}}}
        document={'dataSources':{'count':source}}
        result=service.validate_searches(document,before,profile)
        self.assertEqual(result[0]['fields'],['count']); self.assertNotIn('12',json.dumps(result))
        source['options']['query']='search index="other" | stats count'
        with self.assertRaises(ProviderError): service.validate_searches(document,before,profile)
        source['type']='ds.test'
        with self.assertRaises(ProviderError): service.validate_searches(document,before,profile)
    def test_scope_cannot_be_expanded_and_chart_bindings_must_have_populated_fields(self):
        service=DataService(DataRuntime()); profile=service.profile({'index':'fixture_index'})
        source={'type':'ds.search','options':{'query':'search index="fixture_index" OR index="other" | stats count','queryParameters':{'earliest':'-24h','latest':'now'}}}
        document={'dataSources':{'count':source},'visualizations':{}}
        with self.assertRaises(ProviderError): service.validate_searches(document,{},profile)
        source['options']['query']='search index="fixture_index" | makeresults'
        with self.assertRaises(ProviderError): service.validate_searches(document,{},profile)
        source['options']['query']='search index="fixture_index" | stats count'
        document['visualizations']={'kpi':{'type':'splunk.singlevalue','dataSources':{'primary':'count'},'options':{'majorValue':"> primary | seriesByName('invented') | lastPoint()"}}}
        document['layout']={'type':'absolute','structure':[{'item':'kpi','type':'block'}]}
        with self.assertRaisesRegex(ProviderError,'missing or empty'): service.validate_searches(document,{},profile)
        document['visualizations']['kpi']['options']['majorValue']=42
        with self.assertRaisesRegex(ProviderError,'constant sample'): service.validate_searches(document,{},profile)
    def test_real_data_charts_need_explicit_sources_and_page_placement(self):
        service=DataService(DataRuntime());profile=service.profile({'index':'fixture_index'})
        document={'visualizations':{'kpi':{'type':'splunk.singlevalue'}},'dataSources':{},'layout':{'type':'absolute','structure':[]}}
        with self.assertRaises(ProviderError) as error:service.validate_searches(document,{},profile)
        self.assertIn('dataSources.primary',str(error.exception));self.assertIn('typed layout',str(error.exception))
    def test_native_search_time_must_match_the_inspected_scope(self):
        runtime = DataRuntime(); service = DataService(runtime); profile = service.profile({'index':'fixture_index','earliest':'-1h'})
        source = {'type':'ds.search','options':{'query':'search index="fixture_index" | stats count'}}
        document = {'dataSources':{'count':source}}
        with self.assertRaisesRegex(ProviderError, 'queryParameters'): service.validate_searches(document, {}, profile)
        source['options']['queryParameters'] = {'earliest':'-24h','latest':'now'}
        with self.assertRaisesRegex(ProviderError, 'queryParameters'): service.validate_searches(document, {}, profile)
        source['options']['queryParameters']['earliest'] = '-1h'
        self.assertEqual(service.validate_searches(document, {}, profile)[0]['earliest'], '-1h')
    def test_user_query_profile_exposes_schema_and_never_result_cells(self):
        result=DataService(DataRuntime()).profile({'query':'index="fixture_index" | stats count','earliest':'-1h'})
        self.assertEqual(result['fields'][0]['name'],'count'); self.assertTrue(result['fields'][0]['numeric'])
        self.assertNotIn('12',json.dumps(result))


class UpgradeContractsTests(unittest.TestCase):
    def test_migrations_preserve_original_and_future_versions_are_not_overwritten(self):
        original=blank(); migrated=migrate_snapshot(original,0)
        self.assertEqual(original,blank()); self.assertEqual(migrated['dataContext'],original['dataContext'])
        self.assertEqual(migrated['pendingRequest'],'')
        with self.assertRaises(ProviderError): migrate_snapshot(original,4)
        store=MemoryDrafts(); item=store.operation({'action':'save','id':'a'*32,'version':0,'state':original})
        store.entries[store.key(item['id'])]['content']['schema_version']='4'
        before=copy.deepcopy(store.entries)
        with self.assertRaises(ProviderError): store.operation({'action':'save','id':item['id'],'version':item['version'],'state':original})
        self.assertEqual(store.entries,before)
        self.assertEqual(store.listing()['drafts'][0]['schemaVersion'],4)
        with self.assertRaises(ProviderError):
            MemoryDrafts().operation({'action':'save','id':'b'*32,'schemaVersion':4,'version':0,'state':original})
    def test_version_rules_and_retrieval_are_independent_of_the_provider(self):
        self.assertFalse(feature_profile('10.2.8',[])['networkGraph'])
        self.assertTrue(feature_profile('10.4.4',[])['networkGraph'])
        self.assertFalse(feature_profile('10.4.4',[])['autoRefreshPermitted'])
        self.assertTrue(feature_profile('10.4.4',['auto_refresh_dashboards'])['autoRefreshPermitted'])
        self.assertFalse(any(feature_profile('unknown',[]).values()))
        older=retrieve_guidance('networkgraph custom refresh scatter',{}, {'version':'10.2.8'})
        newer=retrieve_guidance('networkgraph custom refresh scatter',{}, {'version':'10.4.4'})
        self.assertNotIn('modern-studio',[item['id'] for item in older])
        self.assertIn('modern-studio',[item['id'] for item in newer])
        self.assertIn('scatter-bindings',[item['id'] for item in older])
        self.assertTrue(all(item['source'].startswith('https://help.splunk.com/') for item in newer))


class NativeMemory(MemoryDrafts):
    def __init__(self):
        super().__init__(); self.views={}
    def request(self,path,method='GET',fields=None,projection=False):
        if '/data/ui/views' not in path: return super().request(path,method,fields,projection)
        name=path.rsplit('/',1)[-1]
        if name=='views' and method=='POST':
            name=fields['name']; self.views[name]={'name':name,'content':{'eai:data':fields['eai:data']},'acl':{'owner':self.user,'app':'constellation','sharing':'user'}}
        elif name not in self.views: return None
        elif method=='POST': self.views[name]['content'].update(fields)
        elif method=='DELETE': del self.views[name]; return {}
        return {'entry':[copy.deepcopy(self.views[name])]}


class NativeManagementTests(unittest.TestCase):
    def fixture(self):
        store=NativeMemory()
        xml='<dashboard version="2" theme="dark"><label>Original</label><definition>'+json.dumps(blank()['definition'])+'</definition><future setting="keep"/></dashboard>'
        store.views['owned_view']={'name':'owned_view','content':{'eai:data':xml},'acl':{'owner':'alice','app':'constellation','sharing':'user'}}
        return store,DashboardLibrary(store),xml
    def test_native_delete_and_restore_preserve_original_xml_and_private_owner(self):
        store,service,xml=self.fixture()
        result=service.operation({'action':'delete','name':'owned_view'})
        self.assertTrue(result['recoverable']); self.assertNotIn('owned_view',store.views)
        trash=store.listing()['trash'][0]
        service.operation({'action':'restore','id':trash['id'],'version':trash['version']})
        self.assertEqual(store.views['owned_view']['content']['eai:data'],xml)
        self.assertEqual(store.views['owned_view']['acl']['sharing'],'user')
        self.assertEqual(store.listing()['trash'],[])
    def test_native_rename_keeps_unknown_envelope_and_shared_views_are_not_modified(self):
        store,service,xml=self.fixture()
        service.operation({'action':'rename','name':'owned_view','title':'New title'})
        self.assertIn('future setting="keep"',store.views['owned_view']['content']['eai:data'])
        store.views['owned_view']['acl']['sharing']='app'
        before=copy.deepcopy(store.views)
        with self.assertRaises(ProviderError): service.operation({'action':'delete','name':'owned_view'})
        self.assertEqual(store.views,before)
        copy_record=service.operation({'action':'duplicate','name':'owned_view'})
        self.assertTrue(copy_record['state']['definition']['title'].endswith('copy'))


class GroundedAgentTests(unittest.TestCase):
    def test_verified_events_cannot_be_reported_as_an_empty_source(self):
        from agent_feedback import validate_data_claims
        for message in ('The search returned no events.', 'There are zero matching rows.', 'No data was found in this index.'):
            with self.subTest(message=message), self.assertRaises(ProviderError):
                validate_data_claims({'changes':[],'message':message},{'sampledRows':200})
        for message in ('No outliers were found.', 'No illustrative data was used.', 'Which temperature unit should I use?'):
            validate_data_claims({'changes':[],'message':message},{'sampledRows':200})
        validate_data_claims({'changes':[],'message':'The search returned no events.'},{'sampledRows':0})

    def test_false_empty_claim_is_repaired_using_the_profile_not_old_chat(self):
        class Runtime(DataRuntime):
            def environment(self): return {'version':'10.2.8','features':feature_profile('10.2.8',[])}
        class Provider:
            def __init__(self): self.calls=[]
            def configured(self): return {'model':'fixture-model'}
            def capabilities(self,saved): return {'images':False,'pdf':False}
            def complete(self,saved,request):
                self.calls.append(copy.deepcopy(request))
                message = 'The search returned no events.' if len(self.calls)==1 else 'Which temperature unit should I use?'
                return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps({'message':message,'changes':[],'suggestions':[]})}]}]}
        provider=Provider()
        reply=AgentService(provider,Runtime()).assist({'prompt':'Build from index=fixture_index','revision':0,'definition':blank()['definition']})
        self.assertTrue(reply['repaired']);self.assertIn('sampledRows=20',reply['validationNotes'][0])
        self.assertIn('verified events',provider.calls[1]['input'][-1]['content'][0]['text'])
        self.assertNotIn('PRIVATE EVENT VALUE',json.dumps(provider.calls))

    def test_agent_retrieves_fields_and_repairs_bad_bindings_with_metadata_only(self):
        class Runtime(DataRuntime):
            def environment(self): return {'version':'10.2.8','features':feature_profile('10.2.8',[])}
        class Provider:
            def __init__(self): self.calls=[]
            def configured(self): return {'model':'fixture-model'}
            def capabilities(self,saved): return {'images':False,'pdf':False}
            def complete(self,saved,request):
                self.calls.append(copy.deepcopy(request))
                field='invented' if len(self.calls)==1 else 'count'
                reply={'message':'Built the dashboard from the selected data.','suggestions':[], 'changes':[
                    {'op':'set','path':'/dataSources','value':json.dumps({'count':{'type':'ds.search','options':{'query':'search index="fixture_index" | stats count','queryParameters':{'earliest':'-24h','latest':'now'}}}})},
                    {'op':'set','path':'/visualizations','value':json.dumps({'kpi':{'type':'splunk.singlevalue','title':'Events','dataSources':{'primary':'count'},'options':{'majorValue':"> primary | seriesByName('"+field+"') | lastPoint()"}}})},
                    {'op':'set','path':'/layout','value':json.dumps({'type':'absolute','structure':[{'item':'kpi','type':'block','position':{'x':0,'y':0,'w':300,'h':150}}]})}]}
                return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(reply)}]}]}
        runtime,provider=Runtime(),Provider()
        reply=AgentService(provider,runtime).assist({'prompt':'Build event volume using index=fixture_index','revision':0,'definition':blank()['definition'],'suggestionFormat':'cards'})
        self.assertTrue(reply['repaired']); self.assertEqual(len(provider.calls),2)
        context=json.loads(provider.calls[0]['input'][0]['content'][0]['text'])
        self.assertIn('dataProfile',context); self.assertIn('retrievedGuidance',context)
        self.assertEqual(reply['searchReceipts'][0]['fields'],['count'])
        self.assertNotIn('PRIVATE EVENT VALUE',json.dumps(provider.calls))
        self.assertNotIn('"12"',json.dumps(provider.calls))


if __name__ == '__main__': unittest.main()

class DraftOpenTests(unittest.TestCase):
    def test_open_records_last_draft_without_changing_its_revision_or_conversation(self):
        store=MemoryDrafts();a=store.operation({'action':'save','id':'a'*32,'version':0,'state':blank()});b=store.operation({'action':'save','id':'b'*32,'version':0,'state':blank()})
        store.operation({'action':'read','id':a['id']});self.assertEqual(store.listing()['activeId'],b['id'])
        reopened=store.operation({'action':'open','id':a['id']})
        self.assertEqual(reopened,a);self.assertEqual(store.listing()['activeId'],a['id'])
        self.assertEqual(store.operation({'action':'read','id':a['id']}),a)
    def test_failed_open_preserves_previous_active_draft(self):
        store=MemoryDrafts();a=store.operation({'action':'save','id':'a'*32,'version':0,'state':blank()});b=store.operation({'action':'save','id':'b'*32,'version':0,'state':blank()})
        deleted=store.operation({'action':'delete','id':a['id'],'version':a['version']})
        with self.assertRaises(ProviderError):store.operation({'action':'open','id':deleted['id']})
        self.assertEqual(store.listing()['activeId'],b['id'])
