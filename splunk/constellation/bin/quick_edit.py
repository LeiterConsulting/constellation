"""Exact, single-element presentation instructions that need no inference.

Deliberately small grammar: additional goals, ambiguous prose, attachments and
other chart conversions use normal model authoring and validation.
"""
import json
import re
import copy
from studio_contract import apply_changes


def full_width_table(prompt, document, selected):
    """Exact selected-table placement below all unchanged page items, without asking inference to rebuild a page."""
    match = re.fullmatch(r'Make only this selected summary table full width below the trend(?: on ([^.!?]+))?\. '
                         r'Keep its existing height and every query, column, page, drilldown and other element unchanged\.'
                         r'(?: Grow the ([^.!?]+) canvas height if needed to contain the moved table\.)?', prompt, re.I)
    if not match or document['visualizations'][selected].get('type') != 'splunk.table': return None
    layout = document.get('layout', {})
    pages = [(key, page) for key, page in layout.get('layoutDefinitions', {}).items()
             if any(item.get('item') == selected for item in page.get('structure', []))]
    if len(pages) != 1: return None
    page_id, page = pages[0]
    label = next((tab.get('label') for tab in layout.get('tabs', {}).get('items', []) if tab.get('layoutId') == page_id), None)
    if any(name and (not isinstance(label, str) or name.casefold() != label.casefold()) for name in match.groups()): return None
    items = page.get('structure', [])
    if page.get('type') != 'absolute' or len(items) < 2 or len({item.get('item') for item in items}) != len(items): return None
    others = [item for item in items if item.get('item') != selected]
    if not others: return None
    charts = [document['visualizations'].get(item.get('item'), {}) for item in items]
    if not any(document['visualizations'].get(item.get('item'), {}).get('type') in ('splunk.line','splunk.area','splunk.column') for item in others): return None
    if any(not chart or chart.get('type') in ('splunk.markdown','splunk.richtext','splunk.rectangle','splunk.ellipse','splunk.image') for chart in charts): return None
    if any(chart.get('containerOptions', {}).get('visibility') for chart in charts): return None
    bounds = page.get('options', {})
    if any(type(bounds.get(key)) is not int or not 40 < bounds[key] <= 20000 for key in ('width', 'height')): return None
    if any(type(item.get('position', {}).get(key)) is not int for item in items for key in ('x', 'y', 'w', 'h')): return None
    index = next(i for i, item in enumerate(items) if item.get('item') == selected)
    position = copy.deepcopy(items[index]['position'])
    position.update(x=20, y=max(item['position']['y'] + item['position']['h'] for item in others) + 20, w=bounds['width'] - 40)
    height = max(bounds['height'], position['y'] + position['h'] + 20)
    if height > 20000: return None
    base = '/layout/layoutDefinitions/' + page_id.replace('~', '~0').replace('/', '~1')
    changes = [{'op': 'set', 'path': base + '/structure/' + str(index) + '/position', 'value': json.dumps(position)}]
    if height != bounds['height']: changes.append({'op': 'set', 'path': base + '/options/height', 'value': json.dumps(height)})
    from authoring_actions import validate_chart_placement
    result = apply_changes(document, changes)
    validate_chart_placement(result, document)
    return changes


def quick_edit(prompt, document, selected, attachments):
    if attachments or not isinstance(selected, str): return None
    if selected in document.get('inputs', {}):
        button = document['inputs'][selected]
        match = re.fullmatch(r'Rename only this selected existing return button to "([^"\n]{1,200})" and keep its destination ([^.!?]+)\. Preserve its position, size and every other element and interaction\.', prompt, re.I)
        if not match or button.get('type') != 'input.button': return None
        targets = {handler.get('options', {}).get('tabId') for handler in button.get('eventHandlers', []) if handler.get('type') == 'drilldown.switchToTab'}
        pages = [tab for tab in document.get('layout', {}).get('tabs', {}).get('items', []) if str(tab.get('label', '')).casefold() == match[2].strip().casefold()]
        if len(pages) != 1 or targets != {pages[0]['layoutId']}: return None
        placements = [item for page in document['layout'].get('layoutDefinitions', {}).values() for item in page.get('structure', []) if item.get('item') == selected]
        if len(placements) != 1: return None
        from page_service import button_label_width
        from provider_service import ProviderError
        if placements[0].get('position', {}).get('w', 0) < button_label_width(match[1]):
            raise ProviderError('That label will not fit the current button width. Use a shorter label or allow resizing. Your draft is unchanged.', 422, 'button_label_fit')
        changes = [{'op': 'set', 'path': '/inputs/' + selected.replace('~', '~0').replace('/', '~1') + '/options/label', 'value': json.dumps(match[1])}]
        apply_changes(document, changes)
        return changes
    if selected not in document['visualizations']: return None
    placement = full_width_table(prompt, document, selected)
    if placement: return placement
    viz = document['visualizations'][selected]
    title = re.fullmatch(r'Rename only (?:this |the )?selected chart to "([^"\n]{1,200})"\.?', prompt, re.I)
    change = re.fullmatch(r'Change only this selected chart to an (area|line) chart and rename it "([^"\n]{1,200})"\. Preserve its search, page placement, interactions and every other element\.', prompt, re.I)
    if not title and not change: return None
    if change and viz.get('type') not in ('splunk.line', 'splunk.area'): return None
    path = '/visualizations/' + selected.replace('~', '~0').replace('/', '~1')
    changes = [{'op': 'set', 'path': path + '/title', 'value': json.dumps(title[1] if title else change[2])}]
    if change: changes.append({'op': 'set', 'path': path + '/type', 'value': json.dumps('splunk.' + change[1].lower())})
    apply_changes(document, changes)
    return changes
