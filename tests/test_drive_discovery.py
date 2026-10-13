import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from server import Bridge, normalize_drives, safe_path

class DriveDiscovery(unittest.TestCase):
    def test_sdk_string_and_older_adapter_combined_entry(self):
        for raw in ('Hdd:\\;Usb0:\\;Flash:\\', ['Hdd:\\;Usb0:\\;Flash:\\']):
            b=Bridge('unused')
            b.adapter=lambda action: {'drives':raw}
            self.assertEqual(b.status()['drives'], ['Hdd:\\','Usb0:\\','Flash:\\'])
            self.assertEqual(safe_path('Usb0:\\Games\\', b.drives), 'Usb0:\\Games\\')

    def test_no_assumed_roots_or_paths(self):
        self.assertEqual(normalize_drives(['CustomDisk:', 'USB4', 'usb4:\\', 'Hdd:\\folder', '../', None]), ['CustomDisk:\\','USB4:\\'])
        for value in (None, '', [], {}, ';', 'Hdd:\\bad\npath'):
            self.assertEqual(normalize_drives(value), [])

    def test_active_discovery_replaces_stale_roots_and_projects_diagnostics(self):
        b=Bridge('unused');b.target='demo';b.drives=['Old:\\']
        b.adapter=lambda action: {'drives':['Usb3:\\'], 'storage':{'source':'xdevkit','state':'OK','checked':2,'unavailable':1,'private':'secret'}}
        result=b.dispatch('storage/discover',{})
        self.assertEqual(result['drives'], ['Usb3:\\'])
        self.assertEqual(result['storage'], {'source':'xdevkit','state':'OK','checked':2,'unavailable':1})
        with self.assertRaises(ValueError):safe_path('Old:\\Games',b.drives)
        b.adapter=lambda action: {'drives':['Old:\\','Usb3:\\']}
        self.assertEqual(b.status()['drives'], ['Usb3:\\'])

