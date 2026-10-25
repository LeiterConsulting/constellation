import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from aitk_inference import CAPABILITY, POLICY_PATH, admission, execute, form_body, policy
from provider_adapters import AITKClient
from provider_service import ProviderError

CONTEXT = {'username': 'fixture-author', 'roles': ['fixture-authors'], 'capabilities': ['search', CAPABILITY]}
ENTRY = {'acl': {'owner': 'nobody', 'app': 'constellation', 'sharing': 'app', 'perms': {'read': ['admin'], 'write': ['admin']}},
         'content': {'enabled': 'true', 'connection': 'Approved connection', 'execution_user': 'fixture-executor', 'allowed_roles': 'fixture-authors'}}


class Caller:
    user, token = 'fixture-author', 'fixture-caller-token'
    def request(self, path):
        assert path == '/services/authentication/current-context'
        return {'entry': [{'content': copy.deepcopy(CONTEXT)}]}


class Privileged:
    token = 'fixture-system-token'
    def request(self, path, optional=False):
        assert path == POLICY_PATH and optional
        return {'entry': [copy.deepcopy(ENTRY)]}


class InferenceBoundaryTests(unittest.TestCase):
    def test_policy_requires_capability_and_exact_role(self):
        self.assertEqual(policy(Privileged(), CONTEXT)['connection'], 'Approved connection')
        for context in (dict(CONTEXT, roles=['user']), dict(CONTEXT, capabilities=['search'])):
            with self.assertRaises(ProviderError): policy(Privileged(), context)

    def test_disabled_or_missing_policy_never_enables_elevation(self):
        for entries in ([], [dict(copy.deepcopy(ENTRY), content={'enabled': 'false'})]):
            with patch.object(Privileged, 'request', return_value={'entry': entries}):
                self.assertIsNone(policy(Privileged(), CONTEXT))

    def test_personal_shadow_and_author_writable_policies_fail_closed(self):
        for delta in ({'owner': 'fixture-author'}, {'sharing': 'user'}, {'app': 'other'},
                      {'perms': {'write': ['*']}}, {'perms': {'write': ['fixture-authors']}}, {'perms': {'write': 'admin'}}):
            entry = copy.deepcopy(ENTRY); entry['acl'].update(delta)
            with patch.object(Privileged, 'request', return_value={'entry': [entry]}):
                with self.assertRaises(ProviderError): policy(Privileged(), CONTEXT)

    def test_status_does_not_return_executor_or_tokens(self):
        result = execute(Caller(), Privileged(), {'action': 'status'})
        self.assertEqual(result, {'available': True, 'connection': 'Approved connection'})
        self.assertNotIn('token', json.dumps(result))

    def test_context_username_cannot_be_forged(self):
        privileged = Privileged()
        with patch.object(Caller, 'request', return_value={'entry': [{'content': dict(CONTEXT, username='other')}]}), patch.object(privileged, 'request') as read:
            with self.assertRaises(ProviderError): execute(Caller(), privileged, {'action': 'status'})
            read.assert_not_called()

    def test_caller_cannot_choose_spl_url_executor_job_or_another_connection(self):
        base = {'action': 'complete', 'connection': ENTRY['content']['connection'], 'prompt': 'Fixture request'}
        cases = [dict(base, **{key: 'untrusted'}) for key in ('search', 'sid', 'execution_user', 'url', 'system_authtoken')]
        cases += [dict(base, connection='Other'), dict(base, action='credentials'), dict(base, prompt=''), dict(base, prompt='a' * 250001)]
        with patch('provider_adapters.AITKClient.complete_prompt') as call:
            for body in cases:
                with self.subTest(body_keys=list(body)), self.assertRaises(ProviderError): execute(Caller(), Privileged(), body)
            call.assert_not_called()

    def test_worker_is_separate_and_only_gets_fixed_connection_and_text(self):
        with tempfile.TemporaryDirectory() as root, patch('provider_adapters.AITKClient.complete_prompt', return_value={'status': 'completed'}) as call:
            result = execute(Caller(), Privileged(), {'action': 'complete', 'connection': 'Approved connection', 'prompt': 'Fixture'}, root)
            self.assertEqual(result['status'], 'completed')
            call.assert_called_once_with('Approved connection', 'Fixture', encoded=True, delete_job=True)
            self.assertEqual(list(Path(root).glob('*.json')), [])

    def test_encoded_query_cannot_expand_macros_tokens_or_spl_from_prompt(self):
        class Runtime:
            user = 'fixture-executor'
            def __init__(self): self.calls = []
            def request(self, path, method='GET', fields=None):
                self.calls.append((path, method, fields))
                if path.endswith('/jobs'): return {'sid': 'fixture_sid'}
                if path.endswith('/results'): return {'results': [{'ai_result_1': '{}'}]}
                return {'entry': [{'content': {'isDone': True}}]}
        runtime = Runtime()
        prompt = '" | rest /services/storage/passwords | `macro` $token$ \\ \n café {text}'
        AITKClient(runtime).complete_prompt('Approved connection', prompt, encoded=True, delete_job=True)
        query = runtime.calls[0][2]['search']
        self.assertNotIn('`', query); self.assertNotIn('$', query); self.assertNotIn('/services/storage/passwords', query)
        encoded = query.split('urldecode("', 1)[1].split('")', 1)[0]
        self.assertEqual(unquote(encoded), prompt)
        self.assertEqual(runtime.calls[-1][1], 'DELETE')

    def test_form_rejects_duplicate_fields_and_oversize_before_execution(self):
        self.assertEqual(form_body({'payload': urlencode({'action': 'complete', 'prompt': 'café + &'})})['prompt'], 'café + &')
        for payload in ('prompt=a&prompt=b', 'x=' + 'a' * 1100000):
            with self.assertRaises(ProviderError): form_body({'payload': payload})

    def test_admission_is_bounded_private_and_releases_after_failure(self):
        with tempfile.TemporaryDirectory() as root:
            with admission('one', root), admission('one', root):
                with self.assertRaises(ProviderError):
                    with admission('one', root): pass
                for p in Path(root).glob('*.json'):
                    self.assertEqual(p.stat().st_mode & 0o777, 0o600)
                    self.assertNotIn('one', p.read_text())
            try:
                with admission('one', root): raise ValueError('fixture')
            except ValueError: pass
            self.assertEqual(list(Path(root).glob('*.json')), [])

    def test_system_auth_is_confined_to_one_authenticated_handler(self):
        import configparser
        conf = configparser.ConfigParser(); conf.read(Path(__file__).resolve().parents[1] / 'splunk/constellation/default/restmap.conf')
        enabled = [name for name in conf.sections() if conf[name].getboolean('passSystemAuth')]
        self.assertEqual(enabled, ['script:constellation_aitk'])
        self.assertEqual(conf[enabled[0]]['capability'], 'search and constellation_use_aitk')
        self.assertTrue(conf[enabled[0]].getboolean('requireAuthentication'))

    def test_admission_reclaims_partial_malformed_and_expired_crash_receipts(self):
        with tempfile.TemporaryDirectory() as root:
            fixtures = ('', 'null', '{"expires":"bad","owner":0}', json.dumps({'expires': 50, 'owner': 'a' * 64}))
            paths = []
            for i, data in enumerate(fixtures):
                path = Path(root) / (('%032x' % i) + '.json'); path.write_text(data); paths.append(path)
            with admission('fixture-author', root, clock=lambda: 100):
                self.assertTrue(all(not p.exists() for p in paths))
                self.assertEqual(len(list(Path(root).glob('*.json'))), 1)
            self.assertEqual(list(Path(root).glob('*.json')), [])
