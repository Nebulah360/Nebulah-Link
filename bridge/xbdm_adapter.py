"""Direct XBDM adapter for hosts without Xbox Neighborhood COM.

Neighborhood-class writes covered here: file upload, folder create, rename,
delete, power, notify, and inspected title launch. Plugin, controller, and
launch.ini calls stay on the Neighborhood adapter.
"""

import hashlib
import os
import re
import tempfile
import time
from pathlib import Path

from diagnostics import BridgeDiagnostic
from xbdm import drives, exact, line, session


MAX_FILE = 128 * 1024 * 1024
BULK_TIMEOUT = 210
FIELDS = ('type', 'kernel', 'motherboard', 'cpu', 'gpu', 'edram',
          'board_temperature', 'executable', 'title_id')


def _path(value):
    if not isinstance(value, str) or not 3 <= len(value) <= 512 or re.search(r'[^\x20-\x7E]|"', value):
        raise ValueError('Invalid console path.')
    return value


def _command(stream, command, limit=32):
    stream.sendall((command + '\r\n').encode('ascii'))
    response = line(stream)
    if response.startswith(b'200-'):
        return response[4:].strip(), []
    if not response.startswith(b'202-'):
        raise ValueError('XBDM command rejected.')
    rows = []
    for _ in range(limit + 1):
        row = line(stream)
        if row == b'.\r\n':
            return b'', rows
        if len(row) > 4096 or len(rows) == limit:
            raise ValueError('XBDM reply exceeds its limit.')
        rows.append(row.rstrip(b'\r\n'))
    raise ValueError('XBDM reply incomplete.')


def _query(host, command, limit=32):
    with session(host) as stream:
        return _command(stream, command, limit)


def _drives(host):
    return drives(host)


def _listing(host, path):
    _, rows = _query(host, f'dirlist name="{_path(path)}"', 10000)
    files = []
    for row in rows:
        name = re.search(rb'(?:^| )name="([^"\x00-\x1f]{1,260})"(?= |$)', row)
        hi = re.search(rb'(?:^| )sizehi=0x([0-9A-Fa-f]{1,8})(?= |$)', row)
        lo = re.search(rb'(?:^| )sizelo=0x([0-9A-Fa-f]{1,8})(?= |$)', row)
        if not (name and hi and lo):
            raise ValueError('XBDM directory entry malformed.')
        files.append({'name': name[1].decode('utf-8', 'replace'),
                      'directory': bool(re.search(rb'(?:^| )directory(?: |$)', row)),
                      'size': (int(hi[1], 16) << 32) + int(lo[1], 16)})
    return files


def _info(host, path):
    path = _path(path)
    parent, _, basename = path.rpartition('\\')
    if not parent or not basename:
        raise ValueError('Choose a file below a discovered root.')
    for item in _listing(host, parent + '\\'):
        if item['name'].casefold() == basename.casefold():
            return {'directory': item['directory'], 'size': item['size']}
    raise ValueError('Console file unavailable.')


def _jrpc_reply(host, command):
    with session(host) as stream:
        body, _ = _command(stream, command)
        for _ in range(12):
            text = body.decode('ascii', 'replace') if isinstance(body, (bytes, bytearray)) else str(body)
            match = re.fullmatch(r'buf_addr=(?:0x)?([0-9A-Fa-f]{1,8})', text.strip())
            if not match:
                return text.strip()
            time.sleep(0.25)
            body, _ = _command(stream, f'consolefeatures buf_addr=0x{match[1]}')
        raise ValueError('JRPC2 call did not finish.')


def _module_names(host):
    _, rows = _query(host, 'modules', 512)
    names = set()
    for row in rows:
        match = re.search(rb'(?:^| )name="([A-Za-z0-9_.-]{1,128}\.xex)"', row)
        if match:
            names.add(match[1].decode('ascii'))
    return names


def _receive(host, remote, local, expected, maximum):
    if type(expected) is not int or not 0 <= expected <= maximum:
        raise ValueError('Console file size is outside the read limit.')
    with session(host, timeout=BULK_TIMEOUT if expected > 65536 else 3) as stream:
        stream.sendall(f'getfile name="{_path(remote)}"\r\n'.encode('ascii'))
        if not line(stream).startswith(b'203-'):
            raise ValueError('XBDM file read rejected.')
        length = int.from_bytes(exact(stream, 4), 'little')
        if length != expected:
            raise ValueError('Console file size changed before transfer.')
        with open(local, 'wb') as output:
            remaining = length
            while remaining:
                block = exact(stream, min(65536, remaining))
                output.write(block)
                remaining -= len(block)


