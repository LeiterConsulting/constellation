import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from provider_service import ProviderService, ProviderError, OpenAIClient


class Store:
    def __init__(self, saved=None):
        self.saved = saved
    def read(self):
        return copy.deepcopy(self.saved)
    def write(self, config):
        self.saved = copy.deepcopy(config)


class Client:
    def __init__(self, output=None):
        self.calls = []
        self.output = output or {'message': 'Updated the title.', 'operations': [{'type':'rename','id':'','title':'Healthy'}]}
    def call(self, key, resource, body=None):
        self.calls.append((key, resource, body))
        if resource == 'models':
            return {'data': [{'id':'model-b'}, {'id':'model-a'}, {'id':'model-a'}, {'id':None}]}
        return {'status':'completed','id':'response_fixture','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(self.output)}]}]}


class ProviderBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.store = Store({'api_key':'fixture-only-not-a-real-key','model':'fixture-model'})
        self.client = Client()
        self.service = ProviderService(self.store, self.client)

    def test_settings_never_returns_secret(self):
        settings = self.service.settings()
        self.assertTrue(settings['keyConfigured'])
        self.assertNotIn(self.store.saved['api_key'], json.dumps(settings))

    def test_blank_key_keeps_saved_key_while_model_changes(self):
        self.service.save({'apiKey':'','model':'next-model'})
        self.assertEqual(self.store.saved, {'api_key':'fixture-only-not-a-real-key','model':'next-model'})

    def test_invalid_save_never_replaces_existing_secret(self):
        for body in [{'apiKey':'unsafe\nheader','model':'model'}, {'apiKey':'new-fixture','model':'bad model'}, {'provider':'other','apiKey':'new-fixture'}]:
            with self.assertRaises(ProviderError): self.service.save(body)
        self.assertEqual(self.store.saved['api_key'],'fixture-only-not-a-real-key')

    def test_model_inventory_does_not_claim_capability_verification(self):
        result = self.service.models()
        self.assertEqual(result['models'], ['model-a','model-b'])
        self.assertFalse(result['capabilityVerified'])

    def test_structured_edit_uses_minimized_context_and_no_remote_storage(self):
        result = self.service.assist({'prompt':'Rename it','revision':4,'context':{'title':'Sample','tiles':{'viz':'Latency'},'canCompare':True,'query':'do not send','results':['private']}})
        self.assertEqual(result['revision'],4)
        key,resource,body = self.client.calls[0]
        self.assertEqual(resource,'responses')
        self.assertFalse(body['store'])
        self.assertNotIn('do not send',body['input'])
        self.assertNotIn('private',body['input'])
        self.assertNotIn(key,body['input'])
        self.assertTrue(body['text']['format']['strict'])

    def test_missing_tile_and_unsupported_operations_are_rejected(self):
        for operation in [{'type':'tile-title','id':'missing','title':'Wrong'}, {'type':'delete','id':'viz','title':''}, {'type':'compare','id':'','title':''}]:
            service=ProviderService(self.store,Client({'message':'Change','operations':[operation]}))
            with self.assertRaises(ProviderError): service.assist({'prompt':'change','revision':0,'context':{'tiles':{'viz':'Title'}}})

    def test_model_check_cannot_commit_edits(self):
        with self.assertRaises(ProviderError): self.service.test()
        service=ProviderService(self.store,Client({'message':'Verified','operations':[]}))
        self.assertTrue(service.test()['verified'])

    def test_unconfigured_service_makes_no_upstream_call(self):
        service=ProviderService(Store(),self.client)
        with self.assertRaises(ProviderError): service.models()
        self.assertEqual(self.client.calls,[])

    def test_only_official_fixed_resources_are_allowed(self):
        with self.assertRaises(ProviderError): OpenAIClient().call('fixture','https://other.example')

    def test_upstream_auth_errors_never_echo_provider_body_or_key(self):
        class Opener:
            def open(self, *args, **kwargs):
                raise HTTPError('https://api.openai.com/v1/models',401,'fixture-secret-in-error',{},None)
        with patch('provider_service.build_opener',return_value=Opener()):
            with self.assertRaises(ProviderError) as error: OpenAIClient().call('fixture-secret-in-error','models')
        self.assertNotIn('fixture-secret-in-error',str(error.exception))

    def test_incomplete_and_refused_responses_are_not_edits(self):
        for response in [{'status':'incomplete','output':[]}, {'status':'completed','output':[{'content':[{'type':'refusal'}]}]}]:
            class BoundaryClient:
                def call(self, *args, **kwargs): return response
            with self.assertRaises(ProviderError): ProviderService(self.store,BoundaryClient()).test()

    def test_timeout_is_distinct_from_a_connection_or_tls_failure_and_never_retries(self):
        for failure, status, code in [(TimeoutError('fixture-secret'), 504, 'provider_timeout'),
                                       (URLError(TimeoutError('fixture-secret')), 504, 'provider_timeout'),
                                       (URLError('fixture-secret'), 502, 'provider_connection')]:
            class Opener:
                def __init__(self): self.calls = 0
                def open(self, *args, **kwargs): self.calls += 1; raise failure
            opener = Opener()
            with patch('provider_service.build_opener', return_value=opener), self.assertRaises(ProviderError) as error:
                OpenAIClient().call('fixture-secret', 'responses', {'store':False})
            self.assertEqual(error.exception.status,status); self.assertEqual(error.exception.code,code)
            self.assertNotIn('fixture-secret',str(error.exception)); self.assertEqual(opener.calls,1)


if __name__ == '__main__':
    unittest.main()
