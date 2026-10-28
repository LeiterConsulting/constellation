"""Authored transport faults; no Splunk instance or network required."""
import socket,ssl,sys,types,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'splunk/constellation/bin'))
from native_transport import native_read_retry
from search_service import SearchService
from provider_service import ProviderError
from data_service import DataService

NS='/servicesNS/fixture-user/constellation'
class NativeTransportTests(unittest.TestCase):
    def test_splunk_connection_wrapper_keeps_read_budget_and_never_replays_mutations(self):
        class SplunkdConnectionException(Exception): pass
        for method,path,count in [('GET',NS+'/data/indexes',2),('POST',NS+'/search/v2/jobs/fixture_1/results',2),('POST',NS+'/search/v2/jobs',1),('POST','/servicesNS/nobody/constellation/constellation/aitk/infer',1)]:
            call=Mock(side_effect=SplunkdConnectionException('fixture-private timeout'))
            with self.assertRaises(SplunkdConnectionException):native_read_retry(call,path,NS,method,20)
            self.assertEqual(call.call_count,count)
        error=SplunkdConnectionException('fixture-private');error.statusCode=403
        call=Mock(side_effect=error)
        with self.assertRaises(SplunkdConnectionException):native_read_retry(call,NS+'/data/indexes',NS,'GET',20)
        self.assertEqual(call.call_count,1)
        rest=types.ModuleType('splunk.rest');rest.simpleRequest=Mock(side_effect=SplunkdConnectionException('fixture-private timeout'))
        splunk=types.ModuleType('splunk');splunk.rest=rest
        with patch.dict(sys.modules,{'splunk':splunk,'splunk.rest':rest}):
            with self.assertRaises(ProviderError)as caught:SearchService('fixture-user','fixture-session').request(NS+'/data/indexes')
        self.assertEqual(caught.exception.status,503);self.assertEqual(caught.exception.code,'splunk_transport')
        self.assertNotIn('fixture-private',str(caught.exception));self.assertNotIn('Simplify',str(caught.exception))
    def test_retries_read_once_with_remaining_deadline_and_same_identity(self):
        call=Mock(side_effect=[socket.gaierror(8,'fixture-private'),({'status':200},b'{}')]);clock=Mock(side_effect=[10,12,12])
        self.assertEqual(native_read_retry(call,NS+'/data/indexes',NS,'GET',20,clock=clock,sessionKey='fixture-session')[1],b'{}')
        self.assertEqual(call.call_count,2);self.assertEqual([c.kwargs['timeout']for c in call.call_args_list],[20,18])
        self.assertTrue(all(c.kwargs['sessionKey']=='fixture-session'for c in call.call_args_list))
    def test_owned_results_post_is_read_but_dispatch_and_other_posts_are_not(self):
        for path,safe in [(NS+'/search/v2/jobs/fixture_1/results',True),(NS+'/search/v2/jobs',False),(NS+'/search/v2/jobs/fixture_1/control',False),('/servicesNS/other/constellation/search/v2/jobs/fixture_1/results',False),('/servicesNS/nobody/constellation/constellation/aitk/infer',False)]:
            with self.subTest(path=path):
                call=Mock(side_effect=ConnectionResetError('fixture-private'))
                with self.assertRaises(ConnectionResetError):native_read_retry(call,path,NS,'POST',20)
                self.assertEqual(call.call_count,2 if safe else 1)
    def test_permissions_certificates_and_elapsed_deadline_are_not_retried(self):
        class Restricted(Exception):statusCode=403
        for error in (Restricted(),ssl.SSLCertVerificationError('fixture-private')):
            call=Mock(side_effect=error)
            with self.assertRaises(type(error)):native_read_retry(call,NS+'/data/indexes',NS,'GET',20)
            self.assertEqual(call.call_count,1)
        call=Mock(side_effect=TimeoutError());clock=Mock(side_effect=[10,31])
        with self.assertRaises(TimeoutError):native_read_retry(call,NS+'/data/indexes',NS,'GET',20,clock=clock)
        self.assertEqual(call.call_count,1)
    def test_stop_prevents_read_retry_and_retains_cancellation(self):
        call=Mock(side_effect=ConnectionResetError())
        with self.assertRaisesRegex(ProviderError,'Stopped'):native_read_retry(call,NS+'/data/indexes',NS,'GET',20,check_cancel=Mock(side_effect=ProviderError('Stopped',409,'author_cancelled')))
        self.assertEqual(call.call_count,1)
    def test_exhausted_native_transport_is_not_invalid_spl_and_never_echoes_details(self):
        rest=types.ModuleType('splunk.rest');rest.simpleRequest=Mock(side_effect=ConnectionResetError('fixture-private'))
        splunk=types.ModuleType('splunk');splunk.rest=rest
        with patch.dict(sys.modules,{'splunk':splunk,'splunk.rest':rest}):
            with self.assertRaises(ProviderError)as caught:SearchService('fixture-user','fixture-session').request(NS+'/data/indexes')
        self.assertEqual(rest.simpleRequest.call_count,2);self.assertEqual(caught.exception.status,503);self.assertEqual(caught.exception.code,'splunk_transport');self.assertNotIn('fixture-private',str(caught.exception))
    def test_search_validation_does_not_turn_transport_into_model_repair_feedback(self):
        runtime=Mock();runtime.preview.side_effect=ProviderError('Interrupted',503,'splunk_transport')
        profile={'baseQuery':'search index="fixture"','scope':{'index':'fixture','language':'spl','earliest':'-24h'},'fields':[]}
        source={'type':'ds.search','options':{'query':'search index="fixture" | stats count AS readings','queryParameters':{'earliest':'-24h','latest':'now'}}}
        with self.assertRaises(ProviderError)as caught:DataService(runtime).validate_searches({'dataSources':{'summary':source},'visualizations':{}},{},profile)
        self.assertEqual(caught.exception.code,'splunk_transport');self.assertEqual(runtime.preview.call_count,1)
