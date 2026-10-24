import base64
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from provider_service import ProviderError, ProviderService
from agent_service import AgentService
from model_capabilities import attachment_parts, capabilities
from search_service import SearchService, read_only_query
from studio_contract import apply_changes, model_document, validate_document

STARTER = json.loads((Path(__file__).resolve().parents[1] / 'src/starter.json').read_text())


class Store:
    def __init__(self, model='gpt-6-luna'): self.model = model
    def read(self): return {'api_key': 'fixture-secret', 'model': self.model}


class Client:
    def __init__(self, outputs): self.outputs, self.calls = outputs, []
    def call(self, key, resource, body):
        self.calls.append(copy.deepcopy(body))
        result = self.outputs.pop(0)
        return {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps(result)}]}]}


class Runtime:
    calls = 0
    def environment(self):
        self.calls += 1
        return {'version': '10.2.8', 'features': {'networkGraph': False}}
    def datasets(self): return {'indexes': [{'name': 'fixture_index'}]}


def change(path, value, op='set'):
    return {'op': op, 'path': path, 'value': json.dumps(value) if op == 'set' else ''}


class StudioAgentTests(unittest.TestCase):
    def body(self, **changes): return dict({'prompt': 'Improve this dashboard', 'revision': 7, 'definition': copy.deepcopy(STARTER)}, **changes)
    def result(self, changes=None): return {'message': 'Updated the layout.', 'changes': changes or [], 'suggestions': ['Add a service comparison']}

    def test_changes_are_atomic_and_preserve_unknown_configuration(self):
        document = dict(copy.deepcopy(STARTER), futureSetting={'keep': True})
        changed = apply_changes(document, [change('/title', 'Healthy'), change('/visualizations/viz_trend/options/legendDisplay', 'right')])
        self.assertEqual(changed['futureSetting'], {'keep': True})
        self.assertEqual(document['title'], 'Checkout performance')
        with self.assertRaises(ProviderError): apply_changes(document, [change('/title', 'Wrong'), change('/layout', {'type': 'absolute', 'structure': [{'item': 'missing'}]})])
        self.assertEqual(document['title'], 'Checkout performance')

    def test_unsafe_and_invalid_paths_are_rejected(self):
        for path in ('/visualizations/__proto__/x', '/provider/apiKey', '/visualizations/missing/title', '/title~2bad'):
            with self.subTest(path=path), self.assertRaises(ProviderError): apply_changes(STARTER, [change(path, 'bad')])

    def test_invalid_value_feedback_lists_all_paths_without_echoing_values(self):
        with self.assertRaises(ProviderError) as error:
            apply_changes(STARTER,[{'op':'set','path':'/title','value':'fixture-secret-title'}, {'op':'set','path':'/description','value':'fixture-secret-description'}])
        self.assertIn('/title',str(error.exception)); self.assertIn('/description',str(error.exception))
        self.assertNotIn('fixture-secret',str(error.exception))

    def test_array_append_and_omitted_sample_data_guard(self):
        changed = apply_changes(STARTER, [change('/layout/tabs/items/-', {'layoutId': 'layout_detail', 'label': 'Additional detail'})])
        self.assertEqual(len(changed['layout']['tabs']['items']), 3)
        with self.assertRaises(ProviderError):
            apply_changes(STARTER, [change('/dataSources/ds_requests/options/data', {'fields': [{'name': 'requests'}]})])

    def test_missing_references_and_cycles_are_rejected(self):
        for sources in ({'a': {'type': 'ds.chain', 'options': {'extend': 'a'}}}, {'a': {'type': 'ds.chain', 'options': {'extend': 'b'}}}):
            document = {'visualizations': {}, 'layout': {'type': 'grid'}, 'dataSources': sources}
            with self.assertRaises(ProviderError): validate_document(document)

    def test_layout_feedback_identifies_all_missing_and_available_ids_atomically(self):
        document = {'visualizations': {'actual_chart': {'type': 'splunk.markdown', 'options': {'markdown': 'private fixture text'}}},
                    'inputs': {'actual_button': {'type': 'input.button'}},
                    'layout': {'layoutDefinitions': {
                        'overview': {'type': 'absolute', 'structure': [{'item': 'wrong_chart'}]},
                        'details': {'type': 'absolute', 'structure': [{'item': 'wrong_button'}]}}}}
        before = copy.deepcopy(document)
        with self.assertRaises(ProviderError) as caught: validate_document(document)
        feedback = str(caught.exception)
        for identifier in ('overview: wrong_chart', 'details: wrong_button', 'actual_chart', 'actual_button'):
            self.assertIn(identifier, feedback)
        self.assertNotIn('private fixture text', feedback)
        self.assertEqual(document, before)

    def test_sample_and_search_result_rows_do_not_enter_model_context(self):
        document = copy.deepcopy(STARTER)
        document['dataSources']['ds_requests']['state'] = {'rows': ['private-result']}
        minimized = model_document(document)
        self.assertNotIn('private-result', json.dumps(minimized))
        self.assertNotIn('columns', minimized['dataSources']['ds_requests']['options']['data'])
        self.assertIn('columns', document['dataSources']['ds_requests']['options']['data'])

    def test_unknown_model_attachment_is_blocked_before_any_provider_or_discovery_call(self):
        client, runtime = Client([]), Runtime()
        with self.assertRaises(ProviderError): AgentService(ProviderService(Store('unknown-model'), client), runtime).assist(self.body(attachments=[{'name': 'reference.png', 'data': 'not sent'}]))
        self.assertEqual(client.calls, [])
        self.assertEqual(runtime.calls, 0)
        self.assertFalse(capabilities('gpt-6-luna-unverified-suffix')['images'])

    def test_verified_vision_attachment_uses_responses_image_part(self):
        image = 'data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode()
        client = Client([self.result([change('/title', 'Sketch dashboard')])])
        reply = AgentService(ProviderService(Store(), client), Runtime()).assist(self.body(attachments=[{'name': 'sketch.png', 'data': image}]))
        self.assertEqual(reply['revision'], 7)
        request = client.calls[0]
        self.assertFalse(request['store'])
        self.assertEqual(request['input'][0]['content'][1]['type'], 'input_image')
        self.assertNotIn('fixture-secret', json.dumps(request))

    def test_bad_mime_and_remote_urls_never_pass_attachment_validation(self):
        for data in ('https://example.com/image.png', 'data:image/png;base64,aGVsbG8=', 'data:image/svg+xml;base64,aGVsbG8='):
            with self.subTest(data=data), self.assertRaises(ProviderError): attachment_parts([{'name': 'bad.png', 'data': data}], 'gpt-6-luna')

    def test_validation_recovery_is_bounded_to_two_repairs(self):
        bad = self.result([change('/layout', {'type': 'grid', 'structure': [{'item': 'missing'}]})])
        good = self.result([change('/title', 'Healthy')])
        client = Client([bad, good])
        reply = AgentService(ProviderService(Store(), client), Runtime()).assist(self.body())
        self.assertTrue(reply['repaired'])
        self.assertEqual(len(client.calls), 2)
        self.assertIn('validationError', client.calls[1]['input'][-1]['content'][0]['text'])
        client = Client([bad, bad, bad])
        with self.assertRaises(ProviderError): AgentService(ProviderService(Store(), client), Runtime()).assist(self.body())
        self.assertEqual(len(client.calls), 3)

    def test_newer_visualization_is_not_added_to_older_target(self):
        bad = self.result([change('/visualizations/viz_network', {'type': 'splunk.networkgraph'})])
        client = Client([bad, bad, bad])
        with self.assertRaises(ProviderError): AgentService(ProviderService(Store(), client), Runtime()).assist(self.body())


