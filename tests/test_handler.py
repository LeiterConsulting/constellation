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


class HandlerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.handler = handler.ConstellationHandler('driver','args')
    def request(self, **changes):
        value={'method':'GET','path_info':'settings','session':{'user':'fixture-user','authtoken':'fixture-session'}}
        value.update(changes)
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
    def test_internal_exceptions_are_never_echoed(self):
        with patch.object(handler.CredentialStore,'read',side_effect=ValueError('fixture-secret-value')):
            result=self.request()
        self.assertEqual(result['status'],500)
        self.assertNotIn('fixture-secret-value',json.dumps(result))
    def test_platform_missing_credential_is_unconfigured(self):
        store=handler.CredentialStore('fixture-user','fixture-session')
        with patch.object(handler.splunk.rest,'simpleRequest',side_effect=RESTException(404),create=True):
            self.assertIsNone(store.read())


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
             patch.object(self.store, 'request') as request:
            self.store.write(config)
        fields = request.call_args_list[0].args[2]
        self.assertEqual(fields['name'], self.store.name)
        self.assertEqual(fields['realm'], 'constellation.openai')
        self.assertEqual(request.call_args_list[1].args[0], self.store.entry + '/acl')


if __name__ == '__main__': unittest.main()

class PreviewResultLimitTests(unittest.TestCase):
    def test_native_oneshot_count_matches_the_declared_200_row_budget(self):
        from search_service import SearchService
        calls=[]
        def request(path,**kwargs):
            calls.append(kwargs);return {},json.dumps({'results':[{'row':str(i)} for i in range(150)],'fields':[{'name':'row'}]})
        runtime=SearchService('fixture-user','fixture-session')
        with patch.dict(sys.modules,{'splunk':handler.splunk,'splunk.rest':handler.splunk.rest}), patch.object(handler.splunk.rest,'simpleRequest',side_effect=request,create=True):
            preview=runtime.preview({'query':'| makeresults count=150 | streamstats count AS row | table row'})
            runtime.datasets()
        self.assertEqual(len(preview['results']),150)
        self.assertEqual(calls[0]['postargs']['count'],'200');self.assertEqual(calls[0]['postargs']['max_count'],'200')
        self.assertEqual(calls[1]['getargs']['count'],'100')
