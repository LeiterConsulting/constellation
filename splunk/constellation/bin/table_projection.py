"""Check explicit new table output aliases against verified fields and projection."""
import json
import re
from provider_service import ProviderError


def focused_calculation(prompt, selected, document, profile, receipt, attachments):
    """One explicit new aggregate on an exclusive inspected SPL table source."""
    if attachments or not profile or not receipt or receipt.get('status')=='failed' or profile.get('scope',{}).get('language','spl')!='spl':return None
    table,requested,_fields=requested_columns(prompt,selected,document,[])
    if len(requested)!=1 or not re.search(r'(?i)\bchange no other element\b|\bto only this selected\b.{0,50}\btable\b',prompt):return None
    if re.search(r'\b(?:move|resize|rename|retarget|remove|delete|create)\b',prompt,re.I):return None
    aggregates=re.findall(r'\b(avg|min|max|sum|count|latest|earliest)\(\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\)\s+AS\s+([A-Za-z_][A-Za-z0-9_]*)\b',prompt,re.I)
    if len(aggregates)!=1 or aggregates[0][2]in {f['name']for f in receipt.get('fields',[])}:return None
    if aggregates[0][1]not in {f['name']for f in profile.get('fields',[])if f.get('numeric')is True}:return None
    bindings=table.get('dataSources',{});sid=bindings.get('primary')
    source=document.get('dataSources',{}).get(sid,{})
    if set(bindings)!={'primary'}or source.get('type')!='ds.search':return None
    if any(key!=selected and sid in v.get('dataSources',{}).values()for key,v in document['visualizations'].items()):return None
    if any(sid in v.get('dataSources',{}).values()for v in document.get('inputs',{}).values()):return None
    if any(v.get('options',{}).get('extend',v.get('extend'))==sid for v in document.get('dataSources',{}).values()):return None
    from search_scope import scoped_suffix
    suffix=scoped_suffix(source.get('options',{}).get('query',''),profile)
    if suffix is None:return None
    return {'tableId':selected,'sourceId':sid,'pipeline':suffix,'requestedAliases':sorted(requested),
            'existingOutputFields':[f['name']for f in receipt.get('fields',[])]}


CALCULATION_INSTRUCTIONS = '''Update only the selected table's CURRENT search.
Return JSON message,changes,suggestions with ONE search action {op:"search",id,
pipeline}. Use calculationOnly.sourceId and edit its supplied EXACT existing
pipeline to add the requested aggregate and exact AS alias. Preserve existing
aggregations, grouping, formatting, filters and columns. Do not replace the search
with a new summary. Add the aggregate within its existing stats command before BY;
retain that grouping. If a terminal fields/table projection exists, include the
new alias there too. The server prepends the verified base query, preserves all
native properties and exposes the new column only AFTER actual output verifies it.
Do not emit native, chart, binding, page or navigation actions. Keep metadata-only
existingOutputFields and the durable brief's units, exclusions and populations.
Never fill missing/excluded temperatures with zero or drop independent Wi-Fi
events. The server's temperature null mask retains other measurements. Preserve
the source scope and time range; no files or result rows are in this context.
History is completed work; request is the current instruction. On recovery replace
the complete pipeline against the original selected source, retaining successful
query checks. Return a short visible-result message; never claim a save.'''


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


def validate_creation_columns(prompt, document, previous, profile, receipts):
    """An explicit field list for one new raw table must survive query and DOS.

    Only verified literal identifiers and a single ordinary unaggregated SPL
    table are eligible. Existing dashboards and ambiguous targets stay native.
    """
    if previous.get('visualizations') or not profile: return
    match = re.search(r'\braw(?:\s+reading)?\s+table\s+with\s+([A-Za-z_][A-Za-z0-9_.]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_.]*)*)', prompt, re.I)
    if not match: return
    known = {field['name'] for field in profile.get('fields', [])}
    requested = {name.strip().rstrip('.') for name in match[1].split(',')}
    requested.update(re.findall(r'\bAlso\s+include\s+([A-Za-z_][A-Za-z0-9_.]*)\s+in\s+the\s+raw\s+table\b', prompt, re.I))
    requested &= known
    if not requested: return
    from measurement_constraints import pipeline_commands
    from search_scope import scoped_suffix
    tables = []
    for table in document.get('visualizations', {}).values():
        source = document.get('dataSources', {}).get(table.get('dataSources', {}).get('primary'), {})
        if table.get('type') != 'splunk.table' or source.get('type') != 'ds.search': continue
        suffix = scoped_suffix(source.get('options', {}).get('query', ''), profile)
        if suffix is not None and not any(re.match(r'(?:stats|timechart|chart|tstats|top|rare|transpose|xyseries)\b', command, re.I) for _, _, command in pipeline_commands(suffix)):
            tables.append(table)
    if len(tables) != 1: return  # Never choose between several raw tables.
    table = tables[0];sid = table['dataSources']['primary']
    fields = next((set(receipt['fields']) for receipt in receipts if receipt.get('source') == sid and receipt.get('fields')), None)
    if fields is None: return
    missing = requested - fields
    projections = re.findall(r'\bframeBySeriesNames\(([^)]*)\)', str(table.get('options', {}).get('table', '')))
    for args in projections: missing |= requested - set(re.findall(r'''['"]([^'"]+)['"]''', args))
    if missing:
        raise ProviderError('The raw reading table must return and display the explicitly requested verified fields: ' + ', '.join(sorted(missing))[:300] + '. Retain its raw event grain, existing columns, filters and unrelated charts.', 422, 'table_projection')