class SearchGuardTests(unittest.TestCase):
    def test_read_only_spl_and_spl2_pipelines(self):
        self.assertIn('search index=_internal', read_only_query('index=_internal | stats count by sourcetype'))
        self.assertTrue(read_only_query('from _internal | stats count()', 'spl2').startswith('| @spl2 from'))
        self.assertIn('eval note="| outputlookup harmless-text"', read_only_query('| makeresults | eval note="| outputlookup harmless-text"'))

    def test_writes_scripts_macros_subsearches_and_unresolved_tokens_are_blocked(self):
        queries = ['| makeresults | outputlookup bad.csv', '| rest /services/storage/passwords',
                   '| search `macro`', '| search "`macro`"', 'index=$index$',
                   '| map search="x"', '| search [| inputlookup private.csv]',
                   '| makeresults count="10000000"', '| makeresults count=1001',
                   'from read_json("https://example.com") | stats count()', 'from main; export x',
                   'search index=main earliest=0 | stats count']
        for query in queries:
            with self.subTest(query=query), self.assertRaises(ProviderError): read_only_query(query, 'spl2')

    def test_live_search_requests_have_enforced_server_side_limits(self):
        runtime = SearchService('fixture-user', 'fixture-session')
        from test_preview_jobs import JobRuntime
        runtime = JobRuntime(rows=3)
        result = runtime.preview({'query': '| makeresults count=3 | stats count', 'max_time': 999, 'earliest_time': '0'})
        fields = runtime.calls[0][2]
        self.assertEqual(fields['max_time'], '5')
        self.assertEqual(fields['earliest_time'], '-15m')
        self.assertEqual(fields['max_count'], '201')
        self.assertEqual(fields['adhoc_search_level'], 'fast')
        self.assertNotIn('search_mode', fields)
        self.assertEqual(result['state'], 'complete')



