"""Private Splunk-backed working documents, with revision checks and recoverable trash."""
import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import re
import uuid
from urllib.parse import quote
from provider_service import ProviderError
from studio_contract import validate_document
from model_capabilities import attachment_parts
from draft_migrations import SCHEMA_VERSION, migrate_snapshot
from dashboard_brief import validate_brief
import draft_history


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def validate_snapshot(state):
    allowed = {'definition', 'messages', 'prompt', 'attachments', 'tokens', 'activeTab', 'selected',
               'suggestions', 'activity', 'saved', 'dataContext', 'searchesEnabled', 'pendingRequest', 'pagePurposes', 'brief'}
    if not isinstance(state, dict) or set(state) - allowed or len(json.dumps(state)) > 11_500_000:
        raise ProviderError('This draft exceeds the supported size or contains unknown session properties.', 413)
    validate_document(state.get('definition'))
    from page_service import validate_purposes
    validate_purposes(state.get('pagePurposes', {}), state['definition'])
    validate_brief(state.get('brief', {}))
    messages = state.get('messages', [])
    if not isinstance(messages, list) or len(messages) > 100:
        raise ProviderError('A draft supports up to 100 conversation messages.')
    for message in messages:
        if (not isinstance(message, dict) or set(message) != {'id', 'user', 'text'}
                or type(message['id']) is not int or type(message['user']) is not bool
                or not isinstance(message['text'], str) or len(message['text']) > 8000):
            raise ProviderError('The draft conversation is invalid.')
    for name, maximum in (('prompt', 8000), ('pendingRequest', 8000), ('selected', 200), ('activeTab', 200)):
        if state.get(name) is not None and (not isinstance(state[name], str) or len(state[name]) > maximum):
            raise ProviderError('The draft contains an invalid ' + name + '.')
    # This only validates file contents for storage, without discovery or inference.
    attachment_parts(state.get('attachments', []), '', {'images': True, 'pdf': True})
    for name in ('tokens', 'dataContext'):
        if state.get(name) is not None and (not isinstance(state[name], dict) or len(json.dumps(state[name])) > 64000):
            raise ProviderError('The draft ' + name + ' is invalid.')
    if state.get('suggestions') is not None and (not isinstance(state['suggestions'], list) or len(state['suggestions']) > 3):
        raise ProviderError('The draft suggestions are invalid.')
    if not isinstance(state.get('activity', []), list) or len(json.dumps(state.get('activity', []))) > 12000:
        raise ProviderError('The draft activity is too large.')
    return state


