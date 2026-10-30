"""Bounded source-shape checks, not a general dynamic-options interpreter.

Only direct selectors have provable field provenance. Derived/native expressions
stay native; result values are inspected locally and never included in feedback.
"""
import ast
from datetime import datetime
import math
import re
from measurement_constraints import pipeline_commands
from provider_service import ProviderError
from native_geography import validate_geography

CONTRACTS = {
    'splunk.map': {'source': 'Put coordinate/area bindings INSIDE options.layers[]. Marker/bubble layers select finite latitude (-90..90) and longitude (-180..180) in degrees. Bubble sizes are nonnegative; choropleth layers select areaIds/areaValues with a native geo://default/world or geo://default/us source. Do not infer coordinates or geocode without a verified data relationship. Explicitly retain/explain unlocated observations; never turn missing coordinates into zero.', 'events': ['map.load', 'map.click']},
    'splunk.choropleth.svg': {'source': 'options.svg is the supplied literal SVG/data URI or existing native asset reference; never invent an upload ID. Inline paths need unique id and d attributes. areaIds selects exact matching IDs and areaValues a numeric series; areaColors can use a native context mapping. Missing values remain missing. Opaque assets are preserved, not fetched or claimed verified.', 'events': ['area.click']},
    'splunk.sankey': {'source': 'Exact source and target fields; linkValues selects one numeric weight. Missing measurements stay null.', 'events': ['node.click', 'link.click']},
    'splunk.linkgraph': {'source': 'Ordered adjacent relationship columns; fieldOrder is an array of exact output field names or a native field selector.', 'events': ['node.click', 'node.mouseover']},
    'splunk.parallelcoordinates': {'source': 'First output column is the category; subsequent columns are numeric axes. Project the intended ordered columns in the search.', 'events': []},
    'splunk.pie': {'source': 'label selects one category series; value selects one numeric series. Preserve null measurements.', 'events': ['point.click']},
    'splunk.punchcard': {'source': 'x and y select category series; size selects one nonnegative numeric series.', 'events': ['point.click', 'legend.click']},
    'splunk.timeline': {'source': 'x selects standard _time (Splunk adapts its epoch seconds) or an ISO timestamp string, y selects a lane, duration selects nonnegative milliseconds. Do not bind raw custom epoch numbers directly: derive a separate ISO field with strftime(start_ms/1000,"%Y-%m-%dT%H:%M:%S.%3N%:z") when input is milliseconds. Preserve original timestamps. durationUnit requires its documented version.', 'events': ['event.click', 'lane.click', 'legend.click']},
    'splunk.networkGraph': {'source': 'Native node membership is inferred from the source series. Include target-only nodes as source rows with null target in a graph-only chain, preserving actual edges and weights. A read-only closure uses eval constellation_role=mvappend("edge","node") | mvexpand constellation_role | eval source=if(constellation_role="edge",source,target), target=if(constellation_role="edge",target,null()) | fields - constellation_role (adapt literal endpoint aliases). Do not use blocked appendpipe/subsearches or duplicate self-links. nodeIds is for styling; it must also include BOTH endpoint sets. A separate nodeSource chain can mvappend/mvexpand both fields then stats by id. Bind nodeIds/nodeTexts and node values explicitly to that aligned node frame. Use explicit series selectors for custom names.', 'events': ['node.click', 'node.mouseOver', 'node.mouseOut', 'node.drag']},
}


def numeric(value):
    if isinstance(value, (bool, list, dict)): return False
    try: return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError): return False


def timestamp(value):
    if not isinstance(value, str) or not re.match(r'^\d{4}-\d{2}-\d{2}T', value): return False
    try: datetime.fromisoformat(value.replace('Z', '+00:00')); return True
    except ValueError: return False


def present(value):
    return value is not None and value != ''


def field_type(result, name):
    if name == '_time': return 'time'
    declared = next((f.get('type') for f in result['fields'] if f['name'] == name), None)
    if declared in ('number', 'time', 'string'): return declared
    values = [row.get(name) for row in result['results'] if present(row.get(name))]
    return 'number' if values and all(numeric(value) for value in values) else 'string'


