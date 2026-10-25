import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from aitk_diagnostics import failure_guidance


class DiagnosticsTests(unittest.TestCase):
    def runtime(self, text):
        class Runtime:
            user = 'fixture-author'
            calls = []
            def aitk_job_log(self, path):
                self.calls.append(path)
                return text
        return Runtime()

    def test_private_connection_is_actionable_without_echoing_native_content(self):
        r = self.runtime('ERROR No configuration found for llm connection: private-fixture\nsecret fixture-only')
        message, status, code = failure_guidance(r, '/servicesNS/fixture-author/Splunk_ML_Toolkit/search/jobs/fixture.1')
        self.assertEqual((status, code), (403, 'aitk_connection_unavailable'))
        self.assertIn('your Splunk user', message)
        self.assertNotIn('private-fixture', message)
        self.assertNotIn('secret', message)

    def test_cannot_read_another_user_job_or_an_arbitrary_resource(self):
        r = self.runtime('No configuration found for llm connection')
        for path in ['/servicesNS/other/Splunk_ML_Toolkit/search/jobs/job', '/servicesNS/fixture-author/Splunk_ML_Toolkit/search/jobs/job/search.log', '/services/storage/passwords']:
            self.assertEqual(failure_guidance(r, path)[1], 502)
        self.assertEqual(r.calls, [])

    def test_unknown_error_remains_generic_and_log_failure_does_not_replace_error(self):
        r = self.runtime('private prompt fixture-only')
        self.assertNotIn('fixture-only', failure_guidance(r, '/servicesNS/fixture-author/Splunk_ML_Toolkit/search/jobs/job')[0])
        r.aitk_job_log = lambda path: (_ for _ in ()).throw(RuntimeError('private body'))
        self.assertEqual(failure_guidance(r, '/servicesNS/fixture-author/Splunk_ML_Toolkit/search/jobs/job')[2], 'aitk_inference_failed')

    def test_known_provider_limits_return_fixed_guidance(self):
        for text, code in [('insufficient_quota private account', 'aitk_provider_quota'), ('maximum context length private prompt', 'aitk_context_limit')]:
            r = self.runtime(text)
            self.assertEqual(failure_guidance(r, '/servicesNS/fixture-author/Splunk_ML_Toolkit/search/jobs/job')[2], code)
