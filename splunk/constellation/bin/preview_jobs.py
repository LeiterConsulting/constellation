"""Short-lived, current-session search jobs with explicit completion evidence.

Handles authorize only jobs created by this service in this session. No job registry,
credentials, query text or results are persisted by Constellation.
"""
import hashlib
import hmac
import json
import re
import time
from datetime import datetime, timezone
from provider_service import ProviderError

ROWS, SECONDS = 200, 5


def flag(value):
    return value in (True, 1, '1', 'true')


def number(value):
    try: return max(0, int(value))
    except (ValueError, TypeError): return None


class PreviewJobs:
    def __init__(self, runtime):
        self.runtime = runtime
        self.base = runtime.namespace + '/search/v2/jobs'

    def signature(self, payload):
        return hmac.new(self.runtime.token.encode('utf-8'),
                        ('constellation-preview:' + self.runtime.user + ':' + payload).encode('utf-8'), hashlib.sha256).hexdigest()

    def path(self, handle):
        if not isinstance(handle, str) or len(handle) > 400:
            raise ProviderError('This preview job is unavailable to this session.', 403)
        parts = handle.split(':')
        if len(parts) != 4:
            raise ProviderError('This preview job is unavailable to this session.', 403)
        sid, earliest, expires, signature = parts
        payload = ':'.join(parts[:3])
        if (not re.fullmatch(r'[A-Za-z0-9_.-]{1,200}', sid) or not expires.isdigit()
                or not hmac.compare_digest(self.signature(payload), signature)):
            raise ProviderError('This preview job is unavailable to this session.', 403)
        if int(expires) < time.time():
            raise ProviderError('This preview expired. Refresh searches to run it again.', 410, 'preview_expired')
        return self.base + '/' + sid, earliest

    def start(self, query, earliest, field_discovery=False):
        result = self.runtime.request(self.base, 'POST', {
            'search': query, 'exec_mode': 'normal', 'earliest_time': earliest, 'latest_time': 'now',
            'max_time': str(SECONDS), 'max_count': str(ROWS + 1), 'auto_finalize_ec': '10000',
            'auto_cancel': '30', 'timeout': '60', 'adhoc_search_level': 'verbose' if field_discovery else 'fast', 'allow_partial_results': 'false'})
        sid = result.get('sid')
        if not isinstance(sid, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,200}', sid):
            raise ProviderError('Splunk did not return a preview job.', 503)
        payload = ':'.join((sid, earliest, str(int(time.time()) + 60)))
        return {'handle': payload + ':' + self.signature(payload), 'state': 'running'}

    def cancel(self, handle):
        path, _ = self.path(handle)
        self.runtime.request(path + '/control', 'POST', {'action': 'cancel'})
        return {'state': 'cancelled'}

    def poll(self, handle):
        from search_service import search_feedback
        path, earliest = self.path(handle)
        try:
            response = self.runtime.request(path)
        except ProviderError as error:
            if str(error.code or '').endswith('_404'):
                raise ProviderError('This preview expired. Refresh searches to run it again.', 410, 'preview_expired') from None
            raise
        entry = response.get('entry', [{}])[0]
        acl = entry.get('acl', {})
        if acl.get('owner') != self.runtime.user or acl.get('app') != 'constellation':
            raise ProviderError('This preview job is not owned by this user and app.', 403)
        meta = entry.get('content', {})
        if flag(meta.get('isFailed')) or flag(meta.get('isZombie')) or meta.get('dispatchState') in ('FAILED', 'BAD_INPUT_CANCEL'):
            diagnostics = meta.get('messages', [])
            # Splunk versions can return diagnostics as text, dictionaries or
            # lists. Only the allowlisted classifier output leaves this boundary.
            diagnostic_text = json.dumps(diagnostics)[:20000]
            raise ProviderError('The preview search failed. ' + search_feedback(diagnostic_text), 422, 'preview_failed')
        if not flag(meta.get('isDone')) and not flag(meta.get('isFinalized')):
            return {'state': 'running'}
        # Results are POSTed so count is applied by both supported v2 endpoints.
        result = self.runtime.request(path + '/results', 'POST', {'count': str(ROWS + 1), 'offset': '0'})
        if result.get('resultsPending') is True:
            return {'state': 'running'}
        errors = [m for m in result.get('messages', []) if m.get('type') in ('ERROR', 'FATAL')]
        if errors:
            raise ProviderError('The preview search failed. ' + search_feedback(' '.join(str(m.get('text', '')) for m in errors)), 422, 'preview_failed')
        raw_rows = result.get('results', [])
        fields = result.get('fields') or [{'name': name} for name in (raw_rows[0] if raw_rows else {})]
        names = [f['name'] for f in fields if isinstance(f, dict) and isinstance(f.get('name'), str)][:100]
        rows = [{k: v for k, v in row.items() if k in names} for row in raw_rows[:ROWS] if isinstance(row, dict)]
        if len(json.dumps(rows)) > 1_000_000:
            raise ProviderError('The preview rows exceeded the allowed size. Select fewer fields.', 413)
        reasons = []
        if flag(meta.get('isFinalized')): reasons.append('Search stopped at a resource limit.')
        count = number(meta.get('resultCount'))
        if len(raw_rows) > ROWS or (count is not None and count > ROWS): reasons.append('Only the first 200 result rows are shown.')
        # Missing metadata and upstream warnings never become a completeness claim.
        if not flag(meta.get('isDone')) or 'isFinalized' not in meta or count is None: reasons.append('Splunk did not verify completion.')
        if any(m.get('type') in ('WARN', 'WARNING') for m in result.get('messages', [])) or meta.get('messages'):
            reasons.append('Splunk reported search diagnostics; results may be incomplete.')
        state = 'partial' if reasons else 'complete'
        return {'state': state, 'results': rows, 'fields': [{'name': name} for name in names], 'bounded': True,
                'evidence': {'state': state, 'reasons': reasons, 'resultCount': count, 'finalized': flag(meta.get('isFinalized')),
                             'checkedAt': datetime.now(timezone.utc).isoformat(), 'earliest': earliest, 'latest': 'now'},
                'limits': {'rows': ROWS, 'seconds': SECONDS, 'earliest': earliest, 'latest': 'now'},
                'warning': ' '.join(reasons)}

    def execute(self, query, earliest, field_discovery=False):
        handle = (self.start(query, earliest, field_discovery=True) if field_discovery else self.start(query, earliest))['handle']
        try:
            deadline = time.monotonic() + 9
            while time.monotonic() < deadline:
                check = getattr(self.runtime, 'check_cancel', None)
                if check: check()
                result = self.poll(handle)
                if result['state'] != 'running': return result
                time.sleep(0.15)
            raise ProviderError('The bounded preview did not finish. Simplify the search or refresh to retry.', 422, 'preview_timeout')
        finally:
            try: self.cancel(handle)
            except ProviderError: pass  # Job TTL and server resource limits still apply.
