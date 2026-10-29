#!/usr/bin/env python3
"""Bundle the unchanged qualified app with reviewed, self-contained documentation."""
import hashlib
import json
from pathlib import Path
import zipfile
from check_repository import text_issues, path_issues
from check_documentation import link_findings

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / 'package.json').read_text())['version']
DOCS = (
    'CHANGELOG.md',
    'CONTRIBUTING.md',
    'README.md',
    'SECURITY.md',
    'docs/README.md',
    'docs/aitk-setup.md',
    'docs/architecture.md',
    'docs/assets-and-portability.md',
    'docs/development.md',
    'docs/documentation-review.md',
    'docs/glossary.md',
    'docs/history/README.md',
    'docs/history/product-direction.md',
    'docs/history/sharing-review.md',
    'docs/history/validation.md',
    'docs/installation.md',
    'docs/model-benchmark.md',
    'docs/native-coverage.md',
    'docs/product-direction.md',
    'docs/provider-qualification.md',
    'docs/providers.md',
    'docs/reference/README.md',
    'docs/reference/design-notes.md',
    'docs/reference/native-coverage-notes.md',
    'docs/reference/upgrade-contracts.md',
    'docs/reference/validation-1.0.md',
    'docs/reliability-goal.md',
    'docs/roadmap.md',
    'docs/screenshots.md',
    'docs/security-review.md',
    'docs/share-readiness.md',
    'docs/studio-support.md',
    'docs/support-policy.md',
    'docs/troubleshooting.md',
    'docs/upgrade-guide.md',
    'docs/user-guide.md',
    'docs/v1-readiness.md',
    'docs/validation.md',
    'documentation-standards.md',
    'tests/fixtures/README.md',
    'tests/fixtures/service-health-napkin-prompt.txt',
)
ASSETS = (
    'tests/fixtures/service-health-napkin.png',
    'tests/fixtures/native_chart_shapes.json',
    'tests/fixtures/native_geography.json',
    'assets/branding/exports/mark-light-48.png',
    'assets/branding/exports/mark-dark-48.png',
    'docs/images/manifest.json',
    'docs/images/workspace-docked-light.jpg',
    'docs/images/workspace-docked-dark.jpg',
    'docs/images/focused-conversation.jpg',
    'docs/images/draft-brief.jpg',
)

def main():
    package = ROOT / 'artifacts' / ('constellation-' + VERSION + '.tgz')
    app = package.read_bytes()
    digest = hashlib.sha256(app).hexdigest()
    recorded = (ROOT / 'docs/validation.md').read_text()
    if digest not in recorded:
        raise SystemExit('The app bytes are not identified by the current validation record.')
    files = {package.name: app}
    for name in DOCS:
        path = ROOT / name
        if path.is_symlink() or path_issues(name):
            raise SystemExit('Refusing an unreviewed handoff document: ' + name)
        content = path.read_text()
        if text_issues(content):
            raise SystemExit('Refusing an unreviewed handoff document: ' + name)
        files[name] = content.encode()
    for name in ASSETS:
        path = ROOT / name
        if path.is_symlink() or path_issues(name):
            raise SystemExit('Refusing an unreviewed handoff asset: ' + name)
        files[name] = path.read_bytes()
    pdf = ROOT / 'output/pdf' / ('constellation-' + VERSION + '-user-guide.pdf')
    pdf_bytes = pdf.read_bytes()
    for source in ('docs/user-guide.md', 'docs/images/manifest.json'):
        if hashlib.sha256((ROOT / source).read_bytes()).hexdigest().encode() not in pdf_bytes:
            raise SystemExit('Regenerate and visually verify the illustrated user guide before bundling.')
    files[pdf.name] = pdf_bytes
    files['START-HERE.md'] = ('# Constellation ' + VERSION + ' offline guide\n\n'
        'Open [' + pdf.name + '](' + pdf.name + ') for the illustrated guide, or [docs/user-guide.md](docs/user-guide.md) for Markdown.\n\n'
        'Install the enclosed ' + package.name + ' through Splunk app management using [installation](docs/installation.md). Verify SHA256SUMS before use.\n\n'
        'The [documentation index](docs/README.md) separates author, administrator and developer paths. [Support scope](docs/support-policy.md) and [security](SECURITY.md) describe limits and data handling.\n\n'
        'The app bytes are the qualified 1.0 release. Documentation images are local synthetic examples, not live acceptance evidence.\n').encode()
    local = {name: data.decode() if name.endswith('.md') else None for name, data in files.items()}
    findings = link_findings(local)
    if findings:
        raise SystemExit('Handoff navigation is incomplete: ' + str(sorted({(f[0], f[1]) for f in findings})))
    sums = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n' for name, data in sorted(files.items()))
    files['SHA256SUMS'] = sums.encode()
    target = ROOT / 'artifacts' / ('constellation-' + VERSION + '-handoff.zip')
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    print(json.dumps({'artifact': str(target), 'app_sha256': digest,
                      'bundle_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'files': len(files)}))


if __name__ == '__main__':
    main()
