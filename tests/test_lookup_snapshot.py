"""Synthetic fixed-query transfer jobs, independent of ordinary preview limits."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from lookup_snapshot import read_static_csv, ROWS
from provider_service import ProviderError


class Runtime:
    user, namespace = 'fixture_author', '/servicesNS/fixture_author/constellation'
    def __init__(self, count=1201):
        self.rows = [{'key': str(i), 'value': 'value'} for i in range(count)]
        self.calls, self.checks = [], 0
        self.meta = {'isDone': True, 'isFinalized': False, 'resultCount': str(count), 'messages': []}
        self.acl = {'owner': self.user, 'app': 'constellation'}
        self.page_change, self.meta_change = lambda x: x, lambda x: x
        self.shadow, self.missing, self.uncertain, self.pending = False, False, False, False
        self.sid = 'fixture_sid';self.metadata_reads = 0
    def check_cancel(self): self.checks += 1
    def request(self, path, method='GET', fields=None, optional=False):
        self.calls.append((path, method, fields))
        if '/data/lookup-table-files/' in path: return {'entry': [] if self.missing else [{'name': 'fixture.csv', 'content': {}}]}
        if '/data/transforms/lookups/' in path: return {'entry': [{'name': 'fixture.csv', 'content': {}}] if self.shadow else []}
        if path.endswith('/jobs'):
            if self.uncertain: raise ProviderError('uncertain dispatch', 503)
            return {'sid': self.sid}
        if path.endswith('/control'): return {}
        if path.endswith('/results'):
            if self.pending: self.pending = False;return {'resultsPending': True}
            offset, count = int(fields['offset']), int(fields['count'])
            result = {'fields': [{'name': 'key'}, {'name': 'value'}], 'results': copy.deepcopy(self.rows[offset:offset+count])}
            return self.page_change(result)
        self.metadata_reads += 1
        return self.meta_change({'entry': [{'acl': copy.deepcopy(self.acl), 'content': copy.deepcopy(self.meta)}]})


class SnapshotTests(unittest.TestCase):
    def run_read(self, runtime, **kw): return read_static_csv(runtime, 'fixture.csv', sleep=lambda _: None, **kw)
    def assert_cancelled(self, runtime):
        self.assertEqual(sum(p.endswith('/control') for p, _, _ in runtime.calls), 1)
    def test_paginated_complete_table_does_not_use_or_expand_preview(self):
        runtime = Runtime();result = self.run_read(runtime)
        self.assertEqual(result['results'], runtime.rows);self.assertEqual(result['state'], 'complete')
        pages = [x[2] for x in runtime.calls if x[0].endswith('/results')]
        self.assertEqual([x['offset'] for x in pages], ['0', '500', '1000'])
        created = [x[2] for x in runtime.calls if x[0].endswith('/jobs')]
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]['search'], '| inputlookup strict=true max=5001 fixture.csv')
        self.assertEqual(created[0]['max_time'], '5');self.assertEqual(created[0]['max_count'], '5001')
        self.assertEqual(runtime.metadata_reads, 2);self.assert_cancelled(runtime)
    def test_exact_limit_empty_header_and_pending_results(self):
        runtime = Runtime(ROWS);self.assertEqual(len(self.run_read(runtime)['results']), ROWS)
        runtime = Runtime(0);runtime.pending = True
        result = self.run_read(runtime);self.assertEqual(result['results'], []);self.assertEqual(len(result['fields']), 2)
        self.assert_cancelled(runtime)
    def test_unsafe_filename_missing_or_shadowed_file_never_dispatches(self):
        for filename in ('../fixture.csv', 'fixture.csv | collect index=x', '$lookup$', 'fixture'):
            runtime = Runtime()
            with self.assertRaises(ProviderError): read_static_csv(runtime, filename)
            self.assertEqual(runtime.calls, [])
        for attr in ('missing', 'shadow'):
            runtime = Runtime();setattr(runtime, attr, True)
            with self.assertRaises(ProviderError): self.run_read(runtime)
            self.assertFalse(any(x[0].endswith('/jobs') for x in runtime.calls))
    def test_failed_finalized_unverified_oversized_and_foreign_jobs_refuse(self):
        for change in ({'isFailed': '1'}, {'isZombie': True}, {'isFinalized': True}, {'dispatchState': 'FAILED'}, {'resultCount': '5001'}, {'resultCount': None}, {'messages': [{'type': 'WARN', 'text': 'partial'}]}):
            runtime = Runtime();runtime.meta.update(change)
            with self.subTest(change=change), self.assertRaises(ProviderError): self.run_read(runtime)
            self.assert_cancelled(runtime)
        for key in ('owner', 'app'):
            runtime = Runtime();runtime.acl[key] = 'other'
            with self.assertRaises(ProviderError): self.run_read(runtime)
        runtime = Runtime();runtime.meta.pop('isFinalized')
        with self.assertRaises(ProviderError): self.run_read(runtime)
    def test_row_count_changes_and_malformed_pages_never_return_samples(self):
        def malformed_header(x): x['fields'] = [{'name': 'key'}, {'name': 'key'}];return x
        def short_page(x): x['results'].pop();return x
        def multivalue(x): x['results'][0]['value'] = ['a', 'b'];return x
        def hidden_field(x): x['results'][0]['extra'] = 'unknown';return x
        def diagnostics(x): x['messages'] = [{'type': 'ERROR', 'text': 'search failed'}];return x
        for change in (malformed_header, short_page, multivalue, hidden_field, diagnostics):
            runtime = Runtime();runtime.page_change = change
            with self.subTest(change=change.__name__), self.assertRaises(ProviderError): self.run_read(runtime)
            self.assert_cancelled(runtime)
        runtime = Runtime()
        def changed(x):
            if runtime.metadata_reads > 1: x['entry'][0]['content']['resultCount'] = '1200'
            return x
        runtime.meta_change = changed
        with self.assertRaisesRegex(ProviderError, 'changed'): self.run_read(runtime)
    def test_header_changes_midstream_and_json_budget_refuse(self):
        runtime = Runtime()
        def changed(x):
            if len([c for c in runtime.calls if c[0].endswith('/results')]) > 1: x['fields'].reverse()
            return x
        runtime.page_change = changed
        with self.assertRaises(ProviderError): self.run_read(runtime)
        runtime = Runtime(600);runtime.rows = [{'key': 'x'*3999, 'value': 'y'*3999}]*600
        with self.assertRaisesRegex(ProviderError, 'size budget'): self.run_read(runtime)
    def test_timeout_cancellation_and_uncertain_dispatch_do_not_replay(self):
        runtime = Runtime();runtime.meta['isDone'] = False
        tick = iter(range(100))
        with self.assertRaisesRegex(ProviderError, 'timed out'): self.run_read(runtime, clock=lambda: next(tick))
        self.assert_cancelled(runtime)
        runtime = Runtime()
        def cancel():
            if runtime.metadata_reads: raise ProviderError('cancelled')
        runtime.check_cancel = cancel
        with self.assertRaisesRegex(ProviderError, 'cancelled'): self.run_read(runtime)
        self.assert_cancelled(runtime)
        runtime = Runtime();runtime.uncertain = True
        with self.assertRaises(ProviderError): self.run_read(runtime)
        self.assertEqual(sum(p.endswith('/jobs') for p, _, _ in runtime.calls), 1)
        runtime = Runtime();runtime.sid = '../other'
        with self.assertRaises(ProviderError): self.run_read(runtime)
        self.assertFalse(any(p.endswith('/control') for p, _, _ in runtime.calls))
    def test_timestamp_projection_keeps_exact_cells_and_avoids_existing_header(self):
        class TimeRuntime(Runtime):
            def request(self, path, method='GET', fields=None, optional=False):
                if path.endswith('/jobs'): self.projected = fields['search'].endswith('rename _time AS constellation_csv_time_1')
                result = super().request(path, method, fields, optional)
                if path.endswith('/results'):
                    key = 'constellation_csv_time_1' if self.projected else '_time'
                    result['fields'] = [{'name': name} for name in sorted([key, 'label', 'constellation_csv_time_0'])]
                    result['results'] = [{key: '1704067200.000' if self.projected else '2023-12-31T19:00:00.000-05:00', 'label': 'Old', 'constellation_csv_time_0': 'preserved'}]
                return result
        runtime = TimeRuntime(1);result = self.run_read(runtime)
        self.assertEqual(result['results'], [{'_time': '1704067200.000', 'label': 'Old', 'constellation_csv_time_0': 'preserved'}])
        self.assertEqual(sum(p.endswith('/jobs') for p, _, _ in runtime.calls), 2)
        self.assertEqual(sum(p.endswith('/control') for p, _, _ in runtime.calls), 2)
    def test_changed_projected_header_is_not_accepted(self):
        class TimeRuntime(Runtime):
            def request(self, path, method='GET', fields=None, optional=False):
                if path.endswith('/jobs'): self.projected = 'rename _time AS ' in fields['search']
                result = super().request(path, method, fields, optional)
                if path.endswith('/results'):
                    result['fields'] = [{'name': 'unexpected' if self.projected else '_time'}]
                    result['results'] = [{result['fields'][0]['name']: '1704067200'}]
                return result
        runtime = TimeRuntime(1)
        with self.assertRaisesRegex(ProviderError, 'header changed'): self.run_read(runtime)
        self.assertEqual(sum(p.endswith('/jobs') for p, _, _ in runtime.calls), 2)
        self.assertEqual(sum(p.endswith('/control') for p, _, _ in runtime.calls), 2)


if __name__ == '__main__': unittest.main()
