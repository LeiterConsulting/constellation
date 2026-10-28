"""Current-session discovery and bounded read-only preview searches."""
import re
from urllib.parse import quote, parse_qsl
import copy
import json
from provider_service import ProviderError
from compatibility import feature_profile
from native_transport import native_read_retry, transport_failure

TIME_RANGES = {'-15m', '-1h', '-24h', '-7d'}

READ_COMMANDS = {'search', 'from', 'makeresults', 'stats', 'timechart', 'chart', 'eval',
                 'where', 'fields', 'table', 'rename', 'sort', 'head', 'bin', 'dedup',
                 'rex', 'fillnull', 'streamstats', 'eventstats', 'mvexpand', 'mvcombine',
                 'convert', 'spath', 'top', 'rare', 'untable', 'xyseries', 'transpose',
                 'addtotals', 'addcoltotals', 'tstats', 'metadata'}
COMMON_VIZ = ['splunk.singlevalue', 'splunk.singlevalueicon', 'splunk.singlevalueradial',
              'splunk.line', 'splunk.area', 'splunk.column', 'splunk.bar', 'splunk.table',
              'splunk.pie', 'splunk.scatter', 'splunk.bubble', 'splunk.treemap', 'splunk.punchcard',
              'splunk.sankey', 'splunk.linkgraph', 'splunk.map', 'splunk.markdown',
              'splunk.rectangle', 'splunk.ellipse', 'splunk.fillergauge', 'splunk.markergauge',
              'splunk.timeline', 'splunk.richtext', 'splunk.image', 'splunk.parallelcoordinates', 'splunk.events', 'splunk.choropleth.svg']
COMMON_VIZ.append('abslayout.line')


def read_only_query(query, language='spl'):
    if not isinstance(query, str) or not 1 <= len(query) <= 8000 or language not in ('spl', 'spl2'):
        raise ProviderError('Provide an SPL or SPL2 query under 8000 characters.')
    query = query.strip()
    if '`' in query or '$' in query:
        raise ProviderError('Resolve tokens and remove macros before running a bounded preview.')
    if re.match(r'^\|?\s*@spl2\b', query, re.I):
        if language != 'spl2':
            raise ProviderError('Use a ds.spl2 data source for an SPL2 query.')
        query = re.sub(r'^\|?\s*@spl2\b\s*', '', query, count=1, flags=re.I)
    segments, current, quoted, escaped = [], '', None, False
    for char in query:
        if escaped:
            current += char
            escaped = False
        elif char == '\\':
            current += char
            escaped = True
        elif quoted:
            current += char
            if char == quoted:
                quoted = None
        elif char in ('"', "'"):
            quoted = char
            current += char
        elif char in '`[];$':
            raise ProviderError('Preview supports read-only pipelines without macros, subsearches, module statements, or unresolved tokens.')
        elif char == '|':
            if current.strip():
                segments.append(current.strip())
            current = ''
        else:
            current += char
    if quoted or escaped:
        raise ProviderError('The search has an unfinished string.')
    if current.strip():
        segments.append(current.strip())
    if not segments or len(segments) > 30:
        raise ProviderError('Use a pipeline with 1 to 30 commands.')
    if not query.startswith('|') and not re.match(r'^(search|from|makeresults|tstats|metadata)\b', segments[0], re.I):
        segments[0] = 'search ' + segments[0]
    for segment in segments:
        match = re.match(r'^([a-zA-Z][a-zA-Z0-9_]*)\b', segment)
        command = match.group(1).lower() if match else ''
        if command not in READ_COMMANDS:
            raise ProviderError('This command is not enabled for bounded read-only previews: ' + command[:40])
        if command == 'from' and not re.match(r'^from\s+[A-Za-z_][A-Za-z0-9_.]*(?:\s|$)', segment, re.I):
            raise ProviderError('SPL2 previews support named index datasets, without dataset functions.')
        if command == 'makeresults':
            if not re.fullmatch(r'makeresults(?:\s+count\s*=\s*\d+)?', segment, re.I):
                raise ProviderError('Synthetic previews support makeresults with a numeric count only.')
            count = re.search(r'\bcount\s*=\s*(\d+)', segment, re.I)
            if count and int(count.group(1)) > 1000:
                raise ProviderError('Synthetic previews allow at most 1000 generated rows.')
    pipeline = ' | '.join(segments)
    syntax = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', pipeline)
    if re.search(r'\b(?:earliest|latest|starttime|endtime)\s*=', syntax, re.I):
        raise ProviderError('Remove inline time overrides for the bounded last-15-minute preview. The saved Studio query is preserved.')
    return '| @spl2 ' + pipeline if language == 'spl2' else '| ' + pipeline


