"""Lossless conversion of typed item geometry placed in a native structure edit."""
import json
import re
import copy
from provider_service import ProviderError
from page_service import BUTTON_MIN_HEIGHT, button_label_width


def normalize_structure_text(action, document):
    """Encode only known native item IDs/kinds on existing structure entries."""
    if action.get('op') != 'set': return action
    match = re.fullmatch(r'(/layout/(?:layoutDefinitions/[^/]+/)?structure)/(\d+)/(item|type)', str(action.get('path', '')))
    value = action.get('value')
    if not match or not isinstance(value, str): return action
    try: json.loads(value);return action
    except ValueError: pass
    parent = document
    for key in match[1].strip('/').split('/'):
        parent = parent.get(key.replace('~1', '/').replace('~0', '~')) if isinstance(parent, dict) else None
    if not isinstance(parent, list) or int(match[2]) >= len(parent): return action
    eligible = value in ('block', 'input') if match[3] == 'type' else value in document.get('visualizations', {}) or value in document.get('inputs', {})
    if not eligible or value.lstrip().startswith(('"', '{', '[')): return action
    return dict(action, value=json.dumps(value))


def normalize_structure(action, document):
    if action.get('op') != 'set' or not re.fullmatch(r'/layout/(?:layoutDefinitions/[^/]+/)?structure', str(action.get('path', ''))):
        return normalize_structure_text(action, document)
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
            control = document.get('inputs', {}).get(identifier, {})
            old_label = previous.get('inputs', {}).get(identifier, {}).get('options', {}).get('label')
            label = control.get('options', {}).get('label')
            if control.get('type') != 'input.button' or position == old.get(identifier) and label == old_label: continue
            if not all(type(position.get(key)) in (int, float) for key in ('x', 'y', 'w', 'h')): continue
            width = max(position['w'], button_label_width(label));height = max(position['h'], BUTTON_MIN_HEIGHT)
            if width == position['w'] and height == position['h']: continue
            bounds = page.get('options', {})
            if (not all(isinstance(bounds.get(key), (int, float)) for key in ('width', 'height'))
                    or position['x'] + width > bounds['width'] or position['y'] + height > bounds['height']): continue
            blocked = False
            for other in page.get('structure', []):
                other_id, rectangle = other.get('item'), other.get('position', {})
                chart = document.get('visualizations', {}).get(other_id, document.get('inputs', {}).get(other_id, {}))
                if other_id == identifier or chart.get('type') in decorative: continue
                if not all(type(rectangle.get(key)) in (int, float) for key in ('x', 'y', 'w', 'h')): continue
                if (position['x'] < rectangle['x'] + rectangle['w'] and rectangle['x'] < position['x'] + width and
                        position['y'] < rectangle['y'] + rectangle['h'] and rectangle['y'] < position['y'] + height): blocked = True
            if not blocked:
                position.update(w=width, h=height)
                changed = True
    return layout if changed else None
