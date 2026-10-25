"""Repair only an exact invalid time alias using executed timechart metadata."""
import json
import re


def verified_time_axes(document, previous, receipts):
    changes = []
    outputs = {r['source']: set(r.get('fields', [])) for r in receipts if r.get('source') and r.get('status') == 'results'}
    for key, chart in document.get('visualizations', {}).items():
        if chart.get('type') not in ('splunk.line', 'splunk.area', 'splunk.column', 'splunk.bar'): continue
        binding = chart.get('options', {}).get('x')
        if binding == previous.get('visualizations', {}).get(key, {}).get('options', {}).get('x'): continue
        if not isinstance(binding, str) or not re.fullmatch(r'''\s*>\s*primary\s*\|\s*seriesByName\(\s*(['"])time\1\s*\)\s*''', binding): continue
        source_id = chart.get('dataSources', {}).get('primary')
        fields = outputs.get(source_id, set())
        source = document.get('dataSources', {}).get(source_id, {})
        if source.get('type') != 'ds.search' or '_time' not in fields or 'time' in fields: continue
        query = source.get('options', {}).get('query', '')
        # Quoted prose mentioning timechart is not an execution command.
        syntax = re.sub(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*' ''', '""', query, flags=re.X)
        if not re.search(r'(?:^|\|)\s*timechart\b', syntax, re.I): continue
        changes.append({'op': 'set', 'path': '/visualizations/' + key.replace('~', '~0').replace('/', '~1') + '/options/x',
                        'value': json.dumps('> primary | seriesByName("_time")')})
    return changes