class NewDashboardTests(unittest.TestCase):
    def blank(self):
        return {'title':'New dashboard','description':'','visualizations':{},'dataSources':{},'inputs':{},'defaults':{},'expressions':{},
                'layout':{'globalInputs':[],'tabs':{'items':[{'label':'Overview','layoutId':'layout_main'}]},'layoutDefinitions':{'layout_main':{'type':'absolute','structure':[]}}}}
    def proposal(self):
        return {'label':'Compare visitor patterns','prompt':'Compare weekday and weekend attendance using the current illustrative visitor data.',
                'reason':'The curator can see when visitor behavior changes.','kind':'comparison'}
    def test_blank_context_has_no_starter_assumptions_and_creates_its_own_sources(self):
        result={'message':'Created a museum concept with illustrative sample data.', 'changes':[
            change('/title','Museum visitors'),change('/dataSources/visitors',{'type':'ds.test','options':{'data':{'fields':[{'name':'visitors'}],'columns':[[120]]}}}),
            change('/visualizations/visitors',{'type':'splunk.singlevalue','dataSources':{'primary':'visitors'}}),
            change('/layout/layoutDefinitions/layout_main/structure',[{'item':'visitors','type':'block','position':{'x':0,'y':0,'w':300,'h':150}}])], 'suggestions':[self.proposal()]}
        client=Client([result]);blank=self.blank()
        reply=AgentService(ProviderService(Store(),client),Runtime()).assist({'prompt':'Create a museum visitor concept using illustrative data.','revision':0,'definition':blank,'history':[],'suggestionFormat':'cards'})
        context=json.loads(client.calls[0]['input'][0]['content'][0]['text'])
        self.assertEqual(context['canvasState'],'blank');self.assertEqual(context['definition'],blank);self.assertEqual(context['history'],[])
        self.assertNotIn('checkout',json.dumps(context['definition']))
        self.assertEqual(reply['suggestions'],[self.proposal()]);self.assertFalse(reply['repaired'])
        self.assertEqual(blank['visualizations'],{})
    def test_legacy_clients_receive_plain_prompt_strings(self):
        client=Client([{'message':'Ready','changes':[],'suggestions':[self.proposal()]}])
        reply=AgentService(ProviderService(Store(),client),Runtime()).assist({'prompt':'Help shape this idea','revision':0,'definition':self.blank()})
        self.assertEqual(reply['suggestions'],[self.proposal()['prompt']])
    def test_invalid_proposals_are_repaired_once_and_duplicates_are_removed(self):
        from prompt_suggestions import normalize_suggestions
        self.assertEqual(normalize_suggestions([self.proposal(),self.proposal()]),[self.proposal()])
        invalid=dict(self.proposal(),label='x'*61)
        client=Client([{'message':'Ready','changes':[],'suggestions':[invalid]}, {'message':'Ready','changes':[],'suggestions':[self.proposal()]}])
        reply=AgentService(ProviderService(Store(),client),Runtime()).assist({'prompt':'Help shape this idea','revision':0,'definition':self.blank(),'suggestionFormat':'cards'})
        self.assertTrue(reply['repaired']);self.assertEqual(len(client.calls),2)
        self.assertNotIn('fixture-secret',json.dumps(client.calls))

    def test_chart_labels_use_native_root_properties_and_preserve_unchanged_legacy(self):
        from studio_features import validate_features
        blank=self.blank()
        document=copy.deepcopy(blank)
        document['visualizations']={'visitors':{'type':'splunk.singlevalue','options':{'title':'Visitors'}}}
        with self.assertRaisesRegex(ProviderError,'belong beside'):
            validate_features(document,blank,{})
        validate_features(document,copy.deepcopy(document),{})
        document['visualizations']['visitors']={'type':'splunk.singlevalue','title':'Visitors','description':'Illustrative attendance','options':{}}
        validate_features(document,blank,{})

    def test_scatter_requires_series_axes_and_category_grouping(self):
        from studio_features import validate_features
        document=self.blank()
        document['visualizations']={'comparison':{'type':'splunk.scatter','options':{'x':"> primary | frameBySeriesNames('visits')"}}}
        with self.assertRaisesRegex(ProviderError,'one series'):
            validate_features(document,self.blank(),{})
        document['visualizations']['comparison']['options']={'series':"> primary | seriesByName('exhibit')"}
        with self.assertRaisesRegex(ProviderError,'options.category'):
            validate_features(document,self.blank(),{})
        document['visualizations']['comparison']['options']={'x':"> primary | seriesByName('visits')",'y':"> primary | seriesByName('minutes')",'category':"> primary | seriesByName('exhibit')"}
        validate_features(document,self.blank(),{})

if __name__ == '__main__': unittest.main()
