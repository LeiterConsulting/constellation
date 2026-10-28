"""Build contract only: no native runtime, credentials or inference needed."""
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from package_runtime import pin_driver_revision


class DriverIdentityTests(unittest.TestCase):
    def test_all_driver_revisions_change_without_changing_endpoint_authority(self):
        original = (Path(__file__).resolve().parents[1] / 'splunk/constellation/default/restmap.conf').read_bytes()
        first = pin_driver_revision(original, '123456abcdef')
        second = pin_driver_revision(original, 'abcdef123456')
        self.assertNotEqual(first, second)
        self.assertEqual(first.count(b'driver.env.CONSTELLATION_RUNTIME_REVISION = 123456abcdef\n'), 4)
        strip = lambda text: re.sub(rb'driver.env.CONSTELLATION_RUNTIME_REVISION = [a-f0-9]{12}\n', b'', text)
        self.assertEqual(strip(first), original); self.assertEqual(strip(second), original)
        for marker in (b'CONSTELLATION_CONTROL = 1', b'CONSTELLATION_AITK_INFERENCE = 1', b'CONSTELLATION_OPENAI_PRIVATE = 1'):
            self.assertIn(marker, first)

    def test_invalid_or_duplicate_revision_is_rejected(self):
        for revision in ('', 'PRIVATE', 'a' * 13, 'abc\nhandler=x'):
            with self.assertRaises(ValueError): pin_driver_revision(b'scripttype = persist\n', revision)
        with self.assertRaises(ValueError):
            pin_driver_revision(pin_driver_revision(b'scripttype = persist\n', '123456abcdef'), 'abcdef123456')
