import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from package_licenses import collect_runtime_notices, notices_archive


class LicensePackagingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'third_party/licenses').mkdir(parents=True)
        (self.root / 'third_party/license-manifest.json').write_text('{"packages": []}')
        (self.root / 'package.json').write_text('{"version": "1.0.0"}')
        (self.root / 'LICENSE').write_text('Synthetic first-party license')
        self.lock = {'packages': {}}

    def package(self, name='example', version='1.0.0', **metadata):
        path = self.root / 'node_modules' / name
        path.mkdir(parents=True)
        self.lock['packages']['node_modules/' + name] = {'version': version, 'license': 'MIT', **metadata}
        (self.root / 'package-lock.json').write_text(json.dumps(self.lock))
        return path

    def test_alternative_filenames_and_all_notices_survive(self):
        path = self.package()
        for name in ('LICENCE.md', 'LICENSE-MIT.txt', 'NOTICE', 'CopyrightNotice.txt', 'ThirdPartyNoticeText.txt'):
            (path / name).write_text('Synthetic notice ' + name)
        files = collect_runtime_notices(self.root)
        self.assertEqual(len(files), 6)
        for name in ('LICENCE.md', 'LICENSE-MIT.txt', 'NOTICE', 'CopyrightNotice.txt', 'ThirdPartyNoticeText.txt'):
            self.assertIn(('Synthetic notice ' + name).encode(), files.values())

    def test_missing_notice_is_not_treated_as_complete(self):
        self.package()
        with self.assertRaisesRegex(ValueError, 'missing upstream license'):
            collect_runtime_notices(self.root)

    def fallback(self):
        data = b'Synthetic upstream MIT notice'
        (self.root / 'third_party/licenses/example.txt').write_bytes(data)
        manifest = {'packages': [{'name': 'example', 'version': '1.0.0', 'license': 'MIT',
                     'files': [{'file': 'example.txt', 'sha256': hashlib.sha256(data).hexdigest()}]}]}
        (self.root / 'third_party/license-manifest.json').write_text(json.dumps(manifest))

    def test_fallback_requires_exact_version_and_original_bytes(self):
        path = self.package()
        self.fallback()
        self.assertIn(b'Synthetic upstream MIT notice', collect_runtime_notices(self.root).values())
        self.lock['packages']['node_modules/example']['version'] = '2.0.0'
        (self.root / 'package-lock.json').write_text(json.dumps(self.lock))
        with self.assertRaisesRegex(ValueError, 'missing upstream license'):
            collect_runtime_notices(self.root)
        (self.root / 'third_party/licenses/example.txt').write_text('Changed')
        with self.assertRaisesRegex(ValueError, 'notice changed'):
            collect_runtime_notices(self.root)

    def test_development_and_absent_optional_packages_need_no_fallback(self):
        self.package('development', dev=True)
        self.lock['packages']['node_modules/optional'] = {'version': '1.0.0', 'optional': True}
        (self.root / 'package-lock.json').write_text(json.dumps(self.lock))
        files = collect_runtime_notices(self.root)
        self.assertEqual(set(files), {'constellation/THIRD_PARTY_NOTICES.md'})

    def test_supplement_has_normalized_members_and_checksums(self):
        path = self.package()
        (path / 'license').write_text('Synthetic upstream license')
        data = notices_archive(self.root)
        self.assertEqual(data, notices_archive(self.root))
        with zipfile.ZipFile(BytesIO(data)) as archive:
            self.assertEqual(archive.read('LICENSE'), b'Synthetic first-party license')
            for line in archive.read('SHA256SUMS').decode().splitlines():
                digest, name = line.split('  ', 1)
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)
            self.assertTrue(all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in archive.infolist()))

    def test_unreviewed_symlink_notices_are_rejected(self):
        path = self.package()
        (path / 'readme.txt').write_text('Synthetic upstream license')
        (path / 'LICENSE').symlink_to(path / 'readme.txt')
        with self.assertRaisesRegex(ValueError, 'regular files'):
            collect_runtime_notices(self.root)