def _status(host):
    roots = _drives(host)
    result = {'adapter_version': 10, 'resolved_target': host, 'drives': roots,
              'storage': {'source': 'xbdm', 'state': 'OK' if roots else 'EMPTY'},
              'type': 'Unavailable', 'kernel': 'Unavailable', 'motherboard': 'Unavailable',
              'temperatures': {'cpu': None, 'gpu': None, 'edram': None, 'motherboard': None},
              'current_title': {'executable': None, 'title_id': None},
              'telemetry_fields': {field: {'state': 'UNAVAILABLE', 'source': 'none'} for field in FIELDS},
              'plugin_support': {'observed': [], 'module_scan': 'unavailable', 'jrpc': 'unavailable'}}
    fields = result['telemetry_fields']
    try:
        _, rows = _query(host, 'systeminfo')
        body = b' '.join(rows)
        kernel = re.search(rb'(?:^| )Krnl="?(\d{1,2}\.\d{1,2}\.\d{1,5}\.\d{1,5})', body)
        board = re.search(rb'(?:^| )System="?(Xenon|Zephyr|Falcon|Opus|Jasper|Trinity|Corona|Winchester)', body)
        if kernel:
            result['kernel'] = kernel[1].decode('ascii')
            fields['kernel'] = {'state': 'OK', 'source': 'xbdm'}
        if board:
            result['motherboard'] = board[1].decode('ascii')
            fields['motherboard'] = {'state': 'OK', 'source': 'xbdm'}
    except (OSError, ValueError):
        pass
    try:
        _, rows = _query(host, 'xbeinfo running')
        name = re.search(rb'(?:^| )name="([^"\x00-\x1f]{1,512})"', b' '.join(rows))
        if name:
            result['current_title']['executable'] = name[1].decode('utf-8', 'replace')
            fields['executable'] = {'state': 'OK', 'source': 'xbdm'}
    except (OSError, ValueError):
        pass
    try:
        _, rows = _query(host, 'modules', 512)
        names = {match[1].decode('ascii').casefold() for row in rows
                 if (match := re.search(rb'(?:^| )name="([A-Za-z0-9_.-]{1,128}\.xex)"', row))}
        result['plugin_support']['observed'] = sorted(names & {'jrpc.xex', 'jrpc2.xex', 'rpc.xex', 'xrpc.xex'})
        result['plugin_support']['module_scan'] = 'ok'
    except (OSError, ValueError):
        pass
    queries = [('title_id', 16, None), ('cpu', 15, 0), ('gpu', 15, 1),
               ('edram', 15, 2), ('board_temperature', 15, 3)]
    for field, kind, sensor in queries:
        params = 'A\\0\\A\\0\\' if sensor is None else f'A\\0\\A\\1\\1\\{sensor}\\'
        try:
            body, _ = _query(host, f'consolefeatures ver=2 type={kind} params="{params}"')
            value = int(body, 16)
            if field == 'title_id' and 0 <= value <= 0xFFFFFFFF:
                result['current_title']['title_id'] = f'{value:08X}'
            elif field != 'title_id' and 0 < value <= 125:
                result['temperatures']['motherboard' if field == 'board_temperature' else field] = value
            else:
                continue
            fields[field] = {'state': 'OK', 'source': 'jrpc'}
            result['plugin_support']['jrpc'] = 'responding'
        except (OSError, ValueError):
            fields[field] = {'state': 'COMMAND_REJECTED', 'source': 'jrpc'}
    if result['plugin_support']['jrpc'] != 'responding':
        result['plugin_support']['jrpc'] = 'rejected'
    return result


