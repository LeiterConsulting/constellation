"""Synthetic lookup/macro migration and privilege boundaries; no live data."""
import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from portable_knowledge import PortableKnowledge, csv_payload, fingerprint, import_lookups, validate_bundle, table_fingerprint, bundle_fingerprint
from lookup_matching import matching_options, validate_matching_fields
from search_references import macro_calls, lookup_calls, replace_lookups
from search_service import SearchService, read_only_query
from dashboard_dependencies import DashboardDependencies
from provider_service import ProviderError
from test_drafts_and_data import blank


class Runtime(SearchService):
    def __init__(self):
        super().__init__('fixture_author', 'fixture-session')
        self.objects = {('configs/conf-macros', 'base'): {'definition': 'search index=fixture'},
                        ('configs/conf-macros', 'cutoff(2)'): {'definition': 'where $field$ <= $limit$', 'args': 'field,limit'},
                        ('configs/conf-macros', 'nested'): {'definition': '`base` | `cutoff(temp,150)`'},
                        ('data/lookup-table-files', 'rooms.csv'): {},
                        ('data/transforms/lookups', 'rooms'): {'type': 'file', 'filename': 'rooms.csv', 'fields_list': 'room,label', 'fields_array': ['room', 'label']}}
        self.rows = {'state': 'complete', 'warning': '', 'fields': [{'name': 'room'}, {'name': 'label'}], 'results': [{'room': 'cold', 'label': 'Freezer'}, {'room': 'warm', 'label': 'Kitchen'}]}
        self.calls, self.uploads, self.metadata_acl = [], [], {'owner': self.user, 'app': 'constellation', 'sharing': 'user'}
        self.fail_write = False
        self.can_upload = True
    def datasets(self): return {'indexes': [{'name': 'fixture'}]}
    def request(self, path, method='GET', fields=None, optional=False):
        from urllib.parse import unquote
        self.calls.append((path, method, fields))
        if path == '/services/authentication/current-context': return {'entry': [{'content': {'capabilities': ['upload_lookup_files'] if self.can_upload else []}}]}
        base = self.namespace + '/'
        if method == 'POST':
            if path.endswith('/data/transforms/lookups'):
                self.objects[('data/transforms/lookups', fields['name'])] = dict(fields, type='file')
                self.objects[('data/transforms/lookups', fields['name'])].pop('name')
                return {'entry': []}
            self.uploads.append((fields['name'], Path(fields['eai:data']).read_text()))
            if self.fail_write: raise ProviderError('synthetic delivery interruption', 503)
            self.objects[('data/lookup-table-files', fields['name'])] = {}
            return {'entry': []}
        resource, _, name = path[len(base):].rpartition('/')
        content = self.objects.get((resource, unquote(name)))
        return {'entry': [] if content is None else [{'name': unquote(name), 'content': copy.deepcopy(content), 'acl': self.metadata_acl}]}
    def execute(self, query, earliest='-15m'):
        self.calls.append(('bounded-current-user', query, earliest)); return copy.deepcopy(self.rows)
    def lookup_snapshot(self, filename):
        self.calls.append(('complete-csv-snapshot', filename, None));return copy.deepcopy(self.rows)


def document(query='search index=fixture | lookup rooms.csv room OUTPUT label | stats count by label'):
    doc = blank()['definition'];doc['future'] = {'keep': True}
    doc['dataSources'] = {'s': {'type': 'ds.search', 'future': 17, 'options': {'query': query}}}
    return doc


def bundled():
    data = {'fields': ['room', 'label'], 'rows': [['cold', 'Freezer'], ['warm', 'Kitchen']]}
    return dict(kind='lookup', name='rooms.csv', app='constellation', **data, fingerprint=fingerprint(data))


