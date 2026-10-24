"""Reported capacity is distinct from successful inference and authoring acceptance."""
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from test_provider_service import Store, Client
from provider_service import ProviderService, ProviderError, OpenAIClient
from provider_adapters import OllamaClient, AITKClient
from model_readiness import report

class ModelReadinessTests(unittest.TestCase):
    def test_unknown_limits_and_aitk_custody_are_explicit(self):
        for provider in ('openai', 'aitk'):
            result=report(provider)
            self.assertFalse(result['tested'])
            self.assertTrue(result['warnings'])
            self.assertIn('not', json.dumps(result['limits']).lower())
            self.assertIn('does not qualify', result['scope'])
    def test_ollama_metadata_is_allowlisted_and_smaller_window_warns(self):
        result=report('ollama', {'model_info':{'general.architecture':'fixture','fixture.context_length':8192,'private':'DO NOT RETURN'},'template':'DO NOT RETURN'})
        self.assertIn('8,192',json.dumps(result));self.assertIn('smaller context',json.dumps(result))
        self.assertNotIn('DO NOT RETURN',json.dumps(result))
        unknown=report('ollama',{},True)
        self.assertIn('unverified',json.dumps(unknown));self.assertIn('could not be checked',json.dumps(unknown))
    def test_success_reports_scope_and_safe_usage_without_claiming_full_creation(self):
        client=Client({'message':'Verified','operations':[]})
        service=ProviderService(Store({'api_key':'fixture-only','model':'fixture-model'}),client)
        result=service.test()
        self.assertTrue(result['verified']);self.assertTrue(result['readiness']['tested'])
        self.assertIn('structured response',result['message'])
        self.assertEqual(client.calls[0][2]['max_output_tokens'],8500)
        usage=report('openai',usage={'input_tokens':100,'output_tokens':40,'output_tokens_details':{'reasoning_tokens':20,'private':'secret'},'private':'secret'})['usage']
        self.assertEqual(usage,{'input_tokens':100,'output_tokens':40,'reasoning_tokens':20})
    def test_token_errors_are_classified_without_echoing_upstream_content(self):
        class BoundaryClient:
            def call(self,*args):return {'status':'incomplete','incomplete_details':{'reason':'max_output_tokens'},'output':[]}
        with self.assertRaises(ProviderError) as caught:ProviderService(Store({'api_key':'fixture','model':'fixture'}),BoundaryClient()).test()
        self.assertEqual(caught.exception.code,'model_output_limit')
        class Opener:
            def open(self,*args,**kwargs):raise HTTPError('https://api.openai.com/v1/responses',400,'secret',{},io.BytesIO(b'{"error":{"code":"context_length_exceeded","message":"secret"}}'))
        with patch('provider_service.build_opener',return_value=Opener()),self.assertRaises(ProviderError) as caught:OpenAIClient().call('fixture','responses',{})
        self.assertEqual(caught.exception.code,'model_token_limit');self.assertNotIn('secret',str(caught.exception))
    def test_ollama_truncation_never_returns_partial_json(self):
        client=OllamaClient()
        request={'instructions':'Fixture','input':'Fixture','max_output_tokens':10,'text':{'format':{'schema':{}}}}
        with patch.object(client,'call',side_effect=[{}, {'done':True,'done_reason':'length','message':{'content':'{"partial"'}}]),self.assertRaises(ProviderError) as caught:client.complete({'base_url':'http://localhost:11434','model':'fixture'},request)
        self.assertEqual(caught.exception.code,'model_output_limit')
    def test_aitk_empty_completion_is_one_failure_and_cancels_job(self):
        class Runtime:
            user='fixture'
            def __init__(self):self.controls=[]
            def request(self,path,method='GET',fields=None):
                if path.endswith('current-context'):return {'entry':[{'content':{'capabilities':['apply_ai_commander_command']}}]}
                if path.endswith('/jobs'):return {'sid':'fixture'}
                if path.endswith('/results'):return {'results':[{'ai_result_1':'Empty response content received from the server.'}]}
                if path.endswith('/control'):self.controls.append(fields)
                return {'entry':[{'content':{'isDone':True}}]}
        runtime=Runtime()
        with self.assertRaises(ProviderError) as caught:AITKClient(runtime).complete({'connection':'fixture'},{'instructions':'Fixture','input':'Fixture','text':{'format':{'schema':{}}}})
        self.assertEqual(caught.exception.code,'aitk_no_completion');self.assertEqual(runtime.controls,[{'action':'cancel'}])
