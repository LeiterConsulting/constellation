"""Typed authoring actions compiled into the stable native Studio edit contract."""
import copy
import json
import re
from provider_service import ProviderError
from page_service import LINK_ACTION, BUTTON_ACTION, BUTTON_MIN_HEIGHT, compile_link, compile_button
from studio_contract import apply_changes
from geometry_normalization import normalize_structure, fit_button_labels
from input_normalization import normalize_button_actions
from search_chart_actions import SEARCH_ACTION, CHART_ACTION, TOKEN_ACTION, compile_search, compile_chart, compile_token, normalize_field_bindings, normalize_event_counts
from search_chart_actions import FILTER_ACTION, DASHBOARD_ACTION, compile_filter, compile_dashboard, normalize_row_filters
from table_format import TABLE_FORMAT_ACTION, compile_table_format
from measurement_constraints import normalize_measurements

LEGACY_CHANGE = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['set', 'remove']},
    'path': {'type': 'string', 'description': 'JSON Pointer within the Studio definition.'},
    'value': {'type': 'string', 'description': 'A complete JSON document encoded as a string. For a title use the JSON text "Healthy" including its quotes. Escape quotes inside SPL queries. Use an empty string for remove.'}},
    'required': ['op', 'path', 'value'], 'additionalProperties': False}

GEOMETRY = {'type': 'object', 'properties': {
    'id': {'type': 'string'}, 'kind': {'type': 'string', 'enum': ['block', 'input']},
    'x': {'type': 'integer', 'minimum': 0, 'maximum': 20000}, 'y': {'type': 'integer', 'minimum': 0, 'maximum': 20000},
    'w': {'type': 'integer', 'minimum': 1, 'maximum': 20000}, 'h': {'type': 'integer', 'minimum': 1, 'maximum': 20000}},
    'required': ['id', 'kind', 'x', 'y', 'w', 'h'], 'additionalProperties': False}

LAYOUT_ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['layout'], 'description': 'Create or update an absolute page using typed geometry; always use this for new absolute canvases.'},
    'layoutId': {'type': 'string'}, 'label': {'type': 'string'},
    'width': {'type': 'integer', 'minimum': 1, 'maximum': 20000}, 'height': {'type': 'integer', 'minimum': 1, 'maximum': 20000},
    'items': {'type': 'array', 'items': GEOMETRY}},
    'required': ['op', 'layoutId', 'label', 'width', 'height', 'items'], 'additionalProperties': False}

PAGE_ACTION = copy.deepcopy(LAYOUT_ACTION)
PAGE_ACTION['properties']['op'] = {'type': 'string', 'enum': ['page']}
PAGE_ACTION['properties']['purpose'] = {'type': 'string', 'maxLength': 1200}
PAGE_ACTION['properties']['moveItems'] = {'type': 'boolean', 'description': 'Move these items off their previous pages when true; otherwise allow reuse.'}
PAGE_ACTION['required'].extend(['purpose', 'moveItems'])
ACTION_SCHEMA = {'anyOf': [LEGACY_CHANGE, DASHBOARD_ACTION, SEARCH_ACTION, CHART_ACTION, TOKEN_ACTION, FILTER_ACTION, TABLE_FORMAT_ACTION, LAYOUT_ACTION, PAGE_ACTION, LINK_ACTION, BUTTON_ACTION]}


def validate_chart_placement(document, previous):
    """Reject newly introduced chart collisions, preserving imported overlays."""
    static = {'splunk.markdown', 'splunk.richtext', 'splunk.rectangle', 'splunk.ellipse', 'splunk.image'}
    layout = document.get('layout', {})
    old_layout = previous.get('layout', {})
    pages = layout.get('layoutDefinitions') or {'legacy': layout}
    old_pages = old_layout.get('layoutDefinitions') or {'legacy': old_layout}
    for page_id, page in pages.items():
        if page.get('type') != 'absolute': continue
        old_positions = {item.get('item'): item.get('position') for item in old_pages.get(page_id, {}).get('structure', [])}
        charts = []
        for item in page.get('structure', []):
            identifier, position = item.get('item'), item.get('position', {})
            chart = document.get('visualizations', {}).get(identifier) or document.get('inputs', {}).get(identifier, {})
            # Decorative backgrounds and intentionally conditional layers can overlap.
            if not chart or chart.get('type') in static or chart.get('containerOptions', {}).get('visibility'): continue
            if not all(isinstance(position.get(key), (int, float)) for key in ('x', 'y', 'w', 'h')): continue
            if chart.get('type') == 'input.button' and position != old_positions.get(identifier) and position['h'] < BUTTON_MIN_HEIGHT:
                raise ProviderError('Give native Studio button inputs at least 80 pixels of height so their labels are visible: ' + identifier)
            charts.append((identifier, position))
        for offset, (first_id, first) in enumerate(charts):
            for second_id, second in charts[offset + 1:]:
                if first == old_positions.get(first_id) and second == old_positions.get(second_id): continue
                if (first['x'] < second['x'] + second['w'] and second['x'] < first['x'] + first['w']
                        and first['y'] < second['y'] + second['h'] and second['y'] < first['y'] + first['h']):
                    raise ProviderError('Place charts and inputs in separate rectangles so every element remains usable: ' + first_id + ', ' + second_id)


