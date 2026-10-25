"""Synthetic metadata only: no vendor files, tokens, connections or live hosts."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from aitk_connection_policy import BASE, verify_connection
from aitk_inference import execute
from provider_service import ProviderError
from test_aitk_inference import Caller, Privileged

ACL = {'owner': 'nobody', 'app': 'Splunk_ML_Toolkit', 'sharing': 'global',
       'perms': {'read': ['*'], 'write': ['admin', 'mltk_admin']}}
RECORD = {'name': 'Approved connection', 'provider': 'OpenAI', 'connection_details': {'endpoint': 'https://api.example.com/v1'},
          'acl': dict(copy.deepcopy(ACL), owner='fixture-maintainer', sharing='app')}


class Metadata:
    token = 'fixture-system-token'
    def __init__(self):
        self.acls = {c: copy.deepcopy(ACL) for c in ('aitk_llm_connection', 'mltk_ai_commander_collection')}
        self.records, self.legacy, self.roles = [copy.deepcopy(RECORD)], [], ['admin']
        self.paths = []
    def request(self, path):
        self.paths.append(path)
        if path.startswith(BASE + 'config/'):
            return {'entry': [{'acl': self.acls[path.rsplit('/', 1)[1]]}]}
        if path.startswith(BASE + 'data/aitk_llm_connection?'): return self.records
        if path.startswith(BASE + 'data/mltk_ai_commander_collection?'): return self.legacy
        if path == '/services/authentication/users/fixture-maintainer': return {'entry': [{'content': {'roles': self.roles}}]}
        if path == '/services/authentication/users/fixture-author': return {'entry': [{'content': {'roles': ['user']}}]}
        if path == '/services/authorization/roles/fixture-custom': return {'entry': [{'content': {'imported_roles': ['mltk_admin']}}]}
        if path == '/services/authorization/roles/user': return {'entry': [{'content': {'imported_roles': []}}]}
        raise AssertionError('Unexpected metadata path')


class AitkDependencyTests(unittest.TestCase):
    def test_protected_modern_record_and_inherited_maintainer_are_accepted(self):
        for roles in (['admin'], ['mltk_admin'], ['fixture-custom']):
            runtime = Metadata(); runtime.roles = roles
            verify_connection(runtime, 'Approved connection', 'fixture-maintainer')
            self.assertFalse(any('password' in p or '/search/' in p for p in runtime.paths))
            data_paths = [p for p in runtime.paths if '/data/' in p]
            self.assertEqual(parse_qs(urlsplit(data_paths[0]).query)['fields'], ['name,provider,acl'])
            self.assertNotIn('fields', parse_qs(urlsplit(data_paths[1]).query))

    def test_ordinary_execution_namespace_is_rejected_before_collection_reads(self):
        runtime = Metadata()
        with self.assertRaises(ProviderError): verify_connection(runtime, 'Approved connection', 'fixture-author')
        self.assertFalse(any(p.startswith(BASE) for p in runtime.paths))

    def test_both_collections_require_shared_nobody_ownership_and_maintainer_only_writes(self):
        for collection in Metadata().acls:
            for change in ({'owner': 'fixture-author'}, {'app': 'other'}, {'sharing': 'user'},
                           {'perms': {'write': ['*']}}, {'perms': {'write': ['admin', 'power']}},
                           {'perms': {'write': []}}, {'perms': {'write': 'admin'}}):
                runtime = Metadata(); runtime.acls[collection].update(change)
                with self.subTest(collection=collection, change=change), self.assertRaises(ProviderError):
                    verify_connection(runtime, 'Approved connection', 'fixture-maintainer')

    def test_record_writes_owner_and_indirect_provider_are_checked(self):
        for mutate in (lambda r: r['acl']['perms'].update(write=['*']),
                       lambda r: r['acl'].update(owner='fixture-author'),
                       lambda r: r.update(provider='AI Tier'),
                       lambda r: r.update(name='Other connection')):
            runtime = Metadata(); mutate(runtime.records[0])
            with self.assertRaises(ProviderError): verify_connection(runtime, 'Approved connection', 'fixture-maintainer')
        runtime = Metadata(); runtime.roles = ['user']
        with self.assertRaises(ProviderError): verify_connection(runtime, 'Approved connection', 'fixture-maintainer')

    def test_absent_duplicate_malformed_or_unreadable_metadata_fails_closed(self):
        for records in ([], [copy.deepcopy(RECORD)] * 2, {}, [None]):
            runtime = Metadata(); runtime.records = records
            with self.assertRaises(ProviderError): verify_connection(runtime, 'Approved connection', 'fixture-maintainer')
        with patch.object(Metadata, 'request', side_effect=ProviderError('fixture upstream body', 422)):
            with self.assertRaises(ProviderError) as error: verify_connection(Metadata(), 'Approved connection', 'fixture-maintainer')
            self.assertEqual(error.exception.code, 'aitk_connection_policy_invalid')
            self.assertNotIn('upstream', str(error.exception))

    def test_legacy_explicit_and_generated_name_shadowing_are_rejected(self):
        for name, model in (('Approved connection', {'connection_name': {'value': 'Approved connection'}}),
                            ('llm_OpenAI_fixture-model', {})):
            runtime = Metadata(); runtime.records[0]['name'] = name
            runtime.legacy = [{'OpenAI': {'models': {'fixture-model': dict(model, is_model_saved={'value': True})}}}]
            with self.assertRaises(ProviderError): verify_connection(runtime, name, 'fixture-maintainer')
        runtime = Metadata(); runtime.legacy = [{'OpenAI': {'models': {'fixture-model': {'is_model_saved': {'value': False}}}}}]
        verify_connection(runtime, 'Approved connection', 'fixture-maintainer')
        for value in (1, 'true', 'false', [], None):
            runtime = Metadata(); runtime.legacy = [{'OpenAI': {'models': {'fixture-model': {'is_model_saved': {'value': value}}}}}]
            with self.assertRaises(ProviderError): verify_connection(runtime, 'Approved connection', 'fixture-maintainer')
        runtime = Metadata(); runtime.legacy = [{'Fixture custom provider': {'models': {'fixture-model': {
            'is_model_saved': {'value': True}, 'connection_name': {'value': 'Approved connection'}}}}}]
        with self.assertRaises(ProviderError): verify_connection(runtime, 'Approved connection', 'fixture-maintainer')

    def test_rejections_never_submit_a_privileged_job(self):
        with patch('aitk_connection_policy.verify_connection', side_effect=ProviderError('fixture rejected', 503)), \
             patch('provider_adapters.AITKClient.complete_prompt') as complete:
            for body in ({'action': 'status'}, {'action': 'complete', 'connection': 'Approved connection', 'prompt': 'Fixture'}):
                with self.assertRaises(ProviderError): execute(Caller(), Privileged(), body)
            complete.assert_not_called()

    def test_oversized_legacy_configuration_fails_before_model_iteration(self):
        runtime = Metadata(); runtime.legacy = [{'fixture': {'unused': 'x' * 1_000_000}}]
        with self.assertRaises(ProviderError): verify_connection(runtime, 'Approved connection', 'fixture-maintainer')
