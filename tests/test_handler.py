import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
splunk = types.ModuleType('splunk')
rest = types.ModuleType('splunk.rest')
application = types.ModuleType('splunk.persistconn.application')
application.PersistentServerConnectionApplication = object
class RESTException(Exception):
    def __init__(self, status): self.statusCode = status
rest.RESTException = RESTException
splunk.rest = rest
with patch.dict(sys.modules, {'splunk':splunk,'splunk.rest':rest,'splunk.persistconn':types.ModuleType('splunk.persistconn'),'splunk.persistconn.application':application}):
    import constellation_handler as handler
    import aitk_inference_handler as inference_handler


class HandlerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.handler = handler.ConstellationHandler('driver','args')
    def request(self, **changes):
        value={'method':'GET','path_info':'settings','session':{'user':'fixture-user','authtoken':'fixture-session'}}
        value.update(changes)
        with patch('connection_store.ConnectionPreferences.read', return_value=None), patch.object(handler.CredentialStore, 'key_access', return_value={'canWrite': True}), patch.object(handler.SearchService, 'shared_aitk_status', return_value={'available': False, 'connection': ''}):
            return self.handler.handle(json.dumps(value))
    def test_authentication_is_required(self):
        self.assertEqual(self.request(session={})['status'],401)
    def test_unknown_methods_are_rejected(self):
        self.assertEqual(self.request(method='DELETE')['status'],404)
    def test_unconfigured_settings_have_no_secret(self):
        with patch.object(handler.CredentialStore,'read',return_value=None):
            result=self.request()
        self.assertEqual(result['status'],200)
        self.assertFalse(result['payload']['keyConfigured'])
        self.assertEqual(result['headers']['Cache-Control'],'no-store')

    def test_optional_shared_metadata_failure_does_not_break_other_settings(self):
        from test_provider_service import Store
        from provider_service import ProviderService, ProviderError
        runtime = handler.SearchService('fixture-user', 'fixture-session')
        with patch.object(runtime, 'shared_aitk_status', side_effect=ProviderError('fixture-native-error', 503)):
            result = ProviderService(Store(), runtime=runtime).settings()
        self.assertEqual(result['aitkAccess'], {'available': False, 'connection': '', 'unavailable': True})
        self.assertNotIn('fixture-native-error', json.dumps(result))
    def test_internal_exceptions_are_never_echoed(self):
        with patch.object(handler.CredentialStore,'read',side_effect=ValueError('fixture-secret-value')):
            result=self.request()
        self.assertEqual(result['status'],500)
        self.assertNotIn('fixture-secret-value',json.dumps(result))
    def test_authoring_failure_returns_numerical_recovery_evidence(self):
        error=handler.ProviderError('Previous dashboard preserved.',422,'studio_validation')
        error.validation_error='Use the existing chart ID.'
        error.recovery={'modelCalls':3,'queryChecks':2,'maximumModelCalls':3,'maximumQueryChecks':16,'seconds':12.5}
        with patch.object(handler.AgentService,'assist',side_effect=error):
            result=self.request(method='POST',path_info='author',payload='{}')
        self.assertEqual(result['status'],422)
        self.assertEqual(result['payload']['recovery'],error.recovery)
        self.assertEqual(result['headers']['Cache-Control'],'no-store')
    def test_platform_missing_credential_is_unconfigured(self):
        store=handler.CredentialStore('fixture-user','fixture-session')
        with patch.object(handler.splunk.rest,'simpleRequest',side_effect=RESTException(404),create=True):
            self.assertIsNone(store.read())


