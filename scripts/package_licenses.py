#!/usr/bin/env python3
"""Collect installed upstream notices offline, with version-pinned omissions."""
import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LICENSE_NAME = re.compile(r'^(?:licen[sc]e|copying)(?:[-_.].*)?$', re.I)
NOTICE_NAME = re.compile(r'^(?:notice|copyrightnotice|thirdpartynoticetext)(?:[-_.].*)?$', re.I)


def curated_files(root):
    path = root / 'third_party/license-manifest.json'
    manifest = json.loads(path.read_text())
    files = {'third_party/license-manifest.json': path.read_bytes()}
    for package in manifest['packages']:
        for item in package['files']:
            name = item['file']
            if Path(name).name != name or not name.endswith('.txt'):
                raise ValueError('Use flat text names for curated upstream notices.')
            source = root / 'third_party/licenses' / name
            if source.is_symlink():
                raise ValueError('Curated upstream notices must be regular files.')
            data = source.read_bytes()
            if hashlib.sha256(data).hexdigest() != item['sha256']:
                raise ValueError('Curated upstream notice changed: ' + name)
            files['third_party/licenses/' + name] = data
    return manifest, files


def collect_runtime_notices(root):
    manifest, curated = curated_files(root)
    fallbacks = {(p['name'], p['version']): p for p in manifest['packages']}
    lock = json.loads((root / 'package-lock.json').read_text())
    files, notices = {}, ['# Runtime dependency notices', '',
        'First-party Constellation code uses MIT. The following upstream components retain their own licenses.',
        'This inventory follows the pinned non-development lockfile; optional packages can be absent from a build host.', '']
    for package_path, metadata in sorted(lock['packages'].items()):
        if not package_path or metadata.get('dev'):
            continue
        name = package_path.rsplit('node_modules/', 1)[-1]
        version = metadata.get('version', '')
        fallback = fallbacks.get((name, version))
        declared = metadata.get('license') or (fallback or {}).get('license', 'license in package')
        notices.append(f'- {name} {version} ({declared})')
        directory = root / package_path
        if not directory.is_dir():
            continue
        slug = re.sub(r'[^A-Za-z0-9._-]', '_', name) + '-' + version
        candidates = sorted((p for p in directory.iterdir() if p.is_file() and
                             (LICENSE_NAME.fullmatch(p.name) or NOTICE_NAME.fullmatch(p.name))),
                            key=lambda p: (not bool(LICENSE_NAME.fullmatch(p.name)), p.name.casefold()))
        license_count = 0
        for source in candidates:
            if source.is_symlink():
                raise ValueError('Upstream notices must be regular files: ' + name)
            is_license = bool(LICENSE_NAME.fullmatch(source.name))
            suffix = '' if is_license and license_count == 0 else '-' + source.name
            if is_license:
                license_count += 1
            files['constellation/licenses/' + slug + suffix + '.txt'] = source.read_bytes()
        if not license_count:
            if not fallback:
                raise ValueError('Review the missing upstream license for ' + name + ' ' + version)
            for number, item in enumerate(fallback['files']):
                suffix = '' if number == 0 else '-' + str(number + 1)
                files['constellation/licenses/' + slug + suffix + '.txt'] = curated['third_party/licenses/' + item['file']]
    files['constellation/THIRD_PARTY_NOTICES.md'] = ('\n'.join(notices) + '\n').encode()
    return files


def notices_archive(root):
    version = json.loads((root / 'package.json').read_text())['version']
    _, curated = curated_files(root)
    files = {name.removeprefix('constellation/'): data for name, data in collect_runtime_notices(root).items()}
    files.update(curated)
    files['LICENSE'] = (root / 'LICENSE').read_bytes()
    files['README.md'] = (f'# Constellation {version} dependency notices\n\n'
        'This supplement accompanies the released app and retains upstream license/copyright notices. '
        'It adds notices omitted by the original collector; it does not change app execution or relicense upstream code.\n\n'
        'THIRD_PARTY_NOTICES.md inventories the pinned dependencies. licenses/ contains their notices. '
        'third_party/license-manifest.json records the version-pinned sources for packages without a standalone license file. '
        'Keep this supplement with redistributed installers. Future source builds embed these notices.\n').encode()
    files['SHA256SUMS'] = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
                                 for name, data in sorted(files.items())).encode()
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, data)
    return output.getvalue()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    version = json.loads((ROOT / 'package.json').read_text())['version']
    target = args.output or ROOT / 'artifacts' / ('constellation-' + version + '-third-party-notices.zip')
    target.parent.mkdir(parents=True, exist_ok=True)
    data = notices_archive(ROOT)
    target.write_bytes(data)
    print(json.dumps({'artifact': str(target), 'sha256': hashlib.sha256(data).hexdigest()}))
