"""Native page/navigation authoring with draft-only purpose metadata."""
import copy
import json
import re
from provider_service import ProviderError


LINK_ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['link']},
    'sourceId': {'type': 'string', 'description': 'The origin table/chart/input ID.'},
    'pageId': {'type': 'string', 'description': 'DESTINATION layout ID to open, never the source element page.'},
    'targetId': {'type': 'string', 'description': 'An ELEMENT ID placed on the destination page to focus, or empty. Never a layout ID.'},
    'field': {'type': 'string'}, 'token': {'type': 'string'}},
    'required': ['op', 'sourceId', 'pageId', 'targetId', 'field', 'token'], 'additionalProperties': False}

# Studio's absolute input wrapper includes label spacing and padding even when
# a button has no separate input title. Smaller rectangles clip its label.
BUTTON_MIN_HEIGHT = 80


def button_label_width(label):
    """Conservative default-font room for a literal native button label."""
    if not isinstance(label, str) or not label or '$' in label: return 0
    return 48 + sum(8 if ord(char) < 128 else 16 for char in label)


def validate_purposes(purposes, document):
    layouts = document.get('layout', {}).get('layoutDefinitions', {})
    if not isinstance(purposes, dict) or len(purposes) > 30 or any(key not in layouts or not isinstance(value, str) or len(value) > 1200 for key, value in purposes.items()):
        raise ProviderError('Page purposes must be concise text for existing page IDs.')
    return copy.deepcopy(purposes)


def proposed_purposes(actions, previous, document):
    result = {key: value for key, value in previous.items() if key in document.get('layout', {}).get('layoutDefinitions', {})}
    for action in actions:
        if action.get('op') == 'page': result[action['layoutId']] = action['purpose']
    return validate_purposes(result, document)


def focus_context(document, selected, active_tab, purposes):
    layouts = document.get('layout', {}).get('layoutDefinitions', {})
    if selected.startswith('page:'):
        page_id = selected[5:]
        if page_id not in layouts: raise ProviderError('The selected page no longer exists.')
        tab = next((tab for tab in document['layout'].get('tabs', {}).get('items', []) if tab.get('layoutId') == page_id), {})
        return {'kind': 'page', 'id': page_id, 'label': tab.get('label', page_id), 'purpose': purposes.get(page_id, '')}
    for root, kind in (('visualizations', 'visualization'), ('inputs', 'input')):
        if selected in document.get(root, {}):
            item = document[root][selected]
            pages = [key for key, page in layouts.items() if any(entry.get('item') == selected for entry in page.get('structure', []))]
            return {'kind': kind, 'id': selected, 'title': item.get('title', item.get('options', {}).get('label', selected)),
                    'type': item.get('type'), 'pages': pages, 'activePage': active_tab,
                    'source': item.get('dataSources', {}).get('primary')}
    if selected: raise ProviderError('The selected dashboard element no longer exists.')
    return {'kind': 'dashboard', 'activePage': active_tab}


def compile_link(document, action):
    if set(action) != {'op', 'sourceId', 'pageId', 'targetId', 'field', 'token'} or any(not isinstance(value, str) or len(value) > 200 for value in action.values()):
        raise ProviderError('A navigation link needs sourceId, pageId, targetId, field and token strings; use empty strings for optional values.')
    source_id, page_id, target_id = action['sourceId'], action['pageId'], action['targetId']
    layouts = document.get('layout', {}).get('layoutDefinitions', {})
    if page_id not in layouts: raise ProviderError('The navigation destination page does not exist.')
    root = 'visualizations' if source_id in document.get('visualizations', {}) else 'inputs'
    source = document.get(root, {}).get(source_id)
    if not source: raise ProviderError('The navigation source element does not exist.')
    # Normalize the exact origin-page/destination-page alias emitted by some
    # providers. A real element with the same ID makes this ambiguous: retain
    # the normal strict element check in that case. Intent checks still run.
    if (target_id in layouts and target_id not in document.get('visualizations', {})
            and target_id not in document.get('inputs', {})
            and any(item.get('item') == source_id for item in layouts[page_id].get('structure', []))):
        page_id, target_id = target_id, ''
    if target_id and not any(item.get('item') == target_id for item in layouts[page_id].get('structure', [])):
        raise ProviderError('Navigation from ' + source_id[:100] + ': targetId=' + target_id[:100] + ' must be an ELEMENT placed on destination pageId=' + page_id[:100] + '. To open a page, put its layout ID in pageId and use targetId="".')
    field, token = action['field'], action['token']
    if bool(field) != bool(token) or (token and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', token)) or any(c in field for c in '$[]'):
        raise ProviderError('A field link needs both a valid row field and a safe destination token name.')
    if field and (root != 'visualizations' or source.get('type') != 'splunk.table'):
        raise ProviderError('Use row-field token navigation on a table; buttons and charts can link directly without a row field.')
    common = {'fields': [field]} if field else {}
    handlers = []
    for original in source.get('eventHandlers', []):
        handler = copy.deepcopy(original)
        if handler.get('options', {}).get('fields', []) == common.get('fields', []):
            if handler.get('type') == 'drilldown.switchToTab': continue
            if handler.get('type') == 'drilldown.setToken':
                handler['options']['tokens'] = [item for item in handler['options'].get('tokens', []) if item.get('token') not in ('constellation_focus', token)]
                if not handler['options']['tokens']: continue
        handlers.append(handler)
    tokens = ([{'token': token, 'key': 'row.' + field + '.value'}] if token else [])
    tokens.append({'token': 'constellation_focus', 'value': target_id})
    handlers.extend([{'type': 'drilldown.setToken', 'options': dict(common, tokens=tokens)},
                     {'type': 'drilldown.switchToTab', 'options': dict(common, tabId=page_id)}])
    escaped = source_id.replace('~', '~0').replace('/', '~1')
    return {'op': 'set', 'path': '/' + root + '/' + escaped + '/eventHandlers', 'value': json.dumps(handlers)}


BUTTON_ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['button']}, 'id': {'type': 'string'}, 'label': {'type': 'string'},
    'pageId': {'type': 'string'}, 'targetPageId': {'type': 'string'}, 'targetId': {'type': 'string'},
    **{key: {'type': 'integer', 'minimum': 0 if key in ('x', 'y') else 1, 'maximum': 20000} for key in ('x', 'y', 'w', 'h')}},
    'required': ['op', 'id', 'label', 'pageId', 'targetPageId', 'targetId', 'x', 'y', 'w', 'h'], 'additionalProperties': False}


