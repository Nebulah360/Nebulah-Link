"""Unit tests for Basic PC FTP path mapping and write safety. No live console."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from ftp_service import (
    DEFAULT_HOST,
    FtpBackend,
    FtpError,
    dispatch,
    drive_labels,
    join_virtual,
    map_roots,
    normalize_virtual,
    virtual_to_console,
    writes_permitted,
)


class PathMappingTests(unittest.TestCase):
    def test_drive_labels_and_roots(self):
        drives = ['Hdd:\\', 'Usb0:\\', 'Hdd:\\']
        self.assertEqual(drive_labels(drives), ['Hdd:', 'Usb0:'])
        self.assertEqual(map_roots(drives), {'Hdd:': 'Hdd:\\', 'Usb0:': 'Usb0:\\'})

    def test_virtual_to_console_maps_discovered_roots(self):
        drives = ['Hdd:\\', 'Usb0:\\']
        self.assertIsNone(virtual_to_console('/', drives))
        self.assertEqual(virtual_to_console('/Hdd:', drives), 'Hdd:\\')
        self.assertEqual(virtual_to_console('/Hdd:/Games/demo.bin', drives), r'Hdd:\Games\demo.bin')
        self.assertEqual(virtual_to_console('/usb0:/Apps', drives), r'Usb0:\Apps')

    def test_virtual_rejects_unknown_root_and_traversal(self):
        drives = ['Hdd:\\']
        with self.assertRaises(FtpError):
            virtual_to_console('/Flash:/x', drives)
        with self.assertRaises(FtpError):
            normalize_virtual('/Hdd:/../Usb0:')
        self.assertEqual(join_virtual('/Hdd:/Games', '..'), '/Hdd:')
        with self.assertRaises(FtpError):
            join_virtual('/', '..')

    def test_join_virtual_relative(self):
        self.assertEqual(join_virtual('/Hdd:/Games', 'demo.bin'), '/Hdd:/Games/demo.bin')
        self.assertEqual(join_virtual('/Hdd:/Games', '/Usb0:/x'), '/Usb0:/x')


class WriteGateTests(unittest.TestCase):
    def test_writes_follow_basic_allowlist_not_settings_flag(self):
        bridge = Mock(http_server=None)
        self.assertTrue(writes_permitted(bridge))

    def test_upload_refuses_overwrite_and_oversize(self):
        bridge = Mock(target='192.168.1.10', recovery_hold=None, drives=['Hdd:\\'], http_server=None)
        bridge.dispatch = Mock(return_value={
            'files': [{'name': 'payload.bin', 'directory': False, 'size': 5}],
            'listing': {'truncated': False, 'rejected': 0},
        })
        bridge.adapter = Mock()
        backend = FtpBackend(bridge)
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder) / 'payload.bin'
            local.write_bytes(b'hello')
            with patch('upload_checkpoint.check_staged_file', return_value=None):
                with self.assertRaisesRegex(FtpError, 'Overwrite is disabled'):
                    backend.upload('/Hdd:/Apps/payload.bin', local, 5)
            with self.assertRaisesRegex(FtpError, '128 MiB'):
                backend.upload('/Hdd:/Apps/big.bin', local, 128 * 1024 * 1024 + 1)

    def test_upload_refuses_executable_needing_consent(self):
        bridge = Mock(target='192.168.1.10', recovery_hold=None, drives=['Hdd:\\'], http_server=None)
        backend = FtpBackend(bridge)
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder) / 'title.xex'
            local.write_bytes(b'XEX2' + b'\0' * 12)
            with patch('upload_checkpoint.check_staged_file', return_value={'sha256': 'a' * 64}):
                with self.assertRaisesRegex(FtpError, 'File transfer confirmation'):
                    backend.upload('/Hdd:/Apps/title.xex', local, local.stat().st_size)


class RenameAndRmdirTests(unittest.TestCase):
    def test_rmdir_requires_empty_directory(self):
        bridge = Mock(target='192.168.1.10', recovery_hold=None, drives=['Hdd:\\'], http_server=None)
        backend = FtpBackend(bridge)
        bridge.dispatch = Mock(side_effect=[
            {'files': [{'name': 'stash', 'directory': True, 'size': 0}],
             'listing': {'truncated': False, 'rejected': 0}},
            {'files': [{'name': 'nested.bin', 'directory': False, 'size': 1}],
             'listing': {'truncated': False, 'rejected': 0}},
        ])
        bridge.adapter = Mock()
        with patch('server.safe_path', side_effect=lambda path, _drives: path):
            with self.assertRaisesRegex(FtpError, 'not empty'):
                backend.rmdir('/Hdd:/Apps/stash')
        bridge.adapter.assert_not_called()

    def test_rmdir_deletes_empty_directory(self):
        bridge = Mock(target='192.168.1.10', recovery_hold=None, drives=['Hdd:\\'], http_server=None)
        bridge.dispatch = Mock(side_effect=[
            {'files': [{'name': 'empty', 'directory': True, 'size': 0}],
             'listing': {'truncated': False, 'rejected': 0}},
            {'files': [], 'listing': {'truncated': False, 'rejected': 0}},
        ])
        bridge.adapter = Mock(return_value={'ok': True})
        backend = FtpBackend(bridge)
        with patch('server.safe_path', side_effect=lambda path, _drives: path):
            self.assertEqual(backend.rmdir('/Hdd:/Apps/empty'), r'Hdd:\Apps\empty')
        bridge.adapter.assert_called_once_with('delete-directory', path=r'Hdd:\Apps\empty')

    def test_rmdir_refuses_incomplete_listing(self):
        bridge = Mock(target='192.168.1.10', recovery_hold=None, drives=['Hdd:\\'], http_server=None)
        bridge.dispatch = Mock(side_effect=[
            {'files': [{'name': 'empty', 'directory': True, 'size': 0}],
             'listing': {'truncated': False, 'rejected': 0}},
            {'files': [], 'listing': {'truncated': True, 'rejected': 0}},
        ])
        bridge.adapter = Mock()
        backend = FtpBackend(bridge)
        with patch('server.safe_path', side_effect=lambda path, _drives: path):
            with self.assertRaisesRegex(FtpError, 'incomplete listing'):
                backend.rmdir('/Hdd:/Apps/empty')
        bridge.adapter.assert_not_called()

    def test_rename_same_root_no_overwrite(self):
        bridge = Mock(target='192.168.1.10', recovery_hold=None, drives=['Hdd:\\', 'Usb0:\\'], http_server=None)
        bridge.dispatch = Mock(side_effect=[
            {'files': [{'name': 'old.bin', 'directory': False, 'size': 4}],
             'listing': {'truncated': False, 'rejected': 0}},
            {'files': [], 'listing': {'truncated': False, 'rejected': 0}},
        ])
        bridge.adapter = Mock(return_value={'ok': True})
        backend = FtpBackend(bridge)
        with patch('server.safe_path', side_effect=lambda path, _drives: path):
            self.assertEqual(backend.rename('/Hdd:/Apps/old.bin', '/Hdd:/Apps/new.bin'),
                             r'Hdd:\Apps\new.bin')
            with self.assertRaisesRegex(FtpError, 'same storage root'):
                backend.rename('/Hdd:/Apps/old.bin', '/Usb0:/Apps/old.bin')
        bridge.adapter.assert_called_once_with(
            'rename-transfer', path=r'Hdd:\Apps\old.bin', destination=r'Hdd:\Apps\new.bin')

    def test_rename_refuses_existing_destination(self):
        bridge = Mock(target='192.168.1.10', recovery_hold=None, drives=['Hdd:\\'], http_server=None)
        bridge.dispatch = Mock(side_effect=[
            {'files': [{'name': 'old.bin', 'directory': False, 'size': 4}],
             'listing': {'truncated': False, 'rejected': 0}},
            {'files': [{'name': 'new.bin', 'directory': False, 'size': 1}],
             'listing': {'truncated': False, 'rejected': 0}},
        ])
        bridge.adapter = Mock()
        backend = FtpBackend(bridge)
        with patch('server.safe_path', side_effect=lambda path, _drives: path):
            with self.assertRaisesRegex(FtpError, 'Overwrite is disabled'):
                backend.rename('/Hdd:/Apps/old.bin', '/Hdd:/Apps/new.bin')
        bridge.adapter.assert_not_called()

    def test_delete_file_points_directories_to_rmd(self):
        bridge = Mock(target='192.168.1.10', recovery_hold=None, drives=['Hdd:\\'], http_server=None)
        bridge.dispatch = Mock(return_value={
            'files': [{'name': 'folder', 'directory': True, 'size': 0}],
            'listing': {'truncated': False, 'rejected': 0},
        })
        bridge.adapter = Mock()
        backend = FtpBackend(bridge)
        with patch('server.safe_path', side_effect=lambda path, _drives: path):
            with self.assertRaisesRegex(FtpError, 'Use RMD'):
                backend.delete('/Hdd:/Apps/folder')
        bridge.adapter.assert_not_called()


class DispatchAndServiceTests(unittest.TestCase):
    def test_status_start_requires_confirm_and_stop(self):
        bridge = Mock(spec=['target', 'drives', 'recovery_hold', 'ftp_service', 'http_server'])
        bridge.target = '192.168.1.10'
        bridge.drives = ['Hdd:\\']
        bridge.recovery_hold = None
        bridge.ftp_service = None
        bridge.http_server = None
        status = dispatch(bridge, 'ftp/status', {})
        self.assertFalse(status['enabled'])
        self.assertFalse(status['pro_only'])
        with self.assertRaisesRegex(FtpError, 'Confirm'):
            dispatch(bridge, 'ftp/start', {'host': DEFAULT_HOST, 'port': 0})
        started = dispatch(bridge, 'ftp/start', {'host': '127.0.0.1', 'port': 0, 'confirmed': True})
        self.assertTrue(started['enabled'])
        self.assertEqual(started['host'], '127.0.0.1')
        self.assertEqual(started['username'], 'nebulah')
        self.assertTrue(started['password'])
        self.assertIn('Hdd:', started['roots'])
        stopped = dispatch(bridge, 'ftp/stop', {})
        self.assertFalse(stopped['enabled'])
        self.assertFalse(stopped['password'])

    def test_start_rejects_public_bind(self):
        bridge = BridgeStub()
        with self.assertRaisesRegex(FtpError, 'private IPv4'):
            dispatch(bridge, 'ftp/start', {'host': '8.8.8.8', 'port': 2121, 'confirmed': True})

    def test_smoke_start_stop_gates_target_recovery_and_payloads(self):
        """Smoke contracts for docs/LINKUI_SMOKE.md FTP proxy section."""
        bridge = BridgeStub()
        bridge.target = None
        with self.assertRaisesRegex(FtpError, 'Connect a console'):
            dispatch(bridge, 'ftp/start', {'host': '127.0.0.1', 'port': 0, 'confirmed': True})
        bridge.target = '192.168.1.10'
        bridge.recovery_hold = object()
        with self.assertRaisesRegex(FtpError, 'recovery'):
            dispatch(bridge, 'ftp/start', {'host': '127.0.0.1', 'port': 0, 'confirmed': True})
        bridge.recovery_hold = None
        with self.assertRaisesRegex(FtpError, 'no options'):
            dispatch(bridge, 'ftp/status', {'extra': True})
        with self.assertRaisesRegex(FtpError, 'no options'):
            dispatch(bridge, 'ftp/stop', {'extra': True})
        with self.assertRaisesRegex(FtpError, 'Unsupported FTP start'):
            dispatch(bridge, 'ftp/start', {'host': '127.0.0.1', 'port': 0, 'confirmed': True, 'tls': True})
        started = dispatch(bridge, 'ftp/start', {'host': '127.0.0.1', 'port': 0, 'confirmed': True})
        self.assertTrue(started['enabled'])
        self.assertEqual(started['username'], 'nebulah')
        self.assertTrue(started['password'])
        status = dispatch(bridge, 'ftp/status', {})
        self.assertTrue(status['enabled'])
        self.assertEqual(status['bind'], f"{started['host']}:{started['port']}")
        stopped = dispatch(bridge, 'ftp/stop', {})
        self.assertFalse(stopped['enabled'])
        self.assertFalse(stopped['password'])
        self.assertIsNone(stopped.get('bind'))


class BridgeStub:
    target = '192.168.1.10'
    drives = ['Hdd:\\']
    recovery_hold = None
    ftp_service = None
    http_server = None


if __name__ == '__main__':
    unittest.main()
