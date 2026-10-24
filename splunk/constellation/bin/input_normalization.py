"""Canonicalize a precise model-authored button action alias, preserving imports."""
import json
from provider_service import ProviderError


def normalize_button_actions(document, previous):
    changes = []
    for identifier, item in document.get('inputs', {}).items():
        old = previous.get('inputs', {}).get(identifier, {})
        handler = item.get('drilldown')
        if item.get('type') != 'input.button' or handler is None or item == old: continue
        exact = isinstance(handler, dict) and set(handler) == {'type', 'options'} and handler.get('type') == 'drilldown.setToken'
        native = item.get('eventHandlers')
        if handler == old.get('drilldown') and (native or not exact): continue
        if not exact or (native and native != [handler]):
            raise ProviderError('Put button actions in the native eventHandlers array. A root drilldown property is ignored by Studio; preserve any existing handlers.')
        path = '/inputs/' + identifier.replace('~', '~0').replace('/', '~1')
        if not native: changes.append({'op': 'set', 'path': path + '/eventHandlers', 'value': json.dumps([handler])})
        changes.append({'op': 'remove', 'path': path + '/drilldown', 'value': ''})
    return changes
