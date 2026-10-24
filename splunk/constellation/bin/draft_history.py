"""Bounded material revisions, stored atomically beside the current snapshot.

History deliberately excludes chat, attachment contents, tokens and result caches.
Restoration changes the dashboard and brief while retaining today's conversation.
"""
import copy
import json
from provider_service import ProviderError

MAX_REVISIONS, MAX_BYTES = 10, 4_000_000
MATERIAL = ('definition', 'brief', 'pagePurposes', 'dataContext')


def material(state):
    return {key: copy.deepcopy(state[key]) for key in MATERIAL if key in state}


def revisions(entry):
    try:
        result = json.loads(entry['content'].get('history', '[]')) if entry else []
        if not isinstance(result, list): raise ValueError()
        return result
    except (ValueError, TypeError):
        raise ProviderError('The revision history could not be read. The saved draft was preserved.', 409)


def next_history(entry, state, old_state):
    history = revisions(entry)
    if old_state is not None and material(old_state) != material(state):
        content = entry['content']
        history.append({'version': int(content['version']), 'updatedAt': content.get('updated_at', ''),
                        'title': old_state['definition'].get('title', 'Untitled dashboard'), 'state': material(old_state)})
    history = history[-MAX_REVISIONS:]
    while history and len(json.dumps(history)) > MAX_BYTES:
        history.pop(0)
    return json.dumps(history, separators=(',', ':'), ensure_ascii=True)


def summaries(entry):
    return [{key: item[key] for key in ('version', 'updatedAt', 'title')} for item in reversed(revisions(entry))]


def restore(state, entry, version):
    revision = next((item for item in revisions(entry) if type(version) is int and item['version'] == version), None)
    if revision is None: raise ProviderError('This revision is no longer available. Refresh the history.', 404)
    result = copy.deepcopy(state)
    for key in MATERIAL:
        if key in revision['state']: result[key] = copy.deepcopy(revision['state'][key])
        else: result.pop(key, None)
    result.update(saved=None, selected='', tokens={}, activeTab=None, pendingRequest='')
    return result
