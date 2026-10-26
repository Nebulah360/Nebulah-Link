"""Ported Basic surfaces stay on the public allowlist; deferred writes stay off."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from access_policy import API_ACTIONS, BRIDGE_ACTIONS, assert_allowed
from app_settings import validate
from companion_ux import BASIC_CATALOG_IDS, resolve_notify


class AccessPolicyPortTests(unittest.TestCase):
    def test_ported_read_actions_allowed(self):
        for action in (
            'games/install-plan', 'discover/search', 'discord/status',
            'profile-package/list', 'profile-package/inspect', 'profile-package/active',
            'cherry/status', 'cherry/switch', 'cherry/profile', 'usb/inventory',
            'launcher/settings', 'launcher/save',
        ):
            self.assertIn(action, API_ACTIONS)

    def test_locked_basic_actions_allowed(self):
        for action in (
            'ftp/status', 'ftp/start', 'ftp/stop',
            'controller/pulse', 'console/power', 'console/notify', 'launch',
            'plugins/load', 'plugins/unload', 'plugins/install', 'plugins/force-release',
            'plugins/capabilities', 'plugins/managed-state',
            'console/launch-ini', 'console/launch-ini-switch',
            'console/launch-ini/plugins', 'console/launch-ini/plugins/preview',
            'console/launch-ini/plugins/save',
            'transfer/start', 'transfer/chunk', 'transfer/finish', 'transfer/mkdir',
        ):
            self.assertIn(action, API_ACTIONS)
            assert_allowed(action, BRIDGE_ACTIONS)

    def test_deferred_writes_still_rejected(self):
        for action in (
            'rte/poke-apply', 'rte/status', 'profile-vibration/apply', 'profile-write/apply',
            'stream360/start', 'linkui/sync',
        ):
            self.assertNotIn(action, API_ACTIONS)
            with self.assertRaises(ValueError):
                assert_allowed(action, BRIDGE_ACTIONS)

    def test_allow_writes_stays_off(self):
        with self.assertRaises(ValueError):
            validate({'default_console_ip': '', 'allow_writes': True})

    def test_notify_catalog_skips_editor_and_pro_ids(self):
        self.assertIn('link.connected', BASIC_CATALOG_IDS)
        self.assertNotIn('editors.menu_hint', BASIC_CATALOG_IDS)
        for catalog_id in ('editors.menu_hint', 'link.dash_ui', 'plugin.managed_loaded'):
            with self.assertRaises(ValueError):
                resolve_notify(catalog_id)


if __name__ == '__main__':
    unittest.main()