def validate_selected_calculation(prompt, selected, candidate, previous):
    """Explicit table-only calculations cannot edit a different element/source."""
    _table, requested, _fields = requested_columns(prompt, selected, previous, [])
    if not requested or not re.search(r'(?i)\bchange no other element\b|\bto only this selected\b.{0,50}\btable\b', prompt): return
    if candidate == previous: return  # A clarification can legitimately make no edits.
    visualizations = previous.get('visualizations', {})
    if any(candidate.get('visualizations', {}).get(key) != value for key, value in visualizations.items() if key != selected) or set(candidate.get('visualizations', {})) != set(visualizations):
        raise ProviderError('This calculation is for selected table ' + selected[:100] + ' only. Preserve every other visualization; do not switch to a differently named summary table.', 422, 'table_focus')
    allowed = set(visualizations[selected].get('dataSources', {}).values()) | set(candidate['visualizations'][selected].get('dataSources', {}).values())
    shared = {source for key, chart in visualizations.items() if key != selected for source in chart.get('dataSources', {}).values()}
    for source in set(previous.get('dataSources', {})) | set(candidate.get('dataSources', {})):
        if previous.get('dataSources', {}).get(source) != candidate.get('dataSources', {}).get(source) and (source not in allowed or source in shared):
            raise ProviderError('Change only the selected table source. Preserve unrelated/shared sources; clone a shared source and bind the selected table if necessary.', 422, 'table_focus')
    if any(previous.get(key) != candidate.get(key) for key in set(previous) | set(candidate) if key not in ('visualizations', 'dataSources')):
        raise ProviderError('This table calculation must preserve the dashboard layout, inputs, defaults and other properties.', 422, 'table_focus')


def isolate_selected_calculation(prompt, selected, candidate, previous):
    """Clone a changed shared search only for an explicit table-only calculation."""
    import hashlib
    _table, requested, _fields = requested_columns(prompt, selected, previous, [])
    if not requested or not re.search(r'(?i)\bchange no other element\b|\bto only this selected\b.{0,50}\btable\b', prompt): return []
    before_table = previous.get('visualizations', {}).get(selected, {})
    after_table = candidate.get('visualizations', {}).get(selected, {})
    bindings = before_table.get('dataSources', {})
    if set(bindings) != {'primary'} or after_table.get('dataSources') != bindings: return []
    source = bindings['primary']
    original = previous.get('dataSources', {}).get(source)
    changed = candidate.get('dataSources', {}).get(source)
    shared = any(source in chart.get('dataSources', {}).values() for key, chart in previous.get('visualizations', {}).items() if key != selected)
    if not shared or original == changed or not original or not changed or original.get('type') != 'ds.search' or changed.get('type') != 'ds.search': return []
    identifier = 'table_' + hashlib.sha256((selected + '\0' + source).encode()).hexdigest()[:20]
    if identifier in candidate.get('dataSources', {}): return []  # Do not overwrite native work.
    escape = lambda value: value.replace('~','~0').replace('/','~1')
    return [{'op':'set','path':'/dataSources/' + identifier,'value':json.dumps(changed)},
            {'op':'set','path':'/dataSources/' + escape(source),'value':json.dumps(original)},
            {'op':'set','path':'/visualizations/' + escape(selected) + '/dataSources/primary','value':json.dumps(identifier)}]
