"""An eager transitive import must count; dynamic renderer bytes must not."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_browser_budget import measure, check


class BrowserBudgetTests(unittest.TestCase):
    def test_static_graph_deduplicates_shared_modules_and_excludes_dynamic_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);(root/'.vite').mkdir()
            manifest = {'main': {'isEntry': True, 'file': 'main.js', 'imports': ['shared','extra'], 'dynamicImports': ['Preview']},
                        'extra': {'file': 'extra.js', 'imports': ['shared']}, 'shared': {'file': 'shared.js'},
                        'Preview': {'file': 'preview.js', 'isDynamicEntry': True, 'imports': ['shared']}}
            for name, size in (('main', 20), ('extra', 30), ('shared', 40), ('preview', 5000)):(root/(name+'.js')).write_bytes(b'x'*size)
            (root/'.vite/manifest.json').write_text(json.dumps(manifest))
            result = measure(root);self.assertEqual(result['initialBytes'], 90);self.assertEqual(result['initialChunks'], 3);check(result)
            manifest['main']['imports'].append('Preview');(root/'.vite/manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):check(measure(root))
    def test_initial_size_and_compressed_size_each_have_a_release_limit(self):
        for raw, compressed, deferred in ((2500001, 10, True), (10, 750001, True), (10, 10, False)):
            with self.assertRaises(ValueError):check({'initialBytes': raw, 'initialGzipBytes': compressed, 'deferredRenderer': deferred})