class ReferenceTests(unittest.TestCase):
    def test_table_readback_ignores_header_order_but_preserves_row_order_and_values(self):
        self.assertEqual(table_fingerprint(['b', 'a'], [['B', 'A']]), table_fingerprint(['a', 'b'], [['A', 'B']]))
        self.assertNotEqual(table_fingerprint(['a'], [['1'], ['2']]), table_fingerprint(['a'], [['2'], ['1']]))
    def test_quote_aware_macro_arity_and_literal_lookup_spans(self):
        calls = macro_calls('`cutoff(temp,if(a,b,c))` | eval note="`ignored`"')
        self.assertEqual(calls[0][2:], ('cutoff(2)', ['temp', 'if(a,b,c)']))
        query = 'search index=fixture |  lookup local=true rooms.csv room OUTPUT label | eval note="rooms.csv | lookup fake room"'
        refs = lookup_calls(query);self.assertEqual(len(refs), 1)
        self.assertEqual(query[refs[0][0]:refs[0][1]], 'rooms.csv')
        replaced = replace_lookups(query, {'rooms.csv': 'fresh.csv'})
        self.assertIn('local=true fresh.csv', replaced);self.assertIn('note="rooms.csv | lookup fake room"', replaced)
        self.assertEqual(replace_lookups('|inputlookup rooms.csv', {'rooms.csv': 'new.csv'}), '|inputlookup new.csv')
    def test_malformed_dynamic_and_unbalanced_references_fail(self):
        for query in ('`bad', '`cutoff(a,)`', '`cutoff(a,if(b,c))oops`', '`cutoff(a,$token$)`'):
            with self.subTest(query=query), self.assertRaises(ProviderError): macro_calls(query)
        for query in ('| lookup $table$ key', '| inputlookup ../private.csv', '| inputlookup "a b.csv"'):
            with self.assertRaises(ProviderError): lookup_calls(query)


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime();self.entry = DashboardDependencies(self.runtime).entry
    def test_recursive_parameterized_macro_expansion_is_read_only_and_preserves_original(self):
        knowledge = PortableKnowledge(self.runtime, self.entry)
        self.assertEqual(knowledge.expand('`nested` | stats avg(temp)'), 'search index=fixture | where temp <= 150 | stats avg(temp)')
        self.assertEqual({x[1] for x in knowledge.receipts}, {'nested', 'base', 'cutoff(2)'})
        self.assertTrue(all(method == 'GET' for _, method, _ in self.runtime.calls))
        self.assertIn('`base`', self.runtime.objects[('configs/conf-macros', 'nested')]['definition'])
    def test_cycles_eval_validation_missing_args_and_size_are_refused(self):
        for content in ({'definition': '`bad`'}, {'definition': '1+1', 'iseval': '1'}, {'definition': 'stats count', 'validation': 'isint(x)'}, {'definition': 'eval x=$unknown$'}, {'definition': 'x' * 8001}):
            self.runtime.objects[('configs/conf-macros', 'bad')] = content
            with self.subTest(content=list(content)), self.assertRaises(ProviderError): PortableKnowledge(self.runtime, self.entry).expand('`bad`')
        with self.assertRaises(ProviderError): PortableKnowledge(self.runtime, self.entry).expand('`absent`')
    def test_macro_writes_never_reach_dispatch_and_lookup_requires_static_metadata(self):
        self.runtime.objects[('configs/conf-macros', 'bad')] = {'definition': '| collect index=fixture'}
        with self.assertRaises(ProviderError): self.runtime.guarded_query('`bad`')
        self.runtime.guarded_query('| inputlookup rooms.csv')
        self.runtime.objects[('data/transforms/lookups', 'external')] = {'type': 'external', 'external_cmd': 'script', 'filename': 'rooms.csv'}
        with self.assertRaises(ProviderError): self.runtime.guarded_query('| inputlookup external')
        self.runtime.objects[('data/transforms/lookups', 'rooms.csv')] = {'type': 'external', 'external_cmd': 'script', 'filename': 'rooms.csv'}
        with self.assertRaises(ProviderError): self.runtime.guarded_query('| inputlookup rooms.csv')
        self.assertFalse(any(call[0] == 'bounded-current-user' for call in self.runtime.calls))
    def test_explicit_bundle_inlines_macro_and_reads_complete_csv_without_mutating_original(self):
        doc = document('`nested` | lookup rooms.csv room OUTPUT label | stats count by label');before = copy.deepcopy(doc)
        result = DashboardDependencies(self.runtime).operation({'action': 'export', 'definition': doc, 'includeKnowledge': True})
        self.assertNotIn('`', result['definition']['dataSources']['s']['options']['query'])
        item = dict(bundled(), matching={});item['fingerprint'] = bundle_fingerprint(item)
        self.assertEqual(result['lookups'], [item]);self.assertIn(('complete-csv-snapshot', 'rooms.csv', None), self.runtime.calls)
        self.assertEqual(doc, before);self.assertEqual(result['definition']['future'], doc['future'])
        self.assertFalse(any(item['kind'] == 'macro' for item in result['dependencies']))
    def test_metadata_export_does_not_read_contents_and_macro_mismatch_blocks(self):
        doc = document('`nested` | stats count');before = DashboardDependencies(self.runtime).operation({'action': 'export', 'definition': doc})
        self.assertEqual(before['definition'], doc);self.assertFalse(any(x[0] == 'bounded-current-user' for x in self.runtime.calls))
        self.runtime.objects[('configs/conf-macros', 'cutoff(2)')]['definition'] = 'where $field$ <= 200'
        result = DashboardDependencies(self.runtime).operation({'action': 'check', 'definition': doc, 'dependencies': before['dependencies']})
        self.assertTrue(result['blocked']);self.assertTrue(any(x['kind'] == 'macro' and x['name'] == 'cutoff(2)' and x['status'] == 'missing' for x in result['dependencies']))
    def test_advanced_references_are_preserved_for_native_review_without_claiming_a_copy(self):
        for query in ('search index=fixture | lookup $table$ room', 'search index=fixture | `cutoff(temp,$limit$)`'):
            doc = document(query)
            result = DashboardDependencies(self.runtime).operation({'action': 'export', 'definition': doc})
            self.assertEqual(result['definition'], doc);self.assertFalse(result['blocked']);self.assertTrue(any(x['status'] == 'review' for x in result['dependencies']))
            with self.assertRaises(ProviderError): DashboardDependencies(self.runtime).operation({'action': 'export', 'definition': doc, 'includeKnowledge': True})
    def test_missing_macro_and_nested_index_are_detected(self):
        self.assertTrue(DashboardDependencies(self.runtime).operation({'action': 'check', 'definition': document('`absent`')})['blocked'])
        self.runtime.objects[('configs/conf-macros', 'base')]['definition'] = 'search index=absent'
        self.assertTrue(DashboardDependencies(self.runtime).operation({'action': 'check', 'definition': document('`nested`')})['blocked'])
    def test_csv_partial_oversized_multivalue_and_filtered_matching_refused(self):
        original = copy.deepcopy(self.runtime.rows)
        for change in ({'state': 'partial'}, {'warning': 'partial'}, {'results': [{'room': ['a', 'b']}]}, {'results': [{'room': 'a'}] * 5001}):
            self.runtime.rows = copy.deepcopy(original)
            self.runtime.rows.update(change)
            with self.assertRaises(ProviderError): PortableKnowledge(self.runtime, self.entry).lookup('rooms.csv', include=True)
        self.runtime.rows = original
        self.runtime.objects[('data/transforms/lookups', 'rooms')]['filter'] = 'room=cold'
        with self.assertRaises(ProviderError): PortableKnowledge(self.runtime, self.entry).lookup('rooms', include=True)
    def test_complete_larger_table_and_supported_matching_are_integrity_bound(self):
        self.runtime.rows['results'] = [{'room': str(i), 'label': 'Value'} for i in range(5000)]
        options = {'case_sensitive_match': 'false', 'match_type': 'CIDR(room), WILDCARD(label)', 'max_matches': '2', 'min_matches': '1', 'default_match': 'unknown'}
        self.runtime.objects[('data/transforms/lookups', 'rooms')].update(options)
        item = PortableKnowledge(self.runtime, self.entry).lookup('rooms', include=True)
        self.assertEqual(item['matching'], options);self.assertEqual(len(item['rows']), 5000)
        self.assertEqual(validate_bundle([item], document('| inputlookup rooms')), [item])
        item['matching']['max_matches'] = '3'
        with self.assertRaisesRegex(ProviderError, 'checksum'): validate_bundle([item], document('| inputlookup rooms'))
    def test_metadata_receipts_keep_legacy_and_canonical_comparisons(self):
        doc = document('search index=fixture | lookup rooms room OUTPUT label')
        item = PortableKnowledge(self.runtime, self.entry).lookup('rooms')
        old = [{'kind': 'lookup', 'app': 'constellation', 'name': 'rooms', 'fingerprint': item['legacyFingerprint']}]
        self.assertFalse(DashboardDependencies(self.runtime).operation({'action': 'check', 'definition': doc, 'dependencies': old})['blocked'])
        exported = DashboardDependencies(self.runtime).operation({'action': 'export', 'definition': doc})
        receipt = next(x for x in exported['dependencies'] if x['kind'] == 'lookup')
        self.assertEqual(receipt['fingerprintVersion'], 2)
        self.runtime.objects[('data/transforms/lookups', 'rooms')].update(case_sensitive_match='1', max_matches='100')
        self.assertFalse(DashboardDependencies(self.runtime).operation({'action': 'check', 'definition': doc, 'dependencies': exported['dependencies']})['blocked'])
        self.runtime.objects[('data/transforms/lookups', 'rooms')]['case_sensitive_match'] = '0'
        self.assertTrue(DashboardDependencies(self.runtime).operation({'action': 'check', 'definition': doc, 'dependencies': exported['dependencies']})['blocked'])
    def test_plain_named_csv_can_be_copied_but_foreign_app_and_geo_cannot(self):
        self.assertEqual(PortableKnowledge(self.runtime, self.entry).lookup('rooms', include=True)['rows'], bundled()['rows'])
        with self.assertRaises(ProviderError): DashboardDependencies(self.runtime).operation({'action': 'export', 'definition': document('| geom rooms'), 'includeKnowledge': True})
        item = bundled();item['app'] = 'search'
        with self.assertRaises(ProviderError): validate_bundle([item], document())
    def test_tampered_unrelated_duplicate_invalid_columns_fail_before_writes(self):
        for change in ({'fingerprint': '0' * 64}, {'name': '../file'}, {'fields': [{}]}, {'rows': [['short']]}, {'name': 'unused.csv'}):
            item = dict(bundled(), **change)
            with self.assertRaises(ProviderError): validate_bundle([item], document())
        with self.assertRaises(ProviderError): validate_bundle([bundled(), bundled()], document())
        with self.assertRaises(ProviderError): validate_bundle([bundled()], document('| geom rooms.csv'))
        self.assertEqual(self.runtime.uploads, [])
    def test_private_import_fresh_names_exact_readback_and_literal_remapping(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, SPLUNK_HOME=root):
            original = copy.deepcopy(self.runtime.objects[('data/lookup-table-files', 'rooms.csv')])
            doc = document();doc['description'] = 'Keep rooms.csv and `nested` text'
            doc['dataSources']['unknown'] = {'type': 'ds.future', 'options': {'query': '| lookup rooms.csv room'}}
            result = DashboardDependencies(self.runtime).operation({'action': 'import', 'definition': doc, 'lookups': [bundled()]})
            name, data = self.runtime.uploads[0]
            self.assertRegex(name, r'^constellation_[a-f0-9]{32}\.csv$');self.assertIn(name, result['definition']['dataSources']['s']['options']['query'])
            self.assertEqual(data, csv_payload(bundled()['fields'], bundled()['rows']));self.assertEqual(result['definition']['description'], doc['description'])
            self.assertEqual(result['definition']['dataSources']['unknown'], doc['dataSources']['unknown'])
            self.assertEqual(self.runtime.objects[('data/lookup-table-files', 'rooms.csv')], original)
            self.assertFalse(list((Path(root) / 'var/run/splunk/lookup_tmp').iterdir()))
            self.assertFalse(any(path.endswith('/acl') or method == 'DELETE' for path, method, _ in self.runtime.calls))
    def test_missing_native_upload_permission_blocks_preflight_without_a_write(self):
        self.runtime.can_upload = False
        result = DashboardDependencies(self.runtime).operation({'action': 'check', 'definition': document(), 'lookups': [bundled()]})
        self.assertTrue(result['blocked']);self.assertTrue(any(x['kind'] == 'permission' for x in result['dependencies']))
        with self.assertRaises(ProviderError): DashboardDependencies(self.runtime).operation({'action': 'import', 'definition': document(), 'lookups': [bundled()]})
        self.assertEqual(self.runtime.uploads, [])
    def test_matching_import_uses_verified_fresh_private_definition(self):
        item = bundled();item['matching'] = {'case_sensitive_match': 'false', 'match_type': 'WILDCARD(room)', 'max_matches': '1'};item['fingerprint'] = bundle_fingerprint(item)
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, SPLUNK_HOME=root):
            result = DashboardDependencies(self.runtime).operation({'action': 'import', 'definition': document(), 'lookups': [item]})
        created = [x for x in self.runtime.calls if x[0].endswith('/data/transforms/lookups') and x[1] == 'POST']
        self.assertEqual(len(created), 1);fields = created[0][2]
        self.assertRegex(fields['name'], r'^constellation_[a-f0-9]{32}$')
        self.assertIn(fields['name'], result['definition']['dataSources']['s']['options']['query'])
        self.assertEqual(fields['filename'], self.runtime.uploads[0][0])
        self.assertEqual({k: fields[k] for k in item['matching']}, item['matching'])
        self.assertFalse(any(x[0].endswith('/acl') or x[1] == 'DELETE' for x in self.runtime.calls))
    def test_unverified_matching_definition_never_replays_or_accepts_document(self):
        item = bundled();item['matching'] = {'case_sensitive_match': 'false'};item['fingerprint'] = bundle_fingerprint(item)
        original = self.runtime.request
        def interrupted(path, method='GET', fields=None, optional=False):
            result = original(path, method, fields, optional)
            if path.endswith('/data/transforms/lookups') and method == 'POST': raise ProviderError('private upstream error', 503)
            return result
        self.runtime.request = interrupted
        doc = document();before = copy.deepcopy(doc)
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, SPLUNK_HOME=root), self.assertRaisesRegex(ProviderError, 'Other uploads may have completed'):
            import_lookups(self.runtime, doc, [item], self.entry)
        self.assertEqual(doc, before)
        self.assertEqual(sum(x[0].endswith('/data/transforms/lookups') and x[1] == 'POST' for x in self.runtime.calls), 1)
    def test_native_definition_readback_requires_exact_matching_and_private_owner(self):
        item = bundled();item['matching'] = {'case_sensitive_match': 'false'};item['fingerprint'] = bundle_fingerprint(item)
        for defect in ('owner', 'sharing', 'filename', 'case_sensitive_match'):
            runtime = Runtime();original = runtime.request
            def incorrect(path, method='GET', fields=None, optional=False):
                response = original(path, method, fields, optional)
                if method == 'GET' and '/data/transforms/lookups/constellation_' in path and response.get('entry'):
                    record = copy.deepcopy(response['entry'][0])
                    record['acl' if defect in ('owner', 'sharing') else 'content'][defect] = 'other'
                    return {'entry': [record]}
                return response
            runtime.request = incorrect;doc = document();before = copy.deepcopy(doc)
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as root, patch.dict(os.environ, SPLUNK_HOME=root), self.assertRaisesRegex(ProviderError, 'Your draft is unchanged'):
                import_lookups(runtime, doc, [item], DashboardDependencies(runtime).entry)
            self.assertEqual(doc, before)
            self.assertEqual(sum(x[0].endswith('/data/transforms/lookups') and x[1] == 'POST' for x in runtime.calls), 1)
    def test_even_a_generated_name_collision_never_updates_an_existing_lookup(self):
        from types import SimpleNamespace
        name = 'constellation_' + 'a' * 32 + '.csv'
        self.runtime.objects[('data/lookup-table-files', name)] = {'original': 'preserve'}
        with patch('portable_knowledge.uuid.uuid4', return_value=SimpleNamespace(hex='a' * 32)), self.assertRaises(ProviderError):
            import_lookups(self.runtime, document(), [bundled()], self.entry)
        self.assertEqual(self.runtime.uploads, [])
        self.assertEqual(self.runtime.objects[('data/lookup-table-files', name)], {'original': 'preserve'})
    def test_uncertain_create_no_retry_shared_acl_refusal_and_staging_symlink_guard(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, SPLUNK_HOME=root):
            self.runtime.fail_write = True
            with self.assertRaisesRegex(ProviderError, 'Other uploads may have completed'): import_lookups(self.runtime, document(), [bundled()], self.entry)
            self.assertEqual(len(self.runtime.uploads), 1)
            self.runtime.fail_write = False;self.runtime.metadata_acl['sharing'] = 'app'
            with self.assertRaises(ProviderError): import_lookups(self.runtime, document(), [bundled()], self.entry)
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as target, patch.dict(os.environ, SPLUNK_HOME=root):
            path = Path(root) / 'var/run/splunk';path.mkdir(parents=True);(path / 'lookup_tmp').symlink_to(target)
            count = len(self.runtime.uploads)
            with self.assertRaises(ProviderError): import_lookups(self.runtime, document(), [bundled()], self.entry)
            self.assertEqual(len(self.runtime.uploads), count)


