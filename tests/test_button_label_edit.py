"""Exact labels never change navigation, geometry or unrelated native work."""
import copy
import unittest
from test_drafts_and_data import blank
from studio_contract import apply_changes
from quick_edit import quick_edit
from provider_service import ProviderError

PROMPT = 'Rename only this selected existing return button to "Overview" and keep its destination Overview. Preserve its position, size and every other element and interaction.'


class ButtonLabelTests(unittest.TestCase):
    def test_agent_label_only_edit_needs_neither_model_nor_search_authority(self):
        from agent_service import AgentService
        from test_reliability_journey import Provider
        class NoRuntime:
            def __getattr__(self, name): raise AssertionError('Unexpected runtime access')
        provider = Provider([])
        result = AgentService(provider, NoRuntime()).assist({'prompt': PROMPT, 'definition': self.document(), 'selected': 'back', 'revision': 2})
        self.assertEqual(provider.requests, []); self.assertEqual(result['recovery']['modelCalls'], 0)
        self.assertEqual(result['recovery']['queryChecks'], 0); self.assertIn('button label', result['message'])

    def document(self):
        doc = blank()['definition']; pid = 'layout_main'
        doc['layout'] = {'globalInputs': [], 'tabs': {'items': [{'label': 'Overview', 'layoutId': pid}]}, 'layoutDefinitions': {pid: {'type': 'absolute', 'options': {'width': 1200, 'height': 800}, 'structure': []}}}
        doc['inputs'] = {'back': {'type': 'input.button', 'options': {'label': 'Back to Overview', 'unknown': 'retained'}, 'eventHandlers': [
            {'type': 'drilldown.switchToTab', 'options': {'tabId': pid}}, {'type': 'drilldown.setToken', 'options': {'tokens': [{'token': 'chosen', 'value': '*'}]}}]}}
        doc['layout']['layoutDefinitions'][pid]['structure'].append({'item': 'back', 'type': 'input', 'position': {'x': 20, 'y': 20, 'w': 240, 'h': 80}})
        return doc

    def test_literal_rename_preserves_every_other_byte_of_the_native_document(self):
        doc = self.document(); before = copy.deepcopy(doc); expected = copy.deepcopy(doc); expected['inputs']['back']['options']['label'] = 'Overview'
        self.assertEqual(apply_changes(doc, quick_edit(PROMPT, doc, 'back', [])), expected)
        self.assertEqual(doc, before)

    def test_different_target_compound_files_and_duplicate_names_use_normal_authoring(self):
        doc = self.document()
        for prompt in [PROMPT.replace('destination Overview', 'destination Details'), PROMPT + ' Add a chart.', PROMPT.replace('size and every', 'size but change every')]:
            self.assertIsNone(quick_edit(prompt, doc, 'back', []))
        self.assertIsNone(quick_edit(PROMPT, doc, 'back', [{}]))
        doc['layout']['tabs']['items'].append({'label': 'Overview', 'layoutId': 'ambiguous'})
        self.assertIsNone(quick_edit(PROMPT, doc, 'back', []))

    def test_long_label_fails_without_resizing_or_mutating(self):
        doc = self.document(); before = copy.deepcopy(doc)
        with self.assertRaises(ProviderError) as caught: quick_edit(PROMPT.replace('to "Overview"', 'to "' + 'W' * 100 + '"'), doc, 'back', [])
        self.assertEqual(caught.exception.code, 'button_label_fit'); self.assertEqual(doc, before)
