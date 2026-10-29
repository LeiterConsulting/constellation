"""Synthetic report contexts and same-name dependency collisions; no lab data."""
import copy
import hashlib
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import unquote
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from dashboard_dependencies import DashboardDependencies
from portable_knowledge import validate_bundle
from provider_service import ProviderError
from portable_context import flatten_lookup_contexts
from test_portable_knowledge import Runtime, document


class ContextRuntime(Runtime):
    def __init__(self):
        super().__init__()
        self.contexts = {}
        for app in ('search', 'fixture_other'):
            self.contexts[app] = {
                ('saved/searches', 'Report'): {'search': '`start` | lookup rooms room OUTPUT label | table room label', 'dispatch.earliest_time': '-7d'},
                ('configs/conf-macros', 'start'): {'definition': '| inputlookup rooms'},
                ('data/lookup-table-files', 'rooms.csv'): {},
                ('data/transforms/lookups', 'rooms'): {'type': 'file', 'filename': 'rooms.csv', 'case_sensitive_match': 'false'}}
    def request(self, path, method='GET', fields=None, optional=False):
        parts = path.split('/')
        if len(parts) > 4 and parts[3] in self.contexts:
            assert method == 'GET' and fields is None
            self.calls.append((path, method, fields))
            app = parts[3];resource, _, name = '/'.join(parts[4:]).rpartition('/')
            content = self.contexts[app].get((resource, unquote(name)))
            return {'entry': [] if content is None else [{'name': unquote(name), 'content': copy.deepcopy(content), 'acl': {'app': app}}]}
        return super().request(path, method, fields, optional)
    def lookup_snapshot(self, filename, app='constellation'):
        self.calls.append(('complete-csv-snapshot', filename, app))
        data = copy.deepcopy(self.rows)
        if app != 'constellation':
            for row in data['results']: row['label'] = app
        return data