class DraftService:
    def __init__(self, user, token, lock_dir=None):
        self.user, self.token = user, token
        digest = hashlib.sha256(user.encode('utf-8')).hexdigest()
        self.prefix = 'draft_' + digest[:20] + '_'
        self.preference = 'recent_' + digest[:20]
        self.base = '/servicesNS/' + quote(user, safe='') + '/constellation/configs/conf-constellation_drafts'
        self.lock_dir = lock_dir
        self.lock_name = digest + '.lock'

    def request(self, path, method='GET', fields=None, projection=False):
        import splunk.rest
        args = {'output_mode': 'json', 'count': '0'}
        if projection:
            args['f'] = ['title', 'version', 'schema_version', 'updated_at', 'deleted_at', 'kind', 'restored_at', 'active_id', 'native_name']
        try:
            _, raw = splunk.rest.simpleRequest(path, sessionKey=self.token, method=method,
                getargs=args, postargs=fields, raiseAllErrors=True)
            return json.loads(raw)
        except Exception as error:
            status = str(getattr(error, 'statusCode', ''))
            if status == '404': return None
            raise ProviderError('Draft storage is unavailable to this Splunk user. Your current work is still in this tab.', 403 if status == '403' else 503) from None

    @contextmanager
    def locked(self):
        # Serializes compare/write across persistent workers on this search head.
        root = self.lock_dir or os.path.join(os.environ['SPLUNK_HOME'], 'var', 'run', 'splunk', 'constellation_drafts')
        os.makedirs(root, mode=0o700, exist_ok=True)
        descriptor = os.open(os.path.join(root, self.lock_name), os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(descriptor, 'a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(handle, fcntl.LOCK_UN)

    def key(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r'[a-f0-9]{32}', identifier):
            raise ProviderError('Choose a valid draft ID.')
        return self.prefix + identifier

    def verify(self, entry):
        acl = entry.get('acl', {})
        if acl.get('owner') != self.user or acl.get('app') != 'constellation' or acl.get('sharing') != 'user':
            raise ProviderError('This draft is not private to the signed-in Splunk user.', 403)

    def entry(self, identifier):
        response = self.request(self.base + '/' + self.key(identifier))
        if not response or not response.get('entry'): return None
        entry = response['entry'][0]
        self.verify(entry)
        return entry

    def record(self, entry, include_state=True):
        content = entry['content']
        result = {'id': entry['name'][len(self.prefix):], 'title': content.get('title', 'Untitled dashboard'),
                  'version': int(content.get('version', 0)), 'updatedAt': content.get('updated_at', ''),
                  'deletedAt': content.get('deleted_at') or None, 'kind': content.get('kind', 'draft'),
                  'schemaVersion': int(content.get('schema_version', 0))}
        if include_state and 'state' in content: result['state'] = migrate_snapshot(json.loads(content['state']), result['schemaVersion'])
        return result

    def listing(self):
        result = self.request(self.base, projection=True) or {}
        drafts, trash, active, retained = [], [], None, 0
        for entry in result.get('entry', []):
            if entry.get('name') == self.preference:
                self.verify(entry)
                active = entry['content'].get('active_id') or None
            elif entry.get('name', '').startswith(self.prefix):
                self.verify(entry)
                retained += 1
                record = self.record(entry, include_state=False)
                if entry['content'].get('restored_at'): continue
                (trash if record['deletedAt'] else drafts).append(record)
        return {'drafts': sorted(drafts, key=lambda item: item['updatedAt'], reverse=True),
                'trash': sorted(trash, key=lambda item: item['updatedAt'], reverse=True), 'activeId': active, 'retainedRecords': retained, 'owner': self.user}

    def read(self, identifier, deleted=False):
        entry = self.entry(identifier)
        if entry and int(entry['content'].get('schema_version', 0)) > SCHEMA_VERSION:
            raise ProviderError('This draft uses a newer session schema. Its stored contents were preserved.', 409, 'draft_schema')
        if not entry: raise ProviderError('This draft no longer exists.', 404)
        record = self.record(entry)
        if record['deletedAt'] and not deleted: raise ProviderError('This draft is in Trash. Restore it before editing.', 409)
        return record

    def write(self, identifier, expected, state, deleted=None, kind='draft', extra=None, active=True):
        entry = self.entry(identifier)
        version = int(entry['content'].get('version', 0)) if entry else 0
        if type(expected) is not int or expected != version:
            raise ProviderError('This draft changed in another session. Save your current work as a new draft to keep both versions.', 409, 'draft_conflict')
        fields = {'title': state['definition'].get('title', '')[:200] or 'Untitled dashboard',
                  'state': json.dumps(state, separators=(',', ':'), ensure_ascii=True),
                  'version': str(version + 1), 'updated_at': timestamp(), 'deleted_at': deleted or '', 'kind': kind}
        old_state = migrate_snapshot(json.loads(entry['content']['state']), int(entry['content'].get('schema_version', 0))) if entry else None
        fields['history'] = draft_history.next_history(entry, state, old_state)
        fields['schema_version'] = str(SCHEMA_VERSION)
        fields.update(extra or {})
        path = self.base + '/' + self.key(identifier)
        if entry: self.request(path, 'POST', fields)
        else:
            listing = self.listing()
            if listing['retainedRecords'] >= 200:
                raise ProviderError('This account has reached the 200-record limit, including drafts and retained recovery copies.', 413)
            self.request(self.base, 'POST', dict(fields, name=self.key(identifier)))
        # User-namespace creation is already private. Changing its ACL requires
        # privileges an ordinary author need not hold; verify rather than widen.
        saved = self.entry(identifier)
        if not saved or any(saved['content'].get(key, '') != value for key, value in fields.items()):
            raise ProviderError('The saved draft did not match its readback. Your current work is still in this tab.', 503)
        if active and not deleted: self.set_active(identifier)
        return self.record(saved)

    def set_active(self, identifier):
        preference = self.request(self.base + '/' + self.preference)
        if preference:
            self.verify(preference['entry'][0])
            self.request(self.base + '/' + self.preference, 'POST', {'active_id': identifier})
        else: self.request(self.base, 'POST', {'name': self.preference, 'active_id': identifier})
        saved = self.request(self.base + '/' + self.preference)
        if not saved or not saved.get('entry'): raise ProviderError('The recent draft could not be verified.', 503)
        self.verify(saved['entry'][0])

    def operation(self, body):
        action, identifier = body.get('action', 'list'), body.get('id')
        if action == 'list': return self.listing()
        if action == 'read': return self.read(identifier)
        if action == 'history':
            self.read(identifier)
            return {'revisions': draft_history.summaries(self.entry(identifier))}
        with self.locked():
            if action == 'open':
                record = self.read(identifier)
                if record['kind'] != 'draft': raise ProviderError('Open a working draft from My dashboards.')
                self.set_active(identifier)
                return record
            if action == 'save':
                if body.get('schemaVersion', SCHEMA_VERSION) != SCHEMA_VERSION:
                    raise ProviderError('This browser uses a different draft format. Refresh the app before saving; your current work is still here.', 409, 'draft_schema')
                state = validate_snapshot(body.get('state'))
                old = self.entry(identifier)
                if old and int(old['content'].get('schema_version', 0)) > SCHEMA_VERSION:
                    raise ProviderError('This draft uses a newer session schema. Update the app before editing it.', 409, 'draft_schema')
                if old and old['content'].get('deleted_at'):
                    raise ProviderError('This draft was deleted in another session. Save a new draft to keep your current work.', 409, 'draft_conflict')
                if (old and type(body.get('version')) is int and body['version'] >= 0
                        and body['version'] < int(old['content']['version'])
                        and json.loads(old['content']['state']) == state):
                    return self.record(old)  # Retry after an unknown save outcome.
                return self.write(identifier, body.get('version'), state)
            record = self.read(identifier, deleted=True)
            if record['kind'] != 'draft': raise ProviderError('Use the saved-dashboard restore action for this item.')
            if record['deletedAt'] and action not in ('restore', 'duplicate'):
                raise ProviderError('Restore this draft before changing it.', 409)
            if body.get('version') != record['version']:
                raise ProviderError('The draft list changed. Refresh the list and retry.', 409, 'draft_conflict')
            if action == 'duplicate':
                state = copy.deepcopy(record['state'])
                state['definition']['title'] = (state['definition'].get('title', 'Dashboard') + ' · copy')[:200]
                state['saved'] = None
                return self.write(uuid.uuid4().hex, 0, state)
            if action == 'restore_revision':
                restored = draft_history.restore(record['state'], self.entry(identifier), body.get('revision'))
                validate_snapshot(restored)
                return self.write(identifier, record['version'], restored)
            if action == 'rename':
                title = body.get('title', '')
                if not isinstance(title, str) or not title.strip() or len(title) > 200:
                    raise ProviderError('Use a dashboard title from 1 to 200 characters.')
                record['state']['definition']['title'] = title.strip()
            elif action not in ('delete', 'restore'):
                raise ProviderError('This draft action is unavailable.', 404)
            return self.write(identifier, record['version'], record['state'],
                              deleted=timestamp() if action == 'delete' else None, active=action != 'delete')
