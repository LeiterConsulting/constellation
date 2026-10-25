"""Synthetic owner-only credential/inference boundary checks; never live keys."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlencode
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from inference_admission import admission
# Install the synthetic Splunk runtime modules used by entry-point tests.
from test_handler import splunk, rest, private_handler
sys.modules.setdefault('splunk', splunk)
sys.modules.setdefault('splunk.rest', rest)
import openai_private
from openai_private import execute, inference_request, public_config
from openai_connection import OpenAIStoreProxy, OpenAIClientProxy
from provider_service import ProviderError, ProviderService

CONFIG = {'api_key': 'fixture-owner-key', 'model': 'fixture-model', 'connections': {}}
REQUEST = {'model': 'fixture-model', 'store': False, 'instructions': 'Fixture instructions',
           'input': [{'role': 'user', 'content': [{'type': 'input_text', 'text': 'Fixture request'}]}],
           'max_output_tokens': 100, 'text': {'format': {'type': 'json_schema', 'name': 'fixture', 'strict': True, 'schema': {'type': 'object'}}}}

class Caller:
    user, token = 'fixture-author', 'fixture-caller'
    def request(self, path):
        assert path == '/services/authentication/current-context'
        return {'entry': [{'content': {'username': self.user, 'capabilities': ['search']}}]}
class Privileged: token = 'fixture-system'

class OpenAIPrivateTests(unittest.TestCase):
    def setUp(self):
        context = patch.dict(sys.modules, {'splunk': splunk, 'splunk.rest': rest, 'openai_private': openai_private})
        context.start(); self.addCleanup(context.stop)

    def test_metadata_contains_presence_only_and_never_the_saved_key(self):
        with patch('openai_private.CredentialStore') as store:
            store.return_value.read.return_value = CONFIG
            result = execute(Caller(), Privileged(), 'connection')
            store.assert_called_once_with('fixture-author', 'fixture-system')
            self.assertTrue(result['config']['key_configured'])
            self.assertNotIn('api_key', result['config'])
            self.assertNotIn(CONFIG['api_key'], json.dumps(result))

    def test_caller_mismatch_is_denied_before_privileged_store_is_constructed(self):
        with patch.object(Caller, 'request', return_value={'entry': [{'content': {'username': 'other', 'capabilities': ['search']}}]}), patch('openai_private.CredentialStore') as store:
            with self.assertRaises(ProviderError): execute(Caller(), Privileged(), 'connection')
            store.assert_not_called()

    def test_save_preserves_own_key_without_returning_it_and_rejects_owner_or_path(self):
        with patch('openai_private.CredentialStore') as store:
            store.return_value.read.return_value = copy.deepcopy(CONFIG)
            result = execute(Caller(), Privileged(), 'connection', {'key_configured': True, 'model': 'next-model'})
            self.assertEqual(result, {'saved': True})
            self.assertEqual(store.return_value.write.call_args.args[0]['api_key'], CONFIG['api_key'])
            for field in ('owner', 'user', 'path', 'url', 'credential', 'system_authtoken'):
                store.return_value.write.reset_mock()
                with self.assertRaises(ProviderError): execute(Caller(), Privileged(), 'connection', {'model': 'fixture-model', field: 'other'})
                store.return_value.write.assert_not_called()
            with self.assertRaises(ProviderError): public_config(dict(CONFIG, unknown_secret='fixture'))

    def test_invalid_replacement_does_not_write_or_remove_previous_key(self):
        with patch('openai_private.CredentialStore') as store:
            store.return_value.read.return_value = copy.deepcopy(CONFIG)
            with self.assertRaises(ProviderError): execute(Caller(), Privileged(), 'connection', {'api_key': 'unsafe\nheader', 'model': 'fixture-model'})
            store.return_value.write.assert_not_called()

    def test_inference_is_fixed_resource_store_false_and_only_uses_own_key(self):
        client = Mock(); client.call.return_value = {'status': 'completed'}
        with tempfile.TemporaryDirectory() as root, patch('openai_private.CredentialStore') as store:
            store.return_value.read.return_value = CONFIG
            body = dict(copy.deepcopy(REQUEST), store=True)
            self.assertEqual(execute(Caller(), Privileged(), 'responses', body, client, root), {'status': 'completed'})
            args = client.call.call_args.args
            self.assertEqual(args[:2], ('fixture-owner-key', 'responses'))
            self.assertIs(args[2]['store'], False)
            self.assertTrue(body['store'])
            self.assertEqual(list(Path(root).glob('*.json')), [])

    def test_other_models_tools_remote_files_and_unknown_modalities_never_reach_provider(self):
        cases = [dict(copy.deepcopy(REQUEST), model='other'), dict(copy.deepcopy(REQUEST), tools=[]), dict(copy.deepcopy(REQUEST), max_output_tokens=16001)]
        for part in ({'type': 'input_file', 'file_id': 'fixture-id'}, {'type': 'input_file', 'filename': 'f', 'file_data': 'https://example.com/f.pdf'},
                     {'type': 'input_image', 'image_url': 'https://example.com/image.png'}, {'type': 'input_image', 'image_url': 'data:image/png;base64,iVBORw0KGgo='}):
            body = copy.deepcopy(REQUEST); body['input'][0]['content'].append(part); cases.append(body)
        with patch('openai_private.CredentialStore') as store:
            store.return_value.read.return_value = CONFIG
            for body in cases:
                client = Mock()
                with self.assertRaises(ProviderError): execute(Caller(), Privileged(), 'responses', body, client)
                client.call.assert_not_called()

    def test_unknown_operations_and_credentialless_models_do_not_call_upstream(self):
        with patch('openai_private.CredentialStore') as store:
            store.return_value.read.return_value = None
            client = Mock()
            for action in ('credentials', 'models', 'responses'):
                with self.assertRaises(ProviderError): execute(Caller(), Privileged(), action, client=client)
            client.call.assert_not_called()

    def test_supported_inline_pdf_is_canonicalized_and_unknown_models_stay_blocked(self):
        body = copy.deepcopy(REQUEST); body['model'] = 'gpt-6-luna'
        body['input'][0]['content'].append({'type': 'input_file', 'filename': 'fixture.pdf', 'file_data': 'data:application/pdf;base64,JVBERi0xLjQ='})
        result = inference_request(body, dict(CONFIG, model='gpt-6-luna'))
        self.assertEqual(result['input'][0]['content'][-1]['filename'], 'reference.pdf')
        with self.assertRaises(ProviderError): inference_request(body, CONFIG)

    def test_openai_busy_guidance_names_the_correct_provider(self):
        with tempfile.TemporaryDirectory() as root, admission('fixture-author', root, provider='openai'), admission('fixture-author', root, provider='openai'):
            with self.assertRaises(ProviderError) as error:
                with admission('fixture-author', root, provider='openai'): pass
            self.assertEqual(error.exception.code, 'openai_busy')
            self.assertNotIn('AITK', str(error.exception))

    def test_main_store_and_provider_work_with_metadata_marker_without_receiving_a_key(self):
        from test_provider_service import Store, Client
        service = ProviderService(Store({'key_configured': True, 'model': 'fixture-model'}), Client())
        self.assertTrue(service.settings()['configured'])
        service.save({'provider': 'openai', 'apiKey': '', 'model': 'next-model'})
        self.assertNotIn('api_key', service.store.saved)
        self.assertTrue(service.store.saved['key_configured'])

    def test_proxy_sends_only_caller_token_and_fixed_route_not_a_key(self):
        with patch.dict(sys.modules, {'splunk': splunk, 'splunk.rest': rest}), patch.object(rest, 'simpleRequest', return_value=({'status': '200'}, '{"config":null}'), create=True) as call:
            self.assertIsNone(OpenAIStoreProxy(Caller()).read())
            self.assertEqual(call.call_args.kwargs['sessionKey'], 'fixture-caller')
            self.assertNotIn('fixture-system', str(call.call_args))

    def test_handler_requires_platform_tokens_and_sanitizes_unexpected_failures(self):
        handler = private_handler.OpenAIPrivateHandler()
        request = {'method': 'GET', 'path_info': 'connection', 'session': {'user': 'fixture-author', 'authtoken': 'fixture-caller'}, 'system_authtoken': 'fixture-system'}
        with patch('openai_private.execute', side_effect=RuntimeError('fixture-owner-key')):
            result = handler.handle(json.dumps(request))
            self.assertEqual(result['status'], 500); self.assertNotIn('fixture-owner-key', json.dumps(result))
        self.assertEqual(handler.handle(json.dumps(dict(request, system_authtoken='')))['status'], 503)
        self.assertEqual(handler.handle(json.dumps(dict(request, path_info='passwords')))['status'], 404)
        with patch('openai_private.execute', return_value={'saved': True}) as execute_mock:
            result = handler.handle(json.dumps(dict(request, method='POST', payload=urlencode({'request': json.dumps({'model': 'fixture-model'})}))))
            self.assertEqual(result['status'], 200)
            self.assertEqual(execute_mock.call_args.args[0].request_timeout, 10)
            self.assertEqual(execute_mock.call_args.args[1].request_timeout, 10)
