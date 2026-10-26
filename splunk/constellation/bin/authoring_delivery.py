"""Bounded, private delivery of an already validated reply, never inference replay.

The caller must hold the original session-signed run handle. Files share the
run lock and expire with that run; cleanup occurs on subsequent control activity.
No credentials, attachments, raw provider replies or indexed rows belong here.
"""
import json
import os

MAX_REPLY_BYTES = 1_000_000
MAX_CACHE_BYTES = 16_000_000


def discard(path):
    try: os.unlink(path + '.reply')
    except FileNotFoundError: pass


def publish(control, path, state, reply):
    """Called under the run lock; delivery pressure never rejects a valid edit."""
    raw = json.dumps(reply, ensure_ascii=True).encode('utf-8')
    if len(raw) > MAX_REPLY_BYTES: return
    used = sum(os.stat(os.path.join(control.root, name)).st_size
               for name in os.listdir(control.root) if name.endswith('.json.reply'))
    if used + len(raw) > MAX_CACHE_BYTES: return
    fd = os.open(path + '.reply', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'wb') as target: target.write(raw)
    except Exception:
        discard(path)
        raise


def retrieve(path):
    try:
        with open(path + '.reply', 'rb') as source: raw = source.read(MAX_REPLY_BYTES + 1)
        if len(raw) > MAX_REPLY_BYTES: return {'available': False}
        return {'available': True, 'reply': json.loads(raw)}
    except (FileNotFoundError, ValueError): return {'available': False}
