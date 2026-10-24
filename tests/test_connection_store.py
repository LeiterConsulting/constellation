import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from connection_store import ConnectionPreferences, ConnectionStore, secretless
from provider_service import ProviderError


class Preferences(ConnectionPreferences):
    def __init__(self, user='alice', entries=None):
        super().__init__(user, 'fixture-session')
        self.entries = {} if entries is None else entries
    def request(self, path, method='GET', fields=None, projection=False):
        if method == 'POST':
            self.entries[self.name] = {'acl': {'owner': self.user, 'app': 'constellation', 'sharing': 'user'}, 'content': dict(fields)}
        if method == 'DELETE': self.entries.pop(self.name, None)
        entry = self.entries.get(self.name)
        return {'entry': [copy.deepcopy(entry)]} if entry else None


class ConnectionStoreTests(unittest.TestCase):
    def test_secretless_preferences_are_private_and_roundtrip_without_acl_changes(self):
        prefs = Preferences()
        config = {'active_provider': 'ollama', 'connections': {'ollama': {'model': 'fixture', 'base_url': 'http://localhost:11434'}}}
        prefs.write(config)
        self.assertEqual(prefs.read(), config)
        self.assertIsNone(Preferences('bob', prefs.entries).read())
        prefs.entries[prefs.name]['acl']['owner'] = 'bob'
        with self.assertRaises(ProviderError): prefs.read()

    def test_preferences_reject_secrets_in_every_supported_shape(self):
        for config in ({'api_key': 'fixture'}, {'apiKey': 'fixture'}, {'connections': {'openai': {}}}, {'connections': {'ollama': {'password': 'fixture'}}}):
            with self.subTest(config=config), self.assertRaises(ProviderError): secretless(config)

    def test_secretless_routes_do_not_need_password_writes_and_preserve_provider_switches(self):
        encrypted, prefs = Mock(), Preferences()
        encrypted.read.return_value = None
        store = ConnectionStore(encrypted, prefs)
        config = {'active_provider': 'ollama', 'connections': {'ollama': {'model': 'fixture'}}}
        store.write(config)
        encrypted.write.assert_not_called()
        encrypted.read.side_effect = AssertionError('Password reads are unnecessary')
        self.assertEqual(store.read(), config)

    def test_openai_never_enters_preferences_and_failed_credentials_keep_previous_route(self):
        encrypted, prefs = Mock(), Preferences()
        previous = {'active_provider': 'ollama', 'connections': {}}
        prefs.write(previous); store = ConnectionStore(encrypted, prefs)
        secret = {'api_key': 'fixture-secret', 'model': 'fixture-model'}
        encrypted.write.side_effect = ProviderError('denied')
        with self.assertRaises(ProviderError): store.write(secret)
        self.assertEqual(store.read(), previous)
        encrypted.write.side_effect = None; encrypted.read.return_value = secret
        store.write(secret)
        self.assertIsNone(prefs.read()); self.assertEqual(store.read(), secret)
