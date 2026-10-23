import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from provider_service import ProviderService, ProviderError
from provider_adapters import OllamaClient, AITKClient, ollama_origin
from model_capabilities import attachment_parts
from studio_features import validate_features
from test_provider_service import Store

REQUEST={'model':'fixture','instructions':'Return an edit.', 'input':[{'role':'user','content':[{'type':'input_text','text':'Fixture context'}]}],
         'max_output_tokens':100,'text':{'format':{'schema':{'type':'object','properties':{}}}}}

class OllamaFixture(OllamaClient):
    def __init__(self): self.calls=[]
    def call(self, origin, resource, body=None):
        self.calls.append((origin,resource,copy.deepcopy(body)))
        if resource == 'tags': return {'models':[{'name':'fixture:latest'}]}
        if resource == 'show': return {'capabilities':['completion','vision'], 'thinking':{'values':[False,True]}}
        return {'done':True,'message':{'content':'{"message":"Ready","operations":[]}'}}

class AdapterTests(unittest.TestCase):
    def test_switching_retains_openai_secret_and_each_saved_connection(self):
        store=Store({'api_key':'fixture-only','model':'openai-fixture'})
        service=ProviderService(store,ollama=OllamaFixture())
        service.save({'provider':'ollama','baseUrl':'http://127.0.0.1:11434','model':'fixture:latest'})
        self.assertTrue(service.settings()['capabilities']['images'])
        self.assertFalse(service.settings()['capabilities']['pdf'])
        service.save({'provider':'aitk','connection':'private fixture'})
        self.assertFalse(service.settings()['capabilities']['images'])
        service.save({'provider':'openai','model':'next-model'})
        self.assertEqual(store.saved['api_key'],'fixture-only')
        self.assertEqual(store.saved['connections']['ollama']['model'],'fixture:latest')
        self.assertEqual(store.saved['connections']['aitk']['connection'],'private fixture')
        self.assertNotIn('fixture-only',json.dumps(service.settings()))

    def test_ollama_native_schema_and_images_no_openai_fields_or_auth(self):
        client=OllamaFixture();request=copy.deepcopy(REQUEST)
        request['input'][0]['content'].append({'type':'input_image','image_url':'data:image/png;base64,YQ=='})
        client.complete({'model':'fixture','base_url':'http://127.0.0.1:11434'},request)
        body=client.calls[-1][2]
        self.assertEqual(body['messages'][1]['images'],['YQ=='])
        self.assertEqual(body['format'],REQUEST['text']['format']['schema'])
        self.assertFalse(body['stream']);self.assertFalse(body['think'])
        self.assertNotIn('store',body);self.assertNotIn('input',body)

    def test_pdf_blocked_for_ollama_and_all_files_blocked_for_aitk(self):
        file={'name':'fixture.pdf','data':'data:application/pdf;base64,JVBERi0xLjQ='}
        for caps in [{'images':True,'pdf':False},{'images':False,'pdf':False}]:
            with self.assertRaises(ProviderError):attachment_parts([file],'fixture',caps)

    def test_ipv4_and_ipv6_loopback_origins_are_accepted(self):
        for origin in ['http://127.0.0.1:11434', 'http://[::1]:11434', 'http://localhost:11434']:
            self.assertEqual(ollama_origin(origin),origin)

    def test_endpoint_rejects_credentials_paths_metadata_and_public_http(self):
        for origin in ['http://127.0.0.1:11434/api','http://a:b@localhost:11434','http://169.254.169.254','http://0.0.0.0:11434','http://8.8.8.8:11434','https://localhost/#x']:
            with self.subTest(origin=origin),self.assertRaises(ProviderError):ollama_origin(origin)

    def test_aitk_uses_one_synthetic_row_named_connection_and_current_user(self):
        class Runtime:
            user='fixture-user'
            def __init__(self):self.calls=[]
            def request(self,path,method='GET',fields=None):
                self.calls.append((path,method,fields))
                if path.endswith('current-context'):return {'entry':[{'content':{'capabilities':['apply_ai_commander_command']}}]}
                if path.endswith('/jobs'):return {'sid':'fixture_sid'}
                if path.endswith('/results'):return {'results':[{'ai_result_1':'```json\n{}\n```'}]}
                return {'entry':[{'content':{'isDone':True}}]}
        runtime=Runtime();response=AITKClient(runtime).complete({'connection':'private connection'},REQUEST)
        query=runtime.calls[1][2]['search']
        self.assertTrue(query.startswith('| makeresults | eval constellation_prompt='))
        self.assertIn('ai prompt="{constellation_prompt}" connection="private connection"',query)
        self.assertIn('/fixture-user/Splunk_ML_Toolkit/',runtime.calls[1][0])
        self.assertEqual(response['output'][0]['content'][0]['text'],'{}')
        self.assertEqual(runtime.calls[-1][2],{'action':'cancel'})

    def test_aitk_permission_denied_before_starting_job(self):
        class Runtime:
            def request(self,*args):return {'entry':[{'content':{'capabilities':[]}}]}
        with self.assertRaises(ProviderError) as error:AITKClient(Runtime()).complete({'connection':'fixture'},REQUEST)
        self.assertEqual(error.exception.status,403)

