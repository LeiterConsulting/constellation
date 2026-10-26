"""Exact placement preserves imported content and falls back on ambiguity."""
import copy
import unittest
from test_drafts_and_data import blank
from quick_edit import quick_edit
from studio_contract import apply_changes


PROMPT = ('Make only this selected summary table full width below the trend on Overview. '
          'Keep its existing height and every query, column, page, drilldown and other element unchanged.')


class ExactLayoutTests(unittest.TestCase):
    def document(self):
        doc = blank()['definition']
        doc['visualizations'] = {'trend': {'type': 'splunk.line', 'future': 'keep'},
                                 'table': {'type': 'splunk.table', 'future': {'keep': True}}}
        doc['dataSources'] = {'existing': {'type': 'ds.search', 'options': {'query': 'search index=fixture_index'}}}
        doc['layout']['layoutDefinitions'] = {'main': {'type': 'absolute', 'options': {'width': 1200, 'height': 500, 'future': 'keep'},
            'structure': [{'item': 'table', 'type': 'block', 'future': True, 'position': {'x': 620, 'y': 20, 'w': 560, 'h': 360, 'future': 9}},
                          {'item': 'trend', 'type': 'block', 'position': {'x': 20, 'y': 20, 'w': 560, 'h': 360}}]}}
        doc['layout']['tabs'] = {'items': [{'layoutId': 'main', 'label': 'Overview'}]}
        return doc

    def test_exact_move_fits_both_charts_and_preserves_every_other_property(self):
        doc = self.document(); before = copy.deepcopy(doc)
        result = apply_changes(doc, quick_edit(PROMPT, doc, 'table', []))
        expected = copy.deepcopy(before)
        page = expected['layout']['layoutDefinitions']['main']
        page['structure'][0]['position'].update(x=20, y=400, w=1160)
        page['options']['height'] = 780
        self.assertEqual(result, expected)
        self.assertEqual(doc, before)

    def test_optional_growth_clause_and_existing_tall_canvas(self):
        doc = self.document(); doc['layout']['layoutDefinitions']['main']['options']['height'] = 1200
        changes = quick_edit(PROMPT + ' Grow the Overview canvas height if needed to contain the moved table.', doc, 'table', [])
        result = apply_changes(doc, changes)
        self.assertEqual(len(changes), 1)
        self.assertEqual(result['layout']['layoutDefinitions']['main']['options']['height'], 1200)

    def test_other_goals_files_or_page_names_use_normal_authoring(self):
        doc = self.document()
        for prompt in (PROMPT + ' Also add a KPI.', PROMPT.replace('Overview', 'Details'),
                       PROMPT.replace('existing height', 'new height'), 'Move this chart below that one.'):
            with self.subTest(prompt=prompt): self.assertIsNone(quick_edit(prompt, doc, 'table', []))
        self.assertIsNone(quick_edit(PROMPT, doc, 'table', [{'data': 'synthetic'}]))

    def test_complex_conditional_multi_page_or_unbounded_geometry_uses_normal_authoring(self):
        for case in ('extra', 'conditional', 'multi', 'overflow'):
            doc = self.document(); page = doc['layout']['layoutDefinitions']['main']
            if case == 'extra': page['structure'].append({'item': 'another'})
            if case == 'conditional': doc['visualizations']['trend']['containerOptions'] = {'visibility': {'showConditions': ['t']}}
            if case == 'multi': doc['layout']['layoutDefinitions']['other'] = copy.deepcopy(page)
            if case == 'overflow': page['structure'][1]['position']['y'] = 19990
            with self.subTest(case=case): self.assertIsNone(quick_edit(PROMPT, doc, 'table', []))
