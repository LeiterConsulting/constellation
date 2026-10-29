"""Synthetic compilation keeps report references and unrelated sources intact."""
import copy
import unittest
from test_search_context import document
from report_actions import eligible, compile_plan
from studio_contract import apply_changes
from provider_service import ProviderError


class ReportActionTests(unittest.TestCase):
    def setUp(self):
        self.doc = document()
        self.context = {'focus': {'id': 'metric'}, 'reportTransform': {'parentId': 'chain', 'freshId': 'new_chain'},
                        'dataProfile': {'scope': {'report': {'ref': 'Fixture report', 'app': 'search'}}}}
    def test_per_row_plan_preserves_sources_unknown_options_and_selection(self):
        original = copy.deepcopy(self.doc)
        actions = compile_plan([{'op': 'reportTransform', 'pipeline': '| eval reading_count=1 | table device value reading_count'}], self.doc, self.context)
        changed = apply_changes(self.doc, actions)
        self.assertEqual(self.doc, original)
        self.assertEqual({key: changed['dataSources'][key] for key in original['dataSources']}, original['dataSources'])
        self.assertEqual(changed['dataSources']['new_chain']['options']['extend'], 'chain')
        before = copy.deepcopy(original['visualizations']);before['metric']['dataSources']['primary'] = 'new_chain'
        self.assertEqual(changed['visualizations'], before)
        self.assertEqual(changed['layout'], original['layout'])
    def test_collision_stale_parent_context_and_unsupported_actions_fail_before_changes(self):
        action = [{'op': 'reportTransform', 'pipeline': '| eval reading_count=1'}]
        for plan in ({'parentId': 'chain', 'freshId': 'chain'}, {'parentId': 'report', 'freshId': 'new_chain'}):
            context = dict(self.context, reportTransform=plan)
            with self.assertRaises(ProviderError): compile_plan(action, self.doc, context)
        for actions in ([], [{'op': 'search', 'pipeline': '| stats count'}], [{'op': 'reportTransform', 'pipeline': 'eval value=1'}]):
            with self.assertRaises(ProviderError): compile_plan(actions, self.doc, self.context)
    def test_eligibility_retains_general_native_path_for_other_requests(self):
        prompt = 'Add a numeric field reading_count for each existing row.'
        self.assertTrue(eligible(prompt, 'metric', self.doc, self.context['dataProfile'], []))
        for request, selected, profile, files in [('Rename the table', 'metric', self.context['dataProfile'], []), (prompt, '', self.context['dataProfile'], []), (prompt, 'metric', {'scope': {}}, []), (prompt, 'metric', self.context['dataProfile'], [{}])]:
            self.assertFalse(eligible(request, selected, self.doc, profile, files))
        for extra in (' Create a new page.', ' Add a dropdown.', ' Change the title.', ' Format the cells.', ' Add a trend chart.'):
            self.assertFalse(eligible(prompt+extra, 'metric', self.doc, self.context['dataProfile'], []))
        self.assertTrue(eligible(prompt+' Preserve every other page, input and chart.', 'metric', self.doc, self.context['dataProfile'], []))
        for clause in (' Keep existing charts and add a page.', '; preserve every source; change the title.', ' Retain all inputs. Create another chart.'):
            self.assertFalse(eligible(prompt+clause, 'metric', self.doc, self.context['dataProfile'], []))
