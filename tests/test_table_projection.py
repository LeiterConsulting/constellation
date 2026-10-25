import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from table_projection import validate_requested_columns
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
