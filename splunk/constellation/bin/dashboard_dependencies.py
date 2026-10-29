"""Read-only portable dependency inspection. No data/file/credential migration."""
import copy
import hashlib
import re
from urllib.parse import quote
from provider_service import ProviderError
from studio_contract import validate_document
from measurement_constraints import pipeline_commands
from search_service import read_only_query
from studio_inventory import INVENTORY


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
        if body.get('action') not in ('export', 'check'): raise ProviderError('Choose a dependency export or check.')
        document = copy.deepcopy(validate_document(body.get('definition')))
        expected = body.get('dependencies', [])
        if not isinstance(expected, list) or len(expected) > 100: raise ProviderError('Use at most 100 dependency receipts.')
        fingerprints = {}
        for item in expected:
            if not isinstance(item, dict): raise ProviderError('Invalid dependency receipt.')
            if item.get('kind') == 'report' and isinstance(item.get('fingerprint'), str):
                if not re.fullmatch(r'[a-f0-9]{64}', item['fingerprint']): raise ProviderError('Invalid report fingerprint.')
                fingerprints[(str(item.get('app', '')), str(item.get('name', '')))] = item['fingerprint']
        found, notes = {}, []
        def add(kind, name, status, detail, app='', **extra):
            found[(kind, app, name)] = dict(kind=kind, name=name, app=app, status=status, detail=detail, **extra)
            if len(found) > 100: raise ProviderError('This dashboard has more than 100 dependencies.')

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
                match = fingerprints.get((app, name))
                status = 'missing' if match and match != fingerprint else 'available' if match or body['action'] == 'export' else 'review'
                add('report', name, status, 'Report search differs from the exported reference.' if status == 'missing' else 'Readable report; native caches, scheduling, app context and execution permissions remain destination-specific.', app, fingerprint=fingerprint)
                if body['action'] == 'export' and body.get('includeReports') is True:
                    # Opt-in conversion is deliberately limited. Never turn a
                    # macro, lookup, token or advanced report into a claimed copy.
                    if set(options) - {'ref', 'app', 'queryParameters'}:
                        raise ProviderError('This report has advanced source options. Keep its reference and configure it in native Studio.')
                    read_only_query(query)
                    parameters = {'earliest': str(report.get('dispatch.earliest_time') or '-24h'), 'latest': str(report.get('dispatch.latest_time') or 'now')}
                    if not isinstance(options.get('queryParameters', {}), dict): raise ProviderError('Invalid report time parameters.')
                    parameters.update(options.get('queryParameters', {}))
                    source['type'] = 'ds.search';source['options'] = dict(query=query, queryParameters=parameters)
                    found.pop(('report', app, name), None)
                    notes.append('Included report search: ' + name + '. It reruns as the dashboard viewer; report caches, schedules and owner permissions are not copied. Verify app-specific field extraction on the destination.')
                queries.append((query, app))
            elif source.get('type') in ('ds.search', 'ds.chain', 'ds.spl2'):
                if isinstance(options.get('query'), str): queries.append((options['query'], 'constellation'))
            elif source.get('type') not in ('ds.test',):
                add('source', source.get('type', 'unknown'), 'review', 'Native source/module configuration needs destination qualification.')

        catalog = {x['name'] for x in self.runtime.datasets().get('indexes', [])}
        for query, app in queries:
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
                lookup = re.match(r'^\s*(?:lookup|inputlookup|geom)\s+(?:\w+=\S+\s+)*([A-Za-z_][A-Za-z0-9_.-]{0,199})\b', segment, re.I)
                if lookup:
                    name = lookup[1];endpoint = 'data/lookup-table-files' if name.endswith('.csv') else 'data/transforms/lookups'
                    exists = self.entry(endpoint, name, app) is not None
                    add('lookup', name, 'review' if exists else 'missing', 'Lookup metadata is readable; contents/definitions are not bundled or compared.' if exists else 'Install this lookup in its native app before importing.', app)
            for name, arguments in re.findall(r'`([A-Za-z_][A-Za-z0-9_.-]{0,99})(\([^`]*\))?`', query):
                if arguments:
                    add('macro', name, 'review', 'Parameterized macro: verify its arity, native definition and dependencies in the destination app. It is not copied.', app)
                    continue
                exists = self.entry('configs/conf-macros', name, app) is not None
                add('macro', name, 'review' if exists else 'missing', 'Review the native macro definition and its own dependencies; it is not copied.', app)
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
        return {'definition': document, 'dependencies': list(found.values()), 'notes': notes,
                'blocked': any(x['status'] == 'missing' for x in found.values())}
