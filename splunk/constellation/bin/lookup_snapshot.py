"""Complete, fixed literal CSV reads for explicit transfer, independent of previews.

No client query/job IDs, indexed searches, owner dispatch or filesystem reads.
The native job and paginated responses must prove completion before data is used.
"""
import json
import re
import time
from provider_service import ProviderError
from preview_jobs import flag, benign_lookup_notice
from search_references import NAME

ROWS, FIELDS, CSV_BYTES, JSON_BYTES, PAGE = 5000, 64, 1_000_000, 2_000_000, 500


def complete_metadata(runtime, response):
    entries = response.get('entry', [])
    if len(entries) != 1: raise ProviderError('Splunk did not verify the lookup job.')
    entry = entries[0];acl = entry.get('acl', {});meta = entry.get('content', {})
    if acl.get('owner') != runtime.user or acl.get('app') != 'constellation':
        raise ProviderError('This lookup job is not owned by your user and app.', 403)
    if flag(meta.get('isFailed')) or flag(meta.get('isZombie')) or meta.get('dispatchState') in ('FAILED', 'BAD_INPUT_CANCEL'):
        raise ProviderError('The native CSV read failed. Check lookup access in Splunk.', 422, 'lookup_read_failed')
    if flag(meta.get('isFinalized')): raise ProviderError('The CSV read stopped at a resource limit; no sample was exported.')
    if any(not benign_lookup_notice(m) for m in meta.get('messages', [])):
        raise ProviderError('Splunk reported CSV search diagnostics; no potentially incomplete table was exported.')
    if not flag(meta.get('isDone')): return None
    count = str(meta.get('resultCount', ''))
    if 'isFinalized' not in meta or not re.fullmatch(r'\d+', count):
        raise ProviderError('Splunk did not verify complete CSV results.')
    if int(count) > ROWS: raise ProviderError('This CSV exceeds the portable limit of 5,000 complete rows.')
    return int(count)


def read_static_csv(runtime, filename, clock=time.monotonic, sleep=time.sleep):
    if not isinstance(filename, str) or not re.fullmatch(NAME + r'\.csv', filename):
        raise ProviderError('Use an exact static CSV filename for transfer.')
    from dashboard_dependencies import DashboardDependencies
    entry = DashboardDependencies(runtime).entry
    if entry('data/lookup-table-files', filename) is None or entry('data/transforms/lookups', filename) is not None:
        raise ProviderError('The backing CSV is missing or shadowed by a same-name native definition. Move this dependency with native tools.')
    deadline = clock() + 20
    def check():
        callback = getattr(runtime, 'check_cancel', None)
        if callback: callback()
        if clock() >= deadline: raise ProviderError('The complete lookup read timed out. No sampled data was exported.', 422, 'lookup_read_timeout')
    result = _read_job(runtime, filename, check, sleep)
    if 'timeHeader' not in result: return result
    fields = result['timeHeader']
    # The results API formats _time for display. Pick a literal projection name
    # absent from the observed complete header, then verify every projected
    # page against that header. Only this second, complete job supplies cells.
    alias = next('constellation_csv_time_' + str(i) for i in range(FIELDS + 1)
                 if 'constellation_csv_time_' + str(i) not in fields)
    return _read_job(runtime, filename, check, sleep, (alias, fields))


def _read_job(runtime, filename, check, sleep, projection=None):
    base = runtime.namespace + '/search/v2/jobs';path = None
    try:
        check()
        query = '| inputlookup strict=true max=' + str(ROWS + 1) + ' ' + filename
        if projection: query += ' | rename _time AS ' + projection[0]
        result = runtime.request(base, 'POST', {'search': query,
            'exec_mode': 'normal', 'earliest_time': '-15m', 'latest_time': 'now', 'max_time': '5', 'max_count': str(ROWS + 1),
            'auto_finalize_ec': str(ROWS + 1), 'auto_cancel': '30', 'timeout': '60', 'adhoc_search_level': 'fast', 'allow_partial_results': 'false'})
        sid = result.get('sid')
        if not isinstance(sid, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,200}', sid):
            raise ProviderError('Splunk did not return a valid lookup job.', 503)
        path = base + '/' + sid
        while True:
            check();count = complete_metadata(runtime, runtime.request(path))
            if count is not None: break
            sleep(.15)
        fields, rows, size, offset = None, [], 0, 0
        while offset < count or fields is None:
            check();expected = min(PAGE, count - offset)
            result = runtime.request(path + '/results', 'POST', {'count': str(PAGE), 'offset': str(offset)})
            if result.get('resultsPending') is True: sleep(.15);continue
            if any(not benign_lookup_notice(m) for m in result.get('messages', [])):
                raise ProviderError('Splunk reported CSV result diagnostics; no potentially incomplete table was exported.')
            header = result.get('fields', [])
            if not isinstance(header, list) or any(not isinstance(item, dict) or not isinstance(item.get('name'), str) for item in header):
                raise ProviderError('The CSV header is invalid.')
            names = [item['name'] for item in header]
            if len(set(names)) != len(names): raise ProviderError('The CSV header contains duplicate fields.')
            if projection:
                alias, expected_fields = projection
                if alias not in names or '_time' in names or set('_time' if name == alias else name for name in names) != set(expected_fields):
                    raise ProviderError('The CSV header changed during timestamp projection. No table was exported.')
                names = expected_fields
            if not names and not count: raise ProviderError('The empty CSV did not return a complete header.')
            if (not 1 <= len(names) <= FIELDS or any(not isinstance(name, str) for name in names)
                    or len(set(names)) != len(names) or fields is not None and names != fields):
                raise ProviderError('The CSV header is invalid, changed or exceeds 64 fields.')
            fields = names;page = result.get('results')
            if not isinstance(page, list) or len(page) != expected:
                raise ProviderError('Splunk returned fewer or more CSV rows than its verified count. No partial table was exported.')
            if not projection and '_time' in names: return {'timeHeader': names}
            if projection:
                if any(not isinstance(row, dict) or '_time' in row for row in page):
                    raise ProviderError('Splunk did not return the projected CSV timestamp.')
                page = [{'_time' if key == alias else key: value for key, value in row.items()} for row in page]
            for row in page:
                if (not isinstance(row, dict) or set(row) - set(fields)
                        or any(not isinstance(v, str) or len(v) > 4000 or '\x00' in v for v in row.values())):
                    raise ProviderError('CSV transfer requires bounded scalar cells and a complete header.')
            size += len(json.dumps(page, ensure_ascii=False).encode('utf-8'))
            if size > JSON_BYTES: raise ProviderError('The CSV results exceed the transfer size budget.')
            rows.extend(page);offset += len(page)
            if not count: break
        check()
        if complete_metadata(runtime, runtime.request(path)) != count:
            raise ProviderError('The lookup job changed while reading its CSV results.')
        return {'state': 'complete', 'warning': '', 'fields': [{'name': name} for name in fields], 'results': rows}
    finally:
        if path:
            try: runtime.request(path + '/control', 'POST', {'action': 'cancel'})
            except ProviderError: pass  # TTL remains; dispatch/control is never replayed.