def direct_fields(binding, aliases, outputs):
    """Resolve only bounded direct source/field selectors; None means unproven."""
    if not isinstance(binding, str) or len(binding) > 8000: return None
    match = re.match(r'^\s*>\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?=\||$)', binding)
    if not match or match[1] not in aliases: return None
    source = aliases[match[1]]
    if source not in outputs: return None
    result = outputs[source]; names = [field['name'] for field in result['fields']]
    suffix = binding[match.end():]
    commands = pipeline_commands(suffix)
    if suffix.strip() and not commands: return None
    for _, _, command in commands:
        operation = re.fullmatch(r'(\w+)\((.*)\)', command, re.S)
        if not operation: return None
        kind, args = operation.groups()
        if kind in ('seriesByName', 'frameBySeriesNames', 'seriesByType', 'frameBySeriesTypes', 'seriesByPrioritizedTypes'):
            try: values = ast.literal_eval('[' + args + ']')
            except (ValueError, SyntaxError, RecursionError): return None
            if not values or any(not isinstance(value, str) for value in values): return None
            if kind in ('seriesByName', 'frameBySeriesNames'): names = values
            elif kind == 'seriesByPrioritizedTypes':
                names = next(([name] for value in values for name in names if field_type(result, name) == value), [])
            else:
                names = [name for name in names if field_type(result, name) in values]
                if kind == 'seriesByType': names = names[:1]
        elif kind in ('seriesByIndex', 'frameBySeriesIndexRange'):
            if not re.fullmatch(r'\s*\d+\s*(?:,\s*\d+\s*)?', args): return None
            indexes = [int(value) for value in args.split(',')]
            names = names[indexes[0]:indexes[0]+1] if kind == 'seriesByIndex' else names[indexes[0]:indexes[1] if len(indexes) > 1 else None]
        elif kind in ('getField', 'lastPoint') and not args.strip(): pass
        else: return None
    return source, names


