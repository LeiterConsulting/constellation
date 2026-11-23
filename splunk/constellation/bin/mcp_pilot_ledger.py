"""Single-head operation claims. Stores IDs, digests and bounded receipt metadata."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

from provider_service import ProviderError

RETAIN_SECONDS = 7 * 86400
ADMISSION_SECONDS = 86400
CLAIM_SECONDS = 90
DEFAULT_AUTHOR_LIMIT = 12
MAX_AUTHOR_LIMIT = 32
TERMINAL = {'created', 'draft_only', 'failed', 'needs_input', 'indeterminate'}
SCHEMA = """
CREATE TABLE IF NOT EXISTS operations (
    owner TEXT NOT NULL,
    request_id TEXT NOT NULL,
    accepted INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (owner, request_id)
)
"""


class PilotLedger:
    def __init__(self, root, clock=time.time, *, author_limit=DEFAULT_AUTHOR_LIMIT):
        self.root = Path(root)
        self.path = self.root / 'operations.sqlite3'
        self.clock = clock
        self.author_limit = author_limit

    @contextmanager
    def connection(self, writable):
        connection = None
        try:
            if writable:
                self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
                fd = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
                os.close(fd)
                connection = sqlite3.connect(self.path, timeout=2)
                connection.execute('BEGIN IMMEDIATE')
                connection.execute(SCHEMA)
            else:
                connection = sqlite3.connect(self.path.as_uri() + '?mode=ro', timeout=2, uri=True)
            yield connection
            if writable:
                connection.commit()
        except (OSError, sqlite3.Error, ValueError):
            raise ProviderError('The pilot could not verify the operation record.', 503,
                                'ledger_unavailable') from None
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def load(connection, owner, request_id):
        row = connection.execute(
            'SELECT accepted, payload FROM operations WHERE owner = ? AND request_id = ?',
            (owner, request_id)).fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def get(self, owner, request_id):
        if not self.path.exists():
            return None
        with self.connection(writable=False) as connection:
            row = self.load(connection, owner, request_id)
            return row[1] if row and row[0] + RETAIN_SECONDS > self.clock() else None

    def capacity(self, owner):
        retained, oldest = 0, None
        if self.path.exists():
            cutoff = int(self.clock()) - RETAIN_SECONDS
            with self.connection(writable=False) as connection:
                retained, oldest = connection.execute(
                    'SELECT count(*), min(accepted) FROM operations WHERE owner = ? AND accepted > ?',
                    (owner, cutoff)).fetchone()
        return {
            'limit': self.author_limit,
            'retained': retained,
            'available': max(0, self.author_limit - retained),
            'next_expiration': (datetime.fromtimestamp(oldest + RETAIN_SECONDS, timezone.utc)
                                .strftime('%Y-%m-%dT%H:%M:%SZ')) if oldest is not None else None,
        }

    def claim(self, owner, request_id, issued_at, digest, *, lease=CLAIM_SECONDS):
        now = int(self.clock())
        with self.connection(writable=True) as connection:
            connection.execute('DELETE FROM operations WHERE accepted <= ?', (now - RETAIN_SECONDS,))
            existing = self.load(connection, owner, request_id)
            if existing:
                record = existing[1]
                if record['digest'] != digest:
                    raise ProviderError('This request ID is already bound to a different brief.', 409,
                                        'request_conflict')
                return record, False
            if issued_at < now - ADMISSION_SECONDS or issued_at > now + 300:
                raise ProviderError('This dashboard request ID is outside its admission window.', 422,
                                    'request_expired')
            owned = connection.execute('SELECT payload FROM operations WHERE owner = ?', (owner,)).fetchall()
            if len(owned) >= self.author_limit or connection.execute('SELECT count(*) FROM operations').fetchone()[0] >= 128:
                raise ProviderError('The pilot receipt limit has been reached.', 429, 'pilot_capacity')
            if any(self.active(json.loads(row[0])) for row in owned):
                raise ProviderError('An operation is already in progress for this author.', 429, 'pilot_busy')
            record = {'digest': digest, 'stage': 'accepted', 'until': now + lease,
                      'draft': uuid4().hex, 'view': 'constellation_' + uuid4().hex[:24]}
            connection.execute('INSERT INTO operations VALUES (?, ?, ?, ?)',
                               (owner, request_id, now, json.dumps(record)))
            return record, True

    def active(self, record):
        return record['stage'] not in TERMINAL and self.clock() < record['until']

    def advance(self, owner, request_id, previous, stage, **values):
        with self.connection(writable=True) as connection:
            row = self.load(connection, owner, request_id)
            if not row or row[1]['stage'] != previous or (
                    stage not in TERMINAL and not self.active(row[1])):
                raise ProviderError('The pilot could not advance this operation safely.', 409,
                                    'operation_interrupted')
            record = dict(row[1], stage=stage, **values)
            connection.execute('UPDATE operations SET payload = ? WHERE owner = ? AND request_id = ?',
                               (json.dumps(record), owner, request_id))
            return record
