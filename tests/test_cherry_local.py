"""PC-local Cherry profile never touches Xbox identity fields."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
import cherry_local


class Bridge:
    cherry_local_enabled = False


class CherryLocalTests(unittest.TestCase):
    def test_virtual_profile_is_bounded_and_persists_without_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            profile = cherry_local.save({'gamertag': 'Test', 'membership': 'Gold',
                                         'gamerscore': 50, 'bypass': True}, path)
            self.assertTrue(profile['isGold'])
            self.assertEqual(cherry_local.load(path), profile)
            self.assertNotIn('xuid', profile)
            self.assertNotIn('cpuKey', path.read_text(encoding='utf-8'))
            with self.assertRaises(ValueError):
                cherry_local.save({'gamerscore': 1000000}, path)
            with self.assertRaises(ValueError):
                cherry_local.save({'xuid': 'forbidden'}, path)

    def test_switch_defaults_off_and_rejects_profile_reads(self):
        bridge = Bridge()
        self.assertFalse(cherry_local.dispatch(bridge, 'cherry/status', {})['enabled'])
        with self.assertRaises(ValueError):
            cherry_local.dispatch(bridge, 'cherry/profile', {})
        cherry_local.dispatch(bridge, 'cherry/switch', {'enabled': True})
        self.assertTrue(cherry_local.dispatch(bridge, 'cherry/status', {})['enabled'])


if __name__ == '__main__':
    unittest.main()
