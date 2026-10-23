"""Bounded, atomic Studio edits. Unknown existing configuration is preserved."""
import copy
import json
import math
import re
from provider_service import ProviderError

ROOTS = {'title', 'description', 'visualizations', 'dataSources', 'inputs', 'layout',
         'defaults', 'expressions', 'applicationProperties'}
UNSAFE = {'__proto__', 'constructor', 'prototype'}


def validate_document(document):
    if not isinstance(document, dict) or not isinstance(document.get('visualizations'), dict) or not isinstance(document.get('layout'), dict):
        raise ProviderError('A Studio definition needs visualizations and a layout.')
    if len(json.dumps(document)) > 1_000_000:
        raise ProviderError('Use a Studio definition under 1 MB.')
    for field in ('title', 'description'):
        if field in document and not isinstance(document[field], str):
            raise ProviderError('Dashboard titles and descriptions must be text.')

    def visit(value, depth=0):
        if depth > 60:
            raise ProviderError('The Studio definition is nested too deeply.')
        if isinstance(value, dict):
            for key, child in value.items():
                if key in UNSAFE:
                    raise ProviderError('The Studio definition contains an unsafe property.')
                visit(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                visit(child, depth + 1)
        elif isinstance(value, float) and not math.isfinite(value):
            raise ProviderError('The Studio definition contains an invalid number.')
    visit(document)
    visualizations = document['visualizations']
    sources, inputs = document.get('dataSources', {}), document.get('inputs', {})
    if not isinstance(sources, dict) or not isinstance(inputs, dict):
        raise ProviderError('Data sources and inputs must be objects.')
    if len(visualizations) > 100 or len(sources) > 200 or len(inputs) > 100:
        raise ProviderError('This workspace supports up to 100 tiles, 200 sources, and 100 inputs.')
    for visualization in visualizations.values():
        if not isinstance(visualization, dict) or not isinstance(visualization.get('type'), str):
            raise ProviderError('Each visualization needs a type.')
        if not isinstance(visualization.get('options', {}), dict):
            raise ProviderError('Visualization options must be an object.')
        bindings = visualization.get('dataSources', {})
        if not isinstance(bindings, dict) or any(not isinstance(source, str) or source not in sources for source in bindings.values()):
            raise ProviderError('A visualization refers to a missing data source.')
    for source in sources.values():
        if not isinstance(source, dict) or not isinstance(source.get('type'), str):
            raise ProviderError('Each data source needs a type.')
        if not isinstance(source.get('options', {}), dict):
            raise ProviderError('Data source options must be an object.')
        extend = source.get('options', {}).get('extend', source.get('extend'))
        if extend is not None and (not isinstance(extend, str) or extend not in sources):
            raise ProviderError('A chain search refers to a missing base search.')
    for source_id in sources:
        seen = set()
        cursor = source_id
        while cursor is not None:
            if cursor in seen:
                raise ProviderError('A chain search contains a cycle.')
            seen.add(cursor)
            source = sources[cursor]
            cursor = source.get('options', {}).get('extend', source.get('extend'))
    layouts = document['layout'].get('layoutDefinitions')
    if layouts is None:
        layouts = {'legacy': document['layout']}
    if not isinstance(layouts, dict) or not layouts or len(layouts) > 30:
        raise ProviderError('Provide between 1 and 30 dashboard layouts.')
    for layout in layouts.values():
        if not isinstance(layout, dict) or layout.get('type') not in ('absolute', 'grid'):
            raise ProviderError('Use an absolute or grid Studio layout.')
        structure = layout.get('structure', [])
        if not isinstance(structure, list):
            raise ProviderError('A layout structure must be a list.')
        for item in structure:
            if not isinstance(item, dict) or not isinstance(item.get('item'), str) or item['item'] not in {**visualizations, **inputs}:
                raise ProviderError('A layout refers to a missing tile or input.')
            if not isinstance(item.get('position', {}), dict):
                raise ProviderError('A tile position must be an object.')
            for axis, size in item.get('position', {}).items():
                if axis in ('x', 'y', 'w', 'h') and (type(size) not in (int, float) or not math.isfinite(size) or size < 0 or size > 20000 or (axis in ('w', 'h') and size == 0)):
                    raise ProviderError('A tile position is outside the supported canvas.')
    tabs = document['layout'].get('tabs', {})
    if not isinstance(tabs, dict) or not isinstance(tabs.get('items', []), list):
        raise ProviderError('Dashboard tabs must contain a list of items.')
    for tab in tabs.get('items', []):
        if not isinstance(tab, dict) or not isinstance(tab.get('layoutId'), str) or tab['layoutId'] not in layouts:
            raise ProviderError('A tab refers to a missing layout.')
    for input_id in document['layout'].get('globalInputs', []):
        if input_id not in inputs:
            raise ProviderError('A global input does not exist.')
    return document


def apply_changes(document, changes):
    if not isinstance(changes, list) or len(changes) > 64:
        raise ProviderError('Use at most 64 changes in one turn.')
    invalid_values = []
    for change in changes:
        if isinstance(change, dict) and change.get('op') == 'set' and isinstance(change.get('value'), str):
            try: json.loads(change['value'])
            except ValueError as error:
                invalid_values.append(str(change.get('path', ''))[:160] + ': ' + getattr(error, 'msg', 'invalid JSON'))
    if invalid_values:
        raise ProviderError('Edit value strings must each decode as JSON. Fix all of these paths: ' + '; '.join(invalid_values)[:1200] + '. Encode plain titles as JSON strings and escape quotes inside SPL queries.')
    draft = copy.deepcopy(document)
    for change in changes:
        if not isinstance(change, dict) or set(change) != {'op', 'path', 'value'} or change['op'] not in ('set', 'remove'):
            raise ProviderError('The agent returned an unsupported document operation.')
        path = change['path']
        if not isinstance(path, str) or not path.startswith('/') or len(path) > 1000 or re.search(r'~(?![01])', path):
            raise ProviderError('The agent returned an invalid document path.')
        parts = [part.replace('~1', '/').replace('~0', '~') for part in path[1:].split('/')]
        if parts[0] not in ROOTS or any(part in UNSAFE for part in parts):
            raise ProviderError('The document path is outside the editable Studio configuration.')
        target = draft
        for part in parts[:-1]:
            if isinstance(target, dict) and part in target:
                target = target[part]
            elif isinstance(target, list) and part.isdigit() and int(part) < len(target):
                target = target[int(part)]
            else:
                raise ProviderError('A parent property in the document path does not exist.')
        key = parts[-1]
        if change['op'] == 'set':
            if not isinstance(change['value'], str) or len(change['value']) > 500_000:
                raise ProviderError('The edit value is too large.')
            try:
                value = json.loads(change['value'])
            except (ValueError, TypeError):
                raise ProviderError('An edit value is not valid JSON.') from None
            if isinstance(target, dict):
                target[key] = value
            elif isinstance(target, list) and (key == '-' or (key.isdigit() and int(key) == len(target))):
                target.append(value)
            elif isinstance(target, list) and key.isdigit() and int(key) < len(target):
                target[int(key)] = value
            else:
                raise ProviderError('The document path cannot be updated.')
        elif isinstance(target, dict) and key in target:
            del target[key]
        elif isinstance(target, list) and key.isdigit() and int(key) < len(target):
            target.pop(int(key))
        else:
            raise ProviderError('The property to remove does not exist.')
    validate_document(draft)
    for key, source in document.get('dataSources', {}).items():
        after = draft.get('dataSources', {}).get(key, {})
        old_data, new_data = source.get('options', {}).get('data', {}), after.get('options', {}).get('data', {})
        if (source.get('type') == 'ds.test' and after.get('type') == 'ds.test'
                and isinstance(old_data, dict) and old_data.get('columns')
                and (not isinstance(new_data, dict) or 'columns' not in new_data)):
            raise ProviderError('Preserve existing sample columns; their omission from model context does not delete them.')
    return validate_document(draft)


def model_document(document):
    """Exclude result/sample rows while retaining field names and Studio options."""
    result = copy.deepcopy(document)
    for source in result.get('dataSources', {}).values():
        source.pop('state', None)
        data = source.get('options', {}).get('data')
        if isinstance(data, dict):
            source['options']['data'] = {'fields': data.get('fields', [])}
        elif data is not None:
            source['options'].pop('data', None)
        source.pop('results', None)
    return result