def _send(host, local, remote, size):
    if type(size) is not int or not 0 <= size <= MAX_FILE:
        raise ValueError('Staged size changed.')
    path = Path(local)
    if not path.is_file() or path.stat().st_size != size:
        raise ValueError('Staged size changed.')
    remote = _path(remote)
    with session(host, timeout=BULK_TIMEOUT) as stream:
        stream.sendall(f'sendfile name="{remote}" length={size}\r\n'.encode('ascii'))
        if not line(stream).startswith(b'204-'):
            raise ValueError('XBDM file write rejected.')
        with open(path, 'rb') as source:
            remaining = size
            while remaining:
                block = source.read(min(65536, remaining))
                if not block:
                    raise ValueError('Staged size changed.')
                stream.sendall(block)
                remaining -= len(block)


def _mkdir(host, path):
    _query(host, f'mkdir name="{_path(path)}"')


def _rename(host, path, destination):
    _query(host, f'rename name="{_path(path)}" newname="{_path(destination)}"')


def _delete(host, path):
    info = _info(host, path)
    if info['directory']:
        raise ValueError('Partial path is a directory')
    _query(host, f'delete name="{_path(path)}"')


def _delete_directory(host, path):
    path = _path(path).rstrip('\\')
    info = _info(host, path)
    if not info['directory']:
        raise ValueError('Not a directory')
    if _listing(host, path + '\\'):
        raise ValueError('Directory is not empty')
    _query(host, f'delete name="{path}"')


def _verify_upload(host, path, size):
    if type(size) is not int or not 0 <= size <= MAX_FILE:
        raise ValueError('Remote size changed')
    info = _info(host, path)
    if info['directory'] or info['size'] != size:
        raise ValueError('Remote size changed')
    handle, temporary = tempfile.mkstemp(prefix='nebulah-xbdm-')
    os.close(handle)
    try:
        _receive(host, path, temporary, size, MAX_FILE)
        if Path(temporary).stat().st_size != size:
            raise ValueError('Read-back size changed')
        return {'sha256': hashlib.sha256(Path(temporary).read_bytes()).hexdigest()}
    finally:
        Path(temporary).unlink(missing_ok=True)


def _power(host, mode):
    if mode in ('warm', 'cold'):
        _query(host, f'magicboot {mode.upper()}')
    elif mode == 'shutdown':
        names = {name.casefold() for name in _module_names(host)}
        if 'jrpc2.xex' not in names:
            raise ValueError('JRPC2 module unavailable')
        _jrpc_reply(host, 'consolefeatures ver=2 type=11 params="A\\0\\A\\0\\"')
    else:
        raise ValueError('Unsupported power operation')
    return {'accepted': True, 'mode': mode}


def _notify(host, message, icon=14):
    if not isinstance(message, str) or not re.fullmatch(r'[\x20-\x7E]{1,80}', message):
        raise ValueError('Invalid notification text')
    if type(icon) is not int or icon not in {
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
            25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 38, 39, 40, 41, 43, 44, 45, 46, 47, 49, 50,
            51, 52, 53, 56, 57, 58, 59, 60, 68}:
        raise ValueError('Unsupported notification icon')
    names = {name.casefold() for name in _module_names(host)}
    if 'jrpc2.xex' not in names:
        raise ValueError('JRPC2 module unavailable')
    payload = message.encode('ascii')
    command = (f'consolefeatures ver=2 type=12 params="A\\0\\A\\2\\7/{len(payload)}\\{payload.hex().upper()}'
               f'\\1\\{icon}\\"')
    _jrpc_reply(host, command)
    return {'accepted': True}


def _launch(host, path):
    path = _path(path)
    directory = path[:path.rfind('\\') + 1]
    if not directory:
        raise ValueError('Invalid console path.')
    _query(host, f'magicboot title="{path}" directory="{directory}"')
    return {'ok': True}


WRITE_CODES = {
    'create-directory': 'TRANSFER_CREATE_FAILED',
    'upload-file': 'TRANSFER_CREATE_FAILED',
    'upload-empty': 'TRANSFER_CREATE_FAILED',
    'verify-upload': 'TRANSFER_READBACK_FAILED',
    'rename-transfer': 'TRANSFER_RENAME_FAILED',
    'delete-file': 'TRANSFER_CLEANUP_FAILED',
    'delete-directory': 'TRANSFER_CLEANUP_FAILED',
    'power': 'CONSOLE_POWER_FAILED',
    'notify': 'CONSOLE_NOTIFY_FAILED',
    'launch': 'ADAPTER_OPERATION_FAILED',
}


