"""Unambiguous native string encoding only; never infer a reference or expression."""
import json
import re


def normalize_reference_text(action, document):
    if not isinstance(action, dict) or action.get('op') != 'set' or not isinstance(action.get('value'), str): return action
    value, path = action['value'], action.get('path')
    try: json.loads(value); return action
    except ValueError: pass
    # Some adapters return a literal hex color rather than its JSON encoding.
    # Admit only this native string slot on a known icon; no expression/reference
    # inference, arbitrary malformed JSON, or color substitution is involved.
    color = re.fullmatch(r'/visualizations/([^/]+)/options/iconColor', path) if isinstance(path, str) else None
    if color and re.fullmatch(r'#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?', value):
        identifier = color[1].replace('~1', '/').replace('~0', '~')
        if document.get('visualizations', {}).get(identifier, {}).get('type') == 'splunk.singlevalueicon':
            return dict(action, value=json.dumps(value))
    match = re.fullmatch(r'/visualizations/([^/]+)/(dataSources/primary|options/table)', path) if isinstance(path,str) else None
    if not match: return action
    key = match[1].replace('~1','/').replace('~0','~')
    chart = document.get('visualizations', {}).get(key)
    if not chart: return action
    if match[2] == 'dataSources/primary' and value in document.get('dataSources', {}):
        return dict(action, value=json.dumps(value))
    if match[2] != 'options/table' or chart.get('type') != 'splunk.table' or not (value.startswith('">') and value.endswith('"')): return action
    text = value[1:-1]
    binding = re.fullmatch(r'>\s*primary\s*\|\s*frameBySeriesNames\((.*)\)', text)
    if not binding: return action
    try: fields = json.loads('[' + binding[1] + ']')
    except ValueError: return action
    if not fields or any(not isinstance(field,str) or not 1 <= len(field) <= 200 or any(ord(c)<32 for c in field) for field in fields): return action
    return dict(action,value=json.dumps(text))
