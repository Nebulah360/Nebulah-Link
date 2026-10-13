import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from aurora_metadata import title_names
from companion import Companion
from server import Bridge


class AuroraMetadataTests(unittest.TestCase):
    def setUp(self):
        self.stage = tempfile.TemporaryDirectory()
        self.addCleanup(self.stage.cleanup)
        self.db = Path(self.stage.name) / 'content.db'
        db = sqlite3.connect(self.db)
        try:
            db.execute('CREATE TABLE ContentItems (TitleId INTEGER, TitleName TEXT)')
            db.executemany('INSERT INTO ContentItems VALUES(?,?)', [
                (0x415607E6, 'Call of Duty 4'), (0x415607E6, 'Call of Duty 4'),
                (0x12345678, 'First'), (0x12345678, 'Other'),
                (0x23456789, 'Private\nName'),
            ])
            db.commit()
        finally:
            db.close()

    def test_only_requested_unambiguous_allowlisted_names(self):
        self.assertEqual(title_names(self.db, {'415607E6', '12345678', '23456789'}),
                         {'415607E6': 'Call of Duty 4'})

    def test_discovered_aurora_install_fills_only_missing_measured_game(self):
        bridge = Bridge('unused')
        bridge.target = 'ConsoleA'
        bridge.drives = ['Usb3:\\']
        companion = Companion(bridge, Path(self.stage.name) / 'workspace.db')
        bridge.companion = companion
        game = 'Usb3:\\Games\\Example\\default.xex'
        aurora = 'Usb3:\\Aurora\\Aurora.xex'
        with companion.store.db() as db:
            for path, ident in [(game, '415607E6'), (aurora, '00000000')]:
                db.execute('INSERT INTO library VALUES(?,?,?,?)', ('consolea', path, 100, 1))
                db.execute('INSERT INTO library_inspections VALUES(?,?,?,?)',
                           ('consolea', path, 100, json.dumps({'size':100,'plugin':False,
                                                               'metadata':{'title_id':ident}})))
        calls = []
        def adapter(action, **data):
            calls.append((action, data['path']))
            self.assertEqual(data['path'], 'Usb3:\\Aurora\\Data\\Databases\\content.db')
            if action == 'file-info':
                return {'directory':False, 'size':self.db.stat().st_size}
            if action == 'download-file':
                Path(data['local']).write_bytes(self.db.read_bytes())
                return {'ok':True}
            self.fail(action)
        bridge.adapter = adapter
        result = companion.dispatch('metadata/aurora-import', {})
        self.assertEqual(result['imported'], 1)
        self.assertEqual(companion.store.title('415607E6')['title'], 'Call of Duty 4')
        games = [item for item in companion.store.library('ConsoleA','installs')['items'] if 'games' in item['categories']]
        self.assertEqual(games[0]['name_source'], 'aurora')
        self.assertEqual(len(calls), 2)
        self.assertEqual(companion.dispatch('metadata/aurora-import', {})['imported'], 0)
        self.assertEqual(len(calls), 2)

