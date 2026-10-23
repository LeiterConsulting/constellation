#!/usr/bin/env python3
"""Build a deterministic, source-only namespace plus compiled browser assets."""
from pathlib import Path
from io import BytesIO
import gzip
import hashlib
import json
import re
import tarfile
from xml.sax.saxutils import escape
from check_repository import path_issues, text_issues

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'splunk' / 'constellation'
dist = ROOT / 'dist'
if not (dist / 'constellation.js').is_file():
    raise SystemExit('Run npm run build first.')
definition = json.loads((ROOT / 'src' / 'starter.json').read_text())
version = json.loads((ROOT / 'package.json').read_text())['version']
definition_json = json.dumps(definition, indent=2).replace(']]>', ']]]]><![CDATA[>')
xml = '<dashboard version="2" theme="light"><label>' + escape(definition['title']) + '</label><description>' + escape(definition['description']) + '</description><definition><![CDATA[' + definition_json + ']]></definition></dashboard>'
files = {}
for path in sorted(source.rglob('*')):
    if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
        data = path.read_bytes()
        name = 'splunk/constellation/' + str(path.relative_to(source))
        issues = path_issues(name)
        try: issues += text_issues(data.decode('utf-8'))
        except UnicodeDecodeError: pass
        if issues:
            raise SystemExit('Refusing to package ' + name + ': ' + ', '.join(issues))
        files['constellation/' + str(path.relative_to(source))] = data
for path in sorted(dist.rglob('*')):
    if path.is_file() and path.name != 'index.html': files['constellation/appserver/static/' + str(path.relative_to(dist))] = path.read_bytes()
# Splunk Web can retain its static cache key across an app update. Give each
# changed entry, loader, and host stylesheet a content-derived URL.
entry = files.pop('constellation/appserver/static/constellation.js')
entry_id = hashlib.sha256(entry).hexdigest()[:12]
entry_name = f'constellation-{entry_id}.js'
files['constellation/appserver/static/' + entry_name] = entry
boot = files.pop('constellation/appserver/static/boot.js').replace(b'/constellation.js', ('/' + entry_name).encode())
boot_name = f'boot-{entry_id}.js'
files['constellation/appserver/static/' + boot_name] = boot
host_css = (dist / 'index.css').read_bytes() + b'\nbody:has(#constellation-root) { min-width: 0; }\n.dashboard-body { padding: 0; min-width: 0; }\n'
css_name = 'constellation-host-' + hashlib.sha256(host_css).hexdigest()[:12] + '.css'
files['constellation/appserver/static/' + css_name] = host_css
workspace_path = 'constellation/default/data/ui/views/workspace.xml'
files[workspace_path] = files[workspace_path].replace(b'script="boot.js"', f'script="{boot_name}"'.encode()).replace(b'constellation-host.css', css_name.encode())
# Persistent REST workers can retain imported Python modules after an update.
# A changed entry script gets its own driver identity without restarting Splunk.
handler_path = 'constellation/bin/constellation_handler.py'
if handler_path in files:
    handler_source = files.pop(handler_path)
    handler_id = hashlib.sha256(handler_source + b''.join(data for name, data in sorted(files.items()) if name.startswith('constellation/bin/') and name.endswith(('.py', '.json')))).hexdigest()[:12]
    handler_module = 'constellation_handler_' + handler_id
    files['constellation/bin/' + handler_module + '.py'] = handler_source
    restmap_path = 'constellation/default/restmap.conf'
    files[restmap_path] = files[restmap_path].replace(b'constellation_handler.py', (handler_module + '.py').encode()).replace(b'constellation_handler.ConstellationHandler', (handler_module + '.ConstellationHandler').encode())
files['constellation/default/data/ui/views/renderer_baseline.xml'] = xml.encode()
for package in ['dashboard-core','dashboard-presets','dashboard-context','dashboard-state','dashboard-layouts','dashboard-inputs','datasources','react-ui','themes','react-icons','splunk-utils']:
    license_file = ROOT / 'node_modules' / '@splunk' / package / 'LICENSE'
    if license_file.exists(): files[f'constellation/licenses/splunk-{package}.txt'] = license_file.read_bytes()
notices = ['# Runtime dependency notices', '']
lock = json.loads((ROOT / 'package-lock.json').read_text())
for package_path, metadata in sorted(lock.get('packages', {}).items()):
    if not package_path or metadata.get('dev'): continue
    name = package_path.rsplit('node_modules/', 1)[-1]
    package_root = ROOT / package_path
    slug = re.sub(r'[^A-Za-z0-9._-]', '_', name) + '-' + str(metadata.get('version', ''))
    notices.append(f'- {name} {metadata.get("version", "")} ({metadata.get("license", "license in package")})')
    for filename in ['LICENSE', 'LICENSE.md', 'LICENSE.txt', 'license.txt', 'LICENCE', 'COPYING']:
        license_file = package_root / filename
        if license_file.is_file():
            files[f'constellation/licenses/{slug}.txt'] = license_file.read_bytes()
            break
files['constellation/THIRD_PARTY_NOTICES.md'] = ('\n'.join(notices) + '\n').encode()
buffer = BytesIO()
with tarfile.open(fileobj=buffer, mode='w') as archive:
    for name, data in sorted(files.items()):
        info = tarfile.TarInfo(name); info.size = len(data); info.mode = 0o644; info.mtime = 0
        archive.addfile(info, BytesIO(data))
output = ROOT / 'artifacts' / f'constellation-{version}.tgz'
output.parent.mkdir(exist_ok=True)
with output.open('wb') as handle:
    with gzip.GzipFile(fileobj=handle, mode='wb', filename='', mtime=0) as compressed:
        compressed.write(buffer.getvalue())
digest = hashlib.sha256(output.read_bytes()).hexdigest()
(output.parent / 'SHA256SUMS').write_text(digest + '  ' + output.name + '\n')
print(json.dumps({'artifact': str(output), 'sha256': digest, 'files': len(files), 'bytes': output.stat().st_size}))
