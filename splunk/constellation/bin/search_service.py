"""Current-session discovery and bounded read-only preview searches."""
import re
from urllib.parse import quote
import json
from provider_service import ProviderError
from compatibility import feature_profile

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
    def __init__(self, user, token):
        self.user, self.token = user, token
        self.namespace = '/servicesNS/' + quote(user, safe='') + '/constellation'

    def request(self, path, method='GET', fields=None, optional=False):
        import splunk.rest
        try:
            _, raw = splunk.rest.simpleRequest(path, sessionKey=self.token, method=method,
                getargs={'output_mode': 'json', 'count': '100'}, postargs=fields, raiseAllErrors=True)
            return json.loads(raw)
        except Exception as error:
            status = str(getattr(error, 'statusCode', ''))
            if optional and status in ('403', '404'):
                return {'unavailable': 'restricted' if status == '403' else 'not_available'}
            # Never forward a Splunk response body, query content, or session token.
            code = 'splunk_' + type(error).__name__ + ('_' + status if status.isdigit() else '')
            raise ProviderError('Splunk could not complete this discovery or search request. ' + search_feedback(str(error)), 422, code) from None

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
            try:
                sample = self.preview({'query': '| makeresults count=3 | stats count() AS generated_rows', 'language': 'spl2'})
                result['spl2']['adhoc'] = 'verified' if sample['results'] == [{'generated_rows': '3'}] else 'not_verified'
            except ProviderError:
                result['spl2']['adhoc'] = 'not_available_to_current_user'
        return result

    def datasets(self):
        result = self.request(self.namespace + '/data/indexes', optional=True)
        return {'indexes': [{'name': item['name'], 'kind': item.get('content', {}).get('datatype', 'event')}
                            for item in result.get('entry', []) if item.get('content', {}).get('disabled') not in (True, 1, '1')],
                'status': result.get('unavailable', 'available'),
                'note': 'Catalog visibility is not proof of search access. No indexed events were sampled.'}

    def preview(self, body):
        language = body.get('language', 'spl')
        query = read_only_query(body.get('query'), language)
        earliest = body.get('earliest', '-15m')
        if earliest not in TIME_RANGES:
            raise ProviderError('Choose a supported bounded preview time range.')
        result = self.execute(query, earliest)
        result['language'] = language
        return result

    def job(self, body):
        from preview_jobs import PreviewJobs
        jobs = PreviewJobs(self)
        action = body.get('action')
        if action in ('poll', 'cancel'):
            return getattr(jobs, action)(body.get('handle'))
        if action != 'start': raise ProviderError('Choose a valid preview job action.')
        query = read_only_query(body.get('query'), body.get('language', 'spl'))
        earliest = body.get('earliest', '-15m')
        if earliest not in TIME_RANGES: raise ProviderError('Choose a supported preview time range.')
        return jobs.start(query, earliest)

    def execute(self, query, earliest='-15m'):
        """Internal discovery and validation use the same completion contract."""
        from preview_jobs import PreviewJobs
        if earliest not in TIME_RANGES: raise ProviderError('Choose a supported time range.')
        return PreviewJobs(self).execute(query, earliest)
