"""Library grouping and additive migration tests; synthetic files only."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from companion import Workspace
from database import open_database
from game_library import file_format
from server import validate_xex
from fixtures import game_fixture, Console


class SavedLibrary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'companion.sqlite3'
        self.store = Workspace(self.path)
        self.value = validate_xex(game_fixture())
        self.first = 'DriveA:\\Games\\Example\\default.xex'
        self.second = 'DriveB:\\Games\\Example\\default.xex'

    def save(self, path, value=None, target='console'):
        self.store.record_inspection(target, path, value or self.value)

    def test_complete_execution_identity_groups_locations_without_claiming_equal_bytes(self):
        changed = validate_xex(game_fixture()[:-1] + b'X')
        self.save(self.first)
        self.save(self.second, changed)
        result = self.store.library('CONSOLE')
        self.assertEqual(len(result['groups']), 1)
        self.assertEqual(result['groups'][0]['paths'], [self.first, self.second])
        self.assertNotEqual(result['files'][0]['inspection']['sha256'], result['files'][1]['inspection']['sha256'])
        self.assertNotIn('verified', json.dumps(result))
        self.assertNotIn('safe', result['groups'][0])

    def test_title_id_alone_never_groups_media_versions_discs_or_modes(self):
        self.save(self.first)
        variants = [('media_id', '87654321'), ('version', '00000002'),
                    ('base_version', '00000002'), ('disc_count', 2)]
        for i, (field, value) in enumerate(variants):
            measured = copy.deepcopy(self.value)
            measured['metadata'][field] = value
            self.save(f'DriveB:\\copy{i}\\default.xex', measured)
        disc = copy.deepcopy(self.value)
        disc['metadata'].update(disc=2, disc_count=2)
        self.save('DriveB:\\disc2\\default.xex', disc)
        self.save('DriveB:\\Games\\Example\\default_mp.xex')
        result = self.store.library('console')
        self.assertEqual(len(result['groups']), 7)
        self.assertTrue(all(len(group['paths']) == 1 for group in result['groups']))

    def test_incomplete_zero_identity_and_plugins_remain_separate(self):
        variants = [{}, {**self.value['metadata'], 'media_id': '00000000'},
                    {**self.value['metadata'], 'title_id': '00000000'},
                    {**self.value['metadata'], 'disc': 0}]
        for i, metadata in enumerate(variants):
            value = {**self.value, 'metadata': metadata}
            self.save(f'DriveA:\\unknown{i}\\default.xex', value)
            self.save(f'DriveB:\\unknown{i}\\default.xex', value)
        plugin = {**self.value, 'plugin': True}
        self.save('DriveA:\\plugins\\default.xex', plugin)
        self.save('DriveB:\\plugins\\default.xex', plugin)
        self.assertEqual(len(self.store.library('console')['groups']), 10)

    def test_formats_keep_unknown_iso_and_god_candidates_separate(self):
        paths = ['DriveA:\\Game.iso', 'DriveB:\\Game.iso',
                 'DriveA:\\Content\\00007000\\' + 'A' * 44,
                 'DriveA:\\Content\\00007000\\' + 'B' * 40]
        self.store.record_files('console', [(path, 100) for path in paths])
        result = self.store.library('console')
        self.assertEqual(sorted(item['format'] for item in result['files']), ['god', 'god', 'iso', 'iso'])
        self.assertEqual(len(result['groups']), 4)
        self.assertTrue(all(item['inspection'] is None for item in result['files']))
        self.assertEqual(file_format('DriveA:\\elsewhere\\' + 'A' * 44), 'unknown')
        self.assertEqual(file_format('DriveA:\\00007000\\' + 'Z' * 44), 'unknown')

    def test_case_only_rescan_retains_snapshot_without_counting_an_extra_copy(self):
        self.save(self.first)
        self.store.record_file('CONSOLE', self.first.lower(), self.value['size'])
        result = self.store.library('console')
        self.assertEqual(len(result['files']), 1)
        self.assertEqual(result['files'][0]['inspection']['sha256'], self.value['hash'])
        self.assertEqual(result['groups'][0]['paths'], [self.first.lower()])

    def test_changed_size_invalidates_observation_and_reinspection_can_regroup(self):
        self.save(self.first)
        self.save(self.second)
        self.store.record_file('console', self.first, self.value['size'] + 1)
        result = self.store.library('console')
        self.assertEqual(len(result['groups']), 2)
        self.assertIsNone(result['files'][0]['inspection'])
        self.save(self.first)
        self.assertEqual(len(self.store.library('console')['groups']), 1)

    def test_restart_and_snapshot_preserve_inspections_without_trust_or_private_fields(self):
        value = copy.deepcopy(self.value)
        value.update(trusted=True, review={'evidence': 'injected'})
        value['metadata']['cpu_key'] = 'synthetic forbidden field'
        self.save(self.first, value)
        restarted = Workspace(self.path)
        self.assertEqual(restarted.library('console'), self.store.library('console'))
        data = json.loads((self.path.parent / 'game-data.json').read_text(encoding='utf-8'))
        snapshot = data['library_inspections'][0]['data']
        self.assertEqual(set(snapshot), {'metadata', 'sha256', 'size', 'plugin', 'inspected_at'})
        self.assertNotIn('cpu_key', snapshot['metadata'])
        self.assertEqual(data['library'][0]['path'], self.first)

    def test_target_isolation_and_clear_remove_only_selected_local_records(self):
        self.save(self.first)
        self.save(self.second, target='other')
        self.assertEqual(self.store.library('console')['groups'][0]['paths'], [self.first])
        self.store.clear_library('CONSOLE')
        self.assertEqual(self.store.library('console'), {'files': [], 'groups': [], 'items': []})
        self.assertEqual(len(self.store.library('other')['files']), 1)
        with self.store.db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM library_inspections').fetchone()[0], 1)

    def test_cached_titles_and_covers_are_display_only_with_no_online_lookup(self):
        self.save(self.first)
        self.save('DriveB:\\Games\\Example\\default_mp.xex')
        with self.store.db() as db:
            db.execute('INSERT INTO titles VALUES(?,?,?)', ('415608C3', json.dumps({'title': 'Example title', 'cover': 'data:image/jpeg;base64,c3ludGhldGlj'}), 1))
        with patch('companion.remote_bytes', side_effect=AssertionError('No network during library listing')):
            result = self.store.library('console')
            group = result['groups'][0]
        self.assertEqual(group['name'], 'Example title')
        self.assertEqual(group['cover_title_id'], '415608C3')
        self.assertTrue(result['covers']['415608C3'].startswith('data:image/jpeg;'))
        self.assertEqual(len(result['groups']), 2)
        self.assertEqual(json.dumps(result).count('data:image/jpeg;'), 1)
        self.assertNotIn('verification', group)

    def test_evicted_library_records_do_not_leave_inspection_rows(self):
        self.save(self.first)
        self.store.record_files('console', [(f'DriveA:\\games\\copy{i}.xex', 100) for i in range(2000)])
        self.assertEqual(len(self.store.library('console')['files']), 2000)
        with self.store.db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM library_inspections').fetchone()[0], 0)

    def test_names_use_folder_hints_then_community_then_explicit_labels(self):
        self.save(self.first)
        self.save(self.second)
        result=self.store.library('console')
        self.assertEqual((result['groups'][0]['name'],result['groups'][0]['name_source']),('Example','folder'))
        with self.store.db() as db:
            db.execute('INSERT INTO titles VALUES(?,?,?)',('415608C3',json.dumps({'title':'Community title'}),1))
        self.assertEqual(self.store.library('console')['groups'][0]['name'],'Community title')
        self.store.label_file('CONSOLE',self.second.lower(),{'path':self.second,'name':'My title','category':'games','mode':'multiplayer','favorite':True})
        group=self.store.library('console')['groups'][0]
        self.assertEqual((group['name'],group['name_source']),('My title','custom'))
        self.assertTrue(group['favorite'])
        self.assertEqual(group['categories'],['uncategorized','games'])
        self.assertEqual(len(group['paths']),2)

    def test_labels_persist_and_stay_target_scoped_without_granting_trust(self):
        self.save(self.first)
        self.save(self.first,target='other')
        self.store.label_file('console',self.first,{'path':self.first,'name':'An emulator','category':'emulators','favorite':True})
        self.store.record_file('console',self.first.lower(),self.value['size']+1)
        result=Workspace(self.path).library('console')
        self.assertIsNone(result['files'][0]['inspection'])
        self.assertEqual(result['files'][0]['label']['category'],'emulators')
        self.assertNotIn('label',self.store.library('other')['files'][0])
        self.assertNotIn('verification',result['files'][0])
        self.store.clear_library('console')
        with self.store.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM library_labels').fetchone()[0],0)

    def test_unknown_paths_invalid_categories_and_trust_fields_are_refused(self):
        self.save(self.first)
        for data in ({'name':'x','trusted':True},{'category':'trainers'},{'favorite':1},{'name':'bad\nname'},{'mode':'guessed-mode'}):
            with self.subTest(data=data),self.assertRaises(ValueError):self.store.label_file('console',self.first,data)
        with self.assertRaises(ValueError):self.store.label_file('other',self.first,{'category':'games'})
        value={**self.value,'plugin':True};self.save(self.first,value)
        with self.assertRaises(ValueError):self.store.label_file('console',self.first,{'mode':'campaign'})

    def test_recent_launches_are_evidence_labels_only(self):
        self.save(self.first)
        self.store.record_launch('console',self.first,'accepted')
        item=self.store.library('console')['files'][0]
        self.assertEqual(item['last_launch']['state'],'accepted')
        self.assertNotIn('ticket',item)


class LibraryMigration(unittest.TestCase):
    def test_additive_schema_preserves_old_writers_and_survives_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'workspace.db'
            with open_database(path) as db:
                db.executescript('CREATE TABLE library(target TEXT,path TEXT,size INTEGER,scanned REAL,PRIMARY KEY(target,path)); CREATE TABLE favorites(target TEXT,path TEXT,name TEXT,directory INTEGER,PRIMARY KEY(target,path));')
                db.execute('INSERT INTO library VALUES(?,?,?,?)', ('console', 'DriveA:\\old.xex', 100, 123))
                db.execute('INSERT INTO favorites VALUES(?,?,?,?)', ('console', 'DriveA:\\old.xex', 'Old favorite', 0))
            for _ in range(2):
                store = Workspace(path)
                self.assertEqual(store.list('library', 'console')[0]['scanned'], 123)
                self.assertEqual(store.list('favorites', 'console')[0]['name'], 'Old favorite')
                self.assertIsNone(store.library('console')['files'][0]['inspection'])
            with open_database(path) as db:
                self.assertEqual([row[1] for row in db.execute('PRAGMA table_info(library)')], ['target', 'path', 'size', 'scanned'])
                db.execute('INSERT INTO library VALUES(?,?,?,?)', ('console', 'DriveB:\\old-writer.iso', 200, 124))
            self.assertEqual(len(store.library('console')['files']), 2)


class LibraryInspectionAPI(unittest.TestCase):
    def setUp(self):
        self.console = Console()
        self.addCleanup(self.console.test_workspace.cleanup)
        self.addCleanup(self.console.companion.reset)

    def test_only_actual_server_bytes_populate_saved_metadata_and_listing_is_read_only(self):
        result = self.console.dispatch('games/inspect', {'path': 'Test:\\unknown.xex', 'metadata': {'title_id': 'FFFFFFFF'}, 'trusted': True})
        listing = self.console.dispatch('library/list', {})
        self.assertEqual(self.console.calls, ['receive'])
        self.assertFalse(hasattr(self.console,'tickets'))
        saved = listing['files'][0]['inspection']
        self.assertEqual(saved['metadata']['title_id'], '415608C3')
        self.assertEqual(saved['sha256'], result['verification']['actual_sha256'])
        self.assertNotIn('verification', saved)
        self.assertEqual(result['verification']['status'], 'unknown')

    def test_iso_inspection_and_invalid_xex_do_not_create_saved_observations(self):
        self.console.files['Test:\\bad.xex'] = b'bad'
        for path in ('Test:\\game.iso', 'Test:\\bad.xex'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.console.dispatch('games/inspect', {'path': path})
        self.assertEqual(self.console.dispatch('library/list', {}), {'files': [], 'groups': [], 'items': []})

