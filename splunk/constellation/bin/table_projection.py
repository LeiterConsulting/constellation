"""Check explicit new table output aliases against verified fields and projection."""
import re
from provider_service import ProviderError


def validate_requested_columns(prompt, selected, document, receipts):
    table = document.get('visualizations', {}).get(selected, {})
    if table.get('type') != 'splunk.table' or not re.search(r'\b(?:add|include)\b', prompt, re.I): return
    if re.search(r'\b(?:hidden|internal|helper)\b', prompt, re.I): return
    requested = set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\([^()]{1,200}\)\s+AS\s+([A-Za-z_][A-Za-z0-9_]*)\b', prompt, re.I))
    if not requested: return
    source = table.get('dataSources', {}).get('primary')
    fields = next((set(r['fields']) for r in receipts if r.get('source') == source and r.get('fields')), None)
    if fields is None: return  # No verified output; do not infer it from SPL text.
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
