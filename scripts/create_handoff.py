#!/usr/bin/env python3
"""Bundle the built app and reviewed user documentation for a private pilot."""
import hashlib
import json
from pathlib import Path
import zipfile
from check_repository import text_issues

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / 'package.json').read_text())['version']
DOCS = ('SECURITY.md', 'CHANGELOG.md', 'docs/user-guide.md', 'docs/installation.md',
        'docs/providers.md', 'docs/security-review.md', 'docs/aitk-setup.md', 'docs/studio-support.md', 'docs/validation.md', 'docs/provider-qualification.md',
        'docs/share-readiness.md', 'docs/architecture.md', 'docs/upgrade-guide.md',
        'docs/roadmap.md', 'docs/development.md', 'docs/product-direction.md',
        'docs/reliability-goal.md', 'tests/fixtures/README.md',
        'tests/fixtures/service-health-napkin-prompt.txt')
ASSETS = ('tests/fixtures/service-health-napkin.png',)


def main():
    package = ROOT / 'artifacts' / ('constellation-' + VERSION + '.tgz')
    app = package.read_bytes()
    digest = hashlib.sha256(app).hexdigest()
    files = {package.name: app, 'SHA256SUMS': (digest + '  ' + package.name + '\n').encode(),
             'README.md': ('# Constellation ' + VERSION + ' private pilot\n\n'
                           'Start with docs/user-guide.md, then review docs/provider-qualification.md '
                           'and docs/validation.md. docs/share-readiness.md retains the historical sharing audit. '
                           'Install the enclosed app archive using docs/installation.md. '
                           'Verify it against SHA256SUMS before installation.\n\n'
                           'This is a development preview, not a production or Splunk Cloud certified release. '
                           'No first-party open-source license has been selected. '
                           'Configure credentials in Splunk; none are supplied in this bundle.\n').encode()}
    for name in DOCS:
        path = ROOT / name
        content = path.read_text()
        if path.is_symlink() or text_issues(content):
            raise SystemExit('Refusing an unreviewed handoff document: ' + name)
        files[name] = content.encode()
    for name in ASSETS:
        path = ROOT / name
        if path.is_symlink():
            raise SystemExit('Refusing a symlinked handoff fixture: ' + name)
        files[name] = path.read_bytes()
    target = ROOT / 'artifacts' / ('constellation-' + VERSION + '-handoff.zip')
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    print(json.dumps({'artifact': str(target), 'app_sha256': digest,
                      'bundle_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'files': len(files)}))


if __name__ == '__main__': main()