class NativeContractTests(unittest.TestCase):
    def document(self):
        return {'visualizations':{'notes':{'type':'splunk.markdown','containerOptions':{'visibility':{'showConditions':['notes_on']}}}},
                'inputs':{'toggle':{'type':'input.button','eventHandlers':[{'type':'drilldown.setToken','options':{'tokens':[{'token':'showNotes','value':'$eval:toggleNotes$'}]}}]}},
                'expressions':{'conditions':{'notes_on':{'name':'notes visible','value':"$showNotes$ = 'true'"}},
                               'eval':{'toggle':{'name':'toggleNotes','value':"$showNotes$ = 'true' ? 'false' : 'true'"}}},
                'layout':{'layoutDefinitions':{'overview':{'type':'absolute'}}}}
    def test_native_conditions_buttons_and_evaluated_tokens_accepted(self):
        validate_features(self.document(),{}, {'features':{'conditionalVisibility':True}})
    def test_new_chart_channels_and_inline_columns_are_checked(self):
        doc={'visualizations':{'chart':{'type':'splunk.bar','options':{'x':'exhibit','y':'visitors'}}},'layout':{'type':'absolute'}}
        with self.assertRaises(ProviderError):validate_features(doc,{}, {'features':{}})
        # Existing unknown/legacy bindings survive an unrelated edit.
        validate_features(doc,copy.deepcopy(doc),{'features':{}})
        doc['visualizations']['chart']['options']={'x':"> primary | seriesByName('exhibit')",'y':"> primary | frameBySeriesNames('visitors')"}
        doc['dataSources']={'sample':{'type':'ds.test','options':{'data':{'fields':[{'name':'exhibit'},{'name':'visitors'}],'columns':[['Ocean','Space'],[120,90]]}}}}
        validate_features(doc,{}, {'features':{}})
        doc['dataSources']['sample']['options']['data']['columns'][1]=[120]
        with self.assertRaises(ProviderError):validate_features(doc,{}, {'features':{}})

    def test_missing_conditions_and_unsupported_target_rejected(self):
        doc=self.document()
        with self.assertRaises(ProviderError):validate_features(doc,{}, {'features':{}})
        doc['expressions']['conditions']={}
        with self.assertRaises(ProviderError):validate_features(doc,{}, {'features':{'conditionalVisibility':True}})
    def test_missing_and_removed_evaluated_token_references_rejected(self):
        doc=self.document();doc['expressions']['eval']={}
        with self.assertRaises(ProviderError):validate_features(doc,{}, {'features':{'conditionalVisibility':True}})
        old=self.document();doc=copy.deepcopy(old);doc['expressions']['eval']={}
        with self.assertRaises(ProviderError):validate_features(doc,old, {'features':{'conditionalVisibility':True}})

    def test_removed_condition_and_missing_tab_targets_rejected(self):
        old=self.document();doc=copy.deepcopy(old);doc['expressions']['conditions']={}
        with self.assertRaises(ProviderError):validate_features(doc,old,{'features':{'conditionalVisibility':True}})
        doc=self.document();doc['inputs']['toggle']['eventHandlers']=[{'type':'drilldown.switchToTab','options':{'tabId':'missing'}}]
        with self.assertRaises(ProviderError):validate_features(doc,{}, {'features':{'conditionalVisibility':True}})

if __name__=='__main__':unittest.main()
