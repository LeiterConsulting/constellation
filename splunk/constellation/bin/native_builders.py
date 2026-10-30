"""Provider-neutral native bindings for bounded new-board plans.

No search execution or inferred data relationships. Native shape/version/source
validators still inspect the expanded document before atomic acceptance.
"""
import json
import math
import re
from measurement_constraints import pipeline_commands
from provider_service import ProviderError

BASIC = {'splunk.line', 'splunk.area', 'splunk.bar', 'splunk.column', 'splunk.table', 'splunk.singlevalue'}
CHANNELS = {
    **{kind: {'x': 'field', 'y': 'fields'} for kind in sorted(BASIC - {'splunk.table', 'splunk.singlevalue'})},
    'splunk.table': {'columns': 'fields'}, 'splunk.singlevalue': {'value': 'field'},
    'splunk.sankey': {'value': 'field'}, 'splunk.pie': {'label': 'field', 'value': 'field'},
    'splunk.punchcard': {'x': 'field', 'y': 'field', 'size': 'field'},
    'splunk.timeline': {'x': 'field', 'y': 'field', 'duration': 'optional', 'category': 'optional'},
    'splunk.parallelcoordinates': {}, 'splunk.linkgraph': {'fields': 'fields'},
    'splunk.networkGraph': {'source': 'field', 'target': 'field'},
}


def binding_schema(kind):
    properties = {}
    for name, form in CHANNELS[kind].items():
        field = {'type': 'string', 'minLength': 1, 'maxLength': 200}
        properties[name] = ({'type': 'array', 'maxItems': 80 if kind == 'splunk.table' else 8,
                             'items': field} if form == 'fields' else dict(field, minLength=0 if form == 'optional' else 1))
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def selector(fields, frame=False, alias='primary'):
    return '> ' + alias + ' | ' + ('frameBySeriesNames' if frame else 'seriesByName') + '(' + ', '.join(json.dumps(f) for f in fields) + ')'


def native_options(kind, bindings, pipeline):
    if kind not in CHANNELS or not isinstance(bindings, dict) or set(bindings) != set(CHANNELS[kind]):
        raise ProviderError('Use the documented binding channels for each planned native chart.', 422, 'board_bindings')
    for key, form in CHANNELS[kind].items():
        value = bindings[key]; values = value if form == 'fields' else [value]
        if (form == 'fields' and (not isinstance(value, list) or len(value) > (80 if kind == 'splunk.table' else 8))
                or not isinstance(values, list) or any(not isinstance(v, str) or len(v) > 200
                or any(ord(c) < 32 for c in v) or (not v and form != 'optional') for v in values)
                or len(set(values)) != len(values)):
            raise ProviderError('Select distinct literal output fields for native bindings.', 422, 'board_bindings')
    if kind == 'splunk.table':
        return {'table': selector(bindings['columns'], True) if bindings['columns'] else '> primary'}
    if kind == 'splunk.singlevalue':
        options = {'majorValue': selector([bindings['value']]) + ' | lastPoint()'}
        commands = [c for _, _, c in pipeline_commands(pipeline)]
        # A grouped/scalar stats result has no chronological sparkline. Never
        # change genuine timechart-backed single values or existing native work.
        if any(re.match(r'(?i)stats\b', c) for c in commands) and not any(re.match(r'(?i)timechart\b', c) for c in commands):
            options.update(sparklineDisplay='off', trendDisplay='off')
        return options
    if kind in BASIC:
        if not bindings['y']:
            commands = [c for _, _, c in pipeline_commands(pipeline)]
            if bindings['x'] != '_time' or not any(re.match(r'(?i)timechart\b.*\bBY\s+', c) for c in commands):
                raise ProviderError('An empty y list is only for an explicitly split timechart. Otherwise name every numeric output series.', 422, 'board_bindings')
            y = '> primary | frameBySeriesIndexRange(1)'
        else: y = selector(bindings['y'], True)
        return {'x': selector([bindings['x']]), 'y': y}
    if kind == 'splunk.sankey': return {'linkValues': selector([bindings['value']])}
    if kind == 'splunk.linkgraph':
        if len(bindings['fields']) < 2: raise ProviderError('Link graphs need at least two ordered output fields.', 422, 'board_bindings')
        return {'fieldOrder': bindings['fields']}
    if kind == 'splunk.parallelcoordinates': return {}
    return {key: selector([field]) for key, field in bindings.items() if field}


