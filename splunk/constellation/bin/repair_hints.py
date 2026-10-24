"""Concrete, bounded repair hints derived from the uncommitted native document."""


def placement_hint(document, active_tab=None):
    layouts = document.get('layout', {}).get('layoutDefinitions', {})
    placed = {item.get('item') for page in layouts.values() for item in page.get('structure', [])}
    missing = [identifier for identifier in document.get('visualizations', {}) if identifier not in placed]
    if not missing: return {}
    candidates = [active_tab] + list(layouts)
    identifier = next((key for key in candidates if key in layouts and layouts[key].get('type') == 'absolute'), None)
    if identifier is None: return {'unplacedVisualizations': missing, 'instruction': 'Place these exact IDs in their intended native page.'}
    page = layouts[identifier]
    width = page.get('options', {}).get('width', 1200)
    if type(width) is not int or not 240 <= width <= 20000: return {'unplacedVisualizations': missing}
    bottom = max([item.get('position', {}).get('y', 0) + item.get('position', {}).get('h', 0) for item in page.get('structure', [])] or [0])
    if not isinstance(bottom, (int, float)) or bottom + 420 * len(missing) > 20000: return {'unplacedVisualizations': missing}
    tabs = document.get('layout', {}).get('tabs', {}).get('items', [])
    label = next((tab.get('label', identifier) for tab in tabs if tab.get('layoutId') == identifier), identifier)
    return {'unplacedVisualizations': missing, 'instruction': 'Include a layout action to place these exact IDs. This valid example keeps existing items; adjust its geometry to the user goal if needed.',
            'layoutActionExample': {'op': 'layout', 'layoutId': identifier, 'label': label, 'width': width,
                                    'height': max(800, int(bottom) + 420 * len(missing)),
                                    'items': [{'id': item, 'kind': 'block', 'x': 20, 'y': int(bottom) + 20 + offset * 420, 'w': width - 40, 'h': 400} for offset, item in enumerate(missing)]}}