class MatchingTests(unittest.TestCase):
    def test_native_booleans_defaults_and_explicit_match_fields(self):
        self.assertEqual(matching_options({'case_sensitive_match': '1', 'batch_index_query': True, 'max_matches': '100', 'min_matches': '0', 'match_type': 'EXACT', 'CLEAN_KEYS': '1'}), {})
        self.assertEqual(matching_options({'case_sensitive_match': 0, 'reverse_lookup_honor_case_sensitive_match': False, 'match_type': 'CIDR(ip),WILDCARD(host)'}), {'case_sensitive_match': 'false', 'reverse_lookup_honor_case_sensitive_match': 'false', 'match_type': 'CIDR(ip), WILDCARD(host)'})
    def test_unsupported_noncanonical_or_invalid_options_and_missing_headers_refuse(self):
        for value in ({'time_field': '_time'}, {'filter': 'a=b'}, {'future': 'nonempty'}, {'CLEAN_KEYS': 'false'}, {'case_sensitive_match': 'no'}, {'max_matches': '1001'}, {'max_matches': '0'}, {'min_matches': '2', 'max_matches': '1'}, {'default_match': '\x00'}, {'match_type': 'CIDR(ip), WILDCARD(ip)'}, {'match_type': 'CIDR($ip$)'}, {'disabled': '1'}):
            with self.subTest(value=value), self.assertRaises(ProviderError): matching_options(value)
        for value in ({'filename': 'a.csv'}, {'case_sensitive_match': '0'}, {'max_matches': '100'}, {'max_matches': 1}, {'match_type': 'CIDR(ip),WILDCARD(host)'}):
            with self.subTest(value=value), self.assertRaises(ProviderError): matching_options(value, strict=True)
        with self.assertRaises(ProviderError): validate_matching_fields({'match_type': 'CIDR(ip)'}, ['host'])
    def test_csv_byte_limit_and_scalar_integrity(self):
        csv_payload(['a'], [['x'] for _ in range(5000)])
        for fields, rows in ((['a'], [['x']]*5001), (['a'], [['x'*4000]]*251), (['a']*2, [['1', '2']]), (['a'], [[None]])):
            with self.assertRaises(ProviderError): csv_payload(fields, rows)


if __name__ == '__main__': unittest.main()
