import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fixtures import Fake
from database import open_database
from game_paths import GamePaths

class GameShortcuts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'games.db'
        self.store=GamePaths(self.path)
        self.patch=patch('server.GamePaths',lambda:self.store)
        self.patch.start();self.addCleanup(self.patch.stop)
        self.bridge=Fake()
        self.bridge.adapter=lambda action,**kw:{'files':[{'name':'default.xex','size':500}]}

    def save(self,**changes):
        data={'name':'My game','folder':'Test:\\Games\\','executable':'default.xex'}
        data.update(changes)
        return self.bridge.dispatch('games/save',data)

    def test_persistence_and_target_isolation(self):
        self.save()
        entries=GamePaths(self.path).list('DEMO')
        self.assertEqual(entries[0]['folder'],'Test:\\Games\\')
        self.assertEqual(self.store.list('other'),[])
        self.store.remove('other',entries[0]['id'])
        self.assertEqual(len(self.store.list('demo')),1)
        self.save(name='Renamed')
        self.assertEqual(len(self.store.list('demo')),1)
        self.assertEqual(self.store.list('demo')[0]['name'],'Renamed')
        self.store.remove('demo',entries[0]['id'])
        self.assertEqual(self.store.list('demo'),[])

    def test_rejects_invalid_paths_and_missing_xex(self):
        for changes in [{'folder':'Other:\\Game\\'},{'folder':'Test:\\..\\'}, {'executable':'..\\default.xex'}, {'executable':'missing.xex'}, {'executable':'plugin.dll'}, {'name':'\n'}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.save(**changes)
        self.assertEqual(self.store.list('demo'),[])

    def test_folder_only_and_no_launch_authorization(self):
        self.save(executable='')
        self.assertEqual(self.store.list('demo')[0]['executable'],'')
        self.assertFalse(hasattr(self.bridge,'tickets'))
        with self.assertRaises(ValueError):self.bridge.dispatch('launch',{'path':'Test:\\Games\\default.xex'})

    def test_disconnected_and_unavailable_folder(self):
        self.bridge.target=None
        with self.assertRaises(ValueError):self.save()
        self.bridge.target='demo'
        def unavailable(*a,**kw):raise ValueError('Offline')
        self.bridge.adapter=unavailable
        with self.assertRaises(ValueError):self.save()
        self.assertEqual(self.store.list('demo'),[])


    def test_modes_persist_update_and_validate(self):
        self.save(mode='multiplayer')
        self.assertEqual(GamePaths(self.path).list('demo')[0]['mode'],'multiplayer')
        self.save(mode='zombies')
        self.assertEqual(self.store.list('demo')[0]['mode'],'zombies')
        for mode in ('invalid',None,[],True):
            with self.assertRaises(ValueError):self.save(mode=mode)
        with self.assertRaises(ValueError):self.save(executable='',mode='campaign')
        self.assertFalse(hasattr(self.bridge,'tickets'))

    def test_legacy_database_migration(self):
        import sqlite3
        path=Path(self.tmp.name)/'legacy.db'
        with open_database(path) as db:
            db.execute('CREATE TABLE games (id INTEGER PRIMARY KEY,target TEXT,name TEXT,folder TEXT,executable TEXT,UNIQUE(target,folder,executable))')
            db.execute("INSERT INTO games VALUES(1,'demo','Old game','Test:', 'default.xex')")
        self.assertEqual(GamePaths(path).list('demo')[0]['mode'],'')
        self.assertEqual(GamePaths(path).list('demo')[0]['name'],'Old game')

    def test_cover_lookup_uses_inspected_title_and_persists(self):
        from companion import Workspace
        from types import SimpleNamespace
        self.save()
        entry=self.store.list('demo')[0]
        workspace=Workspace(Path(self.tmp.name)/'companion.sqlite3')
        self.bridge.companion=SimpleNamespace(store=workspace)
        self.bridge.inspect=lambda path:{'valid':True,'plugin':False,'metadata':{'title_id':'415608C3'}}
        import json
        with patch('companion.remote_bytes',side_effect=[json.dumps({'id':'415608C3','title':{'full':'BO2'}}).encode(),b'\xff\xd8\xffcover']):
            result=self.bridge.dispatch('games/cover',{'id':entry['id']})
        self.assertTrue(result['cover'].startswith('data:image/jpeg;base64,'))
        with patch('companion.remote_bytes',side_effect=AssertionError('Must use local cache')):
            listed=self.bridge.dispatch('games/list',{})['shortcuts'][0]
        self.assertEqual(listed['cover'],result['cover'])
        self.assertEqual(GamePaths(self.path).list('demo')[0]['title_id'],'415608C3')
        self.assertFalse(hasattr(self.bridge,'tickets'))
        self.bridge.target='another-console'
        with self.assertRaises(ValueError):self.bridge.dispatch('games/cover',{'id':entry['id']})