class ContextTests(unittest.TestCase):
    def report_document(self):
        doc = document('| inputlookup rooms')
        doc['dataSources']['report'] = {'type': 'ds.savedSearch', 'future': 23, 'options': {'app': 'search', 'ref': 'Report'}}
        return doc
    def export(self, runtime, doc, **options):
        return DashboardDependencies(runtime).operation(dict(action='export', definition=doc, includeReports=True, includeKnowledge=True, **options))
    def test_report_lookup_contexts_are_distinct_and_original_work_is_preserved(self):
        runtime = ContextRuntime();doc = self.report_document()
        doc['dataSources']['other'] = {'type': 'ds.savedSearch', 'options': {'app': 'fixture_other', 'ref': 'Report'}}
        doc['dataSources']['unknown'] = {'type': 'ds.future', 'options': {'query': '| inputlookup rooms'}}
        before = copy.deepcopy(doc);result = self.export(runtime, doc)
        self.assertEqual(doc, before);self.assertFalse(result['blocked'])
        lookups = result['lookups'];self.assertEqual(len(lookups), 3)
        self.assertEqual(len({x['name'] for x in lookups}), 3)
        self.assertTrue(all(x['app'] == 'constellation' for x in lookups))
        sources = result['definition']['dataSources']
        for identifier, label in [('s', 'Freezer'), ('report', 'search'), ('other', 'fixture_other')]:
            query = sources[identifier]['options']['query'];name = query.split('inputlookup ', 1)[1].split()[0]
            bundled = next(x for x in lookups if x['name'] == name)
            self.assertEqual(bundled['rows'][0][1], label)
            if identifier != 's': self.assertIn('lookup '+name+' room', query)
        self.assertEqual(sources['unknown'], before['dataSources']['unknown'])
        self.assertEqual(sources['report']['future'], 23)
        self.assertEqual(sources['report']['options']['queryParameters']['earliest'], '-7d')
        self.assertFalse(any(x['kind'] in ('report', 'macro') for x in result['dependencies']))
        self.assertTrue(all(x['app'] == 'constellation' for x in result['dependencies'] if x['kind'] == 'lookup'))
        self.assertEqual(validate_bundle(lookups, result['definition']), lookups)
        self.assertTrue(all(method == 'GET' for path, method, _ in runtime.calls if path != 'complete-csv-snapshot'))
    def test_alias_does_not_capture_an_existing_literal_name_or_quoted_text(self):
        runtime = ContextRuntime();doc = self.report_document()
        reserved = 'constellation_portable_' + hashlib.sha256(b'search\x00rooms').hexdigest()[:24]
        runtime.objects[('data/lookup-table-files', reserved+'.csv')] = {}
        runtime.objects[('data/transforms/lookups', reserved)] = {'filename': reserved+'.csv'}
        doc['dataSources']['s']['options']['query'] = '| inputlookup '+reserved+' | eval note="rooms | lookup rooms room"'
        result = self.export(runtime, doc)
        self.assertEqual(result['definition']['dataSources']['s'], doc['dataSources']['s'])
        query = result['definition']['dataSources']['report']['options']['query']
        self.assertIn(reserved+'_1', query)
        self.assertEqual(len(result['lookups']), 2)
    def test_report_lookups_require_explicit_report_and_knowledge_choices(self):
        runtime = ContextRuntime();doc = self.report_document();doc['dataSources'].pop('s')
        for reports, knowledge in ((True, False), (False, True)):
            with self.assertRaisesRegex(ProviderError, 'include|Include'):
                DashboardDependencies(runtime).operation(dict(action='export', definition=doc, includeReports=reports, includeKnowledge=knowledge))
        unchanged = DashboardDependencies(runtime).operation(dict(action='export', definition=doc))
        self.assertEqual(unchanged['definition'], doc)
        self.assertEqual(unchanged['lookups'], [])
    def test_plain_chain_is_preserved_but_foreign_app_dependent_chain_refuses(self):
        runtime = ContextRuntime();doc = self.report_document()
        chain = {'type': 'ds.chain', 'options': {'extend': 'report', 'query': '| stats count'}}
        doc['dataSources']['chain'] = chain
        self.assertEqual(self.export(runtime, doc)['definition']['dataSources']['chain'], chain)
        doc['dataSources']['chain']['options']['query'] = '| lookup rooms room'
        with self.assertRaisesRegex(ProviderError, 'chain'): self.export(runtime, doc)
        with self.assertRaisesRegex(ProviderError, 'chain'):
            DashboardDependencies(runtime).operation(dict(action='export', definition=doc, includeKnowledge=True))
    def test_missing_context_dependency_never_falls_back_to_local_names(self):
        runtime = ContextRuntime();runtime.contexts['search'].pop(('data/transforms/lookups', 'rooms'))
        result = self.export(runtime, self.report_document())
        self.assertTrue(result['blocked']);self.assertEqual(len(result['lookups']), 1)
        self.assertTrue(any(x['app'] == 'search' and x['status'] == 'missing' for x in result['dependencies']))
    def test_repeated_context_is_read_once_and_flat_file_still_checks_offline(self):
        runtime = ContextRuntime();doc = self.report_document()
        doc['dataSources']['copy'] = copy.deepcopy(doc['dataSources']['report'])
        result = self.export(runtime, doc)
        reads = [x for x in runtime.calls if x[0] == 'complete-csv-snapshot' and x[2] == 'search']
        self.assertEqual(len(reads), 1);self.assertEqual(len(result['lookups']), 2)
        destination = DashboardDependencies(Runtime()).operation(dict(action='check', definition=result['definition'], dependencies=result['dependencies'], lookups=result['lookups']))
        self.assertFalse(destination['blocked'])
    def test_eight_table_limit_counts_app_identity_and_refuses_before_ninth_read(self):
        runtime = ContextRuntime();doc = self.report_document();doc['dataSources'].pop('s')
        for i in range(9):
            app = 'fixture_'+str(i);runtime.contexts[app] = copy.deepcopy(runtime.contexts['search'])
            doc['dataSources'][str(i)] = {'type': 'ds.savedSearch', 'options': {'ref': 'Report', 'app': app}}
        with self.assertRaisesRegex(ProviderError, 'eight'): self.export(runtime, doc)
        self.assertEqual(len([x for x in runtime.calls if x[0] == 'complete-csv-snapshot']), 8)
    def test_repeated_literal_references_do_not_multiply_transfer_bookkeeping(self):
        runtime = ContextRuntime();doc = self.report_document();doc['dataSources'].pop('s')
        runtime.contexts['search'][('saved/searches', 'Report')]['search'] = '| inputlookup rooms' + ' | lookup rooms room OUTPUT label'*20
        with patch('dashboard_dependencies.flatten_lookup_contexts', wraps=flatten_lookup_contexts) as flatten:
            result = self.export(runtime, doc)
        self.assertEqual(len(result['lookups']), 1)
        self.assertEqual(len(flatten.call_args.args[1]), 1)
        self.assertEqual(len([x for x in runtime.calls if x[0] == 'complete-csv-snapshot']), 1)


if __name__ == '__main__': unittest.main()
