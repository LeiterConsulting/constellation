#!/usr/bin/env python3
"""Check local documentation links, fragments, image provenance and 1.0 entry points."""
import argparse
import hashlib
import json
from pathlib import Path
import posixpath
import re
import struct
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
INLINE = re.compile(r'!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+["\'][^\n]*?["\'])?\s*\)')
REFERENCE = re.compile(r'^\s*\[[^\]]+\]:\s*(\S+)', re.M)
HTML_URL = re.compile(r'<(?:img|source|a)\b[^>]*?\b(?:src|srcset|href)=["\']([^"\']+)["\']', re.I)
EXPLICIT_ID = re.compile(r'<a\b[^>]*\b(?:id|name)=["\']([^"\']+)["\']', re.I)


def prose(text):
    lines, fence = [], None
    for line in text.splitlines():
        mark = re.match(r'^\s*(~~~+|\x60\x60\x60+)', line)
        if mark:
            if fence is None: fence = mark[1][0]
            elif fence == mark[1][0]: fence = None
            continue
        if fence is None: lines.append(line)
    return '\n'.join(lines)


def anchors(text):
    text = prose(text)
    result, used = set(EXPLICIT_ID.findall(text)), {}
    for line in text.splitlines():
        match = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
        if not match: continue
        heading = re.sub(r'!?\[([^\]]+)\]\([^)]+\)', r'\1', match[1])
        heading = re.sub(r'<[^>]*>', '', heading)
        slug = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
        number = used.get(slug, 0);used[slug] = number + 1
        result.add(slug + ('-' + str(number) if number else ''))
    return result


def targets(text):
    clean = prose(text)
    return [m[1].strip('<>') for m in INLINE.finditer(clean)] + REFERENCE.findall(clean) + HTML_URL.findall(clean)


def link_findings(files):
    """files maps published relative paths to text or None for binary payloads."""
    findings = []
    for name, text in sorted(files.items()):
        if not name.endswith('.md') or text is None: continue
        for target in targets(text):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                if parsed.scheme not in ('https', 'http', 'mailto'): findings.append((name, 'unsafe-link-scheme'))
                continue
            path = unquote(parsed.path)
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), path)) if path else name
            if path.startswith('/') or resolved not in files:
                findings.append((name, 'missing-local-target', target));continue
            if parsed.fragment and resolved.endswith('.md') and unquote(parsed.fragment) not in anchors(files[resolved] or ''):
                findings.append((name, 'missing-heading-fragment', target))
    return findings


def jpeg_dimensions(data):
    if data[:2] != bytes((255, 216)): raise ValueError('Expected JPEG capture bytes.')
    offset, dimensions = 2, None
    while offset < len(data):
        if offset + 2 > len(data) or data[offset] != 255: raise ValueError('Malformed JPEG capture.')
        marker = data[offset + 1];offset += 2
        if marker == 218: break
        if offset + 2 > len(data): raise ValueError('Missing JPEG segment length.')
        if marker in (225, 237, 254): raise ValueError('Identifying image metadata is not allowed.')
        length = int.from_bytes(data[offset:offset + 2], 'big')
        if length < 2 or offset + length > len(data): raise ValueError('Malformed JPEG segment.')
        if marker in (192, 194):
            dimensions = (int.from_bytes(data[offset + 5:offset + 7], 'big'), int.from_bytes(data[offset + 3:offset + 5], 'big'))
        offset += length
    if dimensions is None: raise ValueError('JPEG dimensions unavailable.')
    return dimensions


def screenshot_findings(root, bundle=False):
    manifest = json.loads((root / 'docs/images/manifest.json').read_text())
    findings = []
    required = {'providerCalls': False, 'labOrUserContent': False, 'retouched': False,
                'mode': 'standalone local preview', 'data': 'authored synthetic built-in example'}
    if any(manifest.get(k) != v for k, v in required.items()): findings.append(('docs/images/manifest.json', 'screenshot-scope'))
    if not re.fullmatch(r'[a-f0-9]{40}', manifest.get('runtimeCommit', '')): findings.append(('docs/images/manifest.json', 'runtime-identity'))
    fixture = root / manifest['fixture']
    if not bundle and hashlib.sha256(fixture.read_bytes()).hexdigest() != manifest['fixtureSha256']: findings.append(('docs/images/manifest.json', 'fixture-changed'))
    seen = set()
    for item in manifest['images']:
        name = item['file']
        if Path(name).name != name or not name.endswith('.jpg') or name in seen: raise ValueError('Use unique flat JPEG screenshot names.')
        seen.add(name);path = root / 'docs/images' / name;data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']: findings.append((str(path.relative_to(root)), 'image-hash'))
        if jpeg_dimensions(data) != (item['width'], item['height']) or not item.get('alt'): findings.append((str(path.relative_to(root)), 'image-metadata'))
    if seen != {p.name for p in (root / 'docs/images').glob('*.jpg')}: findings.append(('docs/images/manifest.json', 'unrecorded-image'))
    return findings


def collect(root, names=None):
    paths = (root / n for n in names) if names is not None else (p for p in root.rglob('*') if p.is_file())
    files = {}
    for path in paths:
        if not path.is_file(): continue
        name = path.relative_to(root).as_posix()
        files[name] = path.read_text() if path.suffix == '.md' else None
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle', type=Path)
    args = parser.parse_args();root = args.bundle.resolve() if args.bundle else ROOT
    names = None if args.bundle else subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    files = collect(root, [n for n in names if n] if names is not None else None)
    findings = link_findings(files) + screenshot_findings(root, bool(args.bundle))
    if not args.bundle:
        for name in ('README.md', 'CONTRIBUTING.md', 'docs/user-guide.md', 'docs/providers.md', 'docs/installation.md'):
            text = files.get(name) or ''
            for phrase in ('Constellation is a development preview', 'second target lacks a usable AITK completion', 'This remains a private preview'):
                if phrase in text: findings.append((name, 'stale-current-status'))
        version = json.loads((root / 'package.json').read_text())['version']
        if version not in (files.get('README.md') or ''): findings.append(('README.md', 'version-not-disclosed'))
        available = {p.name for folder in ('src', 'splunk/constellation/bin') for p in (root / folder).rglob('*') if p.is_file()}
        for name in re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\.(?:py|tsx?)\b', files.get('docs/architecture.md') or ''):
            if name not in available: findings.append(('docs/architecture.md', 'missing-module', name))
    for finding in sorted(set(findings)): print(': '.join(finding[:2]))
    print(json.dumps({'documents': sum(n.endswith('.md') for n in files), 'localLinks': sum(len(targets(t)) for n, t in files.items() if n.endswith('.md') and t), 'screenshots': len(json.loads((root / 'docs/images/manifest.json').read_text())['images']), 'findings': len(findings)}))
    return bool(findings)


if __name__ == '__main__':
    raise SystemExit(main())