def search_feedback(message):
    """Classify native diagnostics without forwarding bodies, query literals or tokens."""
    text = message.lower()
    if 'evalcommand' in text:
        return 'Correct the eval expression. Separate multiple field assignments with commas. SPL string literals use double quotes; single quotes identify fields. Preserve the verified aggregation, aliases and selected query scope.'
    for patterns, feedback in (
        (('number of wildcards', 'empty field specifier'), 'Avoid empty aggregate field specifiers. In SPL, event counts use count AS alias without parentheses; other aggregate functions need verified fields.'),
        (('unknown search command', 'unknown command'), 'Remove or replace an unknown search command using the supported read-only subset.'),
        (('unsupported function', 'unknown function', 'function is undefined'), 'Use a supported function and the verified field names.'),
        (('malformed', 'parse error', 'unable to parse', 'syntax error', 'unbalanced', 'unexpected token'), 'Correct the query syntax, quoting and parentheses.'),
        (('invalid argument', 'invalid value'), 'Correct command arguments and check their types against the verified field schema.'),
        (('permission', 'not authorized', 'forbidden'), 'This query is restricted for the current Splunk user; preserve the selected scope and use permitted searches.'),
        (('timed out', 'time limit', 'timeout'), 'Simplify the aggregation within the existing bounded time range.'),
    ):
        if any(pattern in text for pattern in patterns): return feedback
    return 'Check query syntax and current-user access using the verified fields.'


