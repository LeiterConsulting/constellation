"""Resolve native source references under the caller; never dispatch as a report owner.

Report previews replay guarded SPL in Constellation's bounded current-user jobs.
They deliberately do not impersonate a scheduled job or change a report.
"""
import re
from urllib.parse import quote
from provider_service import ProviderError

REPORT_WARNING = 'Report preview reruns permitted SPL as your user in the selected time range. Native Studio can use report permissions, app context and scheduled cached results instead.'


class SourceResolver:
    def __init__(self, runtime):
        self.runtime = runtime
        self.reports = {}
        self.used_report = False

    def report(self, options):
        ref, app = options.get('ref'), options.get('app', 'constellation')
        if (not isinstance(ref, str) or not 1 <= len(ref) <= 256 or any(ord(c) < 32 for c in ref)
                or not isinstance(app, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}', app)):
            raise ProviderError('A report source needs an exact report name and a valid app.', 422, 'report_reference')
        key = (app, ref)
        if key not in self.reports:
            path = '/servicesNS/' + quote(self.runtime.user, safe='') + '/' + quote(app, safe='') + '/saved/searches/' + quote(ref, safe='')
            result = self.runtime.request(path, optional=True)
            entries = result.get('entry', [])
            if len(entries) != 1 or entries[0].get('name') != ref or entries[0].get('acl', {}).get('app') != app:
                raise ProviderError('This report is unavailable to your user in the specified app. Check its name and read access in Splunk.', 422, 'report_unavailable')
            content = entries[0].get('content', {})
            query = content.get('search')
            if content.get('disabled') in (True, 1, '1', 'true') or not isinstance(query, str) or not query.strip():
                raise ProviderError('This report is disabled or has no usable search.', 422, 'report_unavailable')
            self.reports[key] = query
        self.used_report = True
        return self.reports[key], 'spl'

    def resolve(self, sources, identifier, seen=None):
        if not isinstance(sources, dict) or len(sources) > 200:
            raise ProviderError('Provide a bounded native data-source map.')
        seen = set() if seen is None else seen
        if not isinstance(identifier, str) or identifier in seen or len(seen) >= 30:
            raise ProviderError('A chain source is cyclic or too deep.', 422, 'source_reference')
        seen.add(identifier)
        source = sources.get(identifier)
        if not isinstance(source, dict) or not isinstance(source.get('options', {}), dict):
            raise ProviderError('The source reference is missing or invalid.', 422, 'source_reference')
        options = source.get('options', {})
        if source.get('type') == 'ds.savedSearch': return self.report(options)
        query = options.get('query')
        if not isinstance(query, str) or not query.strip():
            raise ProviderError('Provide a query for this native search source.', 422, 'source_reference')
        if source.get('type') == 'ds.chain':
            parent, language = self.resolve(sources, options.get('extend', source.get('extend')), seen)
            return parent.rstrip() + ' | ' + query.lstrip('| ').strip(), language
        if source.get('type') not in ('ds.search', 'ds.spl2'):
            raise ProviderError('This source requires native Studio execution.', 422, 'source_reference')
        return query, 'spl2' if source['type'] == 'ds.spl2' else 'spl'


def preview_query(runtime, body):
    if 'sourceRequest' not in body: return body.get('query'), body.get('language', 'spl'), ''
    request = body['sourceRequest']
    if not isinstance(request, dict) or set(request) - {'sources', 'id', 'tokens'}:
        raise ProviderError('The native preview source request is invalid.')
    resolver = SourceResolver(runtime)
    query, language = resolver.resolve(request.get('sources'), request.get('id'))
    from token_service import resolve_query_tokens
    query = resolve_query_tokens(query, {}, request.get('tokens'))
    return query, language, REPORT_WARNING if resolver.used_report else ''
