"""Repair only omitted separators between complete self-formatting assignments.

This is not an SPL parser. Unknown expressions, raw-event formatting, shared
sources and SPL2 retain normal validation/repair. No expression is reconstructed.
"""
import json
import re
from measurement_constraints import pipeline_commands

FIELD = r'[A-Za-z_][A-Za-z0-9_]*'
QUOTED = r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')'''
ASSIGNMENT = re.compile(r'(' + FIELD + r')\s*=\s*(?:(?i:round)\(\s*\1\s*,\s*[0-6]\s*\)|(?i:strftime)\(\s*\1\s*,\s*' + QUOTED + r'\s*\))')


def separated(command):
    match = re.match(r'(?i:eval)\s+(.+)$', command, re.S)
    if not match: return command
    text, position, parts, missing = match[1], 0, [], False
    while position < len(text):
        assignment = ASSIGNMENT.match(text, position)
        if not assignment: return command
        parts.append(assignment[0])
        end = assignment.end()
        if end == len(text): break
        gap = re.match(r'\s*(,?)\s*', text[end:])
        if not gap[0] or end + gap.end() == len(text): return command
        if not gap[1]: missing = True
        position = end + gap.end()
    return 'eval ' + ', '.join(parts) if missing and len(parts) > 1 else command


def repair_query(query):
    offset = 0 if query.lstrip().startswith('|') else 2
    parsed = '| ' + query if offset else query
    changes, aggregated = [], False
    for start, end, command in pipeline_commands(parsed):
        if re.match(r'(?i:stats)\b', command): aggregated = True
        if not aggregated: continue
        fixed = separated(command)
        if fixed != command:
            segment = parsed[start:end]
            changes.append((start-offset, end-offset, segment.replace(command, fixed, 1)))
    for start, end, value in reversed(changes): query = query[:start] + value + query[end:]
    return query


def revise_tail_rounding(query, precisions):
    """Revise only self-rounds in a trailing run of pure formatting evals.

    Appending round(value,1) after round(value,0) cannot restore precision.
    Never cross a filter, calculation, projection or unknown expression: earlier
    rounding there can affect the population or other derived measurements.
    """
    offset = 0 if query.lstrip().startswith('|') else 2
    parsed = '| ' + query if offset else query
    changes = []
    for start, end, command in reversed(list(pipeline_commands(parsed))):
        header = re.match(r'(?i:eval)\s+', command)
        if not header: break
        position, assignments = header.end(), []
        while position < len(command):
            assignment = ASSIGNMENT.match(command, position)
            if not assignment: break
            assignments.append(assignment)
            if assignment.end() == len(command): position = len(command); break
            gap = re.match(r'\s*,\s*', command[assignment.end():])
            if not gap or assignment.end() + gap.end() == len(command): break
            position = assignment.end() + gap.end()
        if not assignments or position != len(command): break
        fixed = command
        for assignment in reversed(assignments):
            field = assignment[1]
            if field in precisions and re.fullmatch(FIELD + r'\s*=\s*(?i:round)\(.*\)', assignment[0]):
                fixed = fixed[:assignment.start()] + field + '=round(' + field + ',' + str(precisions[field]) + ')' + fixed[assignment.end():]
        if fixed != command:
            changes.append((start-offset, end-offset, parsed[start:end].replace(command, fixed, 1)))
    for start, end, value in changes: query = query[:start] + value + query[end:]
    return query


def selected_table_syntax(document, previous, selected):
    table = document.get('visualizations', {}).get(selected, {})
    old = previous.get('visualizations', {}).get(selected, {})
    source_id = table.get('dataSources', {}).get('primary')
    source = document.get('dataSources', {}).get(source_id, {})
    if (table.get('type') != 'splunk.table' or old.get('type') != 'splunk.table'
            or source.get('type') != 'ds.search' or source_id != old.get('dataSources', {}).get('primary')): return []
    if any(key != selected and source_id in value.get('dataSources', {}).values() for key, value in document['visualizations'].items()): return []
    if any(value.get('type') == 'ds.chain' and value.get('options', {}).get('extend', value.get('extend')) == source_id for value in document.get('dataSources', {}).values()): return []
    query = source.get('options', {}).get('query')
    if not isinstance(query, str) or query == previous.get('dataSources', {}).get(source_id, {}).get('options', {}).get('query'): return []
    fixed = repair_query(query)
    if fixed == query: return []
    return [{'op':'set', 'path':'/dataSources/' + source_id.replace('~','~0').replace('/','~1') + '/options/query', 'value':json.dumps(fixed)}]
