"""Catalog reuse is request-local, immutable to callers and never search proof."""
import unittest
from unittest.mock import Mock
from test_reliability_journey import Runtime
from data_service import DataService
from search_service import SearchService
from provider_service import ProviderError


class CatalogSnapshotTests(unittest.TestCase):
    def runtime(self, user='fixture-user'):
        runtime = Runtime()
        SearchService.__init__(runtime, user, 'fixture-session')
        runtime.request = Mock(return_value={'entry': [
            {'name': 'fixture_index', 'content': {'datatype': 'event', 'disabled': '0'}},
            {'name': 'fixture_metrics', 'content': {'datatype': 'metric', 'disabled': '0'}},
            {'name': 'fixture_disabled', 'content': {'disabled': '1'}}]})
        # Use the real catalog boundary with the fixture's native preview.
        runtime.datasets = lambda: SearchService.datasets(runtime)
        return runtime

    def test_agent_catalog_and_repeated_profiles_use_one_native_catalog_read(self):
        runtime = self.runtime()
        catalog = runtime.datasets()
        service = DataService(runtime)
        first = service.profile({'index': 'fixture_index'})
        second = service.profile({'index': 'fixture_index'})
        self.assertEqual(runtime.request.call_count, 1)
        self.assertEqual(len(runtime.calls), 2)  # Both field inspections still execute.
        self.assertEqual(first['scope'], second['scope'])
        self.assertEqual(catalog['indexes'], [{'name': 'fixture_index', 'kind': 'event'}, {'name': 'fixture_metrics', 'kind': 'metric'}])
        catalog['indexes'].clear()
        self.assertEqual(len(runtime.datasets()['indexes']), 2)
        third = runtime.datasets(); third['indexes'][0]['name'] = 'changed'
        self.assertEqual(runtime.datasets()['indexes'][0]['name'], 'fixture_index')

    def test_new_runtime_and_other_user_never_share_a_snapshot(self):
        first, second, peer = self.runtime(), self.runtime(), self.runtime('fixture-peer')
        first.datasets(); second.datasets(); peer.datasets()
        self.assertEqual([r.request.call_count for r in (first, second, peer)], [1, 1, 1])
        self.assertIsNot(first._dataset_catalog, second._dataset_catalog)
        self.assertIsNot(first._dataset_catalog, peer._dataset_catalog)

    def test_failed_read_is_not_cached_and_restricted_catalog_stays_restricted(self):
        runtime = self.runtime(); runtime.request.side_effect = ProviderError('Interrupted', 503, 'splunk_transport')
        with self.assertRaises(ProviderError): runtime.datasets()
        self.assertFalse(hasattr(runtime, '_dataset_catalog'))
        restricted = self.runtime(); restricted.request.return_value = {'unavailable': 'restricted'}
        self.assertEqual(restricted.datasets()['status'], 'restricted')
        with self.assertRaisesRegex(ProviderError, 'visible'): DataService(restricted).profile({'index': 'fixture_index'})
        self.assertEqual(restricted.request.call_count, 1)
