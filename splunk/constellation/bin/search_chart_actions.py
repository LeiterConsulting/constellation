"""Typed, provider-neutral builders for scoped searches and native chart bindings."""
import copy
import json
import re
from provider_service import ProviderError
from search_scope import scoped_suffix
from token_service import without_entity_equality, default_token_values

SEARCH_ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['search']},
    'id': {'type': 'string'},
    'pipeline': {'type': 'string', 'description': 'A pipe followed by filters/aggregations appended to dataProfile.baseQuery. Do not repeat or replace the base query. The inspected language and time range are supplied by the compiler.'}},
    'required': ['op', 'id', 'pipeline'], 'additionalProperties': False}
CHART_TYPES = ('splunk.line', 'splunk.area', 'splunk.column', 'splunk.bar', 'splunk.singlevalue', 'splunk.table')
TOKEN_ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['token']}, 'name': {'type': 'string'},
    'value': {'type': 'string', 'description': 'A native default token value, for example * for an all-entities search filter.'}},
    'required': ['op', 'name', 'value'], 'additionalProperties': False}
FILTER_ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['filter']}, 'sourceId': {'type': 'string'},
    'field': {'type': 'string', 'description': 'Verified source field to filter before aggregation.'},
    'token': {'type': 'string', 'description': 'Native token name, without dollar signs or filter syntax. Define its default with op:token.'}},
    'required': ['op', 'sourceId', 'field', 'token'], 'additionalProperties': False}
DASHBOARD_ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['dashboard']},
    'title': {'type': 'string'}, 'description': {'type': 'string'}},
    'required': ['op', 'title', 'description'], 'additionalProperties': False}
CHART_ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['chart']}, 'id': {'type': 'string'},
    'chartType': {'type': 'string', 'enum': list(CHART_TYPES)},
    'title': {'type': 'string'}, 'description': {'type': 'string'},
    'sourceId': {'type': 'string', 'description': 'The exact search action id or an existing source ID.'},
    'x': {'type': 'string', 'description': 'Exact output field for the time/category axis. SPL timechart emits _time, not time. Empty for a table or single value.'},
    'y': {'type': 'array', 'maxItems': 80, 'items': {'type': 'string'}, 'description': 'Output field names, never category values. Axis charts allow at most 8 numeric series; tables allow up to 80 ordered columns. One field for a single value. An empty table list shows all returned columns.'}},
    'required': ['op', 'id', 'chartType', 'title', 'description', 'sourceId', 'x', 'y'], 'additionalProperties': False}


def chart_variant_schema(schema, discriminator='chartType'):
    series, single, table = copy.deepcopy(schema), copy.deepcopy(schema), copy.deepcopy(schema)
    series['properties'][discriminator]['enum'] = [kind for kind in schema['properties'][discriminator]['enum'] if kind not in ('splunk.table','splunk.singlevalue')]
    series['properties']['x']['minLength'] = 1
    series['properties']['y'].update(minItems=1,maxItems=8)
    single['properties'][discriminator]['enum'] = ['splunk.singlevalue']
    single['properties']['x']['enum'] = ['']
    single['properties']['y'].update(minItems=1,maxItems=1)
    table['properties'][discriminator]['enum'] = ['splunk.table']
    table['properties']['x']['enum'] = ['']
    table['properties']['y']['maxItems'] = 80
    return {'anyOf': [series, single, table]}

CHART_ACTION_SCHEMA = chart_variant_schema(CHART_ACTION)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,149}', value) or value in ('__proto__', 'constructor', 'prototype'):
        raise ProviderError('Typed searches and charts need safe IDs of at most 150 characters.')
    return value


def compile_token(action, defaults):
    if set(action) != {'op', 'name', 'value'} or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,149}', str(action.get('name', ''))):
        raise ProviderError('A typed token needs a safe name and string value.')
    name = identifier(action['name'])
    value = action['value']
    if not isinstance(value, str) or len(value) > 1000:
        raise ProviderError('Keep the default token value under 1000 characters.')
    try:
        tokens = defaults.setdefault('tokens', {}).setdefault('default', {})
        old = tokens.get(name, {})
        if not isinstance(old, dict): raise TypeError()
        tokens[name] = dict(old, value=value)
    except (AttributeError, TypeError):
        raise ProviderError('Preserve this nonstandard default-token configuration using targeted native edits.') from None


