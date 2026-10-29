"""Caller-scoped macro expansion and opt-in, complete small CSV lookup transfer.

No credential/system token, arbitrary file reads, ACL changes, object replacement,
eval macro execution or automatic mutation retry. Native app context stays explicit.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
from urllib.parse import quote
from provider_service import ProviderError
from search_references import macro_calls, lookup_calls, replace_lookups, NAME


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def csv_payload(fields, rows):
    if (not isinstance(fields, list) or not 1 <= len(fields) <= 64
            or any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,99}', x) for x in fields) or len(set(fields)) != len(fields)
            or not isinstance(rows, list) or len(rows) > 200):
        raise ProviderError('Portable CSV lookups support up to 64 plain fields and 200 complete rows.')
    for row in rows:
        if not isinstance(row, list) or len(row) != len(fields) or any(not isinstance(x, str) or len(x) > 4000 or '\x00' in x for x in row):
            raise ProviderError('Invalid or oversized portable CSV lookup cell.')
    out = io.StringIO(newline=''); writer = csv.writer(out, lineterminator='\n'); writer.writerow(fields); writer.writerows(rows)
    data = out.getvalue()
    if len(data.encode('utf-8')) > 256_000: raise ProviderError('This lookup exceeds the 256 KB portable limit.')
    return data


def table_fingerprint(fields, rows):
    """Splunk returns field metadata alphabetically; CSV header order is immaterial."""
    order = sorted(range(len(fields)), key=lambda i: fields[i])
    return fingerprint({'fields': [fields[i] for i in order], 'rows': [[row[i] for i in order] for row in rows]})


class PortableKnowledge:
    def __init__(self, runtime, entry):
        self.runtime, self.entry = runtime, entry
        self.macros, self.lookups, self.receipts = {}, {}, {}
        self.expansions = 0

    def expand(self, query, app='constellation', stack=()):
        if not isinstance(query, str) or len(query) > 8000: raise ProviderError('Macro expansion exceeds the bounded search limit.')
        for start, end, name, values in reversed(macro_calls(query)):
            self.expansions += 1
            if len(stack) >= 8 or (app, name) in stack or self.expansions > 64:
                raise ProviderError('Macro dependencies are cyclic or exceed the portable expansion limit.')
            key = (app, name)
            if key not in self.macros: self.macros[key] = self.entry('configs/conf-macros', name, app)
            content = self.macros[key]
            if not content: raise ProviderError('Macro ' + name + ' is unavailable to your user in ' + app + '.', 422, 'macro_unavailable')
            semantic = {k: content.get(k, '') for k in ('definition', 'args', 'iseval', 'validation')}
            self.receipts[key] = dict(kind='macro', name=name, app=app, fingerprint=fingerprint(semantic))
            if content.get('iseval') in (True, 1, '1', 'true') or content.get('validation'):
                raise ProviderError('Eval-based or argument-validating macros need native configuration; they are not evaluated or inlined.')
            definition = content.get('definition')
            names = [x.strip() for x in str(content.get('args') or '').split(',') if x.strip()]
            if (not isinstance(definition, str) or not definition.strip() or len(names) != len(values)
                    or len(set(names)) != len(names) or any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,99}', x) for x in names)):
                raise ProviderError('The macro definition or declared arguments are incompatible with portable expansion.')
            substitutions = dict(zip(names, values))
            definition = re.sub(r'\$([A-Za-z_][A-Za-z0-9_]*)\$', lambda m: substitutions.get(m[1], m[0]), definition)
            if '$' in definition: raise ProviderError('Resolve macro argument tokens before exporting.')
            expanded = self.expand(definition, app, stack + (key,))
            query = query[:start] + expanded + query[end:]
            if len(query) > 8000: raise ProviderError('Macro expansion exceeds the bounded search limit.')
        return query

    def lookup(self, name, app='constellation', include=False):
        key = (app, name)
        if key in self.lookups: return self.lookups[key]
        if not re.fullmatch(NAME, name): raise ProviderError('Use a literal lookup name.')
        direct = name.endswith('.csv')
        content = self.entry('data/lookup-table-files' if direct else 'data/transforms/lookups', name, app)
        if content is None: raise ProviderError('Lookup ' + name + ' is unavailable to your user in ' + app + '.')
        # A same-name transform must not turn a seemingly literal CSV into an
        # external/KV lookup or change matching during dispatch.
        override = self.entry('data/transforms/lookups', name, app) if direct else None
        if override is not None: content, direct = override, False
        filename = name if direct else content.get('filename', '')
        if not re.fullmatch(NAME + r'\.csv', filename) or not direct and (content.get('type') not in (None, '', 'file') or content.get('external_type') or content.get('collection') or content.get('external_cmd')):
            raise ProviderError('Only static CSV lookup dependencies can be bundled; KV Store and scripted lookups need native configuration.')
        # A direct CSV reference has default native matching. Do not silently
        # discard temporal/CIDR/filter/default/matching semantics when remapping.
        defaults = {'case_sensitive_match': ('', '1', 'true', True, 1), 'max_matches': ('', '100', 100),
                    'min_matches': ('', '0', 0), 'batch_index_query': ('', '1', 'true', True, 1)}
        # fields_list/fields_array are derived CSV header metadata on native
        # file definitions; fields_list configures scripted lookup inputs only.
        advanced = ('match_type', 'time_field', 'time_format', 'filter', 'default_match', 'max_offset_secs', 'min_offset_secs')
        if not direct and (any(content.get(k) not in (None, '') for k in advanced)
                           or any(content.get(k, '') not in v for k, v in defaults.items())
                           or content.get('disabled') in (True, 1, '1', 'true')):
            raise ProviderError('This CSV lookup uses advanced matching. Keep its native definition on the destination.')
        semantic = {'filename': filename} if direct else {k: v for k, v in content.items() if not k.startswith('eai:') and k not in ('filename', 'type')}
        result = {'kind': 'lookup', 'name': name, 'app': app, 'fingerprint': fingerprint(dict(semantic, filename=filename))}
        if include:
            if app != 'constellation': raise ProviderError('CSV bundling currently supports the Constellation app context. Move other app dependencies with native Splunk tools.')
            # Fixed literal read, caller credentials, ordinary bounded completion.
            # max=201 detects oversize rather than silently transferring a sample.
            data = self.runtime.execute('| inputlookup strict=true max=201 ' + name, '-15m')
            if data.get('state') != 'complete' or data.get('warning'):
                raise ProviderError('The lookup read was partial. No sampled lookup data can be exported.')
            fields = [x.get('name') for x in data.get('fields', [])]
            rows = [[row.get(field, '') for field in fields] for row in data.get('results', [])]
            csv_payload(fields, rows)
            result.update(fields=fields, rows=rows)
            result['fingerprint'] = fingerprint({'fields': fields, 'rows': rows})
        self.lookups[key] = result
        return result


def validate_bundle(value, document):
    if not isinstance(value, list) or len(value) > 8: raise ProviderError('Include at most eight portable CSV lookups.')
    if len(json.dumps(value, ensure_ascii=False).encode('utf-8')) > 3_000_000: raise ProviderError('The portable lookups exceed the combined 3 MB limit.')
    if not value: return []
    calls = [call for source in document.get('dataSources', {}).values() if source.get('type') in ('ds.search', 'ds.chain', 'ds.spl2') for call in lookup_calls(source.get('options', {}).get('query', ''))]
    referenced = {name for _, _, name, command in calls if command in ('lookup', 'inputlookup')}
    geometry = {name for _, _, name, command in calls if command == 'geom'}
    found = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {'kind', 'name', 'app', 'fields', 'rows', 'fingerprint'}:
            raise ProviderError('Invalid portable lookup record.')
        name = item['name']
        if item['kind'] != 'lookup' or item['app'] != 'constellation' or not isinstance(name, str) or not re.fullmatch(NAME, name) or name in found or name not in referenced or name in geometry:
            raise ProviderError('Portable lookup records must be unique, literal and used by this dashboard.')
        csv_payload(item['fields'], item['rows'])
        if item['fingerprint'] != fingerprint({'fields': item['fields'], 'rows': item['rows']}):
            raise ProviderError('A lookup checksum does not match. Export the dashboard again.')
        found.add(name)
    return value


def import_lookups(runtime, document, bundle, entry):
    """One explicit write attempt; fresh private names and exact content readback."""
    validate_bundle(bundle, document)
    names, completed = {}, []
    try:
        for item in bundle:
            name = 'constellation_' + uuid.uuid4().hex + '.csv'
            base = '/servicesNS/' + quote(runtime.user, safe='') + '/constellation/data/lookup-table-files'
            if entry('data/lookup-table-files', name) is not None: raise ProviderError('The new lookup name is already in use; import stopped.')
            # This is Splunk's native lookup staging area, not a caller path.
            home = Path(os.environ['SPLUNK_HOME']).resolve(strict=True)
            root = home / 'var' / 'run' / 'splunk' / 'lookup_tmp'
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            if root.is_symlink() or root.resolve() != root.absolute(): raise ProviderError('The native lookup staging path is unsafe.')
            path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='', prefix='constellation_', suffix='.csv', dir=str(root), delete=False) as stream:
                    path = stream.name; stream.write(csv_payload(item['fields'], item['rows']))
                runtime.request(base, 'POST', {'name': name, 'eai:data': path})
            finally:
                if path:
                    try: os.unlink(path)
                    except FileNotFoundError: pass  # Splunk moves a successful upload.
            response = runtime.request(base + '/' + name)
            record = response.get('entry', [{}])[0]
            acl = record.get('acl', {})
            if record.get('name') != name or acl.get('owner') != runtime.user or acl.get('sharing') != 'user' or acl.get('app') != 'constellation':
                raise ProviderError('The copied lookup was not verified as private to this user.')
            readback = PortableKnowledge(runtime, entry).lookup(name, include=True)
            if table_fingerprint(readback['fields'], readback['rows']) != table_fingerprint(item['fields'], item['rows']): raise ProviderError('The copied lookup content could not be verified.')
            names[item['name']] = name; completed.append(name)
    except Exception:
        # Never echo native errors, contents, paths or credentials. No automatic
        # rollback deletes: an uncertain create may have completed.
        raise ProviderError(str(len(completed)) + ' private lookups verified before import stopped. Other uploads may have completed. Your draft is unchanged. Check Settings > Lookups before trying again.', 422, 'lookup_import_unverified') from None
    for source in document.get('dataSources', {}).values():
        options = source.get('options', {})
        if source.get('type') in ('ds.search', 'ds.chain', 'ds.spl2') and isinstance(options.get('query'), str):
            options['query'] = replace_lookups(options['query'], names)
    return document
