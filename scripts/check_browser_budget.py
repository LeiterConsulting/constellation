#!/usr/bin/env python3
"""Bound the eager module graph; the optional Studio renderer loads on demand."""
import gzip
import json
from pathlib import Path

MAX_INITIAL_BYTES = 2_500_000
MAX_INITIAL_GZIP = 750_000


def measure(root):
    root = Path(root)
    manifest = json.loads((root / '.vite/manifest.json').read_text())
    entries = [key for key, value in manifest.items() if value.get('isEntry')]
    if len(entries) != 1: raise ValueError('Expected one browser entry.')
    visited = set()
    def visit(key):
        if key in visited: return
        visited.add(key)
        for child in manifest[key].get('imports', []): visit(child)
    visit(entries[0])
    files = {manifest[key]['file'] for key in visited}
    raw = [ (root / name).read_bytes() for name in files ]
    return {'initialBytes': sum(map(len, raw)), 'initialGzipBytes': sum(len(gzip.compress(data, mtime=0)) for data in raw),
            'initialChunks': len(files), 'deferredRenderer': any('Preview' in key and manifest[key].get('isDynamicEntry') and key not in visited for key in manifest)}


def check(report):
    if report['initialBytes'] > MAX_INITIAL_BYTES or report['initialGzipBytes'] > MAX_INITIAL_GZIP or not report['deferredRenderer']:
        raise ValueError('Browser startup budget exceeded or Studio renderer became eager.')


if __name__ == '__main__':
    report = measure(Path(__file__).resolve().parents[1] / 'dist')
    check(report)
    print(json.dumps(report))
