"""Default ordinary first-draft row drilldowns to destination-local searches.

Only native row mappings, literal verified fields and scoped SPL qualify. The
existing route compiler owns cloning/filtering; search/native checks still run.
Imported work, deliberate shared/global controls and advanced sources stay out.
"""
import copy
import json
import re
from measurement_constraints import pipeline_commands
from provider_service import ProviderError
from route_actions import compile_route
from search_scope import scoped_suffix
from studio_contract import apply_changes
from token_service import default_token_values


def normalize_creation_page_scope(document, previous, profile, prompt):
    if previous.get('visualizations') or previous.get('dataSources') or not profile or profile.get('scope', {}).get('language', 'spl') != 'spl': return []
    # Explicit exceptions keep the ordinary native/intent path. This is a
    # default for row investigation, not an override of requested shared views.
    if re.search(r'\b(?:do not|don.t|never)\s+filter\b|\bfilter\s+only\s+(?:one|the)\b|\b(?:shared|global)\s+(?:entity\s+)?filter\b|\b(?:also|both)\s+filter\s+(?:the\s+)?overview\b|\bkeep\s+(?:the\s+)?details?\s+unfiltered\b', prompt, re.I): return []
    known = {f['name'] for f in profile.get('fields', [])}
    values = default_token_values(document)
    pages = document.get('layout', {}).get('layoutDefinitions', {})
    input_tokens = {v.get('options', {}).get('token') for v in document.get('inputs', {}).values()}
    candidate = copy.deepcopy(document);result = [];destinations = {}
    def stage(changes):
        nonlocal candidate
        candidate = apply_changes(candidate, changes);result.extend(changes)
    for table_id, table in document.get('visualizations', {}).items():
        if table.get('type') != 'splunk.table': continue
        handlers = table.get('eventHandlers', [])
        origins = {pid for pid, p in pages.items() if any(i.get('item') == table_id for i in p.get('structure', []))}
        if len(origins) != 1: continue
        for route in handlers:
            if route.get('type') != 'drilldown.switchToTab': continue
            fields = route.get('options', {}).get('fields', []);destination = route.get('options', {}).get('tabId')
            if not isinstance(fields, list) or len(fields) != 1 or not isinstance(fields[0], str) or fields[0] not in known or not isinstance(destination, str) or destination in origins or pages.get(destination, {}).get('type') != 'absolute': continue
            field = fields[0]
            tokens = {t.get('token') for h in handlers if h.get('type') == 'drilldown.setToken' and h.get('options', {}).get('fields') == fields
                      for t in h.get('options', {}).get('tokens', []) if t.get('key') == 'row.' + field + '.value'}
            if len(tokens) != 1: continue
            token = next(iter(tokens))
            if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,149}', token) or values.get(token) != '*' or token in input_tokens: continue
            if destination in destinations and destinations[destination] != (field, token):
                raise ProviderError('Give this detail page one unambiguous row selection, or use explicit independent destination pages.', 422, 'page_scope')
            destinations[destination] = (field, token)
            placed = {i.get('item') for i in pages[destination].get('structure', [])}
            charts = {k:v for k, v in candidate['visualizations'].items() if k in placed and v.get('dataSources')}
            if not charts or any(set(v.get('dataSources', {})) != {'primary'} or v.get('containerOptions', {}).get('visibility') for v in charts.values()): continue
            sources = {v['dataSources']['primary'] for v in charts.values()}
            if any(candidate['dataSources'].get(s, {}).get('type') != 'ds.search' or not isinstance(candidate['dataSources'][s].get('options', {}).get('query'), str) for s in sources): continue
            if any(any(i.get('item') == k for i in p.get('structure', [])) for k in charts for pid, p in pages.items() if pid != destination):
                raise ProviderError('Give Overview and detail separate chart IDs; a reused chart cannot have two different row populations.', 422, 'page_scope')
            needs_route = False
            for sid in sorted(sources):
                source = candidate['dataSources'][sid];query = source.get('options', {}).get('query', '')
                if not isinstance(query, str): continue
                suffix = scoped_suffix(query, profile)
                if suffix is None: raise ProviderError('Preserve the inspected search scope for each row destination.', 422, 'page_scope')
                commands = pipeline_commands(suffix);exact = 'search ' + field + '=$' + token + '|s$';spans = []
                for start, end, command in commands:
                    if re.match(r'(?i:stats|timechart|chart|eventstats|streamstats)\b', command): break
                    if command == exact: spans.append((start, end))
                remainder = suffix
                for start, end in reversed(spans): remainder = remainder[:start] + remainder[end:]
                if re.search(r'\$' + re.escape(token) + r'(?:\||\$)', remainder):
                    raise ProviderError('Use a separate exact pre-aggregation row filter for the detail page; preserve other predicates with native edits.', 422, 'page_scope')
                outside = any(k not in charts and sid in v.get('dataSources', {}).values() for k, v in candidate['visualizations'].items())
                if outside and (any(sid in v.get('dataSources', {}).values() for v in candidate.get('inputs', {}).values()) or any(v.get('options', {}).get('extend') == sid for v in candidate['dataSources'].values())):
                    raise ProviderError('Give row detail its own ordinary search rather than changing an input/chain dependency.', 422, 'page_scope')
                if outside:
                    needs_route = True
                    if spans:
                        normalized = query.strip().lstrip('| ').strip();prefix = normalized[:len(normalized)-len(suffix)]
                        path = '/dataSources/' + sid.replace('~', '~0').replace('/', '~1') + '/options/query'
                        stage([{'op':'set', 'path':path, 'value':json.dumps(prefix + remainder)}])
                elif not spans: needs_route = True
            if needs_route:
                changes = compile_route(candidate, {'op':'route', 'sourceId':table_id, 'pageId':destination, 'field':field, 'returnLabel':''}, profile)
                # Existing verified mappings/focus/other handlers remain exact.
                stage([c for c in changes if not c['path'].endswith('/eventHandlers')])
    return result
