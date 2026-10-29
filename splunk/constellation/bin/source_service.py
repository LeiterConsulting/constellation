"""Resolve native source references under the caller; never dispatch as a report owner.

Report previews replay guarded SPL in bounded current-user jobs in the report app.
They deliberately do not impersonate a scheduled job or change a report.
"""
from urllib.parse import quote
from provider_service import ProviderError
from search_context import report_reference

REPORT_WARNING = 'Report preview reruns permitted SPL as your user in the report app and selected time range. Native Studio may use different report execution permissions and scheduled cached results.'


def expand_macros(runtime, query, app='constellation'):
    if not isinstance(query, str) or '`' not in query: return query
    from dashboard_dependencies import DashboardDependencies
    from portable_knowledge import PortableKnowledge
    return PortableKnowledge(runtime, DashboardDependencies(runtime).entry).expand(query, app)


class SourceResolver:
    def __init__(self, runtime):
        self.runtime = runtime
        self.reports = {}
        self.used_report = False
        self.report_app = 'constellation'
        self.report_reference = None

    def report(self, options):
        reference = report_reference({'ref': options.get('ref'), 'app': options.get('app', 'constellation')})
        ref, app = reference['ref'], reference['app']
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
            self.reports[key] = expand_macros(self.runtime, query, app)
        self.used_report = True
        self.report_app = app
        self.report_reference = reference
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
            transform = expand_macros(self.runtime, query, self.report_app)
            return parent.rstrip() + ' | ' + transform.lstrip('| ').strip(), language
        if source.get('type') not in ('ds.search', 'ds.spl2'):
            raise ProviderError('This source requires native Studio execution.', 422, 'source_reference')
        self.report_app = 'constellation'
        self.report_reference = None
        return expand_macros(self.runtime, query), 'spl2' if source['type'] == 'ds.spl2' else 'spl'


def preview_query(runtime, body):
    if 'sourceRequest' not in body:
        if 'report' not in body: return body.get('query'), body.get('language', 'spl'), '', 'constellation'
        resolver = SourceResolver(runtime)
        reference = report_reference(body['report'])
        base, language = resolver.report(reference)
        if body.get('language', 'spl') != language:
            raise ProviderError('Keep this report search in its native SPL language.', 422, 'report_scope')
        query = body.get('query', base)
        if not isinstance(query, str) or not 1 <= len(query) <= 8000:
            raise ProviderError('Provide a report-based query under 8000 characters.', 422, 'report_scope')
        query = expand_macros(runtime, query, resolver.report_app)
        from search_scope import scoped_suffix
        if scoped_suffix(query, {'baseQuery': base, 'scope': {}}) is None:
            raise ProviderError('Keep the current report search as the base, then append transforms. Reselect the report panel if its search changed.', 422, 'report_scope')
        from token_service import resolve_query_tokens
        return resolve_query_tokens(query, {}, body.get('tokens')), language, REPORT_WARNING, resolver.report_app
    if 'report' in body: raise ProviderError('Choose one native source reference.', 422, 'report_reference')
    request = body['sourceRequest']
    if not isinstance(request, dict) or set(request) - {'sources', 'id', 'tokens'}:
        raise ProviderError('The native preview source request is invalid.')
    resolver = SourceResolver(runtime)
    query, language = resolver.resolve(request.get('sources'), request.get('id'))
    from token_service import resolve_query_tokens
    query = resolve_query_tokens(query, {}, request.get('tokens'))
    return query, language, REPORT_WARNING if resolver.used_report else '', resolver.report_app