def network_nodes(source_id, bindings):
    """Node membership comes from both actual endpoint columns, not defaults.

    links counts endpoint occurrences in the aggregated topology, not event or
    traffic volume. Uniform node size avoids implying a business measurement.
    """
    fields = [bindings[key] for key in ('source', 'target')]
    if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', f) for f in fields):
        raise ProviderError('Give the planned network endpoints literal output aliases before binding them.', 422, 'board_bindings')
    query = '| eval constellation_node=mvappend(' + ','.join(fields) + ') | mvexpand constellation_node | where isnotnull(constellation_node) | stats count AS links BY constellation_node | rename constellation_node AS id | table id links'
    source = {'type': 'ds.chain', 'options': {'extend': source_id, 'query': query}}
    options = {'nodeIds': selector(['id'], alias='nodeSource'), 'nodeTexts': selector(['id'], alias='nodeSource'),
               'nodeValues': selector(['links'], alias='nodeSource'), 'nodeSize': 28, 'linkWidth': 2,
               'layout': 'grid', 'showDirection': 'oneWay'}
    return source, options


def network_edges(source_id, bindings):
    """Native membership is inferred from source, independently of nodeIds.

    Preserve each actual edge once and add only null-target membership rows.
    This graph-only chain never changes the shared edge/weight population used
    by tables, Sankey charts or the separate aligned node styling chain.
    """
    start, end = (bindings[key] for key in ('source', 'target'))
    if start == end or any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', f) for f in (start,end)):
        raise ProviderError('Use distinct literal output aliases for the network endpoints.', 422, 'board_bindings')
    if 'constellation_role' in (start,end):
        raise ProviderError('Reserve constellation_role for native graph membership; choose another endpoint alias.', 422, 'board_bindings')
    query = ('| eval constellation_role=mvappend("edge","node") | mvexpand constellation_role'
             ' | eval '+start+'=if(constellation_role="edge",'+start+','+end+'), '
             +end+'=if(constellation_role="edge",'+end+',null()) | fields - constellation_role')
    return {'type':'ds.chain','options':{'extend':source_id,'query':query}}


def verified_precision(document, previous, outputs):
    """Presentation-only defaults from local verified values; no rows escape.

    Explicit/inherited precision and existing elements remain unchanged. Shared
    source calculations retain full precision, including table/KPI consumers.
    """
    from native_shapes import direct_fields, numeric, present
    changes = []
    for key, item in document.get('visualizations', {}).items():
        if key in previous.get('visualizations', {}) or item.get('type') != 'splunk.singlevalue': continue
        options = item.get('options', {})
        defaults = document.get('defaults', {}).get('visualizations', {})
        inherited = [defaults.get(kind, {}).get('options', {}) for kind in ('global', 'splunk.singlevalue')]
        selected = direct_fields(options.get('majorValue'), item.get('dataSources', {}), outputs)
        if selected is None or len(selected[1]) != 1: continue
        sid, fields = selected
        source = document.get('dataSources', {}).get(sid, {})
        query = source.get('options', {}).get('query', '')
        commands = [c for _, _, c in pipeline_commands('| '+query.lstrip('| '))] if isinstance(query, str) else []
        if (any(re.match(r'(?i)stats\b', c) for c in commands) and not any(re.match(r'(?i)timechart\b', c) for c in commands)
                and '_time' not in {f['name'] for f in outputs[sid]['fields']}):
            for name in ('sparklineDisplay','trendDisplay'):
                if name not in options and not any(name in v for v in inherited):
                    changes.append({'op':'set','path':'/visualizations/'+key.replace('~','~0').replace('/','~1')+'/options/'+name,'value':'"off"'})
        if 'numberPrecision' in options or any('numberPrecision' in v for v in inherited): continue
        values = [abs(float(row[fields[0]])) for row in outputs[sid]['results'] if present(row.get(fields[0])) and numeric(row[fields[0]])]
        fractions = [v for v in values if v and not v.is_integer()]
        if not fractions: continue
        precision = min(6, max(2, 1 - math.floor(math.log10(min(fractions)))))
        changes.append({'op':'set','path':'/visualizations/'+key.replace('~','~0').replace('/','~1')+'/options/numberPrecision','value':str(precision)})
    return changes
