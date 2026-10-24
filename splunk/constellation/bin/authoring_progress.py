"""Ephemeral stage receipts and cooperative stop, confined to this search head.

No prompts, definitions, credentials, results or provider errors are stored. A
session-signed handle authorizes one execution; short control requests run in a
separate persistconn driver so inference cannot block polling or Stop.
"""
import fcntl
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from contextlib import contextmanager
from provider_service import ProviderError

STAGES = {'queued', 'inspect', 'profile', 'model', 'validate', 'search', 'repair', 'complete', 'failed', 'cancelled'}
TERMINAL = {'complete', 'failed', 'cancelled'}
TTL = 300


class AuthoringProgress:
    def __init__(self, user, token, root=None, clock=time.time):
        self.user, self.token, self.clock = user, token, clock
        self.root = root or os.path.join(os.environ['SPLUNK_HOME'], 'var', 'run', 'splunk', 'constellation_runs')

    def sign(self, value):
        return hmac.new(self.token.encode(), ('constellation-author:' + self.user + ':' + value).encode(), hashlib.sha256).hexdigest()

    def path(self, handle):
        if not isinstance(handle, str) or not re.fullmatch(r'[a-f0-9]{32}:[a-f0-9]{64}', handle):
            raise ProviderError('This authoring request is unavailable to this session.', 403)
        nonce, signature = handle.split(':')
        if not hmac.compare_digest(signature, self.sign(nonce)):
            raise ProviderError('This authoring request is unavailable to this session.', 403)
        return os.path.join(self.root, nonce + '.json')

    @contextmanager
    def locked(self):
        os.makedirs(self.root, mode=0o700, exist_ok=True)
        fd = os.open(os.path.join(self.root, 'control.lock'), os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(lock, fcntl.LOCK_UN)

    def read(self, path):
        try:
            with open(path) as source: result = json.loads(source.read(12000))
        except (FileNotFoundError, ValueError):
            raise ProviderError('This authoring request expired. Your draft is preserved.', 410, 'author_expired') from None
        if result['expires'] <= self.clock():
            raise ProviderError('This authoring request expired. Your draft is preserved.', 410, 'author_expired')
        return result

    def write(self, path, state):
        # Readers/writers share the lock; no partially written receipt is read.
        fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as target: json.dump(state, target)

    def operation(self, body):
        action = body.get('action')
        with self.locked():
            if action == 'start':
                owner = self.sign('owner')
                active, total = 0, 0
                for name in os.listdir(self.root):
                    if not re.fullmatch(r'[a-f0-9]{32}\.json', name): continue
                    path = os.path.join(self.root, name)
                    try: state = self.read(path)
                    except ProviderError:
                        os.unlink(path)
                        continue
                    total += 1
                    if state['owner'] == owner and (state['stage'] not in TERMINAL or (state['claimed'] and not state.get('finished'))): active += 1
                if active >= 2 or total >= 512:
                    raise ProviderError('Another authoring request is still active. Stop it or wait for it to finish.', 429)
                nonce = secrets.token_hex(16)
                handle = nonce + ':' + self.sign(nonce)
                state = {'owner': owner, 'started': self.clock(), 'expires': self.clock() + TTL, 'claimed': False,
                         'stage': 'queued', 'events': [{'stage': 'queued', 'seconds': 0, 'attempt': 0}]}
                self.write(self.path(handle), state)
                return {'handle': handle, **self.public(state)}
            path = self.path(body.get('handle'))
            state = self.read(path)
            if action == 'cancel':
                if state['stage'] not in TERMINAL: self.stage(state, 'cancelled', 0)
                self.write(path, state)
            elif action != 'poll': raise ProviderError('Choose a valid authoring control action.')
            return self.public(state)

    def public(self, state):
        seconds = state['events'][-1]['seconds'] if state['stage'] in TERMINAL else round(max(0, self.clock() - state['started']), 1)
        return {'stage': state['stage'], 'events': state['events'], 'seconds': seconds}

    def stage(self, state, stage, attempt):
        if stage not in STAGES: raise ValueError('Unknown authoring stage')
        state['stage'] = stage
        state['events'] = (state['events'] + [{'stage': stage, 'seconds': round(max(0, self.clock() - state['started']), 1), 'attempt': attempt}])[-24:]

    def claim(self, handle):
        path = self.path(handle)
        with self.locked():
            state = self.read(path)
            if state['stage'] == 'cancelled': self.cancelled()
            if state['claimed']: raise ProviderError('This authoring request has already started. It cannot be replayed.', 409)
            state['claimed'] = True
            self.write(path, state)
        return lambda stage=None, attempt=0: self.check(handle, stage, attempt)

    def check(self, handle, stage=None, attempt=0):
        path = self.path(handle)
        with self.locked():
            state = self.read(path)
            if state['stage'] == 'cancelled': self.cancelled()
            if stage:
                self.stage(state, stage, attempt)
                self.write(path, state)

    def release(self, handle):
        with self.locked():
            try: state = self.read(self.path(handle))
            except ProviderError: return
            state['finished'] = True
            self.write(self.path(handle), state)

    @staticmethod
    def cancelled():
        raise ProviderError('Stopped. Your previous dashboard is preserved.', 409, 'author_cancelled')