def compile_button(document, action):
    if set(action) != set(BUTTON_ACTION['required']): raise ProviderError('A typed navigation button needs id, label, pageId, targetPageId, targetId and x/y/w/h.')
    for key in ('id', 'label', 'pageId', 'targetPageId', 'targetId'):
        if not isinstance(action[key], str) or len(action[key]) > 200 or (key != 'targetId' and not action[key]):
            raise ProviderError('Give the navigation button valid IDs and a concise visible label.')
    if action['id'] in ('__proto__', 'constructor', 'prototype') or action['id'] in document['visualizations']:
        raise ProviderError('Use a distinct, safe input ID for the navigation button.')
    page = document.get('layout', {}).get('layoutDefinitions', {}).get(action['pageId'])
    if not page or page.get('type') != 'absolute': raise ProviderError('Place a typed navigation button on an existing absolute page; preserve grid geometry with native edits.')
    position = {key: action[key] for key in ('x', 'y', 'w', 'h')}
    if any(type(value) is not int or not (0 if key in ('x','y') else 1) <= value <= 20000 for key,value in position.items()):
        raise ProviderError('Button positions require nonnegative integer x/y and positive w/h.')
    position['h'] = max(BUTTON_MIN_HEIGHT, position['h'])
    position['w'] = max(button_label_width(action['label']), position['w'])
    options = page.get('options', {})
    if position['x'] + position['w'] > options.get('width', 1200):
        raise ProviderError('Fit navigation button ' + action['id'][:120] + ' within the width of page ' + action['pageId'][:120] + '.')
    occupied = []
    for entry in page.get('structure', []):
        if entry.get('item') == action['id']: continue
        chart = document['visualizations'].get(entry.get('item'), {})
        other = entry.get('position', {})
        if chart.get('type') in ('splunk.markdown','splunk.richtext','splunk.rectangle','splunk.ellipse','splunk.image'): continue
        if all(type(other.get(key)) in (int,float) for key in ('x','y','w','h')): occupied.append(other)
    # Button geometry is a placement hint. Resolve routine collisions locally,
    # preserving every existing chart rectangle and avoiding extra inference.
    for _ in range(len(occupied) + 1):
        collisions = [other for other in occupied if position['x'] < other['x']+other['w'] and other['x'] < position['x']+position['w'] and position['y'] < other['y']+other['h'] and other['y'] < position['y']+position['h']]
        if not collisions: break
        position['y'] = int(max(other['y']+other['h'] for other in collisions)) + 20
    required_height = max(options.get('height',800),position['y']+position['h']+20)
    if required_height > 20000: raise ProviderError('There is no bounded clear space for this navigation button; use a smaller button or another page.')
    existing = document.get('inputs', {}).get(action['id'], {})
    if existing and existing.get('type') != 'input.button': raise ProviderError('Do not replace a non-button input with a navigation button.')
    item = copy.deepcopy(existing) if existing else {'type': 'input.button', 'options': {}}
    item.setdefault('options', {})['label'] = action['label']
    # Validate and compile native handlers against a temporary input definition.
    candidate = copy.deepcopy(document);candidate.setdefault('inputs', {})[action['id']] = item
    link = compile_link(candidate, {'op':'link','sourceId':action['id'],'pageId':action['targetPageId'],'targetId':action['targetId'],'field':'','token':''})
    item['eventHandlers'] = json.loads(link['value'])
    structure = copy.deepcopy(page.get('structure', []))
    placement = next((entry for entry in structure if entry.get('item') == action['id']), None)
    if placement is None: placement = {'item': action['id']};structure.append(placement)
    placement.update(type='input', position=position)
    if action['id'] in document.get('layout', {}).get('globalInputs', []): raise ProviderError('A page button cannot also be a global input.')
    escape = lambda value:value.replace('~','~0').replace('/','~1')
    resizing = ([{'op':'set','path':'/layout/layoutDefinitions/'+escape(action['pageId'])+'/options','value':json.dumps(dict(options,height=required_height))}] if required_height > options.get('height',800) else [])
    return resizing + ([{'op':'set','path':'/inputs','value':'{}'}] if 'inputs' not in document else []) + [
        {'op':'set','path':'/inputs/'+escape(action['id']),'value':json.dumps(item)},
        {'op':'set','path':'/layout/layoutDefinitions/'+escape(action['pageId'])+'/structure','value':json.dumps(structure)}]