class SearchService:
    def __init__(self, user, token, request_timeout=20):
        self.user, self.token = user, token
        self.request_timeout = request_timeout
        self.namespace = '/servicesNS/' + quote(user, safe='') + '/constellation'

    def shared_aitk_status(self):
        # Missing capability/endpoint preserves the existing current-user route.
        result = self.request('/servicesNS/nobody/constellation/constellation/aitk/status', optional=True)
        return result if result.get('available') else {'available': False, 'connection': ''}

    def shared_aitk_complete(self, connection, prompt):
        status = self.shared_aitk_status()
        if not status.get('available') or status.get('connection') != connection: return None
        fields = {'action': 'complete', 'connection': connection, 'prompt': prompt}
        if getattr(self, 'aitk_run_handle', None): fields['runHandle'] = self.aitk_run_handle
        # Longer than the bounded AITK worker wait; never expose the system token here.
        import splunk.rest
        try:
            response, raw = splunk.rest.simpleRequest('/servicesNS/nobody/constellation/constellation/aitk/infer',
                sessionKey=self.token, method='POST', getargs={'output_mode': 'json'}, postargs=fields,
                timeout=105, raiseAllErrors=False)
            result = json.loads(raw)
        except Exception:
            raise ProviderError('Shared AITK inference could not be completed.', 502, 'aitk_inference_unavailable') from None
        if str(response.get('status', '200')) in ('401', '403'):
            raise ProviderError('Shared AITK access was denied. Ask an administrator to review your author role and connection policy.', 403, 'aitk_inference_denied')
        if 'error' in result:
            # Only fixed, app-owned errors leave the dedicated handler.
            raise ProviderError(result['error'], int(result.get('status', 502)), result.get('code', 'aitk_inference_failed'))
        if result.get('status') != 'completed' or not isinstance(result.get('output'), list):
            raise ProviderError('Shared AITK returned no usable completion.', 502, 'aitk_no_completion')
        return result

    def request(self, path, method='GET', fields=None, optional=False):
        import splunk.rest
        try:
            resource, _, query = path.partition('?')
            parameters = {'output_mode': 'json', 'count': '100'}
            parameters.update(parse_qsl(query, keep_blank_values=True))
            response, raw = native_read_retry(splunk.rest.simpleRequest, resource, self.namespace, method, self.request_timeout,
                check_cancel=getattr(self, 'check_cancel', None), sessionKey=self.token,
                getargs=parameters, postargs=fields, raiseAllErrors=True)
            # A finalized job can briefly report readiness before its results
            # endpoint supplies a body. 204 is pending, never an empty result or
            # invalid SPL. Only the owned preview-results reader handles it.
            results = self.namespace + '/search/v2/jobs/'
            if (str(response.get('status')) == '204' and method == 'POST'
                    and resource.startswith(results)
                    and re.fullmatch(r'[A-Za-z0-9_.-]{1,200}/results', resource[len(results):])):
                return {'resultsPending': True}
            return json.loads(raw)
        except ProviderError:
            raise
        except Exception as error:
            status = str(getattr(error, 'statusCode', ''))
            if optional and status in ('403', '404'):
                return {'unavailable': 'restricted' if status == '403' else 'not_available'}
            import ssl
            if isinstance(error, ssl.SSLError):
                raise ProviderError('Splunk could not verify its TLS connection. Ask an administrator to check its certificate configuration. Your previous dashboard is preserved.', 503, 'splunk_tls') from None
            if transport_failure(error):
                raise ProviderError('The Splunk connection was interrupted. Your previous dashboard is preserved; no query repair was attempted.', 503, 'splunk_transport') from None
            # Never forward a Splunk response body, query content, or session token.
            code = 'splunk_' + type(error).__name__ + ('_' + status if status.isdigit() else '')
            raise ProviderError('Splunk could not complete this discovery or search request. ' + search_feedback(str(error)), 422, code) from None

    def aitk_job_log(self, job_path):
        """Diagnostic text stays local to the AITK allowlist classifier."""
        prefix = '/servicesNS/' + quote(self.user, safe='') + '/Splunk_ML_Toolkit/search/jobs/'
        if not job_path.startswith(prefix) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,300}', job_path[len(prefix):]):
            raise ProviderError('The AITK diagnostic job is invalid.')
        import splunk.rest
        _, raw = splunk.rest.simpleRequest(job_path + '/search.log', sessionKey=self.token, raiseAllErrors=True, timeout=self.request_timeout)
        return raw.decode('utf-8', 'replace')[:1_000_000] if isinstance(raw, bytes) else str(raw)[:1_000_000]

    def environment(self, probe=False):
        info = self.request('/services/server/info')['entry'][0]['content']
        context = self.request('/services/authentication/current-context')['entry'][0]['content']
        studio = self.request('/services/apps/local/splunk-dashboard-studio', optional=True)
        studio_version = studio.get('entry', [{}])[0].get('content', {}).get('version', '')
        version = str(info.get('version', ''))
        features = feature_profile(version, context.get('capabilities', []))
        modules = self.request('/services/spl2/modules', optional=True)
        result = {'version': version, 'studioVersion': studio_version,
                  'spl': 'available' if 'search' in context.get('capabilities', []) else 'restricted',
                  'spl2': {'adhoc': 'not_checked', 'modules': modules.get('unavailable', 'available')},
                  'features': features,
                  'visualizations': COMMON_VIZ + (['splunk.networkGraph'] if features['networkGraph'] else []),
                  'preview': {'rows': 200, 'seconds': 5, 'timeRange': 'last 15 minutes',
                              'externalNavigation': 'paused', 'customVisualizations': 'native Studio only'}}
        if probe:
            from extension_service import installed_extensions
            result['customVisualizations'] = installed_extensions(self)
            try:
                sample = self.preview({'query': '| makeresults count=3 | stats count() AS generated_rows', 'language': 'spl2'})
                result['spl2']['adhoc'] = 'verified' if sample['results'] == [{'generated_rows': '3'}] else 'not_verified'
            except ProviderError:
                result['spl2']['adhoc'] = 'not_available_to_current_user'
        return result

    def datasets(self):
        if hasattr(self, '_dataset_catalog'):
            return copy.deepcopy(self._dataset_catalog)
        result = self.request(self.namespace + '/data/indexes', optional=True)
        catalog = {'indexes': [{'name': item['name'], 'kind': item.get('content', {}).get('datatype', 'event')}
                            for item in result.get('entry', []) if item.get('content', {}).get('disabled') not in (True, 1, '1')],
                'status': result.get('unavailable', 'available'),
                'note': 'Catalog visibility is not proof of search access. No indexed events were sampled.'}
        # Each REST request creates its own current-user runtime. Discovery,
        # profiling and repair share only this metadata snapshot, never a
        # process/global cache or search results. Native searches still enforce
        # the caller's actual permissions on every dispatch.
        self._dataset_catalog = copy.deepcopy(catalog)
        return catalog

    def preview(self, body):
        from source_service import preview_query
        raw_query, language, source_warning = preview_query(self, body)
        query = read_only_query(raw_query, language)
        earliest = body.get('earliest', '-15m')
        if earliest not in TIME_RANGES:
            raise ProviderError('Choose a supported bounded preview time range.')
        if body.get('fieldDiscovery') is True:
            # Raw searches in fast mode omit fields not referenced by the SPL.
            # Inspection needs extracted metadata, under the same job limits.
            from preview_jobs import PreviewJobs
            result = PreviewJobs(self).execute(query, earliest, field_discovery=True)
        else:
            result = self.execute(query, earliest)
        result['language'] = language
        if source_warning: result['warning'] = (result.get('warning', '') + ' ' + source_warning).strip()
        return result

    def job(self, body):
        from preview_jobs import PreviewJobs
        jobs = PreviewJobs(self)
        action = body.get('action')
        if action in ('poll', 'cancel'):
            return getattr(jobs, action)(body.get('handle'))
        if action != 'start': raise ProviderError('Choose a valid preview job action.')
        from source_service import preview_query
        raw_query, language, source_warning = preview_query(self, body)
        query = read_only_query(raw_query, language)
        earliest = body.get('earliest', '-15m')
        if earliest not in TIME_RANGES: raise ProviderError('Choose a supported preview time range.')
        result = jobs.start(query, earliest)
        if source_warning: result['sourceWarning'] = source_warning
        result['language'] = language
        return result

    def execute(self, query, earliest='-15m'):
        """Internal discovery and validation use the same completion contract."""
        from preview_jobs import PreviewJobs
        if earliest not in TIME_RANGES: raise ProviderError('Choose a supported time range.')
        return PreviewJobs(self).execute(query, earliest)
