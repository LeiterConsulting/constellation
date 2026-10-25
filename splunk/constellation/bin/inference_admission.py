"""Local per-provider inference admission; no prompts, keys or raw usernames."""
import fcntl
import hashlib
import json
import os
import re
import secrets
import time
from contextlib import contextmanager
from provider_service import ProviderError


@contextmanager
def admission(user, root=None, clock=time.time, provider='aitk'):
    """Bound this privileged resource; retain only short-lived anonymous slot metadata."""
    if provider not in ('aitk', 'openai'): raise ValueError('Unknown inference resource')
    root = root or os.path.join(os.environ['SPLUNK_HOME'], 'var', 'run', 'splunk', 'constellation_' + provider)
    os.makedirs(root, mode=0o700, exist_ok=True)
    owner, name = hashlib.sha256(user.encode()).hexdigest(), secrets.token_hex(16) + '.json'
    path = os.path.join(root, name)
    def lock(): return os.fdopen(os.open(os.path.join(root, 'admission.lock'), os.O_CREAT | os.O_RDWR, 0o600), 'a')
    with lock() as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        active = []
        for filename in os.listdir(root):
            if not re.fullmatch(r'[a-f0-9]{32}\.json', filename): continue
            item_path = os.path.join(root, filename)
            try:
                with open(item_path) as source: item = json.load(source)
                valid = (isinstance(item, dict) and isinstance(item.get('expires'), (int, float))
                         and isinstance(item.get('owner'), str) and re.fullmatch(r'[a-f0-9]{64}', item['owner']))
            except (FileNotFoundError, ValueError): valid = False
            if not valid:
                try: os.unlink(item_path)
                except FileNotFoundError: pass
                continue
            if item['expires'] <= clock(): os.unlink(item_path)
            else: active.append(item)
        if len(active) >= 8 or sum(item['owner'] == owner for item in active) >= 2:
            raise ProviderError(('Shared AITK' if provider == 'aitk' else 'OpenAI') + ' is busy. Wait for the current request or stop it.', 429, provider + '_busy')
        with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as target:
            json.dump({'owner': owner, 'expires': clock() + 180}, target)
    try: yield
    finally:
        with lock() as guard:
            fcntl.flock(guard, fcntl.LOCK_EX)
            try: os.unlink(path)
            except FileNotFoundError: pass
