"""Caller-scoped portable dependency inspection; explicit CSV import is separate."""
import copy
import hashlib
import re
from urllib.parse import quote
from provider_service import ProviderError
from studio_contract import validate_document
from measurement_constraints import pipeline_commands
from search_service import read_only_query
from studio_inventory import INVENTORY
from portable_knowledge import PortableKnowledge, fingerprint, validate_bundle, import_lookups
from search_references import lookup_calls, macro_calls


class DashboardDependencies:
    def __init__(self, runtime):
        self.runtime = runtime

    def entry(self, endpoint, name, app='constellation'):
        if not isinstance(name, str) or not 1 <= len(name) <= 256 or any(ord(c) < 32 for c in name):
            raise ProviderError('Invalid dashboard dependency name.')
        if not isinstance(app, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}', app): raise ProviderError('Invalid dependency app.')
        result = self.runtime.request('/servicesNS/' + quote(self.runtime.user, safe='') + '/' + quote(app, safe='') + '/' + endpoint + '/' + quote(name, safe=''), optional=True)
        entries = result.get('entry', [])
        if len(entries) != 1 or entries[0].get('name') != name or endpoint == 'saved/searches' and entries[0].get('acl', {}).get('app') != app: return None
        return entries[0].get('content', {})

    def operation(self, body):
        if body.get('action') not in ('export', 'check', 'import'): raise ProviderError('Choose a dependency export, check or import.')
        document = copy.deepcopy(validate_document(body.get('definition')))
        bundle = validate_bundle(body.get('lookups', []), document)
        bundled = {item['name'] for item in bundle}
        expected = body.get('dependencies', [])
        if not isinstance(expected, list) or len(expected) > 100: raise ProviderError('Use at most 100 dependency receipts.')
        fingerprints = {}
        for item in expected:
            if not isinstance(item, dict): raise ProviderError('Invalid dependency receipt.')
            if item.get('kind') in ('report', 'macro', 'lookup') and isinstance(item.get('fingerprint'), str):
                if not re.fullmatch(r'[a-f0-9]{64}', item['fingerprint']): raise ProviderError('Invalid report fingerprint.')
                fingerprints[(item['kind'], str(item.get('app', '')), str(item.get('name', '')))] = item['fingerprint']
        found, notes = {}, []
        def add(kind, name, status, detail, app='', **extra):
            found[(kind, app, name)] = dict(kind=kind, name=name, app=app, status=status, detail=detail, **extra)
            if len(found) > 100: raise ProviderError('This dashboard has more than 100 dependencies.')

        if bundle:
            context = self.runtime.request('/services/authentication/current-context').get('entry', [{}])[0].get('content', {})
            if 'upload_lookup_files' not in context.get('capabilities', []):
                add('permission', 'Upload CSV lookups', 'missing', 'Your native role cannot upload lookup files. Ask an administrator to configure the dependency, then import a reference-only dashboard file.')

        queries = []
        for source in document.get('dataSources', {}).values():
            options = source.get('options', {})
            if source.get('type') == 'ds.savedSearch':
                name, app = options.get('ref'), options.get('app', 'constellation')
                report = self.entry('saved/searches', name, app)
                query = report.get('search') if report else None
                if not isinstance(query, str) or not query or report.get('disabled') in (True, 1, '1', 'true'):
                    add('report', name, 'missing', 'Report is unavailable or disabled for your user in this app.', app);continue
                fingerprint = hashlib.sha256(query.encode('utf-8')).hexdigest()
                match = fingerprints.get(('report', app, name))
                status = 'missing' if match and match != fingerprint else 'available' if match or body['action'] == 'export' else 'review'
                add('report', name, status, 'Report search differs from the exported reference.' if status == 'missing' else 'Readable report; native caches, scheduling, app context and execution permissions remain destination-specific.', app, fingerprint=fingerprint)
                if body['action'] == 'export' and body.get('includeReports') is True:
                    # Opt-in conversion is deliberately limited. Never turn a
                    # macro, lookup, token or advanced report into a claimed copy.
                    if set(options) - {'ref', 'app', 'queryParameters'}:
                        raise ProviderError('This report has advanced source options. Keep its reference and configure it in native Studio.')
                    if body.get('includeKnowledge'):
                        query = PortableKnowledge(self.runtime, self.entry).expand(query, app)
                    read_only_query(query)
                    parameters = {'earliest': str(report.get('dispatch.earliest_time') or '-24h'), 'latest': str(report.get('dispatch.latest_time') or 'now')}
                    if not isinstance(options.get('queryParameters', {}), dict): raise ProviderError('Invalid report time parameters.')
                    parameters.update(options.get('queryParameters', {}))
                    source['type'] = 'ds.search';source['options'] = dict(query=query, queryParameters=parameters)
                    found.pop(('report', app, name), None)
                    notes.append('Included report search: ' + name + '. It reruns as the dashboard viewer; report caches, schedules and owner permissions are not copied. Verify app-specific field extraction on the destination.')
                queries.append((source, query, app))
            elif source.get('type') in ('ds.search', 'ds.chain', 'ds.spl2'):
                if isinstance(options.get('query'), str): queries.append((source, options['query'], 'constellation'))
            elif source.get('type') not in ('ds.test',):
                add('source', source.get('type', 'unknown'), 'review', 'Native source/module configuration needs destination qualification.')

        catalog = {x['name'] for x in self.runtime.datasets().get('indexes', [])}
        knowledge = PortableKnowledge(self.runtime, self.entry)
        exported = []
        for source, query, app in queries:
            expanded = query
            try: calls = macro_calls(query)
            except ProviderError as error:
                if body['action'] == 'export' and body.get('includeKnowledge') is True: raise
                add('macro', 'Native macro references', 'review', str(error), app); calls = []
            if calls:
                try:
                    expanded = knowledge.expand(query, app)
                    if body['action'] == 'export' and body.get('includeKnowledge') is True:
                        if source.get('type') == 'ds.savedSearch': raise ProviderError('Include the report search to inline its macro dependencies.')
                        read_only_query(expanded)
                        source['options']['query'] = expanded
                        notes.append('Inlined compatible macros into a search. Native macro objects are unchanged; future macro updates will not change this copy.')
                except ProviderError as error:
                    if body['action'] == 'export' and body.get('includeKnowledge') is True or error.status >= 500: raise
                    add('macro', 'Native macro dependencies', 'missing' if error.code == 'macro_unavailable' else 'review', str(error), app)
            for key, receipt in knowledge.receipts.items():
                expected_hash = fingerprints.get(('macro', *key))
                differs = expected_hash and expected_hash != receipt['fingerprint']
                add('macro', receipt['name'], 'missing' if differs else 'available', 'Macro definition differs from the exported reference.' if differs else 'Readable macro definition and declared arguments matched. Nested dependencies are inspected; native permissions still apply.', receipt['app'], fingerprint=receipt['fingerprint'])
            # An inlined query has no destination macro dependency.
            if body['action'] == 'export' and body.get('includeKnowledge') is True:
                for key in knowledge.receipts: found.pop(('macro', *key), None)
            query = expanded
            for _start, _end, segment in pipeline_commands('|' + query.lstrip('| ')):
                if re.match(r'^(?:search|tstats)\b', segment.strip(), re.I) or _start == 0 and not query.lstrip().startswith('|'):
                    outside, quoted, escaped = set(), None, False
                    for position, char in enumerate(segment):
                        if escaped: escaped = False; continue
                        if char == '\\': escaped = True; continue
                        if quoted:
                            if char == quoted: quoted = None
                        elif char in ('\"', "'"): quoted = char
                        else: outside.add(position)
                    for match in re.finditer(r'\bindex\s*=\s*(?:"([A-Za-z0-9_.*-]+)"|([A-Za-z0-9_.*-]+))', segment, re.I):
                        if match.start() not in outside: continue
                        name = match[1] or match[2]
                        add('index', name, 'review' if '*' in name or name in catalog else 'missing', 'Catalog visibility does not prove search access or event coverage.' if '*' in name or name in catalog else 'Index is not listed for your user on this instance.')
            try: lookups = lookup_calls(query)
            except ProviderError as error:
                if body['action'] == 'export' and body.get('includeKnowledge') is True: raise
                add('lookup', 'Dynamic lookup references', 'review', str(error), app); lookups = []
            for _, _, name, command in lookups:
                if name in bundled:
                    add('lookup', name, 'available', 'Bundled CSV will be copied under a fresh private name. Existing lookups are preserved.', app)
                    continue
                endpoint = 'data/lookup-table-files' if name.endswith('.csv') else 'data/transforms/lookups'
                content = self.entry(endpoint, name, app)
                if content is None:
                    add('lookup', name, 'missing', 'Include this compatible CSV at export, or configure its native lookup on the destination.', app); continue
                try:
                    include = body['action'] == 'export' and body.get('includeKnowledge') is True
                    if include and command == 'geom': raise ProviderError('Geospatial lookup files need native configuration; CSV bundling does not convert geometry.')
                    receipt = knowledge.lookup(name, app, include)
                    if include:
                        if len(exported) >= 8 and not any(x['name'] == name for x in exported): raise ProviderError('Include at most eight portable CSV lookups.')
                        if not any(x['name'] == name for x in exported): exported.append(receipt)
                        add('lookup', name, 'available', 'Complete bounded CSV included. Import creates a fresh private copy; sharing remains a native Splunk action.', app)
                    else:
                        differs = fingerprints.get(('lookup', app, name)) not in (None, receipt['fingerprint'])
                        add('lookup', name, 'missing' if differs else 'review', 'Lookup definition differs from the exported reference.' if differs else 'Static CSV definition checked; contents were not bundled or compared. Include compatible dependencies to transfer complete small CSV data.', app, fingerprint=receipt['fingerprint'])
                except ProviderError as error:
                    if body['action'] == 'export' and body.get('includeKnowledge') is True or error.status >= 500: raise
                    add('lookup', name, 'review', str(error), app)
        for item in document.get('visualizations', {}).values():
            if item.get('type') not in INVENTORY['visualizations']:
                add('visualization', item.get('type', 'unknown'), 'review', 'Install and qualify this native visualization on the destination; no extension code is copied.')
        def media(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in ('src', 'svg', 'icon') and isinstance(value, str) and re.match(r'^(?:https?://|//)', value):
                        add('media', 'External media', 'review', 'External URLs are not fetched or bundled. Check native allow lists and access on the destination.')
                    elif key in ('src', 'svg', 'icon') and isinstance(value, str) and value.startswith('/') and body['action'] == 'check':
                        add('media', value[:200], 'review', 'This older/imported reference needs its packaged app file on the destination.')
                    else: media(value)
            elif isinstance(node, list):
                for child in node: media(child)
        media(document)
        blocked = any(x['status'] == 'missing' for x in found.values())
        if body['action'] == 'import':
            if blocked: raise ProviderError('Resolve the missing destination dependencies before importing.')
            document = import_lookups(self.runtime, document, bundle, self.entry)
        return {'definition': document, 'dependencies': list(found.values()), 'notes': list(dict.fromkeys(notes)), 'lookups': exported,
                'blocked': blocked}
