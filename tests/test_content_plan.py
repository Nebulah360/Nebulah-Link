"""Read-only placement plans use saved games and current console listings."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
import content_plan


class FakeBridge:
    def __init__(self):
        self.drives = ['Usb3:\\']
        self.files = {
            'Usb3:\\Games\\Example\\': [
                {'name': 'default.xex', 'directory': False},
                {'name': 'Mods', 'directory': True},
            ],
            'Usb3:\\Games\\Example\\Mods\\': [
                {'name': 'patch.gsc', 'directory': False},
            ],
        }

    def dispatch(self, action, data):
        if action == 'browse':
            return {'files': list(self.files.get(data['path'], [])), 'listing': {}}
        raise AssertionError(action)

    def adapter(self, action, **kwargs):
        if action == 'capacity':
            return {'total': 1000, 'free': 400}
        raise AssertionError(action)


class ContentPlanTests(unittest.TestCase):
    def test_exact_destination_conflict_and_capacity_without_write(self):
        bridge = FakeBridge()
        result = content_plan.plan_content(
            bridge, 'Usb3:\\Games\\Example\\default.xex', 'mods', 'patch.gsc', 17)
        self.assertEqual(result['destination'], 'Usb3:\\Games\\Example\\Mods\\patch.gsc')
        self.assertTrue(result['folder_exists'])
        self.assertTrue(result['conflict'])
        self.assertEqual(result['free'], 400)
        self.assertTrue(result['enough_space'])

    def test_missing_folder_and_insufficient_space(self):
        bridge = FakeBridge()
        bridge.files['Usb3:\\Games\\Example\\'] = [{'name': 'default.xex', 'directory': False}]
        result = content_plan.plan_content(
            bridge, 'Usb3:\\Games\\Example\\default.xex', 'trainers', 'trainer.xex', 401)
        self.assertFalse(result['folder_exists'])
        self.assertFalse(result['enough_space'])
        self.assertFalse(result['conflict'])
        self.assertEqual(result['destination'], 'Usb3:\\Games\\Example\\Trainers\\trainer.xex')


if __name__ == '__main__':
    unittest.main()
