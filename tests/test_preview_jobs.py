"""Synthetic native-job lifecycle fixtures. No provider keys or live events."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from preview_jobs import PreviewJobs
from search_service import SearchService
from provider_service import ProviderError
from data_service import DataService


class JobRuntime(SearchService):
    def __init__(self, meta=None, rows=1):
        super().__init__('alice', 'synthetic-session')
        self.meta = dict(isDone='1', isFinalized='0', resultCount=str(rows))
        self.meta.update(meta or {})
        self.rows, self.calls, self.owner = rows, [], 'alice'
        self.messages = []
    def request(self, path, method='GET', fields=None, optional=False):
        self.calls.append((path, method, fields))
        if path.endswith('/control'): return {}
        if path.endswith('/results'):
            return {'fields': [{'name': 'row'}], 'results': [{'row': str(i)} for i in range(self.rows)], 'messages': self.messages}
        if method == 'POST': return {'sid': '1234.56'}
        return {'entry': [{'acl': {'owner': self.owner, 'app': 'constellation'}, 'content': copy.deepcopy(self.meta)}]}


class PreviewJobTests(unittest.TestCase):
    def test_exact_successful_csv_read_notice_is_not_partial_but_warnings_still_are(self):
        runtime = JobRuntime();notice = {'type': 'INFO', 'text': "Successfully read lookup file '/synthetic/fixture.csv'."}
        runtime.meta['messages'] = [notice];runtime.messages = [notice]
        result = PreviewJobs(runtime).execute('| inputlookup fixture.csv', '-15m')
        self.assertEqual(result['state'], 'complete');self.assertNotIn('/synthetic/', json.dumps(result))
        runtime.meta['messages'] = [{'type': 'INFO', 'text': "Assuming implicit lookup table with filename 'fixture.csv'."}]
        self.assertEqual(PreviewJobs(runtime).execute('| inputlookup fixture.csv', '-15m')['state'], 'complete')
        for message in ({'type': 'WARN', 'text': notice['text']}, {'type': 'INFO', 'text': 'Different diagnostic'}, {'type': 'INFO', 'text': notice['text'] + '\nPartial read'}):
            runtime.messages = [message]
            self.assertEqual(PreviewJobs(runtime).execute('| inputlookup fixture.csv', '-15m')['state'], 'partial')

    def wide_runtime(self, rows):
        runtime = JobRuntime(rows=len(rows)); original = runtime.request
        names = sorted({name for row in rows for name in row})
        def request(path, method='GET', fields=None, optional=False):
            if path.endswith('/results'):
                runtime.calls.append((path, method, fields))
                return {'fields': [{'name': name} for name in names], 'results': rows, 'messages': runtime.messages}
            return original(path, method, fields, optional)
        runtime.request = request
        runtime.datasets = lambda: {'indexes': [{'name': 'fixture'}]}
        return runtime

    def test_discovery_omits_raw_without_relaxing_chart_preview_limit(self):
        rows = [{'_time': '1000', 'temperature_f': 0, '_raw': 'PRIVATE' * 200000}]
        runtime = self.wide_runtime(rows)
        profile = DataService(runtime).profile({'index': 'fixture'})
        self.assertEqual(profile['sampledRows'], 1)
        self.assertEqual(profile['completion']['state'], 'complete')
        self.assertNotIn('_raw', json.dumps(profile)); self.assertNotIn('PRIVATE', json.dumps(profile))
        self.assertTrue(next(f for f in profile['fields'] if f['name'] == 'temperature_f')['numeric'])
        with self.assertRaises(ProviderError) as error:
            runtime.preview({'query': 'search index="fixture"'})
        self.assertEqual(error.exception.status, 413)
        self.assertEqual(runtime.calls[-1][2], {'action': 'cancel'})

    def test_discovery_size_sampling_preserves_cells_counts_and_partial_evidence(self):
        rows = [{'wide': ['\u2603' * 50000, 'PRIVATE'], 'value': 0},
                {'wide': ['\u2603' * 50000, 'PRIVATE']},
                {'wide': ['\u2603' * 50000, 'PRIVATE'], 'value': '2'},
                {'wide': ['\u2603' * 50000, 'PRIVATE'], 'value': 'unknown'}]
        runtime = self.wide_runtime(rows); before = copy.deepcopy(rows)
        runtime.meta['isFinalized'] = '1'
        runtime.messages = [{'type': 'WARN', 'text': 'PRIVATE diagnostic'}]
        result = runtime.preview({'query': 'search index="fixture"', 'fieldDiscovery': True})
        self.assertEqual(result['results'], rows[:3]); self.assertEqual(rows, before)
        self.assertLessEqual(len(json.dumps(result['results']).encode('utf-8')), 1_000_000)
        self.assertEqual(result['state'], 'partial'); self.assertEqual(result['evidence']['resultCount'], 4)
        self.assertIn('retained sample', result['warning']); self.assertIn('resource limit', result['warning'])
        self.assertIn('diagnostics', result['warning']); self.assertNotIn('PRIVATE', result['warning'])
        self.assertEqual(sum(path.endswith('/jobs') for path, _, _ in runtime.calls), 1)
        profile = DataService(runtime).profile({'index': 'fixture'})
        self.assertEqual(profile['sampledRows'], 3); self.assertEqual(profile['completion']['state'], 'partial')
        self.assertIn('retained sample', json.dumps(profile['completion']))
        fields = {f['name']: f for f in profile['fields']}
        self.assertEqual(fields['value']['coverage'], {'missing': 1, 'numeric': 2, 'multivalue': 0, 'basis': 'sample_rows'})
        self.assertEqual(fields['wide']['coverage']['multivalue'], 3)
        self.assertNotIn('PRIVATE', json.dumps(profile))
        self.assertEqual(profile['baseQuery'], 'search index="fixture"')

    def test_single_oversized_extracted_row_fails_explicitly_and_cancels(self):
        runtime = self.wide_runtime([{'wide': 'x' * 1_000_000}])
        with self.assertRaises(ProviderError) as error:
            DataService(runtime).profile({'index': 'fixture'})
        self.assertEqual(error.exception.status, 413); self.assertEqual(error.exception.code, 'profile_too_large')
        self.assertEqual(runtime.calls[-1][2], {'action': 'cancel'})
        self.assertEqual(sum(path.endswith('/jobs') for path, _, _ in runtime.calls), 1)

    def test_discovery_prioritizes_useful_fields_before_native_field_cap(self):
        row = {'a_nested_' + str(i): 'fixture' for i in range(120)}
        row.update({'_time': '1000', 'host': 'fixture_host', 'response_time_ms': '3', 'status': 'observed'})
        runtime = self.wide_runtime([row])
        profile = DataService(runtime).profile({'index': 'fixture'})
        names = {field['name'] for field in profile['fields']}
        self.assertTrue({'_time', 'host', 'response_time_ms', 'status'} <= names)
        self.assertEqual(len(names), 60)
        ordinary = runtime.preview({'query': 'search index="fixture"'})
        self.assertEqual(len(ordinary['fields']), 100)
        self.assertNotIn('response_time_ms', {field['name'] for field in ordinary['fields']})

    def test_complete_partial_and_unknown_evidence_are_distinct(self):
        for meta, rows, state in [({},150,'complete'), ({'isFinalized':'1'},1,'partial'), ({},201,'partial'),
                                  ({'resultCount':'unknown'},1,'partial'), ({'isDone':'0','isFinalized':'1'},0,'partial')]:
            with self.subTest(meta=meta, rows=rows):
                runtime = JobRuntime(meta, rows)
                result = runtime.preview({'query': '| makeresults | stats count'})
                self.assertEqual(result['state'], state)
                self.assertLessEqual(len(result['results']), 200)
                self.assertNotIn('synthetic-session', json.dumps(result))
                self.assertEqual(runtime.calls[-1][2], {'action': 'cancel'})
    def test_caller_cannot_override_resource_limits(self):
        runtime = JobRuntime()
        runtime.job({'action':'start','query':'| makeresults','earliest':'-24h','max_time':500,'auto_cancel':0})
        fields = runtime.calls[0][2]
        self.assertEqual(fields['max_time'], '5'); self.assertEqual(fields['max_count'], '201')
        self.assertEqual(fields['auto_finalize_ec'], '10000'); self.assertEqual(fields['auto_cancel'], '30')
        self.assertEqual(fields['allow_partial_results'], 'false')
        for body in ({'action':'start','query':'| outputlookup nope'}, {'action':'start','query':'| makeresults','earliest':'0'}):
            with self.assertRaises(ProviderError): runtime.job(body)
    def test_foreign_modified_expired_or_bare_sid_never_reaches_splunk(self):
        runtime = JobRuntime(); jobs = PreviewJobs(runtime)
        handle = jobs.start('| makeresults', '-15m')['handle']
        other = PreviewJobs(JobRuntime()); other.runtime.token = 'other-session'
        for service, candidate in ((jobs,'1234.56'), (jobs,handle.replace('-15m','-24h')), (other,handle)):
            before = len(service.runtime.calls)
            with self.assertRaises(ProviderError): service.poll(candidate)
            self.assertEqual(len(service.runtime.calls), before)
        with patch('preview_jobs.time.time', return_value=10**12), self.assertRaises(ProviderError) as error: jobs.cancel(handle)
        self.assertEqual(error.exception.status,410)
    def test_failed_jobs_are_cancelled_without_returning_raw_diagnostics(self):
        runtime = JobRuntime({'isFailed':'1', 'messages': ['PRIVATE EVENT VALUE']})
        with self.assertRaises(ProviderError) as error: runtime.preview({'query':'| makeresults'})
        self.assertNotIn('PRIVATE', str(error.exception)); self.assertEqual(runtime.calls[-1][2], {'action':'cancel'})
        runtime = JobRuntime(); runtime.messages = [{'type':'ERROR','text':'syntax error PRIVATE EVENT VALUE'}]
        with self.assertRaises(ProviderError) as error: runtime.preview({'query':'| makeresults'})
        self.assertNotIn('PRIVATE', str(error.exception)); self.assertIn('syntax', str(error.exception))
    def test_running_jobs_and_owner_checks(self):
        runtime = JobRuntime({'isDone':'0'}); jobs=PreviewJobs(runtime)
        handle=jobs.start('| makeresults','-15m')['handle']
        self.assertEqual(jobs.poll(handle), {'state':'running'})
        runtime.owner='bob'
        with self.assertRaises(ProviderError): jobs.poll(handle)
        self.assertFalse(any(call[0].endswith('/results') for call in runtime.calls))
    def test_aggregate_feedback_handles_native_diagnostic_shapes_without_raw_content(self):
        for messages in ('number of wildcards PRIVATE', {'message':'empty field specifiers PRIVATE'}, [{'msg':'number of wildcards PRIVATE'}]):
            runtime=JobRuntime({'isFailed':'1','messages':messages})
            with self.assertRaises(ProviderError) as error:runtime.preview({'query':'| makeresults'})
            self.assertIn('count AS alias',str(error.exception));self.assertNotIn('PRIVATE',str(error.exception))
    def test_missing_completion_fields_and_warnings_fail_closed(self):
        runtime = JobRuntime(); del runtime.meta['isFinalized']
        self.assertEqual(runtime.preview({'query':'| makeresults'})['state'],'partial')
        runtime = JobRuntime(); runtime.messages = [{'type':'WARN','text':'PRIVATE upstream warning'}]
        result = runtime.preview({'query':'| makeresults'})
        self.assertEqual(result['state'],'partial'); self.assertNotIn('PRIVATE',json.dumps(result))

    def test_ready_job_with_pending_results_is_polled_without_redispatch(self):
        runtime=JobRuntime(); original=runtime.request; pending=[True,True,False]
        def request(path,method='GET',fields=None,optional=False):
            if path.endswith('/results') and pending.pop(0):
                runtime.calls.append((path,method,fields));return {'resultsPending':True}
            return original(path,method,fields,optional)
        runtime.request=request
        with patch('preview_jobs.time.sleep'):
            result=runtime.preview({'query':'| makeresults'})
        self.assertEqual(result['state'],'complete')
        self.assertEqual(sum(path.endswith('/jobs') for path,_,_ in runtime.calls),1)
        self.assertEqual(sum(path.endswith('/results') for path,_,_ in runtime.calls),3)
        self.assertEqual(runtime.calls[-1][2],{'action':'cancel'})

    def test_pending_results_exhaust_existing_deadline_and_cancel(self):
        runtime=JobRuntime(); original=runtime.request
        runtime.request=lambda path,*args,**kwargs: {'resultsPending':True} if path.endswith('/results') else original(path,*args,**kwargs)
        with patch('preview_jobs.time.monotonic',side_effect=[0,0,10]),patch('preview_jobs.time.sleep'):
            with self.assertRaises(ProviderError) as error:runtime.preview({'query':'| makeresults'})
        self.assertEqual(error.exception.code,'preview_timeout')
        self.assertEqual(runtime.calls[-1][2],{'action':'cancel'})
