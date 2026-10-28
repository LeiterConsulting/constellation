"""Exact selected-table ordering; every compiled change still needs validation."""
import json
import re


def exact_table_sort(prompt, selected, document, profile, receipt, attachments):
    if attachments or not profile or profile.get('scope', {}).get('language', 'spl') != 'spl' or not receipt or receipt.get('status') == 'failed':
        return None
    match = re.fullmatch(r'\s*Sort\s+only\s+(?:this\s+)?(?:selected\s+)?(?:[A-Za-z]+\s+){0,4}table\s+by\s+["`]?([A-Za-z_][A-Za-z0-9_]*)["`]?\s+(?:in\s+)?(ascending|descending|asc|desc)(?:\s+order)?\s*\.?\s*(.*)', prompt, re.I | re.S)
    if not match: return None
    field, direction, tail = match.groups()
    clauses = [clause.strip() for clause in re.split(r'[.!?]', tail) if clause.strip()]
    if tail and (any(not re.match(r'(?:Preserve|Keep)\b', clause, re.I) for clause in clauses)
                 or re.search(r'\b(?:add|create|build|remove|delete|replace|filter|rename|move|resize|sort|convert|except|unless|but|also|instead|not)\b', tail, re.I)):
        return None
    table = document.get('visualizations', {}).get(selected, {})
    sid = table.get('dataSources', {}).get('primary')
    source = document.get('dataSources', {}).get(sid, {})
    if (table.get('type') != 'splunk.table' or set(table.get('dataSources', {})) != {'primary'} or source.get('type') != 'ds.search'
            or receipt.get('table') != selected or receipt.get('source') != sid
            or field not in {item.get('name') for item in receipt.get('fields', [])}): return None
    if any(key != selected and sid in item.get('dataSources', {}).values() for key, item in document['visualizations'].items()): return None
    if any(sid in item.get('dataSources', {}).values() for item in document.get('inputs', {}).values()): return None
    if any(item.get('options', {}).get('extend', item.get('extend')) == sid for item in document.get('dataSources', {}).values()): return None
    query = source.get('options', {}).get('query')
    if not isinstance(query, str): return None
    path = '/dataSources/' + sid.replace('~', '~0').replace('/', '~1') + '/options/query'
    return {'message': 'Sorted the selected table by ' + field + ' in ' + ('descending' if direction.lower().startswith('desc') else 'ascending') + ' order.',
            'changes': [{'op': 'set', 'path': path, 'value': json.dumps(query + ' | sort 0 ' + ('-' if direction.lower().startswith('desc') else '+') + field)}],
            'suggestions': []}