def dispatch(host, action, kwargs):
    if not host:
        raise BridgeDiagnostic('DEFAULT_CONSOLE_EMPTY', 'default-console')
    try:
        if action == 'status':
            return _status(host)
        if action == 'storage':
            roots = _drives(host)
            accessible = []
            for root in roots[:32]:
                try:
                    _listing(host, root)
                    accessible.append(root)
                except (OSError, ValueError):
                    pass
            state = 'PARTIAL' if len(roots) > 32 else 'OK' if accessible else 'INACCESSIBLE' if roots else 'EMPTY'
            return {'drives': accessible, 'storage': {'source': 'xbdm', 'state': state,
                    'checked': min(len(roots), 32), 'unavailable': min(len(roots), 32) - len(accessible)}}
        if action == 'browse':
            return {'files': _listing(host, kwargs['path'])}
        if action == 'browse-many':
            listings = []
            for path in kwargs['paths']:
                try:
                    listings.append({'files': _listing(host, path)})
                except (OSError, ValueError):
                    listings.append({'error': True})
            return {'listings': listings}
        if action == 'capacity':
            body, _ = _query(host, f'drivefreespace name="{_path(kwargs["path"])}"')
            values = {}
            for key in ('totalbyteshi', 'totalbyteslo', 'totalfreebyteshi', 'totalfreebyteslo'):
                match = re.search(rb'(?:^| )' + key.encode() + rb'=(?:0x)?([0-9A-Fa-f]{1,8})(?= |$)', body)
                if not match:
                    raise ValueError('XBDM capacity reply malformed.')
                values[key] = int(match[1], 16)
            return {'total': values['totalbyteshi'] << 32 | values['totalbyteslo'],
                    'free': values['totalfreebyteshi'] << 32 | values['totalfreebyteslo']}
        if action == 'file-info':
            return _info(host, kwargs['path'])
        if action in ('download-file', 'receive'):
            remote = kwargs['path']
            info = _info(host, remote)
            maximum = 64 * 1024 * 1024 if action == 'receive' else MAX_FILE
            if info['directory'] or info['size'] > maximum or action == 'receive' and info['size'] < 24:
                raise ValueError('Console file is outside the read limit.')
            if action == 'download-file' and info['size'] != kwargs['size']:
                raise ValueError('Console file size changed.')
            _receive(host, remote, kwargs['local'], info['size'], maximum)
            return {'ok': True}
        if action == 'create-directory':
            _mkdir(host, kwargs['path'])
            return {'ok': True}
        if action == 'upload-file':
            _send(host, kwargs['local'], kwargs['path'], kwargs['size'])
            return {'ok': True}
        if action == 'upload-empty':
            if kwargs.get('size') != 0:
                raise ValueError('Invalid empty upload')
            _send(host, kwargs['local'], kwargs['path'], 0)
            return {'ok': True}
        if action == 'verify-upload':
            return _verify_upload(host, kwargs['path'], kwargs['size'])
        if action == 'rename-transfer':
            _rename(host, kwargs['path'], kwargs['destination'])
            return {'ok': True}
        if action == 'delete-file':
            _delete(host, kwargs['path'])
            return {'ok': True}
        if action == 'delete-directory':
            _delete_directory(host, kwargs['path'])
            return {'ok': True}
        if action == 'power':
            return _power(host, kwargs['mode'])
        if action == 'notify':
            return _notify(host, kwargs['message'], kwargs.get('icon', 14))
        if action == 'launch':
            return _launch(host, kwargs['path'])
        raise BridgeDiagnostic('PLATFORM_UNSUPPORTED', 'operation')
    except BridgeDiagnostic:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        if action in WRITE_CODES:
            raise BridgeDiagnostic(WRITE_CODES[action], 'operation') from None
        code = ('CONSOLE_OPEN_FAILED' if action == 'status' else
                'STORAGE_BROWSE_FAILED' if action in ('browse', 'browse-many', 'storage') else
                'TRANSFER_READ_FAILED' if action in ('download-file', 'receive') else
                'ADAPTER_OPERATION_FAILED')
        raise BridgeDiagnostic(code, 'operation') from None
