"""Publication policy regressions use constructed, non-sensitive examples."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('repository_check', Path(__file__).parents[1] / 'scripts/check_repository.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class RepositoryPolicyTests(unittest.TestCase):
    def test_private_paths_are_rejected_even_when_force_added(self):
        for name in ['.local/receipt.json', 'docs/validation/screenshot.png', 'factory001/src/App.tsx',
                     'splunk/constellation/local/passwords.conf', '.env.production', 'credentials/connection.json',
                     'provider.key', 'scripts/lab_probe.py', 'src/__pycache__/module.pyc',
                     'splunk/constellation/default/passwords.conf', 'splunk/constellation/var/state.json', 'splunk.secret']:
            with self.subTest(name=name): self.assertTrue(check.path_issues(name))

    def test_source_and_empty_environment_template_are_permitted(self):
        for name in ['README.md', '.env.example', 'src/App.tsx', 'tests/fixtures/service-health-napkin.png',
                     'splunk/constellation/default/app.conf', '.github/workflows/ci.yml']:
            with self.subTest(name=name): self.assertEqual(check.path_issues(name), [])

    def test_private_identifiers_are_reported_without_returning_content(self):
        home = '/' + 'Users' + '/example-private/person.txt'
        domain = 'fixture.' + 'home' + '.arpa'
        address = '.'.join(['192', '168', '1', '99'])
        findings = check.text_issues(home + '\n' + domain + '\n' + address)
        self.assertEqual(set(findings), {'private-home-path', 'private-network-domain', 'private-lan-address'})
        self.assertNotIn('example-private', repr(findings))

    def test_all_rfc1918_ranges_are_detected(self):
        for octets in [('10', '2', '3', '4'), ('172', '16', '0', '1'), ('172', '31', '1', '1')]:
            with self.subTest(octets=octets): self.assertIn('private-lan-address', check.text_issues('.'.join(octets)))

    def test_loopback_documentation_public_examples_and_adversarial_targets_are_allowed(self):
        self.assertEqual(check.text_issues('http://127.0.0.1:5178 https://example.com 169.254.169.254 8.8.8.8 0.0.0.0'), [])

    def test_document_links_must_resolve_to_published_files(self):
        names = {'README.md', 'docs/guide.md', 'tests/fixtures/example.png'}
        self.assertEqual(check.link_issues('docs/guide.md', '[Root](../README.md#start) ![Fixture](../tests/fixtures/example.png)', names), [])
        self.assertTrue(check.link_issues('README.md', '[Private](docs/validation/private.json)', names))
        self.assertTrue(check.link_issues('README.md', '[Absolute](/private/file.md)', names))

    def test_remote_links_and_fragment_links_do_not_require_local_files(self):
        self.assertEqual(check.link_issues('README.md', '[Docs](https://example.com/path) [Top](#top)', {'README.md'}), [])
