"""Documentation gates catch broken navigation and unsafe screenshot metadata."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_documentation import anchors, jpeg_dimensions, link_findings, screenshot_findings


def jpeg(width=1280, height=720, metadata=False):
    start = bytes((255, 216))
    if metadata: start += bytes((255, 225, 0, 4, 1, 2))
    return start + bytes((255, 192, 0, 8, 8)) + height.to_bytes(2, 'big') + width.to_bytes(2, 'big') + bytes((3, 255, 218))


class DocumentationTests(unittest.TestCase):
    def test_heading_slugs_keep_version_punctuation_and_duplicate_identity(self):
        text = '# Example\n## **0.43.0** report app — October 29, 2026\n## Repeat\n## Repeat\n<a id="legacy"></a>'
        self.assertEqual(anchors(text), {'example', '0430-report-app--october-29-2026', 'repeat', 'repeat-1', 'legacy'})

    def test_missing_page_and_heading_are_distinct_failures(self):
        files = {'README.md': '[Missing](docs/missing.md) [Wrong section](docs/guide.md#absent)', 'docs/guide.md': '# Guide'}
        self.assertEqual({f[1] for f in link_findings(files)}, {'missing-local-target', 'missing-heading-fragment'})

    def test_nested_links_html_picture_and_same_page_fragments_resolve(self):
        files = {'README.md': '<picture><source srcset="docs/image.jpg"><img src="docs/image.jpg" alt=""></picture>\n[Guide](docs/guide.md#use-it)',
                 'docs/image.jpg': None, 'docs/guide.md': '# Guide\n## Use it\n[Home](../README.md) [Here](#use-it)'}
        self.assertEqual(link_findings(files), [])

    def test_fenced_examples_are_not_navigation_and_unsafe_schemes_fail(self):
        files = {'README.md': '~~~md\n[Example](missing.md)\n~~~\n[Bad](javascript:alert)\n'}
        self.assertEqual(link_findings(files), [('README.md', 'unsafe-link-scheme')])

    def test_path_escape_and_reference_definition_are_checked(self):
        files = {'README.md': '[Outside](../private.md)\n[guide]: docs/guide.md#guide\n', 'docs/guide.md': '# Guide'}
        self.assertEqual(link_findings(files), [('README.md', 'missing-local-target', '../private.md')])

    def test_capture_parser_refuses_exif_comments_and_wrong_signature(self):
        self.assertEqual(jpeg_dimensions(jpeg()), (1280, 720))
        for data in (b'not an image', jpeg(metadata=True), jpeg()[:5]):
            with self.assertRaises(ValueError): jpeg_dimensions(data)

    def test_provenance_rejects_hash_fixture_and_scope_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);(root/'docs/images').mkdir(parents=True);(root/'src').mkdir();(root/'src/starter.json').write_text('{}')
            image = jpeg();(root/'docs/images/example.jpg').write_bytes(image)
            manifest = {'providerCalls':False,'labOrUserContent':False,'retouched':False,'mode':'standalone local preview','data':'authored synthetic built-in example','runtimeCommit':'a'*40,
                        'fixture':'src/starter.json','fixtureSha256':hashlib.sha256(b'{}').hexdigest(),'images':[{'file':'example.jpg','sha256':hashlib.sha256(image).hexdigest(),'width':1280,'height':720,'alt':'Authored example'}]}
            path=root/'docs/images/manifest.json';path.write_text(json.dumps(manifest));self.assertEqual(screenshot_findings(root), [])
            manifest['providerCalls']=True;manifest['fixtureSha256']='0'*64;manifest['images'][0]['sha256']='0'*64;path.write_text(json.dumps(manifest))
            self.assertEqual({x[1] for x in screenshot_findings(root)}, {'screenshot-scope','fixture-changed','image-hash'})

    def test_bundle_does_not_require_development_fixture_but_still_checks_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'docs/images').mkdir(parents=True);image=jpeg();(root/'docs/images/example.jpg').write_bytes(image)
            manifest={'providerCalls':False,'labOrUserContent':False,'retouched':False,'mode':'standalone local preview','data':'authored synthetic built-in example','runtimeCommit':'a'*40,
                      'fixture':'src/not-bundled.json','fixtureSha256':'b'*64,'images':[{'file':'example.jpg','sha256':hashlib.sha256(image).hexdigest(),'width':1280,'height':720,'alt':'Example'}]}
            (root/'docs/images/manifest.json').write_text(json.dumps(manifest));self.assertEqual(screenshot_findings(root,bundle=True), [])