class SharedInferenceHandlerTests(unittest.TestCase):
    def setUp(self): self.handler = inference_handler.AitkInferenceHandler('driver', 'args')

    def request(self, **changes):
        value = {'method': 'GET', 'path_info': 'status', 'system_authtoken': 'fixture-system',
                 'session': {'user': 'fixture-user', 'authtoken': 'fixture-caller'}}
        value.update(changes)
        return self.handler.handle(json.dumps(value))

    def test_platform_session_and_system_auth_are_required(self):
        self.assertEqual(self.request(session={})['status'], 401)
        self.assertEqual(self.request(system_authtoken='')['status'], 503)

    def test_worker_and_caller_tokens_are_separated_and_never_returned(self):
        def check(caller, privileged, body):
            self.assertEqual(caller.token, 'fixture-caller')
            self.assertEqual(privileged.token, 'fixture-system')
            self.assertEqual(body, {'action': 'status'})
            return {'available': False, 'connection': ''}
        with patch('aitk_inference.execute', side_effect=check): result = self.request()
        self.assertEqual(result['status'], 200)
        self.assertNotIn('fixture-system', json.dumps(result))
        self.assertNotIn('fixture-caller', json.dumps(result))
        self.assertEqual(result['headers']['Cache-Control'], 'no-store')

    def test_unknown_routes_and_native_exceptions_do_not_disclose_details(self):
        self.assertEqual(self.request(method='POST', path_info='search')['status'], 404)
        with patch('aitk_inference.execute', side_effect=RuntimeError('fixture-secret')):
            result = self.request()
        self.assertEqual(result['status'], 500)
        self.assertNotIn('fixture-secret', json.dumps(result))

    def test_each_entry_module_has_one_persistent_class_for_native_loader(self):
        import ast
        for module in (handler, inference_handler):
            tree = ast.parse(Path(module.__file__).read_text())
            classes = [node for node in tree.body if isinstance(node, ast.ClassDef)
                       and any(isinstance(base, ast.Name) and base.id == 'PersistentServerConnectionApplication' for base in node.bases)]
            self.assertEqual(len(classes), 1)

    def test_inference_entry_bootstraps_app_modules_in_isolated_python(self):
        import subprocess
        program = '''import importlib.util,sys,types
splunk=types.ModuleType('splunk'); app=types.ModuleType('splunk.persistconn.application')
app.PersistentServerConnectionApplication=object
sys.modules.update({'splunk':splunk,'splunk.persistconn':types.ModuleType('splunk.persistconn'),'splunk.persistconn.application':app})
spec=importlib.util.spec_from_file_location('fixture_entry',sys.argv[1]); module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert hasattr(module,'AitkInferenceHandler')
'''
        result = subprocess.run([sys.executable, '-I', '-c', program, inference_handler.__file__], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_shared_transport_uses_caller_token_and_sanitizes_native_denial(self):
        runtime = handler.SearchService('fixture-user', 'fixture-caller')
        with patch.dict(sys.modules, {'splunk': splunk, 'splunk.rest': rest}), \
             patch.object(runtime, 'shared_aitk_status', return_value={'available': True, 'connection': 'approved'}), \
             patch.object(rest, 'simpleRequest', return_value=({'status': '403'}, '{"messages":[{"text":"fixture-private-error"}]}'), create=True) as call:
            with self.assertRaises(handler.ProviderError) as error: runtime.shared_aitk_complete('approved', 'Fixture')
        self.assertEqual(call.call_args.kwargs['sessionKey'], 'fixture-caller')
        self.assertNotIn('fixture-private-error', str(error.exception))
        self.assertEqual(error.exception.status, 403)


class CredentialIsolationTests(unittest.TestCase):
    def setUp(self):
        self.store = handler.CredentialStore('fixture-user', 'fixture-session')
        self.acl = {'owner': 'fixture-user', 'app': 'constellation', 'sharing': 'app',
                    'perms': {'read': [''], 'write': ['']}}

    def entry(self, acl=None, secret='{}'):
        return {'entry': [{'acl': self.acl if acl is None else acl,
                           'content': {'clear_password': secret}}]}

    def test_only_owner_app_and_empty_role_grants_are_accepted(self):
        for changes in ({'owner': 'other'}, {'app': 'other'}, {'sharing': 'global'},
                        {'sharing': 'user'}, {'perms': {}},
                        {'perms': {'read': ['*'], 'write': []}},
                        {'perms': {'read': [], 'write': ['admin']}},
                        {'perms': {'read': '', 'write': []}}):
            with self.subTest(changes=changes):
                acl = dict(self.acl, **changes)
                with patch.object(self.store, 'request', return_value=self.entry(acl)) as request:
                    with self.assertRaises(handler.ProviderError): self.store.read()
                    # The ACL endpoint is checked before requesting any secret.
                    self.assertEqual(request.call_args.args[0], self.store.entry + '/acl')
                    self.assertEqual(request.call_count, 1)

    def test_empty_lists_and_platform_empty_strings_are_supported(self):
        for roles in ([], ['']):
            acl = dict(self.acl, perms={'read': roles, 'write': roles})
            with patch.object(self.store, 'request', return_value=self.entry(acl)):
                self.assertEqual(self.store.read(), {})

    def test_new_ids_are_distinct_and_exact_user_scoped(self):
        other = handler.CredentialStore('other-user', 'other-session')
        self.assertNotEqual(self.store.name, other.name)
        self.assertTrue(self.store.entry.startswith('/servicesNS/fixture-user/constellation/storage/passwords/'))
        with patch.object(self.store, 'request', return_value=None) as request:
            self.assertIsNone(self.store.read())
        self.assertEqual([call.args[0] for call in request.call_args_list],
                         [self.store.entry + '/acl', self.store.legacy_entry + '/acl'])

    def test_legacy_record_of_another_owner_is_never_read(self):
        acl = dict(self.acl, owner='other')
        with patch.object(self.store, 'request', side_effect=[None, self.entry(acl)]) as request:
            self.assertIsNone(self.store.read())
        self.assertTrue(all(call.args[0].endswith('/acl') for call in request.call_args_list))

    def test_acl_is_rechecked_on_secret_read(self):
        changed = dict(self.acl, perms={'read': ['*'], 'write': []})
        with patch.object(self.store, 'request', side_effect=[self.entry(), self.entry(changed, 'invalid-json')]):
            with self.assertRaises(handler.ProviderError): self.store.read()

    def test_restricted_legacy_connection_is_updated_in_place(self):
        config = {'api_key': 'fixture-secret', 'model': 'fixture-model'}
        with patch.object(self.store, 'locate', return_value=self.store.legacy_entry), \
             patch.object(self.store, 'read', return_value=config), \
             patch.object(self.store, 'request') as request:
            self.store.write(config)
        self.assertEqual(request.call_args_list[0].args[0], self.store.legacy_entry)
        self.assertEqual(request.call_args_list[1].args,
                         (self.store.legacy_entry + '/acl', 'POST',
                          {'sharing': 'app', 'owner': 'fixture-user', 'perms.read': '', 'perms.write': ''}))
        self.assertEqual(request.call_count, 2)

    def test_new_connection_is_created_with_unique_id_and_verified(self):
        config = {'api_key': 'fixture-secret', 'model': ''}
        with patch.object(self.store, 'locate', return_value=None), \
             patch.object(self.store, 'read', return_value=config), \
             patch.object(self.store, 'request', return_value=self.entry()) as request:
            self.store.write(config)
        fields = request.call_args_list[0].args[2]
        self.assertEqual(fields['name'], self.store.name)
        self.assertEqual(fields['realm'], 'constellation.openai')
        self.assertEqual(fields['password'], '{}')
        self.assertEqual(request.call_args_list[1].args[0], self.store.entry + '/acl')
        self.assertEqual(request.call_args_list[2].args, (self.store.entry + '/acl',))
        self.assertEqual(json.loads(request.call_args_list[3].args[2]['password']), config)

    def test_new_connection_never_receives_secret_when_acl_restriction_fails(self):
        for result in (None, self.entry(dict(self.acl, owner='other'))):
            with self.subTest(result=result), patch.object(self.store, 'locate', return_value=None), \
                 patch.object(self.store, 'request', return_value=result) as request:
                with self.assertRaises(handler.ProviderError): self.store.write({'api_key': 'fixture-secret'})
                self.assertNotIn('fixture-secret', str(request.call_args_list))


if __name__ == '__main__': unittest.main()

class PreviewResultLimitTests(unittest.TestCase):
    def test_native_job_results_request_explicit_pagination(self):
        from test_preview_jobs import JobRuntime
        runtime=JobRuntime(rows=150)
        preview=runtime.preview({'query':'| makeresults count=150 | streamstats count AS row | table row'})
        self.assertEqual(len(preview['results']),150)
        results_call=next(call for call in runtime.calls if call[0].endswith('/results'))
        self.assertEqual(results_call[2]['count'],'201')
