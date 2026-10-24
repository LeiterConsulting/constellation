"""Typed, provider-neutral builders for scoped searches and native chart bindings."""
import copy
import json
import re
from provider_service import ProviderError

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
CHART_ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['chart']}, 'id': {'type': 'string'},
    'chartType': {'type': 'string', 'enum': list(CHART_TYPES)},
    'title': {'type': 'string'}, 'description': {'type': 'string'},
    'sourceId': {'type': 'string', 'description': 'The exact search action id or an existing source ID.'},
    'x': {'type': 'string', 'description': 'Output field for the time/category axis; empty for a table or single value.'},
    'y': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Numeric output fields, or ordered visible fields for a table. One field for a single value; an empty table list shows all output fields.'}},
    'required': ['op', 'id', 'chartType', 'title', 'description', 'sourceId', 'x', 'y'], 'additionalProperties': False}


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


def compile_chart(action, document):
    if set(action) != set(CHART_ACTION['required']):
        raise ProviderError('A typed chart needs id, chartType, title, description, sourceId, x and y.')
    key, source = identifier(action['id']), identifier(action['sourceId'])
    kind, x, y = action['chartType'], action['x'], action['y']
    if kind not in CHART_TYPES or not isinstance(x, str) or not isinstance(y, list) or len(y) > 8:
        raise ProviderError('Use a supported typed chart with explicit output fields.')
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
