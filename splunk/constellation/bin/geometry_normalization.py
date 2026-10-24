"""Lossless conversion of typed item geometry placed in a native structure edit."""
import json
import re
import copy
from provider_service import ProviderError
from page_service import BUTTON_MIN_HEIGHT


def normalize_structure(action, document):
    if action.get('op') != 'set' or not re.fullmatch(r'/layout/(?:layoutDefinitions/[^/]+/)?structure', str(action.get('path', ''))):
        return action
    try: items = json.loads(action.get('value', ''))
    except (ValueError, TypeError): return action
    keys = {'id', 'kind', 'x', 'y', 'w', 'h'}
    if not isinstance(items, list) or not items or not all(isinstance(item, dict) and set(item) == keys for item in items):
        return action
    parent = document
    for key in action['path'].strip('/').split('/'):
        key = key.replace('~1', '/').replace('~0', '~')
        parent = parent.get(key) if isinstance(parent, dict) else None
    native = copy.deepcopy(parent) if isinstance(parent, list) else []
    seen = set()
    for item in items:
        identifier = item['id']
        if not isinstance(identifier, str) or not identifier or identifier in seen or item['kind'] not in ('block', 'input'):
            raise ProviderError('Typed structure items need unique IDs and block/input kinds.')
        if any(type(item[key]) is not int or not (0 if key in ('x', 'y') else 1) <= item[key] <= 20000 for key in ('x', 'y', 'w', 'h')):
            raise ProviderError('Typed structure positions require nonnegative integers and positive sizes.')
        seen.add(identifier)
        existing = next((entry for entry in native if isinstance(entry, dict) and entry.get('item') == identifier), None)
        if existing is None:
            existing = {'item': identifier, 'position': {}}
            native.append(existing)
        existing['type'] = item['kind']
        existing.setdefault('position', {}).update({key: item[key] for key in ('x', 'y', 'w', 'h')})
    return dict(action, value=json.dumps(native))


def fit_button_labels(document, previous):
    """Enlarge changed absolute buttons only into already empty canvas space."""
    layout = copy.deepcopy(document['layout'])
    pages = layout.get('layoutDefinitions') or {'legacy': layout}
    old_pages = previous.get('layout', {}).get('layoutDefinitions') or {'legacy': previous.get('layout', {})}
    decorative = {'splunk.rectangle', 'splunk.ellipse'}
    changed = False
    for page_id, page in pages.items():
        if page.get('type') != 'absolute': continue
        old = {item.get('item'): item.get('position') for item in old_pages.get(page_id, {}).get('structure', [])}
        for item in page.get('structure', []):
            identifier, position = item.get('item'), item.get('position', {})
            if document.get('inputs', {}).get(identifier, {}).get('type') != 'input.button' or position == old.get(identifier): continue
            if not all(type(position.get(key)) in (int, float) for key in ('x', 'y', 'w', 'h')) or position['h'] >= BUTTON_MIN_HEIGHT: continue
            height = page.get('options', {}).get('height')
            if not isinstance(height, (int, float)) or position['y'] + BUTTON_MIN_HEIGHT > height: continue
            blocked = False
            for other in page.get('structure', []):
                other_id, rectangle = other.get('item'), other.get('position', {})
                chart = document.get('visualizations', {}).get(other_id, document.get('inputs', {}).get(other_id, {}))
                if other_id == identifier or chart.get('type') in decorative: continue
                if not all(type(rectangle.get(key)) in (int, float) for key in ('x', 'y', 'w', 'h')): continue
                if (position['x'] < rectangle['x'] + rectangle['w'] and rectangle['x'] < position['x'] + position['w'] and
                        position['y'] < rectangle['y'] + rectangle['h'] and rectangle['y'] < position['y'] + BUTTON_MIN_HEIGHT): blocked = True
            if not blocked:
                position['h'] = BUTTON_MIN_HEIGHT
                changed = True
    return layout if changed else None
