"""Versioned session format. Future schemas are never silently rewritten."""
import copy
from provider_service import ProviderError

SCHEMA_VERSION = 2


def migrate_snapshot(state, version):
    if type(version) is not int or version < 0 or version > SCHEMA_VERSION:
        raise ProviderError('This draft was saved by a newer app version. Update Constellation before editing it.', 409, 'draft_schema')
    result = copy.deepcopy(state)
    if version == 0:
        for name, value in {'attachments': [], 'suggestions': None, 'activity': [], 'dataContext': None,
                            'searchesEnabled': False, 'pendingRequest': ''}.items():
            result.setdefault(name, value)
    if version < 2:
        result.setdefault('pagePurposes', {})
    return result
