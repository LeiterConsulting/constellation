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
from lookup_matching import matching_options, validate_matching_fields
from lookup_snapshot import ROWS, FIELDS, CSV_BYTES


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def csv_payload(fields, rows):
    if (not isinstance(fields, list) or not 1 <= len(fields) <= FIELDS
            or any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,99}', x) for x in fields) or len(set(fields)) != len(fields)
            or not isinstance(rows, list) or len(rows) > ROWS):
        raise ProviderError('Portable CSV lookups support up to 64 plain fields and 5,000 complete rows.')
    for row in rows:
        if not isinstance(row, list) or len(row) != len(fields) or any(not isinstance(x, str) or len(x) > 4000 or '\x00' in x for x in row):
            raise ProviderError('Invalid or oversized portable CSV lookup cell.')
    out = io.StringIO(newline=''); writer = csv.writer(out, lineterminator='\n'); writer.writerow(fields); writer.writerows(rows)
    data = out.getvalue()
    if len(data.encode('utf-8')) > CSV_BYTES: raise ProviderError('This lookup exceeds the 1 MB portable limit.')
    return data


def table_fingerprint(fields, rows):
    """Splunk returns field metadata alphabetically; CSV header order is immaterial."""
    order = sorted(range(len(fields)), key=lambda i: fields[i])
    return fingerprint({'fields': [fields[i] for i in order], 'rows': [[row[i] for i in order] for row in rows]})


def bundle_fingerprint(item):
    data = {'fields': item['fields'], 'rows': item['rows']}
    if 'matching' in item: data['matching'] = item['matching']
    return fingerprint(data)


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
        matching = {} if direct else matching_options(content)
        semantic = {'filename': filename} if direct else {k: v for k, v in content.items() if not k.startswith('eai:') and k not in ('filename', 'type')}
        result = {'kind': 'lookup', 'name': name, 'app': app, 'fingerprint': fingerprint({'filename': filename, 'matching': matching}),
                  'legacyFingerprint': fingerprint(dict(semantic, filename=filename)), 'matching': matching}
        if include:
            # Read the complete backing CSV, not a filtered/matched alias. The
            # dedicated transfer job does not widen ordinary preview limits.
            data = self.runtime.lookup_snapshot(filename, app=app)
            if data.get('state') != 'complete' or data.get('warning'):
                raise ProviderError('The lookup read was partial. No sampled lookup data can be exported.')
            fields = [x.get('name') for x in data.get('fields', [])]
            rows = [[row.get(field, '') for field in fields] for row in data.get('results', [])]
            csv_payload(fields, rows)
            validate_matching_fields(matching, fields)
            result.update(fields=fields, rows=rows)
            result.pop('legacyFingerprint')
            result['fingerprint'] = bundle_fingerprint(result)
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
        if not isinstance(item, dict) or set(item) not in ({'kind', 'name', 'app', 'fields', 'rows', 'fingerprint'}, {'kind', 'name', 'app', 'fields', 'rows', 'fingerprint', 'matching'}):
            raise ProviderError('Invalid portable lookup record.')
        name = item['name']
        if item['kind'] != 'lookup' or item['app'] != 'constellation' or not isinstance(name, str) or not re.fullmatch(NAME, name) or name in found or name not in referenced or name in geometry:
            raise ProviderError('Portable lookup records must be unique, literal and used by this dashboard.')
        csv_payload(item['fields'], item['rows'])
        matching = matching_options(item.get('matching', {}), strict=True)
        validate_matching_fields(matching, item['fields'])
        if item['fingerprint'] != bundle_fingerprint(item):
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
            reference = name
            if item.get('matching'):
                reference = 'constellation_' + uuid.uuid4().hex
                if entry('data/transforms/lookups', reference) is not None:
                    raise ProviderError('The new lookup definition name is already in use.')
                definitions = '/servicesNS/' + quote(runtime.user, safe='') + '/constellation/data/transforms/lookups'
                runtime.request(definitions, 'POST', dict(item['matching'], name=reference, filename=name))
                response = runtime.request(definitions + '/' + reference)
                record = response.get('entry', [{}])[0];acl = record.get('acl', {});content = record.get('content', {})
                if (record.get('name') != reference or acl.get('owner') != runtime.user or acl.get('sharing') != 'user' or acl.get('app') != 'constellation'
                        or content.get('filename') != name or content.get('type') != 'file' or matching_options(content) != item['matching']):
                    raise ProviderError('The private native lookup definition could not be verified.')
            names[item['name']] = reference; completed.append(reference)
    except Exception:
        # Never echo native errors, contents, paths or credentials. No automatic
        # rollback deletes: an uncertain create may have completed.
        raise ProviderError(str(len(completed)) + ' private lookups verified before import stopped. Other uploads may have completed. Your draft is unchanged. Check Settings > Lookups before trying again.', 422, 'lookup_import_unverified') from None
    for source in document.get('dataSources', {}).values():
        options = source.get('options', {})
        if source.get('type') in ('ds.search', 'ds.chain', 'ds.spl2') and isinstance(options.get('query'), str):
            options['query'] = replace_lookups(options['query'], names)
    return document
