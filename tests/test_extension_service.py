import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'splunk/constellation/bin'))
from extension_service import installed_extensions


class ExtensionTests(unittest.TestCase):
    def test_discovery_returns_only_fixed_metadata_without_fetching_code_or_prose(self):
        entries = [{'name': 'fixture_viz', 'acl': {'app': 'fixture_app'}, 'content': {'framework_type': 'studio_visualization', 'description': 'UNTRUSTED', 'search_fragment': '| delete'}}]
        class Runtime:
            def request(self, path, optional=False):
                self.path = path
                return {'entry': entries}
        runtime = Runtime(); result = installed_extensions(runtime)
        self.assertEqual(result['items'], [{'name': 'fixture_viz', 'app': 'fixture_app', 'framework': 'studio_visualization'}])
        self.assertNotIn('UNTRUSTED', str(result)); self.assertNotIn('delete', str(result))
        self.assertEqual(runtime.path, '/servicesNS/-/-/configs/conf-visualizations?count=51')

    def test_disabled_invalid_builtin_unknown_and_restricted_are_not_advertised(self):
        entries = [{'name': name, 'acl': {'app': 'fixture'}, 'content': content} for name, content in [
            ('disabled', {'disabled': '1'}), ('hidden', {'allow_user_selection': '0'}),
            ('builtin', {'core.type': 'chart'}), ('../invalid', {}), ('future', {'framework_type': 'unknown'})]]
        class Runtime:
            def request(self, path, optional=False): return {'entry': entries}
        self.assertEqual(installed_extensions(Runtime())['items'], [])
        class Denied:
            def request(self, path, optional=False): return {'unavailable': 'restricted'}
        self.assertEqual(installed_extensions(Denied())['status'], 'restricted')