def compile_search(action, document, profile):
    if set(action) != {'op', 'id', 'pipeline'} or not profile:
        raise ProviderError('A typed search needs id, pipeline and an inspected dataProfile.')
    key = identifier(action['id'])
    pipeline = action['pipeline']
    if not isinstance(pipeline, str) or not pipeline.strip().startswith('|') or len(pipeline) > 8000:
        raise ProviderError('Start the typed search pipeline with a pipe; the verified baseQuery is supplied automatically.')
    scope = profile['scope']
    language, earliest = scope.get('language', 'spl'), scope['earliest']
    source_type = 'ds.spl2' if language == 'spl2' else 'ds.search'
    source = copy.deepcopy(document.get('dataSources', {}).get(key, {}))
    if source and source.get('type') != source_type:
        raise ProviderError('Preserve this source type with targeted native edits instead of replacing it with a typed search.')
    source['type'] = source_type
    options = source.setdefault('options', {})
    options['query'] = profile['baseQuery'].strip() + ' ' + pipeline.strip()
    options.setdefault('queryParameters', {}).update(earliest=earliest, latest='now')
    return key, source


def compile_filter(action, document, profile):
    if set(action) != set(FILTER_ACTION['required']) or not profile:
        raise ProviderError('A typed filter needs sourceId, field, token and an inspected data profile.')
    source_id, token = identifier(action['sourceId']), identifier(action['token'])
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,149}', token):
        raise ProviderError('Use a plain native token name without punctuation or dollar signs.')
    field = action['field']
    if not isinstance(field, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', field) or field not in {item['name'] for item in profile['fields']}:
        raise ProviderError('A typed filter needs an exact verified source field with a simple field name.')
    source = document.get('dataSources', {}).get(source_id, {})
    if source.get('type') != 'ds.search' or profile['scope'].get('language', 'spl') != 'spl':
        raise ProviderError('Typed entity filters currently support scoped SPL ds.search sources. Preserve SPL2/chain semantics with targeted native query edits.')
    suffix = scoped_suffix(source.get('options', {}).get('query', ''), profile)
    if suffix is None or (suffix.strip() and not suffix.lstrip().startswith('|')):
        raise ProviderError('The filtered source must preserve the inspected baseQuery before its pipeline.')
    suffix = without_entity_equality(suffix, field, token)
    clause = '| search ' + field + '=$' + token + '|s$'
    # A compiler-added measurement mask may precede an already-correct route
    # clause. Repeated retarget/repair must not append duplicate predicates.
    from measurement_constraints import pipeline_commands
    for _start, _end, command in pipeline_commands(suffix):
        if re.match(r'(?:stats|timechart|chart|eventstats|streamstats)\b', command, re.I): break
        if command == clause[2:]:
            return {'op':'set','path':'/dataSources/'+source_id.replace('~','~0').replace('/','~1')+'/options/query','value':json.dumps(source['options']['query'])}
    query = profile['baseQuery'].strip() + ' ' + clause + (' ' + suffix.strip() if suffix.strip() else '')
    if suffix.strip() == clause or suffix.strip().startswith(clause + ' |'): query = source['options']['query']
    return {'op': 'set', 'path': '/dataSources/' + source_id.replace('~', '~0').replace('/', '~1') + '/options/query', 'value': json.dumps(query)}


def normalize_row_filters(document, previous, profile):
    """Repair exact new row-filter syntax from verified native intent, not prose."""
    if not profile or profile['scope'].get('language', 'spl') != 'spl': return []
    defaults = default_token_values(document)
    verified = {item['name'] for item in profile.get('fields', [])}
    pages = document['layout'].get('layoutDefinitions', {})
    changes, handled = [], set()
    for table in document['visualizations'].values():
        if table.get('type') != 'splunk.table': continue
        handlers = table.get('eventHandlers', [])
        for handler in handlers:
            if handler.get('type') != 'drilldown.setToken': continue
            fields = handler.get('options', {}).get('fields', [])
            targets = [h.get('options', {}).get('tabId') for h in handlers if h.get('type') == 'drilldown.switchToTab' and h.get('options', {}).get('fields', []) == fields]
            sources = {source for target in targets for entry in pages.get(target, {}).get('structure', [])
                       for source in document['visualizations'].get(entry.get('item'), {}).get('dataSources', {}).values()}
            for token in handler.get('options', {}).get('tokens', []):
                name = token.get('token')
                if not isinstance(name, str) or defaults.get(name) != '*': continue
                for field in fields:
                    if field not in verified or token.get('key') != 'row.' + field + '.value': continue
                    for source_id in sources:
                        source = document.get('dataSources', {}).get(source_id, {})
                        query = source.get('options', {}).get('query', '')
                        old = previous.get('dataSources', {}).get(source_id, {}).get('options', {}).get('query')
                        if source.get('type') != 'ds.search' or query == old or source_id in handled: continue
                        suffix = scoped_suffix(query, profile)
                        if suffix is None or without_entity_equality(suffix, field, name) == suffix: continue
                        changes.append(compile_filter({'op':'filter','sourceId':source_id,'field':field,'token':name}, document, profile))
                        handled.add(source_id)
    return changes


def compile_dashboard(action):
    if set(action) != set(DASHBOARD_ACTION['required']) or any(not isinstance(action.get(key), str) or len(action[key]) > maximum for key, maximum in (('title', 200), ('description', 2000))) or not action['title'].strip():
        raise ProviderError('Give the dashboard a concise title and completed description.')
    return [{'op': 'set', 'path': '/' + key, 'value': json.dumps(action[key])} for key in ('title', 'description')]


def compile_chart(action, document):
    if set(action) != set(CHART_ACTION['required']):
        raise ProviderError('A typed chart needs id, chartType, title, description, sourceId, x and y.')
    key, source = identifier(action['id']), identifier(action['sourceId'])
    kind, x, y = action['chartType'], action['x'], action['y']
    if kind not in CHART_TYPES:
        raise ProviderError('Chart ' + key + ': chartType must be one of ' + ', '.join(CHART_TYPES) +
                            '. To move or resize an existing chart, change only its /layout position and canvas bounds; do not rebuild the chart.')
    maximum = 80 if kind == 'splunk.table' else 8
    if not isinstance(x, str) or not isinstance(y, list) or len(y) > maximum:
        raise ProviderError('Chart ' + key + ': x must be a string and y an array of at most ' + str(maximum) + ' output field names. '
                            'Received x type=' + type(x).__name__ + ', y type=' + type(y).__name__ + (', y count=' + str(len(y)) if isinstance(y,list) else '') + '. Use y=[] for a table that should show all returned columns; axis charts need at most 8 named output series. '
                            'To move or resize an existing chart, change only its /layout position and canvas bounds; preserve its bindings.')
    if any(not isinstance(field, str) or not 1 <= len(field) <= 200 or any(ord(c) < 32 for c in field) for field in ([x] if x else []) + y):
        raise ProviderError('Use nonempty output field names under 200 characters for chart bindings.')
    if (kind == 'splunk.table' and x) or (kind == 'splunk.singlevalue' and (x or len(y) != 1)) or (kind not in ('splunk.table', 'splunk.singlevalue') and (not x or not y)):
        raise ProviderError('Chart ' + key + ' (' + kind + '): tables use x=""; single values use x="" and one y field; axis charts need x and numeric y fields.')
    if any(not isinstance(action[name], str) or len(action[name]) > maximum for name, maximum in (('title', 200), ('description', 2000))) or not action['title'].strip():
        raise ProviderError('Give the chart a concise title and description.')
    chart = copy.deepcopy(document.get('visualizations', {}).get(key, {}))
    old_kind = chart.get('type')
    chart.update(type=kind, title=action['title'], description=action['description'])
    chart.setdefault('dataSources', {})['primary'] = source
    options = chart.setdefault('options', {})
    if old_kind != kind:
        for channel in ('x', 'y', 'y2', 'category', 'majorValue', 'table'): options.pop(channel, None)
    if kind == 'splunk.singlevalue':
        options['majorValue'] = '> primary | seriesByName(' + json.dumps(y[0]) + ') | lastPoint()'
    elif kind == 'splunk.table':
        options['table'] = '> primary' + (' | frameBySeriesNames(' + ', '.join(json.dumps(field) for field in y) + ')' if y else '')
    else:
        options['x'] = '> primary | seriesByName(' + json.dumps(x) + ')'
        options['y'] = '> primary | frameBySeriesNames(' + ', '.join(json.dumps(field) for field in y) + ')'
    return key, chart


def normalize_field_bindings(document, previous, profile):
    """Compile explicit field references from a repair into native DOS bindings.

    Only changed channels backed by actual searches qualify. The data validator
    still proves that every named field exists in the bounded search output.
    Imported expressions and unrelated native options remain byte-for-byte intact.
    """
    if not profile: return []
    changes = []
    for key, chart in document.get('visualizations', {}).items():
        if chart.get('type') not in CHART_TYPES: continue
        source = document.get('dataSources', {}).get(chart.get('dataSources', {}).get('primary'), {})
        if source.get('type') not in ('ds.search', 'ds.spl2', 'ds.chain'): continue
        options = chart.get('options', {})
        old = previous.get('visualizations', {}).get(key, {}).get('options', {})
        for channel in ('x', 'y', 'y2', 'majorValue', 'table'):
            value = options.get(channel)
            if channel not in options or value == old.get(channel): continue
            if isinstance(value, dict) and set(value) == {'field'}: value = value['field']
            fields = value if isinstance(value, list) else [value]
            if not 1 <= len(fields) <= (1 if channel in ('x', 'majorValue') else 8): continue
            if any(not isinstance(field, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_ .:-]{0,199}', field) for field in fields): continue
            expression = '> primary | ' + ('seriesByName' if channel in ('x', 'majorValue') else 'frameBySeriesNames') + '(' + ', '.join(json.dumps(field) for field in fields) + ')'
            if channel == 'majorValue': expression += ' | lastPoint()'
            path = '/visualizations/' + key.replace('~', '~0').replace('/', '~1') + '/options/' + channel
            changes.append({'op': 'set', 'path': path, 'value': json.dumps(expression)})
    return changes


def normalize_event_counts(document, previous, profile):
    """An empty SPL count() with a single alias cannot produce that field.

    Compile this exact event-count shorthand only in changed aggregate searches.
    SPL2, quoted text, field counts and wildcard output aliases are untouched.
    """
    if not profile: return []
    changes = []
    for key, source in document.get('dataSources', {}).items():
        if source.get('type') != 'ds.search': continue
        query = source.get('options', {}).get('query', '')
        if not isinstance(query, str) or query == previous.get('dataSources', {}).get(key, {}).get('options', {}).get('query'): continue
        masked = re.sub(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*' ''', lambda match: ' ' * len(match[0]), query, flags=re.X)
        edits = []
        for command in re.finditer(r'(?:^|\|)\s*(?:stats|eventstats|streamstats|timechart|chart)\b([^|]*)', masked, re.I):
            for match in re.finditer(r'\bcount\(\s*\)(?=\s+as\s+[A-Za-z_][A-Za-z0-9_]*(?:\s|,|$))', command[1], re.I):
                edits.append((command.start(1) + match.start(), command.start(1) + match.end()))
        normalized = query
        for start, end in reversed(edits): normalized = normalized[:start] + 'count' + normalized[end:]
        if normalized != query:
            path = '/dataSources/' + key.replace('~', '~0').replace('/', '~1') + '/options/query'
            changes.append({'op': 'set', 'path': path, 'value': json.dumps(normalized)})
    return changes
