"""Authored CSV rule fixtures, never live fields, values or event data."""
import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from lookup_filter import filter_fields
from lookup_matching import matching_options, validate_matching_fields
from portable_knowledge import PortableKnowledge, bundle_fingerprint, import_lookups, validate_bundle
from dashboard_dependencies import DashboardDependencies
from provider_service import ProviderError
from test_portable_knowledge import Runtime, document, bundled


class FilterTests(unittest.TestCase):
    def test_explicit_groups_comparisons_and_literals_preserve_field_meaning(self):
        cases = [('room="cold" AND (rank>=2 OR NOT mode=hidden)', {'room', 'rank', 'mode'}),
                 ('NOT NOT (reading < -1.5e2 OR reading >= +0.5)', {'reading'}),
                 ('host=*.example.test AND label="OR AND NOT"', {'host', 'label'}),
                 ('room!="warm" AND rank<=2 AND value>.25', {'room', 'rank', 'value'}),
                 (r'label="quoted \"text\" and \\ path"', {'label'}),
                 ('site.name="caf\u00e9" OR site-name=""', {'site.name', 'site-name'})]
        for text, fields in cases:
            with self.subTest(text=text): self.assertEqual(filter_fields(text), fields)
    def test_pipeline_functions_dynamic_and_ambiguous_syntax_are_refused(self):
        for text in ('', ' ', 'room=', 'room==cold', 'a=b c=d', 'a=b and c=d', 'a=b OR',
                     'a=b | outputlookup other.csv', 'a=$token$', 'a=`macro`', 'a=[search x]',
                     'a=b; x=y', 'isnull(a)', 'a IN (b,c)', 'a=b XOR c=d', '(a=b', 'a=b)',
                     'a="unterminated', 'a="line\nvalue"', r'a="bad\q"', 'AND=1', 'a=NOT'):
            with self.subTest(text=text), self.assertRaises(ProviderError): filter_fields(text)
    def test_size_depth_term_and_token_budgets_are_bounded(self):
        for text in ('a="'+'x'*2000+'"', '('*18+'a=1'+')'*18, ' AND '.join('a=1' for _ in range(65)), 'NOT '*257+'a=1'):
            with self.assertRaises(ProviderError): filter_fields(text)


class TemporalTests(unittest.TestCase):
    def test_temporal_default_match_count_differs_from_static_default(self):
        self.assertEqual(matching_options({'time_field': 'stamp', 'time_format': '%s.%Q', 'max_matches': '1', 'max_offset_secs': 2000000000, 'min_offset_secs': 0}), {'time_field': 'stamp'})
        self.assertEqual(matching_options({'max_matches': '1'}), {'max_matches': '1'})
        self.assertEqual(matching_options({'time_field': 'stamp', 'max_matches': 100}), {'time_field': 'stamp', 'max_matches': '100'})
    def test_native_integer_offsets_and_literal_formats_are_canonical(self):
        source = {'time_field': 'stamp', 'time_format': '%Y-%m-%dT%H:%M:%S%z', 'min_offset_secs': 60, 'max_offset_secs': 600, 'filter': 'mode="active" AND rank>=2'}
        expected = dict(source, min_offset_secs='60', max_offset_secs='600')
        self.assertEqual(matching_options(source), expected);self.assertEqual(matching_options(expected, strict=True), expected)
        validate_matching_fields(expected, ['stamp', 'mode', 'rank'])
    def test_inconsistent_or_orphaned_offsets_invalid_formats_and_fields_refuse(self):
        for value in ({'time_field': 'bad field'}, {'time_field': '$stamp$'}, {'time_format': '%s'},
                      {'min_offset_secs': '1'}, {'max_offset_secs': '600'},
                      {'time_field': 'stamp', 'max_offset_secs': '-1'}, {'time_field': 'stamp', 'max_offset_secs': '2000000001'},
                      {'time_field': 'stamp', 'min_offset_secs': '601', 'max_offset_secs': '600'},
                      {'time_field': 'stamp', 'min_offset_secs': True}, {'time_field': 'stamp', 'time_format': '%s\x00'},
                      {'time_field': 'stamp', 'time_format': 'x'*257}):
            with self.subTest(value=value), self.assertRaises(ProviderError): matching_options(value)
        for options in ({'time_field': 'absent'}, {'filter': 'absent=1'}, {'match_type': 'CIDR(absent)'}):
            with self.assertRaises(ProviderError): validate_matching_fields(options, ['stamp'])
    def test_noncanonical_portable_defaults_types_and_offsets_refuse(self):
        for value in ({'time_field': 'stamp', 'max_matches': '1'}, {'time_field': 'stamp', 'time_format': '%s.%Q'},
                      {'time_field': 'stamp', 'min_offset_secs': '0'}, {'time_field': 'stamp', 'max_offset_secs': '00600'},
                      {'time_field': 'stamp', 'max_offset_secs': 600}, {'filter': ''}):
            with self.assertRaises(ProviderError): matching_options(value, strict=True)


class TransferRuleTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime();self.entry = DashboardDependencies(self.runtime).entry
    def test_filtered_export_keeps_complete_backing_rows_and_exact_predicate(self):
        self.runtime.objects[('data/transforms/lookups', 'rooms')]['filter'] = 'room="cold"'
        item = PortableKnowledge(self.runtime, self.entry).lookup('rooms', include=True)
        self.assertEqual(item['rows'], bundled()['rows']);self.assertEqual(item['matching'], {'filter': 'room="cold"'})
        self.assertIn(('complete-csv-snapshot', 'rooms.csv', None), self.runtime.calls)
        self.assertEqual(validate_bundle([item], document('| inputlookup rooms')), [item])
        item['matching']['filter'] = 'room="warm"'
        with self.assertRaisesRegex(ProviderError, 'checksum'): validate_bundle([item], document('| inputlookup rooms'))
    def test_filtered_temporal_import_preserves_native_rules_and_unrelated_work(self):
        item = bundled();item['matching'] = {'filter': 'room="cold"', 'time_field': 'label', 'time_format': '%s', 'max_offset_secs': '600'};item['fingerprint'] = bundle_fingerprint(item)
        before = copy.deepcopy(document())
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, SPLUNK_HOME=root):
            result = DashboardDependencies(self.runtime).operation({'action': 'import', 'definition': before, 'lookups': [item]})
        self.assertEqual(before, document());self.assertEqual(result['definition']['future'], before['future'])
        post = next(fields for path, method, fields in self.runtime.calls if path.endswith('/data/transforms/lookups') and method == 'POST')
        self.assertEqual({key: post[key] for key in item['matching']}, item['matching'])
    def test_missing_filter_or_timestamp_columns_block_before_writes(self):
        for options in ({'filter': 'absent=1'}, {'time_field': 'absent'}):
            item = bundled();item['matching'] = options;item['fingerprint'] = bundle_fingerprint(item)
            with self.assertRaises(ProviderError): import_lookups(self.runtime, document(), [item], self.entry)
        self.assertEqual(self.runtime.uploads, [])
    def test_filter_changes_block_reference_only_import(self):
        self.runtime.objects[('data/transforms/lookups', 'rooms')]['filter'] = 'room="cold"'
        doc = document('| inputlookup rooms');receipt = DashboardDependencies(self.runtime).operation({'action': 'export', 'definition': doc})
        self.runtime.objects[('data/transforms/lookups', 'rooms')]['filter'] = 'room="warm"'
        self.assertTrue(DashboardDependencies(self.runtime).operation({'action': 'check', 'definition': doc, 'dependencies': receipt['dependencies']})['blocked'])


if __name__ == '__main__': unittest.main()
