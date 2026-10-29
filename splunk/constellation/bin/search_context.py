"""Explicit caller/app namespaces and bounded native report ancestry.

No owner selection, authority changes, cached-job impersonation or dispatch.
"""
import re
from urllib.parse import quote
from provider_service import ProviderError

APP = r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}'
SID = r'[A-Za-z0-9_.-]{1,200}'
RANGES = {'-15m', '-1h', '-24h', '-7d'}


def app_name(value):
    if not isinstance(value, str) or not re.fullmatch(APP, value):
        raise ProviderError('Use an exact native app name.', 422, 'source_context')
    return value


def namespace(user, app='constellation'):
    return '/servicesNS/' + quote(user, safe='') + '/' + app_name(app)


def results_namespace(user, path):
    prefix = '/servicesNS/' + quote(user, safe='') + '/'
    match = re.fullmatch(re.escape(prefix) + '(' + APP + ')/search/v2/jobs/' + SID + '/results', path)
    return namespace(user, match[1]) if match else None


def report_reference(value):
    if not isinstance(value, dict) or set(value) - {'ref', 'app'}:
        raise ProviderError('Use an exact report reference and app.', 422, 'report_reference')
    name = value.get('ref')
    if not isinstance(name, str) or not 1 <= len(name) <= 256 or any(ord(c) < 32 for c in name):
        raise ProviderError('Use an exact report name.', 422, 'report_reference')
    return {'ref': name, 'app': app_name(value.get('app', 'constellation'))}


def source_report(sources, identifier):
    if not isinstance(sources, dict):
        raise ProviderError('Use a valid native source map.', 422, 'source_reference')
    seen = set()
    while isinstance(identifier, str):
        if identifier in seen or len(seen) >= 30:
            raise ProviderError('A chain source is cyclic or too deep.', 422, 'source_reference')
        seen.add(identifier)
        source = sources.get(identifier, {})
        if not isinstance(source, dict) or not isinstance(source.get('options', {}), dict):
            raise ProviderError('Use a valid native source definition.', 422, 'source_reference')
        options = source.get('options', {})
        if source.get('type') == 'ds.savedSearch':
            return report_reference({'ref': options.get('ref'), 'app': options.get('app', 'constellation')})
        if source.get('type') != 'ds.chain': break
        identifier = options.get('extend', source.get('extend'))
    return None
