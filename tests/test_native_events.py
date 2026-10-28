"""Exact literal events preserve unrelated native work and cannot infer payloads."""
import copy
import unittest
from test_drafts_and_data import blank
from native_events import exact_event_set
from studio_contract import apply_changes
from studio_features import validate_features
from provider_service import ProviderError

PROMPT='For only the selected Sankey diagram, add a native node.click interaction that sets the token selected_stage to the literal string picked. Use options.events to constrain it to node.click. Preserve all searches, page structure and unrelated work.'
class NativeEventTests(unittest.TestCase):
    def doc(self):
        doc=blank()['definition'];doc['visualizations']['v']={'type':'splunk.sankey','options':{'future':{'preserved':True}},'eventHandlers':[{'type':'future.preserve','options':{'unrelated':'yes'}}]};return doc
    def test_exact_literal_compiles_only_handlers_and_is_idempotent(self):
        doc=self.doc();before=copy.deepcopy(doc);reply=exact_event_set(PROMPT,'v',doc,[]);result=apply_changes(doc,reply['changes'])
        validate_features(result,doc,{'version':'10.4.4'});self.assertEqual(doc,before)
        expected=copy.deepcopy(before);expected['visualizations']['v']['eventHandlers'].append({'type':'drilldown.setToken','options':{'events':['node.click'],'tokens':[{'token':'selected_stage','value':'picked'}]}})
        self.assertEqual(result,expected);self.assertEqual(exact_event_set(PROMPT,'v',result,[])['changes'],[])
    def test_unsupported_mismatched_dynamic_compound_and_attachment_requests_keep_model_path(self):
        doc=self.doc()
        for prompt in (PROMPT.replace('node.click','cell.click'),PROMPT.replace('Sankey diagram','timeline'),PROMPT.replace('literal string picked','clicked field value'),PROMPT+' Also rename the chart.',PROMPT+' Preserve everything except the source.',PROMPT.replace('Preserve all searches','Do not preserve all searches'),PROMPT.replace('string picked','string "$other_token$"'),PROMPT.replace('token selected_stage','token __proto__')):
            self.assertIsNone(exact_event_set(prompt,'v',doc,[]),prompt)
        self.assertIsNone(exact_event_set(PROMPT,'v',doc,[{'type':'input_image'}]));self.assertIsNone(exact_event_set(PROMPT,'missing',doc,[]))
    def test_quote_content_and_selected_identity_remain_literal(self):
        doc=self.doc();reply=exact_event_set(PROMPT.replace('string picked','string "two words"'),'v',doc,[])
        result=apply_changes(doc,reply['changes']);self.assertEqual(result['visualizations']['v']['eventHandlers'][-1]['options']['tokens'][0]['value'],'two words')