def validate_shape(item, outputs):
    kind = item.get('type')
    axes = kind in ('splunk.line', 'splunk.area', 'splunk.bar', 'splunk.column', 'splunk.scatter')
    if kind not in CONTRACTS and not axes: return
    aliases = item.get('dataSources', {}); source = aliases.get('primary')
    if source not in outputs: return
    if kind in ('splunk.map', 'splunk.choropleth.svg'):
        validate_geography(item, outputs, direct_fields)
        return
    result = outputs[source]; fields = [field['name'] for field in result['fields']]
    options = item.get('options', {})

    def fail(detail):
        raise ProviderError('Native ' + kind + ': ' + detail + ' Use actual output fields and preserve unrelated searches.', 422, 'native_data_shape')

    def channel(name, default=None, number=False, nonnegative=False, time=False):
        binding = options.get(name, default)
        if binding is None: return
        if isinstance(binding, str) and not binding.lstrip().startswith(('>', '$')):
            fail(name + ' needs a native source binding, not a field-name string.')
        selected = direct_fields(binding, aliases, outputs)
        if selected is None: return
        sid, names = selected; actual = outputs[sid]
        if not actual['fields'] and not actual['results']: return
        if len(names) != 1 or names[0] not in {field['name'] for field in actual['fields']}:
            fail(name + ' must select one existing source series.')
        values = [row.get(names[0]) for row in actual['results'] if present(row.get(names[0]))]
        if any(isinstance(value, (dict, list)) for value in values): fail(name + ' needs scalar output; expand multivalue observations explicitly.')
        if time and any(not timestamp(value) and not (names[0] == '_time' and numeric(value)) for value in values):
            fail('x needs standard _time or an ISO timestamp series. Raw custom epoch numbers do not render reliably; derive a separate ISO field using the declared input unit, preserving original timestamps.')
        if number and any(not numeric(value) for value in values): fail(name + ' needs numeric output; do not replace unknown measurements with zero.')
        if nonnegative and any(numeric(value) and float(value) < 0 for value in values): fail(name + ' needs nonnegative values; resolve the intended measurement instead of clamping it silently.')
        return selected

    if axes:
        channel('x')
        for name in ('y', 'y2'):
            selected = direct_fields(options.get(name), aliases, outputs)
            if selected is None: continue
            sid, names = selected; actual = outputs[sid]
            if not actual['fields'] and not actual['results']: continue
            if not names or set(names) - {f['name'] for f in actual['fields']}:
                fail(name + ' must select existing numeric series; split timecharts bind the actual returned series, not absent category names.')
            if '_time' in names or any(present(row.get(field)) and not numeric(row.get(field)) for row in actual['results'] for field in names):
                fail(name + ' needs numeric series; keep category/time fields out of the metric frame.')
    elif kind == 'splunk.sankey':
        if fields and not {'source', 'target'} <= set(fields): fail('The search must return the exact source and target fields.')
        channel('linkValues', '> primary | seriesByName("value")' if 'value' in fields else '> primary | seriesByType("number")', True, True)
        for name in ('source', 'target'):
            channel(name, '> primary | seriesByName("' + name + '")')
    elif kind == 'splunk.parallelcoordinates':
        if fields and len(fields) < 2: fail('Return a category column followed by numeric axis columns.')
        for name in fields[1:]:
            if any(present(row.get(name)) and not numeric(row.get(name)) for row in result['results']):
                fail('Every axis after the first category column must be numeric. Project only the intended category and metrics.')
    elif kind == 'splunk.linkgraph':
        order = options.get('fieldOrder')
        if isinstance(order, list) and (len(order) < 2 or len(set(order)) != len(order) or set(order) - set(fields)):
            fail('fieldOrder needs at least two distinct actual output fields, in relationship order.')
        if fields and len(fields) < 2: fail('Return at least two relationship columns.')
    elif kind == 'splunk.pie':
        channel('label', '> primary | seriesByIndex(0)')
        channel('value', '> primary | seriesByIndex(1)', True, True)
    elif kind == 'splunk.punchcard':
        channel('x', '> primary | seriesByIndex(0)'); channel('y', '> primary | seriesByIndex(1)')
        channel('size', '> primary | seriesByIndex(2)', True, True)
    elif kind == 'splunk.timeline':
        channel('x', '> primary | seriesByType("time")', time=True)
        channel('y', '> primary | seriesByPrioritizedTypes("string","number")')
        channel('duration', number=True, nonnegative=True)
    elif kind == 'splunk.networkGraph':
        start = channel('source', '> primary | frameBySeriesTypes("string") | seriesByIndex(0)')
        end = channel('target', '> primary | frameBySeriesTypes("string") | seriesByIndex(1)')
        if start is not None and end is not None:
            if len(outputs[start[0]]['results'])!=len(outputs[end[0]]['results']):
                fail('source and target must align one endpoint per link row; do not bind a node frame as an edge endpoint frame.')
            source_ids = {str(row[start[1][0]]) for row in outputs[start[0]]['results'] if present(row.get(start[1][0]))}
            target_ids = {str(row[end[1][0]]) for row in outputs[end[0]]['results'] if present(row.get(end[1][0]))}
            if target_ids - source_ids:
                fail('Native graph membership comes from source, not nodeIds. Include target-only endpoints as source rows with null target in a graph-only chain, preserving real links and shared edge weights.')
        node_binding = options.get('nodeIds', '> source')
        nodes = start if isinstance(node_binding, str) and node_binding.strip() == '> source' else channel('nodeIds')
        if nodes is not None:
            sid, names = nodes
            ids = {str(row[names[0]]) for row in outputs[sid]['results'] if present(row.get(names[0]))}
            endpoints = set()
            for selected in (start, end):
                if selected is not None:
                    endpoint_sid, fields = selected
                    endpoints.update(str(row[fields[0]]) for row in outputs[endpoint_sid]['results'] if present(row.get(fields[0])))
            if endpoints - ids:
                fail('nodeIds omits ' + str(len(endpoints - ids)) + ' observed source/target endpoints. Include both endpoint sets in an aligned node source; the default source-only node list can hide nodes and links.')
            for name in ('nodeTexts', 'nodeValues', 'nodeColors', 'nodeTypes', 'nodeIcons', 'nodeIconColors', 'nodeSize', 'xPositions', 'yPositions'):
                selected = direct_fields(options.get(name), aliases, outputs)
                if selected is not None and len(outputs[selected[0]]['results']) != len(outputs[sid]['results']):
                    fail(name + ' must align one value with each nodeIds row; link rows and node rows are different populations.')
        for name in ('nodeValues', 'linkWidth', 'nodeSize', 'xPositions', 'yPositions'):
            if isinstance(options.get(name), str) and options[name].lstrip().startswith('>'): channel(name, number=True, nonnegative=name in ('nodeSize', 'linkWidth'))
