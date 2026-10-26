"""Check explicit new table output aliases against verified fields and projection."""
import json
import re
from provider_service import ProviderError


def requested_columns(prompt, selected, document, receipts):
    table = document.get('visualizations', {}).get(selected, {})
    if table.get('type') != 'splunk.table' or not re.search(r'\b(?:add|include)\b', prompt, re.I): return table, set(), None
    if re.search(r'\b(?:hidden|internal|helper)\b', prompt, re.I): return table, set(), None
    requested = set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\([^()]{1,200}\)\s+AS\s+([A-Za-z_][A-Za-z0-9_]*)\b', prompt, re.I))
    if not requested: return table, set(), None
    source = table.get('dataSources', {}).get('primary')
    fields = next((set(r['fields']) for r in receipts if r.get('source') == source and r.get('fields')), None)
    return table, requested, fields


def verified_requested_projection(prompt, selected, document, receipts):
    """Append verified requested aliases to a simple terminal table projection.

    Complex DOS expressions retain ordinary model repair. No query, existing
    column, interaction or other element changes here.
    """
    table, requested, fields = requested_columns(prompt, selected, document, receipts)
    if not requested or fields is None or not requested <= fields: return []
    binding = table.get('options', {}).get('table', '')
    if not isinstance(binding, str): return []
    match = re.fullmatch(r'\s*>\s*primary\s*\|\s*frameBySeriesNames\(([^()]*)\)\s*', binding)
    if not match: return []
    try: visible = json.loads('[' + match[1] + ']')
    except (ValueError, TypeError): return []
    if (not visible or any(not isinstance(field, str) for field in visible)
            or not set(visible) <= fields): return []
    missing = sorted(requested - set(visible))
    if not missing: return []
    value = '> primary | frameBySeriesNames(' + ', '.join(json.dumps(field) for field in visible + missing) + ')'
    return [{'op': 'set', 'path': '/visualizations/' + selected.replace('~', '~0').replace('/', '~1') + '/options/table', 'value': json.dumps(value)}]


def validate_requested_columns(prompt, selected, document, receipts):
    table, requested, fields = requested_columns(prompt, selected, document, receipts)
    if not requested or fields is None: return  # Never infer output from SPL text.
    missing = requested - fields
    if missing:
        raise ProviderError('The selected table must return the explicitly requested output columns: ' + ', '.join(sorted(missing))[:300] + '. Preserve its existing columns and interactions.', 422, 'table_projection')
    binding = table.get('options', {}).get('table', '')
    if not isinstance(binding, str): return  # Native feature validation handles invalid types.
    projections = re.findall(r'\bframeBySeriesNames\(([^)]*)\)', binding)
    for args in projections:
        visible = set(re.findall(r'''['"]([^'"]+)['"]''', args))
        hidden = requested - visible
        if hidden:
            raise ProviderError('The query returns the requested columns, but the selected table hides them: ' + ', '.join(sorted(hidden))[:300] + '. Update options.table frameBySeriesNames to display them while retaining existing columns and drilldowns.', 422, 'table_projection')