def compile_actions(document, actions, profile=None, table_receipt=None):
    if not isinstance(actions, list) or len(actions) > 64: raise ProviderError('Use at most 64 authoring actions.')
    layout = copy.deepcopy(document['layout'])
    defaults, token_changes = copy.deepcopy(document.get('defaults', {})), False
    result, links, buttons, filters, formats, typed = [], [], [], [], [], False
    for action in actions:
        if not isinstance(action, dict): raise ProviderError('Each authoring action must be an object.')
        if action.get('op') == 'dashboard': result.extend(compile_dashboard(action)); continue
        if action.get('op') == 'formatTable': formats.append(action); continue
        if action.get('op') == 'filter': filters.append(action); continue
        if action.get('op') == 'token':
            compile_token(action, defaults); token_changes = True
            continue
        if action.get('op') in ('search', 'chart'):
            root = 'dataSources' if action['op'] == 'search' else 'visualizations'
            key, value = compile_search(action, document, profile) if root == 'dataSources' else compile_chart(action, document)
            if root not in document and not any(change.get('path') == '/' + root for change in result):
                result.append({'op': 'set', 'path': '/' + root, 'value': '{}'})
            result.append({'op': 'set', 'path': '/' + root + '/' + key, 'value': json.dumps(value)})
            continue
        if action.get('op') == 'link': links.append(action); continue
        if action.get('op') == 'button': buttons.append(action); continue
        if action.get('op') == 'page':
            if not isinstance(action.get('purpose'), str) or len(action['purpose']) > 1200 or type(action.get('moveItems')) is not bool:
                raise ProviderError('Give the page a purpose under 1200 characters.')
            if action['moveItems']:
                moving = {item.get('id') for item in action.get('items', []) if isinstance(item, dict)}
                for key, page in layout.get('layoutDefinitions', {}).items():
                    if key != action.get('layoutId'): page['structure'] = [item for item in page.get('structure', []) if item.get('item') not in moving]
            action = {key: value for key, value in action.items() if key not in ('purpose', 'moveItems')}
            action['op'] = 'layout'
        if action.get('op') != 'layout':
            # These native properties are unambiguously text. Some providers
            # return their literal text instead of the JSON-encoded string.
            # Normalize that narrow case without accepting malformed objects,
            # arrays, quoted JSON, or changing any other native property contract.
            path = action.get('path', '')
            query_path = re.fullmatch(r'/dataSources/([^/]+)/options/query', path) if isinstance(path, str) else None
            known_query = query_path and document.get('dataSources', {}).get(query_path[1].replace('~1', '/').replace('~0', '~'), {}).get('type') in ('ds.search', 'ds.spl2', 'ds.chain')
            chart_path = re.fullmatch(r'/visualizations/([^/]+)/(title|description|options/(?:x|y|y2|category|majorValue|table))', path) if isinstance(path, str) else None
            known_chart = bool(chart_path and chart_path[1].replace('~1', '/').replace('~0', '~') in document['visualizations'])
            chart_text = known_chart and chart_path[2] in ('title', 'description')
            binding_text = known_chart and chart_path[2].startswith('options/') and str(action.get('value', '')).lstrip().startswith('>')
            if action.get('op') == 'set' and (path in ('/title', '/description') or known_query or chart_text or binding_text) and isinstance(action.get('value'), str):
                value = action['value']
                try: json.loads(value)
                except ValueError:
                    if not value.lstrip().startswith(('"', '{', '[')):
                        action = dict(action, value=json.dumps(value))
            result.append(normalize_structure(action, document))
            continue
        if not typed and not document['visualizations'] and not document.get('inputs') and not document.get('dataSources'):
            definitions = layout.get('layoutDefinitions', {})
            if set(definitions) == {'layout_main'} and not definitions['layout_main'].get('structure') and action.get('layoutId') != 'layout_main':
                del definitions['layout_main']
                layout.setdefault('tabs', {})['items'] = [tab for tab in layout.get('tabs', {}).get('items', []) if tab.get('layoutId') != 'layout_main']
        if 'layoutDefinitions' not in layout and layout.get('structure'):
            raise ProviderError('Preserve this legacy layout with targeted native edits; typed pages require the tabbed layout structure.')
        typed = True
        if set(action) != {'op', 'layoutId', 'label', 'width', 'height', 'items'}:
            raise ProviderError('A typed layout needs layoutId, label, width, height and items.')
        identifier, label = action['layoutId'], action['label']
        if not isinstance(identifier, str) or not 1 <= len(identifier) <= 150 or identifier in ('__proto__', 'constructor', 'prototype'):
            raise ProviderError('Use a safe, nonempty layout ID.')
        if not isinstance(label, str) or not 1 <= len(label) <= 200: raise ProviderError('Give the layout a concise page label.')
        if any(type(action[key]) is not int or not 1 <= action[key] <= 20000 for key in ('width', 'height')):
            raise ProviderError('Typed canvas dimensions must be integers from 1 to 20000.')
        if not isinstance(action['items'], list) or len(action['items']) > 200:
            raise ProviderError('A typed page supports up to 200 positioned items.')
        definitions = layout.setdefault('layoutDefinitions', {})
        page = definitions.setdefault(identifier, {'type': 'absolute', 'options': {'display': 'auto-scale'}, 'structure': []})
        if page.get('type') != 'absolute': raise ProviderError('Typed pixel positions require an absolute page. Preserve grid layouts with targeted native edits.')
        if not isinstance(page.get('options', {}), dict): raise ProviderError('Canvas options must be an object.')
        page.setdefault('options', {}).update(width=action['width'], height=action['height'])
        structure = page.setdefault('structure', [])
        seen = set()
        for item in action['items']:
            if (not isinstance(item, dict) or set(item) != {'id', 'kind', 'x', 'y', 'w', 'h'}
                    or not isinstance(item['id'], str) or not item['id'] or item['id'] in seen
                    or item['kind'] not in ('block', 'input')):
                raise ProviderError('Each typed position needs a unique item ID, block/input kind and integer x/y/w/h.')
            seen.add(item['id'])
            if any(type(item[key]) is not int or not (0 if key in ('x','y') else 1) <= item[key] <= 20000 for key in ('x','y','w','h')):
                raise ProviderError('Typed positions must use valid nonnegative integers and positive sizes.')
            if item['x'] + item['w'] > action['width'] or item['y'] + item['h'] > action['height']:
                raise ProviderError('Fit every positioned item within the typed canvas dimensions.')
            existing = next((entry for entry in structure if entry.get('item') == item['id']), None)
            if existing is None:
                existing = {'item': item['id'], 'type': item['kind'], 'position': {}}; structure.append(existing)
            existing['type'] = item['kind']
            existing.setdefault('position', {}).update({key: item[key] for key in ('x','y','w','h')})
        tabs = layout.setdefault('tabs', {}).setdefault('items', [])
        tab = next((entry for entry in tabs if entry.get('layoutId') == identifier), None)
        if tab is None: tabs.append({'layoutId': identifier, 'label': label})
        else: tab['label'] = label
        layout.setdefault('globalInputs', [])
    if token_changes:
        if any(str(action.get('path', '')).split('/')[1:2] == ['defaults'] for action in result):
            raise ProviderError('Use typed token actions or native /defaults edits in one batch, not both.')
        result.append({'op': 'set', 'path': '/defaults', 'value': json.dumps(defaults)})
    if typed:
        if any(str(action.get('path', '')).split('/')[1:2] == ['layout'] for action in result):
            raise ProviderError('Use typed layout actions or native /layout edits in a batch, not both.')
        # A typed button owns its creation AND placement. Some models also list
        # the same new input in page.items. Defer that redundant placeholder so
        # the intermediate layout is valid before compile_button creates it.
        # Only exact, same-page button actions qualify; unknown references still
        # fail and unrelated or imported placements are never removed.
        for button in buttons:
            identifier, page_id = button.get('id'), button.get('pageId')
            if not isinstance(identifier, str) or not isinstance(page_id, str): continue
            if identifier in document.get('inputs', {}) or identifier in document['visualizations']: continue
            for key, page in layout.get('layoutDefinitions', {}).items():
                if not any(item.get('item') == identifier for item in page.get('structure', [])): continue
                if key != page_id:
                    raise ProviderError('Button ' + identifier[:150] + ' is listed on page ' + str(key)[:150] +
                                        ' but its button action places it on ' + page_id[:150] + '. Use one consistent placement pageId.')
                page['structure'] = [item for item in page['structure'] if item.get('item') != identifier]
        result.append({'op': 'set', 'path': '/layout', 'value': json.dumps(layout)})
    if links or buttons or filters:
        candidate = apply_changes(document, result)
        for action in filters:
            change = compile_filter(action, candidate, profile)
            result.append(change)
            candidate = apply_changes(candidate, [change])
        for action in buttons:
            changes = compile_button(candidate, action)
            result.extend(changes)
            candidate = apply_changes(candidate, changes)
        for action in links:
            change = compile_link(candidate, action)
            result.append(change)
            candidate = apply_changes(candidate, [change])
    candidate = apply_changes(document, result)
    for action in formats:
        change = compile_table_format(action, candidate, table_receipt)
        result.append(change)
        candidate = apply_changes(candidate, [change])
    for normalize in (normalize_field_bindings, normalize_event_counts, normalize_row_filters, normalize_measurements):
        bindings = normalize(candidate, document, profile)
        if bindings:
            result.extend(bindings)
            candidate = apply_changes(candidate, bindings)
    button_changes = normalize_button_actions(candidate, document)
    if button_changes:
        result.extend(button_changes)
        candidate = apply_changes(candidate, button_changes)
    fitted = fit_button_labels(candidate, document)
    if fitted is not None: result.append({'op': 'set', 'path': '/layout', 'value': json.dumps(fitted)})
    return result
