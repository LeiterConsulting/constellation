"""Current-user dataset grounding; only field metadata reaches the authoring model."""
import json
import re
from provider_service import ProviderError
from search_service import read_only_query, TIME_RANGES
from token_service import resolve_query_tokens, validate_wildcard_filters
from search_scope import scoped_suffix
from population_guard import validate_populations
from search_evidence import sample_completion, empty_columns, verified_null_columns
from search_hints import preview_repair_hint
from field_context import sample_fields, enrich_profile, validate_missing_measurements, validate_definitions


def spl_literal(value):
    return json.dumps(value, ensure_ascii=True)


class DataService:
    def __init__(self, runtime, recovery=None, document=None, tokens=None, independent_populations=False):
        self.runtime, self.recovery = runtime, recovery
        self.document, self.tokens = document or {}, tokens
        self.receipts = []
        self.independent_populations = independent_populations

    def discovery(self):
        catalog = self.runtime.datasets()
        visible = {item['name'] for item in catalog['indexes']}
        activity, problem = [], ''
        try:
            result = self.runtime.execute('| tstats count WHERE (index=* OR index=_internal) BY index sourcetype | eval priority=if(substr(index,1,1)="_",1,0) | sort priority - count | head 120 | fields index sourcetype count', '-24h')
            activity = [{'index': row['index'], 'sourcetype': str(row.get('sourcetype', ''))[:200], 'events': str(row.get('count', ''))[:30]}
                        for row in result['results'] if row.get('index') in visible]
        except ProviderError:
            problem = 'Recent dataset activity could not be checked. You can still choose a catalog-visible index or supply a search.'
        return dict(catalog, activity=activity, earliest='-24h', warning=problem,
                    note='Current-user catalog and bounded indexed-metadata search. Counts may be incomplete; no event values are returned.')

    def profile(self, body):
        definitions = validate_definitions(body.get('fieldDefinitions'))
        earliest = body.get('earliest', '-24h')
        if earliest not in TIME_RANGES: raise ProviderError('Choose one of the supported preview time ranges.')
        if body.get('query'):
            query, language = body['query'], body.get('language', 'spl')
            if not isinstance(query, str): raise ProviderError('Supply an existing search.')
            inspection = resolve_query_tokens(query, self.document, self.tokens)
            if language == 'spl': inspection += ' | head 201'
            result = self.runtime.preview({'query': inspection, 'language': language, 'earliest': earliest, 'fieldDiscovery': True})
            if not result['results'] and result.get('state') == 'partial':
                raise ProviderError('The sample stopped before completion. No absence of data was established; simplify the existing search or retry.', 422, 'profile_partial')
            fields, sampled = sample_fields(result)
            return enrich_profile({'scope': {'query': query, 'language': language, 'earliest': earliest, **({'fieldDefinitions': definitions} if definitions else {})}, 'baseQuery': query,
                    'fields': fields, 'sampledRows': sampled, 'bounded': True,
                    'completion': sample_completion(result),
                    'note': 'Field metadata from at most 200 returned rows, not complete source coverage. Missing counts refer only to this sample; event values are excluded.'}, body.get('question', ''))
        index, sourcetype = body.get('index'), body.get('sourcetype', '')
        catalog = self.runtime.datasets()
        if not isinstance(index, str) or index not in {item['name'] for item in catalog['indexes']}:
            raise ProviderError('Choose an index visible to this Splunk user.')
        if not isinstance(sourcetype, str) or len(sourcetype) > 200 or any(ord(char) < 32 for char in sourcetype):
            raise ProviderError('Choose a valid sourcetype.')
        base = 'search index=' + spl_literal(index) + (' sourcetype=' + spl_literal(sourcetype) if sourcetype else '')
        result = self.runtime.preview({'query': base + ' | head 201', 'language': 'spl', 'earliest': earliest, 'fieldDiscovery': True})
        if not result['results'] and result.get('state') == 'partial':
            raise ProviderError('The field inspection stopped before completion. Retry inspection; the source has not been proven empty.', 422, 'profile_partial')
        fields, sampled = sample_fields(result)
        return enrich_profile({'scope': {'index': index, 'sourcetype': sourcetype, 'earliest': earliest, 'language': 'spl', **({'fieldDefinitions': definitions} if definitions else {})},
                'baseQuery': base, 'fields': fields, 'sampledRows': sampled,
                'bounded': True, 'completion': sample_completion(result),
                'note': 'Field metadata from at most 200 recent returned events and 5 seconds, not complete source coverage. Missing counts refer only to the inspected sample. Event values are excluded.'}, body.get('question', ''))

    def resolve_query(self, document, identifier, seen=None):
        seen = set() if seen is None else seen
        if identifier in seen: raise ProviderError('A chain search contains a cycle.')
        seen.add(identifier)
        source = document.get('dataSources', {}).get(identifier, {})
        options = source.get('options', {})
        query = options.get('query', '')
        if source.get('type') == 'ds.chain':
            parent, language = self.resolve_query(document, options.get('extend', source.get('extend')), seen)
            return parent.rstrip() + ' | ' + query.lstrip('| ').strip(), language
        if source.get('type') not in ('ds.search', 'ds.spl2'):
            raise ProviderError('Use a search or a compatible chain source for this real-data draft.')
        return query, 'spl2' if source['type'] == 'ds.spl2' else 'spl'

    def inspect_source(self, document, identifier, source, profile):
        if source.get('type') == 'ds.test':
            raise ProviderError('This dashboard uses real Splunk data. Do not introduce illustrative sample data.')
        query, language = self.resolve_query(document, identifier)
        # Keep generated queries within the explicitly selected search scope.
        suffix = scoped_suffix(query, profile)
        if suffix is None or (suffix.strip() and not suffix.lstrip().startswith('|')):
            raise ProviderError('Start with the supplied baseQuery, then a pipe before filters or aggregations. Preserve its index/sourcetype scope.', 422, 'search_scope')
        if re.search(r'(?:^|\|)\s*(?:from|makeresults|metadata|tstats)\b', suffix, re.I):
            raise ProviderError('Append transforming commands to the selected source; do not replace it with another generating command.')
        resolved_query = resolve_query_tokens(query, document, self.tokens)
        read_only_query(resolved_query, language)
        # A fine span can silently truncate the preview's chronological tail.
        syntax = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', query)
        window = {'-15m': 900, '-1h': 3600, '-24h': 86400, '-7d': 604800}[profile['scope']['earliest']]
        for segment in re.findall(r'(?:^|\|)\s*timechart\b([^|]*)', syntax, re.I):
            span = re.search(r'\bspan\s*=\s*(\d+(?:\.\d+)?)(s|m|h|d)\b', segment, re.I)
            if span:
                seconds = float(span[1]) * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[span[2].lower()]
                if seconds <= 0 or window / seconds + 2 > 200:
                    raise ProviderError('The timechart span exceeds the 200-row preview budget across the selected window. Use timechart bins=100 without span, or a coarser span. Do not truncate the series with head.')
        if source.get('type') in ('ds.search', 'ds.spl2'):
            parameters = source.get('options', {}).get('queryParameters', {})
            if parameters.get('earliest') != profile['scope']['earliest'] or parameters.get('latest') != 'now':
                raise ProviderError('Set each new search options.queryParameters to earliest=' + profile['scope']['earliest'] + ' and latest=now so native Studio uses the inspected time range.')
        result = (self.recovery or self.runtime).preview({'query': resolved_query, 'language': language, 'earliest': profile['scope']['earliest']})
        return language, result

    def focused_table_receipt(self, document, selected, profile):
        table = document.get('visualizations', {}).get(selected, {})
        source_id = table.get('dataSources', {}).get('primary')
        source = document.get('dataSources', {}).get(source_id, {})
        if table.get('type') != 'splunk.table' or source.get('type') != 'ds.search': return None
        receipt = {'table': selected, 'source': source_id, 'query': source['options'].get('query', ''), 'fields': []}
        try:
            _language, result = self.inspect_source(document, source_id, source, profile)
            for entry in result['fields'][:80]:
                name = entry['name']
                values = [row[name] for row in result['results'] if row.get(name) not in (None, '', [])]
                numeric = bool(values)
                for value in values:
                    try: float(value)
                    except (ValueError, TypeError): numeric = False; break
                receipt['fields'].append({'name': name, 'numeric': numeric})
            receipt['status'] = result.get('state', 'unknown')
        except ProviderError as error:
            if error.code in ('recovery_budget', 'author_cancelled', 'author_expired'): raise
            receipt.update(status='failed', code=error.code)
        return receipt

    def validate_searches(self, document, previous, profile):
        receipts = self.receipts = []
        usable = {}
        static_types = {'splunk.markdown', 'splunk.richtext', 'splunk.rectangle', 'splunk.ellipse', 'splunk.image'}
        layouts = document.get('layout', {}).get('layoutDefinitions') or {'legacy': document.get('layout', {})}
        placed = {item.get('item') for layout in layouts.values() for item in layout.get('structure', [])}
        missing_bindings, unplaced = [], []
        for identifier, visualization in document.get('visualizations', {}).items():
            if visualization == previous.get('visualizations', {}).get(identifier): continue
            if visualization.get('type') not in static_types and not visualization.get('dataSources', {}).get('primary'):
                missing_bindings.append(identifier)
            if identifier not in previous.get('visualizations', {}) and identifier not in placed:
                unplaced.append(identifier)
        if missing_bindings or unplaced:
            details = []
            if missing_bindings: details.append('Bind visualization.dataSources.primary to its actual source ID for: ' + ', '.join(missing_bindings)[:400])
            if unplaced: details.append('Place each new visualization in the active page using the typed layout action: ' + ', '.join(unplaced)[:400])
            raise ProviderError('; '.join(details))
        base = profile['baseQuery'].strip().lstrip('| ').strip()
        needed = set()
        for identifier, visualization in document.get('visualizations', {}).items():
            old = previous.get('visualizations', {}).get(identifier, {})
            channels = ('x', 'y', 'y2', 'category', 'majorValue', 'table')
            if (visualization.get('dataSources') != old.get('dataSources') or
                    visualization.get('eventHandlers') != old.get('eventHandlers') or
                    any(visualization.get('options', {}).get(key) != old.get('options', {}).get(key) for key in channels)):
                needed.update(visualization.get('dataSources', {}).values())
        pending = [(identifier, source) for identifier, source in document.get('dataSources', {}).items()
                   if source != previous.get('dataSources', {}).get(identifier) or identifier in needed]
        if len(pending) > 8: raise ProviderError('Build at most eight new search sources in one turn.')
        problems = []
        for identifier, source in pending:
            try:
                if source.get('options', {}).get('query') != previous.get('dataSources', {}).get(identifier, {}).get('options', {}).get('query'):
                    validate_wildcard_filters(source.get('options', {}).get('query', ''), document)
                    query, language = self.resolve_query(document, identifier)
                    suffix = scoped_suffix(query, profile)
                    if suffix is not None: validate_missing_measurements(suffix, profile, language)
                    if self.independent_populations: validate_populations(source.get('options', {}).get('query', ''), profile)
                language, result = self.inspect_source(document, identifier, source, profile)
            except ProviderError as error:
                if error.code in ('recovery_budget', 'author_cancelled', 'author_expired'): raise
                receipt = {'source': identifier, 'status': 'failed', 'code': error.code,
                           'earliest': profile['scope']['earliest'], 'bounded': True}
                if error.code == 'search_scope': receipt['requiredPrefix'] = base
                receipts.append(receipt)
                hint = preview_repair_hint(source.get('options', {}).get('query'), 'spl' if source.get('type') == 'ds.search' else '', error.code)
                problems.append('Source ' + identifier[:100] + ': ' + str(error)[:600] + (' ' + hint if hint else ''))
                continue
            fields = [field['name'] for field in result['fields']]
            # Successful filtered searches can legitimately have no matches. In
            # particular, zero statistical outliers must not reject other panels.
            # A returned column can be entirely null in sparse data or after a
            # measurement exclusion. Its schema still supports a native binding;
            # never invent a replacement value or reject it as an absent alias.
            empty = empty_columns(fields, result['results'])
            nullable = verified_null_columns(self.resolve_query(document, identifier)[0], language, profile) if empty else set()
            usable[identifier] = (set(fields) - set(empty)) | (set(empty) & nullable) if result['results'] else set(fields) if fields else None
            receipts.append({'source': identifier, 'language': language, 'rows': len(result['results']),
                             'fields': fields, 'earliest': profile['scope']['earliest'], 'bounded': True, 'completion': result.get('evidence', {'state': 'unknown'}),
                             'emptyFields': empty,
                             'status': 'partial' if result.get('state') == 'partial' else 'results' if result['results'] else 'empty'})
        for identifier, visualization in document.get('visualizations', {}).items():
            source_id = visualization.get('dataSources', {}).get('primary')
            if source_id not in usable: continue
            fields = next((receipt['fields'] for receipt in receipts if receipt.get('source') == source_id and 'fields' in receipt), [])
            if visualization.get('type') == 'splunk.table' and fields:
                linked_fields = {field for handler in visualization.get('eventHandlers', []) for field in handler.get('options', {}).get('fields', [])}
                if linked_fields - set(fields):
                    problems.append('Table ' + identifier[:100] + ' drilldown references absent fields. Tested output fields: ' + ', '.join(fields)[:400])
            for channel in ('x', 'y', 'y2', 'category', 'majorValue', 'table'):
                binding = visualization.get('options', {}).get(channel)
                if binding is None: continue
                if not isinstance(binding, str) or not binding.lstrip().startswith(('>', '$')):
                    problems.append('Visualization ' + identifier[:100] + ', channel ' + channel + ': bind to search output, not constant sample values.')
                    continue
                if binding != previous.get('visualizations', {}).get(identifier, {}).get('options', {}).get(channel) and re.search(r'\|\s*eval\s+', binding, re.I):
                    problems.append('Visualization ' + identifier[:100] + ', channel ' + channel + ': SPL eval is not a native DOS binding function. Format fields in the ds.search query with eval round/strftime after aggregation, then bind the existing output fields with seriesByName/frameBySeriesNames. Preserve query scope and temperature/Wi-Fi exclusions.')
                    continue
                for args in re.findall(r'(?:seriesByName|frameBySeriesNames)\(([^)]*)\)', binding):
                    names = re.findall(r'''['"]([^'"]+)['"]''', args)
                    missing = [name for name in names if usable[source_id] is not None and name not in usable[source_id]]
                    if missing:
                        query, _language = self.resolve_query(document, source_id)
                        hint = (' A timechart BY clause creates split-series columns instead of the aggregation alias. For one combined or already-filtered trend, remove BY and keep the alias; do not invent a different field.'
                                if re.search(r'\btimechart\b[^|]*\bby\b', query, re.I) else '')
                        problems.append('Visualization ' + identifier[:100] + ', channel ' + channel + ', source ' + source_id[:100] + ': missing output fields ' + ', '.join(missing)[:180] + '. Tested output fields: ' + ', '.join(sorted(usable[source_id]))[:300] + '.' + hint +
                            (' Table projections must match the search output. For a requested NEW metric, add its calculation with the exact alias to the selected search before projecting it. Preserve existing columns and row-navigation fields. For formatting alone, preserve the verified aggregation and aliases.' if channel == 'table' else ''))
        if problems:
            raise ProviderError('\n'.join(problems[:16])[:10000])
        return receipts
