"""Conservative query-token dependency checks; no data, token or DOS evaluation."""
import re
from provider_service import ProviderError
TOKEN = re.compile(r'\$([A-Za-z0-9_.:-]+)(?:\|[A-Za-z]+)?\$')


def _cyclic_inputs(document):
    inputs = document.get('inputs', {})
    sources = document.get('dataSources', {})
    if not isinstance(inputs, dict) or not isinstance(sources, dict): return set()
    inputs = {key: value for key, value in inputs.items() if isinstance(value, dict)}
    owners, edges = {}, {key: set() for key in inputs}
    for key, item in inputs.items():
        options = item.get('options') or {}
        if not isinstance(options, dict): continue
        token = options.get('token')
        if isinstance(token, str): owners.setdefault((options.get('tokenNamespace') or 'default', token), set()).add(key)
    for key, item in inputs.items():
        links = item.get('dataSources') or {}
        if not isinstance(links, dict): continue
        pending, seen = list(links.values()), set()
        while pending:
            sid = pending.pop()
            if not isinstance(sid, str) or sid in seen: continue
            seen.add(sid)
            source = sources.get(sid, {})
            if not isinstance(source, dict): continue
            options = source.get('options') or {}
            if not isinstance(options, dict): continue
            # Saved-report query dependencies are not available in the native definition.
            query = options.get('query', '')
            if isinstance(query, str):
                for token in TOKEN.findall(query):
                    namespace, sep, name = token.partition(':')
                    edges[key].update(owners.get((namespace, name) if sep else ('default', token), set()))
            parent = options.get('extend') or source.get('extend')
            if parent: pending.append(parent)
    incoming = {key: set() for key in edges}
    for child, parents in edges.items():
        for parent in parents: incoming[parent].add(child)
    cyclic_edges = set()
    for start in edges:
        pending, seen = list(edges[start]), set()
        while pending:
            key = pending.pop()
            if key in seen: continue
            seen.add(key); pending.extend(edges.get(key, ()))
        # An incoming edge is cyclic only if its origin is reachable from here.
        cyclic_edges.update((origin, start) for origin in incoming[start] if origin in seen)
    return cyclic_edges



def validate_input_dependencies(document, previous):
    if (document.get('inputs') == previous.get('inputs') and document.get('dataSources') == previous.get('dataSources')): return
    if _cyclic_inputs(document) - _cyclic_inputs(previous):
        raise ProviderError('Dynamic inputs contain a query-token dependency cycle. Each child menu must depend on an upstream input, not itself or a descendant. Preserve unrelated inputs and searches.', 422, 'input_dependency_cycle')


def validate_menu_intent(prompt, document, previous):
    """Exact additive menu counts only; compound/ambiguous requests stay general."""
    match = re.search(r'\b(?:add|create)\s+(?:exactly\s+)?(one|two|three|four|[1-4])\s+(?:(?:global|native|dynamic|new)\s+)*(dropdowns?|multiselects?)(?:\s+inputs?)?\b', prompt, re.I)
    if not match or document == previous: return
    count = {'one': 1, 'two': 2, 'three': 3, 'four': 4}.get(match[1].lower(), int(match[1]) if match[1].isdigit() else 0)
    kind = 'input.multiselect' if match[2].lower().startswith('multiselect') else 'input.dropdown'
    added = [item for key, item in document.get('inputs', {}).items() if key not in previous.get('inputs', {}) and item.get('type') == kind]
    if len(added) != count:
        raise ProviderError('The current request requires exactly ' + str(count) + ' new ' + kind + ' inputs, but the proposal adds ' + str(len(added)) + '. Complete all requested menus in this atomic proposal using op:menu plus their scoped search actions; a search source alone does not create a usable menu. Preserve existing navigation and inputs.', 422, 'menu_intent')
    if re.search(r'\bdo not change any existing\b', prompt, re.I):
        if any(document.get('inputs', {}).get(key) != value for key, value in previous.get('inputs', {}).items()):
            raise ProviderError('Adding these menus must preserve every existing input and return button. Use additive op:menu actions; never replace the inputs collection.', 422, 'menu_preservation')


def additive_menu_plan(prompt, document, profile, attachments):
    if attachments or not profile or profile.get('scope', {}).get('language', 'spl') != 'spl' or not document.get('visualizations'): return None
    if not re.search(r'\bdo not change any existing\b', prompt, re.I): return None
    match = re.search(r'\b(?:add|create)\s+(?:exactly\s+)?(one|two|three|four|[1-4])\s+(?:(?:global|native|dynamic|new)\s+)*global\s+(?:(?:native|dynamic|new)\s+)*(dropdowns?|multiselects?)(?:\s+inputs?)?\b', prompt, re.I)
    if not match: return None
    count = {'one':1,'two':2,'three':3,'four':4}.get(match[1].lower(), int(match[1]) if match[1].isdigit() else 0)
    return {'count':count,'inputType':'input.multiselect' if match[2].lower().startswith('multiselect') else 'input.dropdown',
            'existingInputIds':list(document.get('inputs', {})), 'existingSourceIds':list(document.get('dataSources', {})),
            'existingTokens':[item.get('options', {}).get('token') for item in document.get('inputs', {}).values() if item.get('options', {}).get('token')]}


def validate_additive_menus(document, previous):
    for root in set(document) | set(previous):
        if root not in ('inputs', 'dataSources', 'layout') and document.get(root) != previous.get(root):
            raise ProviderError('New global menu planning must preserve every unrelated native property.', 422, 'menu_preservation')
    for root in ('inputs', 'dataSources'):
        if any(document.get(root, {}).get(key) != value for key, value in previous.get(root, {}).items()):
            raise ProviderError('New menus must preserve existing inputs, return buttons and searches; choose fresh IDs.', 422, 'menu_preservation')
    old_layout, layout = dict(previous.get('layout', {})), dict(document.get('layout', {}))
    before, after = old_layout.pop('globalInputs', []), layout.pop('globalInputs', [])
    added = set(document.get('inputs', {})) - set(previous.get('inputs', {}))
    if layout != old_layout or after[:len(before)] != before or set(after[len(before):]) != added or len(after) != len(before)+len(added):
        raise ProviderError('The menu compiler must append each new global input once and preserve all original layout/navigation.', 422, 'menu_preservation')
