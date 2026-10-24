"""Verified table output formatting; never reconstruct the upstream aggregation."""
import json
import re
from provider_service import ProviderError

TABLE_FORMAT_ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['formatTable']},
    'id': {'type': 'string', 'description': 'The selected existing table ID.'},
    'columns': {'type': 'array', 'maxItems': 16, 'items': {'type': 'object', 'properties': {
        'field': {'type': 'string', 'description': 'Exact existing numeric OUTPUT field from focusedSourceReceipt.'},
        'kind': {'type': 'string', 'enum': ['number', 'datetime']},
        'precision': {'type': 'integer', 'minimum': 0, 'maximum': 6, 'description': 'Decimal places for number; 0 for datetime.'}},
        'required': ['field', 'kind', 'precision'], 'additionalProperties': False}}},
    'required': ['op', 'id', 'columns'], 'additionalProperties': False}


def formatting_only(prompt, selected, document):
    """A narrow presentation-only request; broader edits retain the full schema."""
    if document.get('visualizations', {}).get(selected, {}).get('type') != 'splunk.table': return False
    if not re.search(r'\b(?:round|format|formatting|decimal|precision)\b', prompt, re.I): return False
    # Require an explicit selected/this-table-only scope, not a classifier guess.
    if not re.search(r'\bonly\b[^.!?:]{0,70}\b(?:this|selected)\b[^.!?:]{0,70}\btable\b', prompt, re.I): return False
    if re.search(r'\b(?:add|create|remove|delete|replace|recalculate|calculate|filter|regroup|rename|sort|convert units)\b', prompt, re.I): return False
    return True


def compile_table_format(action, document, receipt):
    if set(action) != set(TABLE_FORMAT_ACTION['required']) or not isinstance(action['columns'], list) or not 1 <= len(action['columns']) <= 16:
        raise ProviderError('Format an existing table with 1 to 16 verified output columns.')
    table = document['visualizations'].get(action['id'], {})
    source_id = table.get('dataSources', {}).get('primary')
    source = document.get('dataSources', {}).get(source_id, {})
    if table.get('type') != 'splunk.table' or source.get('type') != 'ds.search' or not receipt or receipt.get('source') != source_id or receipt.get('table') != action['id']:
        raise ProviderError('formatTable is available only for the selected existing SPL table with a verified focusedSourceReceipt. For a NEW table, format its output aliases with eval round/strftime AFTER aggregation in its search action; do not use formatTable. Preserve other tables and sources.')
    if any(key != action['id'] and source_id in chart.get('dataSources', {}).values() for key, chart in document['visualizations'].items()):
        raise ProviderError('This table shares its source with another chart. Preserve that source and use native table display options for formatting, or explicitly create a separate source first.')
    query = source.get('options', {}).get('query', '')
    if query != receipt.get('query'):
        raise ProviderError('Do not rebuild the table search when formatting. Use formatTable alone against its verified existing output columns; preserve the aggregation and aliases.')
    if not re.search(r'\|\s*(?:stats|chart|timechart)\b', query, re.I):
        raise ProviderError('formatTable requires an existing aggregate search; preserve raw tables using native display options.')
    linked = {field for h in table.get('eventHandlers', []) for field in h.get('options', {}).get('fields', [])}
    numeric = {f['name'] for f in receipt.get('fields', []) if f.get('numeric')}
    assignments, seen = [], set()
    for column in action['columns']:
        if not isinstance(column, dict) or set(column) != {'field', 'kind', 'precision'}:
            raise ProviderError('Each formatted column needs field, kind and precision.')
        field, kind, precision = column['field'], column['kind'], column['precision']
        if not isinstance(field, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', field) or field not in numeric or field in linked or field in seen:
            raise ProviderError('Format only existing numeric output fields from focusedSourceReceipt. Omit absent/already-readable columns and preserve row-navigation fields.')
        if kind not in ('number', 'datetime') or type(precision) is not int or not 0 <= precision <= 6 or (kind == 'datetime' and precision != 0):
            raise ProviderError('Use number precision 0 to 6, or datetime precision 0.')
        assignments.append(field + '=' + ('round(' + field + ',' + str(precision) + ')' if kind == 'number' else 'strftime(' + field + ',"%Y-%m-%d %H:%M:%S %Z")'))
        seen.add(field)
    # Appending a final eval preserves every existing output name, data source
    # property, binding and handler. It adds no aggregation or invented column.
    return {'op': 'set', 'path': '/dataSources/' + source_id.replace('~', '~0').replace('/', '~1') + '/options/query',
            'value': json.dumps(query + ' | eval ' + ', '.join(assignments))}
