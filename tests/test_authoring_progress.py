import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from authoring_progress import AuthoringProgress, TTL
from provider_service import ProviderError
from quick_edit import quick_edit
from studio_contract import apply_changes


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = 1000
        self.control = AuthoringProgress('fixture-user', 'fixture-session', self.tmp.name, lambda: self.now)
    def start(self): return self.control.operation({'action': 'start'})['handle']
    def test_receipts_cross_instances_and_session_isolation(self):
        handle = self.start(); report = self.control.claim(handle)
        report('model', 1); self.now += 12; report('validate', 1)
        other = AuthoringProgress('fixture-user', 'fixture-session', self.tmp.name, lambda: self.now)
        state = other.operation({'action': 'poll', 'handle': handle})
        self.assertEqual(state['events'][-1], {'stage': 'validate', 'attempt': 1, 'seconds': 12})
        for user, token in [('other-user','fixture-session'), ('fixture-user','other-session')]:
            with self.assertRaises(ProviderError): AuthoringProgress(user, token, self.tmp.name).operation({'action':'poll','handle':handle})
        raw = Path(self.control.path(handle)).read_text()
        self.assertNotIn('fixture-user', raw); self.assertNotIn('fixture-session', raw)
        self.assertEqual(os.stat(self.control.path(handle)).st_mode & 0o777, 0o600)
    def test_cancel_cannot_be_overwritten_and_replay_never_runs(self):
        handle=self.start(); report=self.control.claim(handle); report('model',1)
        self.control.operation({'action':'cancel','handle':handle})
        for operation in (lambda: report('complete'), lambda: self.control.claim(handle)):
            with self.assertRaises(ProviderError) as error: operation()
            self.assertEqual(error.exception.code,'author_cancelled')
        self.assertEqual(self.control.operation({'action':'poll','handle':handle})['stage'],'cancelled')
        self.control.release(handle)
        second=self.start(); self.control.claim(second)
        with self.assertRaises(ProviderError): self.control.claim(second)
    def test_stop_before_author_and_expiry_release_capacity(self):
        handle=self.start(); self.control.operation({'action':'cancel','handle':handle})
        with self.assertRaises(ProviderError): self.control.claim(handle)
        active=[self.start(),self.start()]
        with self.assertRaises(ProviderError): self.start()
        self.now += TTL + 1
        with self.assertRaises(ProviderError): self.control.operation({'action':'poll','handle':active[0]})
        self.start()
        self.assertFalse(Path(self.control.path(handle)).exists())
    def test_aitk_and_preview_stop_release_native_jobs(self):
        from provider_adapters import AITKClient
        from preview_jobs import PreviewJobs
        runtime=Mock(user='fixture-user',token='fixture-session',namespace='/servicesNS/fixture-user/constellation')
        runtime.shared_aitk_complete.return_value = None
        runtime.check_cancel.side_effect=ProviderError('Stopped',409,'author_cancelled')
        runtime.request.side_effect=[{'entry':[{'content':{'capabilities':['apply_ai_commander_command']}}]}, {'sid':'fixture-sid'}, {}]
        request={'instructions':'synthetic','input':[], 'text':{'format':{'schema':{}}}}
        with self.assertRaises(ProviderError): AITKClient(runtime).complete({'connection':'fixture'},request)
        self.assertTrue(runtime.request.call_args.args[0].endswith('/control'))
        self.assertEqual(runtime.request.call_args.args[2],{'action':'cancel'})
        jobs=PreviewJobs(runtime)
        with unittest.mock.patch.object(jobs,'start',return_value={'handle':'fixture'}), unittest.mock.patch.object(jobs,'cancel') as cancel:
            with self.assertRaises(ProviderError): jobs.execute('| makeresults','-15m')
            cancel.assert_called_once_with('fixture')


class QuickEditTests(unittest.TestCase):
    def setUp(self):
        self.doc={'title':'Synthetic','description':'','visualizations':{'v':{'type':'splunk.line','title':'Before','dataSources':{'primary':'s'},'options':{'x':42},'futureProperty':True}},'dataSources':{'s':{'type':'ds.test','options':{'data':{'fields':[],'columns':[]}}}},'layout':{'type':'absolute','structure':[{'item':'v','position':{'x':0,'y':0,'w':500,'h':300}}]}}
    def test_exact_edit_preserves_every_unmentioned_property(self):
        original=copy.deepcopy(self.doc)
        result=apply_changes(self.doc,quick_edit('Change only this selected chart to an area chart and rename it "Temperature". Preserve its search, page placement, interactions and every other element.',self.doc,'v',[]))
        expected=copy.deepcopy(original);expected['visualizations']['v'].update(title='Temperature',type='splunk.area')
        self.assertEqual(result,expected);self.assertEqual(self.doc,original)
    def test_ambiguous_and_additional_requests_never_short_circuit(self):
        for prompt in ['Rename only the selected chart to "Name". Also change the search.', 'Change only this selected chart to an area chart.', 'Rename the dashboard to "Name"']:
            self.assertIsNone(quick_edit(prompt,self.doc,'v',[]))
        self.assertIsNone(quick_edit('Rename only the selected chart to "Name"',self.doc,'v',[{'data':'synthetic'}]))
