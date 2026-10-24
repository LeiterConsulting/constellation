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
