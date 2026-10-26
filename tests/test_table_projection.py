import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from table_projection import validate_requested_columns, verified_requested_projection
from studio_contract import apply_changes
from test_drafts_and_data import blank
from provider_service import ProviderError


class TableProjectionTests(unittest.TestCase):
    def setUp(self):
        self.doc = {'visualizations': {'table': {'type': 'splunk.table', 'dataSources': {'primary': 'source'}, 'options': {'table': '> primary | frameBySeriesNames("device", "count")'}}}}
        self.receipts = [{'source': 'source', 'fields': ['device', 'count', 'host_count']}]

    def test_returned_but_hidden_requested_metric_is_rejected(self):
        with self.assertRaises(ProviderError) as error:
            validate_requested_columns('Add dc(host) AS host_count to this table.', 'table', self.doc, self.receipts)
        self.assertEqual(error.exception.code, 'table_projection')
        self.assertIn('hides', str(error.exception))

    def test_repaired_projection_and_default_full_frame_are_accepted(self):
        for value in ['> primary | frameBySeriesNames("device", "count", "host_count")', '> primary']:
            self.doc['visualizations']['table']['options']['table'] = value
            validate_requested_columns('Add dc(host) AS host_count.', 'table', self.doc, self.receipts)

    def test_requested_alias_must_be_in_verified_output(self):
        with self.assertRaises(ProviderError):
            validate_requested_columns('Include dc(host) AS absent.', 'table', self.doc, self.receipts)

    def test_unrelated_format_hidden_helper_and_unverified_output_unchanged(self):
        before = copy.deepcopy(self.doc)
        for prompt, selected, receipts in [('Display count as a whole number, time as a readable date.', 'table', self.receipts), ('Add hidden helper dc(host) AS host_count.', 'table', self.receipts), ('Add dc(host) AS host_count.', '', self.receipts), ('Add dc(host) AS host_count.', 'table', [])]:
            validate_requested_columns(prompt, selected, self.doc, receipts)
        self.assertEqual(self.doc, before)

    def test_verified_visible_metric_repair_preserves_existing_columns_and_other_work(self):
        self.doc=dict(blank()['definition'], **self.doc)
        self.doc['dataSources']={'source':{'type':'ds.search','options':{'query':'| makeresults'}}}
        before=copy.deepcopy(self.doc)
        changes=verified_requested_projection('Add dc(host) AS host_count.', 'table', self.doc, self.receipts)
        fixed=apply_changes(self.doc,changes)
        self.assertEqual(fixed['visualizations']['table']['options']['table'], '> primary | frameBySeriesNames("device", "count", "host_count")')
        self.assertEqual(self.doc,before)
        validate_requested_columns('Add dc(host) AS host_count.', 'table', fixed, self.receipts)
        self.assertEqual(verified_requested_projection('Add dc(host) AS host_count.', 'table', fixed, self.receipts),[])

    def test_projection_repair_does_not_infer_outputs_or_rewrite_complex_bindings(self):
        for binding in ('> primary', '> primary | frameBySeriesNames("device", "count") | filter(x)', '> primary | frameBySeriesNames("absent")', '> primary | frameBySeriesNames("device", token)', '> secondary | frameBySeriesNames("device")'):
            self.doc['visualizations']['table']['options']['table']=binding
            self.assertEqual(verified_requested_projection('Add dc(host) AS host_count.', 'table', self.doc, self.receipts),[])
        for prompt,receipts in [('Add hidden helper dc(host) AS host_count.',self.receipts),('Add dc(host) AS absent.',self.receipts),('Add dc(host) AS host_count.',[])]:
            self.assertEqual(verified_requested_projection(prompt,'table',self.doc,receipts),[])

    def test_agent_repairs_verified_projection_without_another_model_or_search(self):
        from test_reliability_journey import Provider, Runtime, reply
        from agent_service import AgentService
        class Outputs(Runtime):
            def preview(self, body):
                self.calls.append(body)
                return {'state':'complete','fields':[{'name':name} for name in ('count','max_duration')], 'results':[{'count':'12','max_duration':'42'}]}
        doc=blank()['definition'];doc.update(visualizations={'table':{'type':'splunk.table','title':'Observations','options':{'table':'> primary | frameBySeriesNames("count")'},'dataSources':{'primary':'source'}}},dataSources={'source':{'type':'ds.search','options':{'query':'search index="fixture_index" | stats count','queryParameters':{'earliest':'-24h','latest':'now'}}}},layout={'type':'grid','structure':[{'item':'table'}]})
        provider=Provider([reply([{'op':'search','id':'source','pipeline':'| stats count max(duration) AS max_duration'}])]);runtime=Outputs()
        result=AgentService(provider,runtime).assist({'prompt':'Add max(duration) AS max_duration to this selected table.', 'definition':doc,'revision':0,'selected':'table','dataContext':blank()['dataContext']})
        fixed=apply_changes(doc,result['changes'])
        self.assertEqual(result['recovery']['modelCalls'],1)
        # Original focused receipt plus changed query; projection reuses both.
        self.assertEqual(result['recovery']['queryChecks'],2)
        self.assertEqual(len([call for call in runtime.calls if isinstance(call,dict)]),2)
        self.assertIn('"max_duration"',fixed['visualizations']['table']['options']['table'])
        self.assertEqual(fixed['layout'],doc['layout']);self.assertEqual(doc['visualizations']['table']['options']['table'],'> primary | frameBySeriesNames("count")')
