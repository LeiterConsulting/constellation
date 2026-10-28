"""Verified per-column sparkline styling, compiled for every native row."""
import copy
import hashlib
import json
import re
from provider_service import ProviderError

ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['tableSparkline']}, 'id': {'type': 'string'},
    'field': {'type': 'string'}, 'sparklineType': {'type': 'string', 'enum': ['unchanged', 'line', 'area']},
    'width': {'type': 'integer', 'minimum': 0, 'maximum': 20000, 'description': '0 preserves width; otherwise at least 30 pixels.'}},
    'required': ['op', 'id', 'field', 'sparklineType', 'width'], 'additionalProperties': False}


def focused_schema(prompt, selected, document, receipt, attachments):
    if attachments or not receipt or receipt.get('status') == 'failed' or receipt.get('table') != selected: return None
    if not re.search(r'\bsparklines?\b', prompt, re.I) or not re.search(r'\bonly\b[^.!?:]{0,50}\b(?:this|selected)\b[^.!?:]{0,50}\btable\b', prompt, re.I): return None
    intent = re.sub(r'\b(?:do not|don.t|never)\b[^.!?]*', '', prompt, flags=re.I)
    if re.search(r'\b(?:add|create|remove|delete|rename|filter|query|search|calculate|regroup|sort|round|color)\b', intent, re.I): return None
    fields = [field['name'] for field in receipt.get('fields', []) if field.get('cellKind') in ('sparkline', 'numericArray')]
    named = [name for name in fields if re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', intent)]
    if not named and len(fields) == 1: named = fields
    if len(named) != 1: return None
    styles = set(re.findall(r'\b(line|area)\b', intent.lower()))
    widths = re.findall(r'\bwidth\s*(?:to|of|=|:)?\s*(\d+)\s*(?:pixels?|px)\b', intent, re.I)
    if len(styles) > 1 or len(set(widths)) > 1 or not (styles or widths): return None
    width = int(widths[0]) if widths else 0
    if width and not 30 <= width <= 20000: return None
    schema = copy.deepcopy(ACTION)
    for name, value in (('id', selected), ('field', named[0]), ('sparklineType', next(iter(styles)) if styles else 'unchanged'), ('width', width)):
        schema['properties'][name]['enum'] = [value]
    return schema


def compile_sparkline(action, document, receipt):
    if (set(action) != set(ACTION['required']) or not receipt or not isinstance(action.get('id'), str)
            or not isinstance(action.get('field'), str) or action.get('id') != receipt.get('table')):
        raise ProviderError('Style the selected existing table using its verified focusedSourceReceipt.', 422, 'table_sparkline')
    key, field = action['id'], action['field']
    table = document.get('visualizations', {}).get(key, {})
    verified = next((item for item in receipt.get('fields', []) if item['name'] == field), {})
    if (table.get('type') != 'splunk.table' or table.get('dataSources', {}).get('primary') != receipt.get('source')
            or verified.get('cellKind') not in ('sparkline', 'numericArray')):
        raise ProviderError('A sparkline needs a verified numeric-array output column. Add its actual time-bucketed calculation before styling it.', 422, 'table_sparkline')
    if action['sparklineType'] not in ('unchanged', 'line', 'area') or type(action['width']) is not int or not (action['width'] == 0 or 30 <= action['width'] <= 20000):
        raise ProviderError('Use line/area/unchanged and a column width of 0 (preserve) or 30–20000 pixels.', 422, 'table_sparkline')
    context = copy.deepcopy(table.get('context', {}))
    options = copy.deepcopy(table.get('options', {}))
    if not isinstance(context, dict) or not isinstance(options.get('columnFormat', {}), dict):
        raise ProviderError('Preserve this advanced native context with targeted edits.', 422, 'table_sparkline')
    column = options.setdefault('columnFormat', {}).setdefault(field, {})
    if not isinstance(column, dict): raise ProviderError('The existing column format is not an object.', 422, 'table_sparkline')
    prefix = 'ctSparkline_' + hashlib.sha256((key + '\0' + field).encode()).hexdigest()[:12]
    def mapping(suffix, value):
        name = prefix + suffix
        data = [{'match': kind, 'value': value} for kind in ('sparkline', 'array')]
        while name in context and context[name] != data: name += '_'
        context[name] = data
        return '> table | seriesByName(' + json.dumps(field) + ') | type() | matchValue(' + name + ')'
    column['cellTypes'] = mapping('Cells', 'SparklineCell')
    if action['sparklineType'] != 'unchanged': column['sparklineTypes'] = mapping('Types', action['sparklineType'])
    if action['width']: column['width'] = action['width']
    path = '/visualizations/' + key.replace('~', '~0').replace('/', '~1')
    return [{'op': 'set', 'path': path + '/context', 'value': json.dumps(context)},
            {'op': 'set', 'path': path + '/options', 'value': json.dumps(options)}]


INSTRUCTIONS = '''Style ONLY the verified selected table column using ONE
tableSparkline action {op,id,field,sparklineType,width}. Follow the exact allowed
schema values; 0 preserves width and unchanged preserves line/area styling.
The server compiles native DOS mappings for EVERY row, including rows outside the
bounded preview. Never return a one-element per-row array, standalone unused
context, raw native edits or a query change. Preserve other columns, context,
handlers, pages and searches. Return JSON message,changes,suggestions. History is
completed work; request is current. Do not claim a save.'''
