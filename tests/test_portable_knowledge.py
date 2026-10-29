"""Synthetic lookup/macro migration and privilege boundaries; no live data."""
import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from portable_knowledge import PortableKnowledge, csv_payload, fingerprint, import_lookups, validate_bundle, table_fingerprint
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
            self.uploads.append((fields['name'], Path(fields['eai:data']).read_text()))
            if self.fail_write: raise ProviderError('synthetic delivery interruption', 503)
            self.objects[('data/lookup-table-files', fields['name'])] = {}
            return {'entry': []}
        resource, _, name = path[len(base):].rpartition('/')
        content = self.objects.get((resource, unquote(name)))
        return {'entry': [] if content is None else [{'name': unquote(name), 'content': copy.deepcopy(content), 'acl': self.metadata_acl}]}
    def execute(self, query, earliest='-15m'):
        self.calls.append(('bounded-current-user', query, earliest)); return copy.deepcopy(self.rows)


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
        self.assertNotIn('`', result['definition']['dataSources']['s']['options']['query']);self.assertEqual(result['lookups'], [bundled()])
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
    def test_csv_partial_oversized_multivalue_and_advanced_matching_refused(self):
        for change in ({'state': 'partial'}, {'warning': 'partial'}, {'results': [{'room': ['a', 'b']}]}, {'results': [{'room': 'a'}] * 201}):
            self.runtime.rows.update(change)
            with self.assertRaises(ProviderError): PortableKnowledge(self.runtime, self.entry).lookup('rooms.csv', include=True)
        self.runtime.objects[('data/transforms/lookups', 'rooms')]['match_type'] = 'CIDR(room)'
        with self.assertRaises(ProviderError): PortableKnowledge(self.runtime, self.entry).lookup('rooms', include=True)
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


if __name__ == '__main__': unittest.main()
