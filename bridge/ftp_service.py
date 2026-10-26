"""PC FTP proxy over Neighborhood/XBDM browse and transfer adapters.

Basic-owned (Neighborhood-class). The console does not host FTP; this process binds
on the bridge PC and maps virtual roots to discovered console drives. Writes use
the same safety gate, 128 MiB cap, no-overwrite rule, and staged upload
path as Companion File transfer. Executable uploads that would need interactive
consent are refused here — use the PC File transfer UI instead.

RNFR/RNTO maps to rename-transfer (same-root, no overwrite). RMD deletes only
empty directories via delete-directory. Stdlib FTP is cleartext; TLS is not
implemented. DashLaunch launch.ini ftpserv is not managed here (launch_ini only
covers active-file/plugin selection; no accepted ftpserv enable/status path).
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
import secrets
import socket
import tempfile
import threading
import time
from pathlib import Path

MAX_TRANSFER = 128 * 1024 * 1024
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 2121
USERNAME = 'nebulah'


class FtpError(ValueError):
    """FTP or path mapping failure with a short operator message."""


def drive_labels(drives):
    """Return unique drive folder names (for example Hdd:)."""
    labels = []
    for root in drives or []:
        if not isinstance(root, str):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_]+):\\?', root.strip())
        if not match:
            continue
        label = match[1] + ':'
        if label.lower() not in [item.lower() for item in labels]:
            labels.append(label)
    return labels


def normalize_virtual(path):
    """Normalize an FTP path to absolute POSIX-style segments without .."""
    if not isinstance(path, str) or len(path) > 512 or '\x00' in path:
        raise FtpError('Invalid FTP path.')
    text = path.replace('\\', '/')
    if not text.startswith('/'):
        raise FtpError('FTP path must be absolute.')
    parts = []
    for part in text.split('/'):
        if part in ('', '.'):
            continue
        # Match console safe_path: never accept .. (also blocks root hopping via /Hdd:/../Usb0:).
        if part == '..' or '/' in part or '\\' in part:
            raise FtpError('Relative path segments are not allowed.')
        parts.append(part)
    return '/' + '/'.join(parts)


def join_virtual(cwd, argument):
    """Resolve CWD + relative or absolute FTP argument. Supports a single .. parent step."""
    if argument is None or argument == '':
        return normalize_virtual(cwd)
    text = argument.replace('\\', '/')
    if text.startswith('/'):
        return normalize_virtual(text)
    if text == '..':
        cwd = normalize_virtual(cwd)
        if cwd == '/':
            raise FtpError('Relative path segments are not allowed.')
        parent = cwd.rsplit('/', 1)[0]
        return parent if parent else '/'
    if text.startswith('../') or '/../' in f'/{text}/' or text.endswith('/..'):
        raise FtpError('Relative path segments are not allowed.')
    base = cwd if cwd.endswith('/') else cwd + '/'
    return normalize_virtual(base + text)


def virtual_to_console(virtual, drives):
    """Map /Drive:/rest to Drive:\\rest. Root '/' has no console path."""
    path = normalize_virtual(virtual)
    if path == '/':
        return None
    parts = [part for part in path.split('/') if part]
    if not parts:
        return None
    drive = parts[0]
    if not drive.endswith(':'):
        drive = drive + ':'
    roots = drive_labels(drives)
    match = next((root for root in roots if root.lower() == drive.lower()), None)
    if match is None:
        raise FtpError('Storage root has not been discovered on this console.')
    rest = parts[1:]
    if any(segment in ('.', '..') for segment in rest):
        raise FtpError('Relative path segments are not allowed.')
    if any(re.search(r'[\x00-\x1f"<>|?*:/\\]', segment) for segment in rest):
        raise FtpError('Invalid console path segment.')
    console = match + '\\'
    if rest:
        console += '\\'.join(rest)
    return console


def console_parent_and_name(console_path):
    if not isinstance(console_path, str) or '\\' not in console_path or console_path.endswith('\\'):
        raise FtpError('Choose a file path under a discovered root.')
    parent, name = console_path.rsplit('\\', 1)
    if not name:
        raise FtpError('Choose a file path under a discovered root.')
    return parent + '\\', name


def writes_permitted(_bridge=None):
    """FTP writes are on the Basic allowlist.

    Size caps, no-overwrite, recovery holds, and staged upload still apply.
    app settings keep allow_writes false; that flag is not a payment switch
    and is not consulted here.
    """
    return True


def map_roots(drives):
    """Status helper: virtual folder -> console root."""
    return {label: label + '\\' for label in drive_labels(drives)}


class FtpBackend:
    """Serialize console adapter calls for one FTP session set."""

    def __init__(self, bridge):
        self.bridge = bridge
        self.lock = threading.RLock()

    def _require_connected(self):
        if self.bridge.target is None:
            raise FtpError('Connect a console before using FTP.')
        if self.bridge.recovery_hold is not None:
            raise FtpError('Console recovery is required before FTP continues.')

    def list_entries(self, virtual):
        with self.lock:
            self._require_connected()
            path = normalize_virtual(virtual)
            if path == '/':
                return [{'name': label, 'directory': True, 'size': 0} for label in drive_labels(self.bridge.drives)]
            console = virtual_to_console(path, self.bridge.drives)
            if console is None:
                return []
            if not console.endswith('\\'):
                console += '\\'
            from server import safe_path
            folder = safe_path(console, self.bridge.drives)
            listing = self.bridge.dispatch('browse', {'path': folder})
            files = listing.get('files') if isinstance(listing, dict) else None
            if not isinstance(files, list):
                raise FtpError('Console listing failed.')
            return [{'name': item['name'], 'directory': bool(item.get('directory')),
                     'size': max(0, int(item.get('size', 0)))} for item in files
                    if isinstance(item, dict) and isinstance(item.get('name'), str)]

    def is_directory(self, virtual):
        path = normalize_virtual(virtual)
        if path == '/':
            return True
        console = virtual_to_console(path, self.bridge.drives)
        if console is None:
            return True
        if console.endswith('\\'):
            return True
        parent, name = console_parent_and_name(console)
        with self.lock:
            self._require_connected()
            from server import safe_path
            listing = self.bridge.dispatch('browse', {'path': safe_path(parent, self.bridge.drives)})
            for item in listing.get('files') or []:
                if item.get('name', '').casefold() == name.casefold():
                    return bool(item.get('directory'))
        raise FtpError('Path not found on console.')

    def file_size(self, virtual):
        console = virtual_to_console(virtual, self.bridge.drives)
        if console is None or console.endswith('\\'):
            raise FtpError('Not a file.')
        with self.lock:
            self._require_connected()
            from server import safe_path
            info = self.bridge.adapter('file-info', path=safe_path(console, self.bridge.drives))
            if info.get('directory') is not False:
                raise FtpError('Not a file.')
            size = info.get('size')
            if type(size) is not int or size < 0:
                raise FtpError('File size unavailable.')
            return size

    def download(self, virtual, local_path):
        console = virtual_to_console(virtual, self.bridge.drives)
        if console is None or console.endswith('\\'):
            raise FtpError('Not a file.')
        with self.lock:
            self._require_connected()
            from server import safe_path
            path = safe_path(console, self.bridge.drives)
            info = self.bridge.adapter('file-info', path=path)
            size = info.get('size')
            if info.get('directory') is not False or type(size) is not int or not 0 <= size <= MAX_TRANSFER:
                raise FtpError('Transfer limit is 128 MiB per file.')
            self.bridge.adapter('download-file', path=path, local=str(local_path), size=size)
            return size

    def upload(self, virtual, local_path, size):
        if not writes_permitted(self.bridge):
            raise FtpError('Write access is off. Enable it in PC Settings.')
        if type(size) is not int or not 0 <= size <= MAX_TRANSFER:
            raise FtpError('Transfer limit is 128 MiB per file.')
        console = virtual_to_console(virtual, self.bridge.drives)
        if console is None or console.endswith('\\'):
            raise FtpError('Choose a file path under a discovered root.')
        with self.lock:
            self._require_connected()
            from server import safe_path
            from companion import console_upload_filename
            from upload_checkpoint import check_staged_file
            folder, name = console.rsplit('\\', 1)
            folder = safe_path(folder + '\\', self.bridge.drives)
            path = safe_path(folder + console_upload_filename(name), self.bridge.drives)
            digest = hashlib.sha256()
            with open(local_path, 'rb') as staged:
                while True:
                    chunk = staged.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
            expected = digest.hexdigest()
            if Path(local_path).stat().st_size != size:
                raise FtpError('Staged upload size changed.')
            report = check_staged_file(str(local_path), path, size, expected)
            if report is not None:
                raise FtpError('Executable uploads require PC File transfer confirmation.')
            parent, leaf = path.rsplit('\\', 1)
            listing = self.bridge.dispatch('browse', {'path': parent + '\\'})
            if listing.get('listing', {}).get('truncated') or listing.get('listing', {}).get('rejected'):
                raise FtpError('Cannot establish destination absence from incomplete listing.')
            if any(item['name'].casefold() == leaf.casefold() for item in listing.get('files') or []):
                raise FtpError('Destination exists. Overwrite is disabled.')
            temporary = parent + '\\nb-ftp-' + secrets.token_hex(8) + '.part'
            self.bridge.adapter('upload-empty' if size == 0 else 'upload-file',
                                path=temporary, local=str(local_path), size=size)
            verified = self.bridge.adapter('verify-upload', path=temporary, size=size)
            if verified.get('sha256') != expected:
                try:
                    self.bridge.adapter('delete-file', path=temporary)
                except Exception:
                    pass
                raise FtpError('Full-file read-back hash mismatch; partial removed when possible.')
            listing = self.bridge.dispatch('browse', {'path': parent + '\\'})
            if any(item['name'].casefold() == leaf.casefold() for item in listing.get('files') or []):
                raise FtpError('Destination exists. Overwrite is disabled.')
            self.bridge.adapter('rename-transfer', path=temporary, destination=path)
            return path

    def mkdir(self, virtual):
        if not writes_permitted(self.bridge):
            raise FtpError('Write access is off. Enable it in PC Settings.')
        console = virtual_to_console(virtual, self.bridge.drives)
        if console is None or console.count('\\') < 1:
            raise FtpError('Choose a folder below a discovered root.')
        path = console.rstrip('\\')
        with self.lock:
            self._require_connected()
            result = self.bridge.dispatch('transfer/mkdir', {'path': path, 'confirmed': True})
            return result.get('path', path + '\\')

    def delete(self, virtual):
        if not writes_permitted(self.bridge):
            raise FtpError('Write access is off. Enable it in PC Settings.')
        console = virtual_to_console(virtual, self.bridge.drives)
        if console is None or console.endswith('\\'):
            raise FtpError('Choose a file path under a discovered root.')
        with self.lock:
            self._require_connected()
            from server import safe_path
            path = safe_path(console, self.bridge.drives)
            parent, name = console_parent_and_name(path)
            listing = self.bridge.dispatch('browse', {'path': parent})
            match = next((item for item in listing.get('files') or []
                          if item.get('name', '').casefold() == name.casefold()), None)
            if match is None:
                raise FtpError('Path not found on console.')
            if match.get('directory'):
                raise FtpError('Use RMD for empty directories.')
            self.bridge.adapter('delete-file', path=path)
            return path

    def rmdir(self, virtual):
        """Remove an empty directory only. Non-empty trees are refused."""
        if not writes_permitted(self.bridge):
            raise FtpError('Write access is off. Enable it in PC Settings.')
        console = virtual_to_console(virtual, self.bridge.drives)
        if console is None or console.endswith('\\'):
            raise FtpError('Choose a folder below a discovered root.')
        path = console.rstrip('\\')
        with self.lock:
            self._require_connected()
            from server import safe_path
            path = safe_path(path, self.bridge.drives)
            parent, name = console_parent_and_name(path)
            listing = self.bridge.dispatch('browse', {'path': parent})
            match = next((item for item in listing.get('files') or []
                          if item.get('name', '').casefold() == name.casefold()), None)
            if match is None:
                raise FtpError('Path not found on console.')
            if not match.get('directory'):
                raise FtpError('Not a directory.')
            children = self.bridge.dispatch('browse', {'path': path + '\\'})
            meta = children.get('listing') if isinstance(children, dict) else None
            if not isinstance(meta, dict) or meta.get('truncated') or meta.get('rejected'):
                raise FtpError('Cannot confirm directory is empty from incomplete listing.')
            if children.get('files'):
                raise FtpError('Directory is not empty. Remove contents first.')
            self.bridge.adapter('delete-directory', path=path)
            return path

    def rename(self, source_virtual, dest_virtual):
        """Rename or move within one discovered root. Overwrite is refused."""
        if not writes_permitted(self.bridge):
            raise FtpError('Write access is off. Enable it in PC Settings.')
        source = virtual_to_console(source_virtual, self.bridge.drives)
        dest = virtual_to_console(dest_virtual, self.bridge.drives)
        if source is None or dest is None or source.endswith('\\') or dest.endswith('\\'):
            raise FtpError('Choose paths under a discovered root.')
        source_root = source.split('\\', 1)[0]
        dest_root = dest.split('\\', 1)[0]
        if source_root.casefold() != dest_root.casefold():
            raise FtpError('Rename must stay on the same storage root.')
        if source.casefold() == dest.casefold():
            raise FtpError('Source and destination are the same path.')
        with self.lock:
            self._require_connected()
            from server import safe_path
            source = safe_path(source, self.bridge.drives)
            dest = safe_path(dest, self.bridge.drives)
            parent, name = console_parent_and_name(source)
            listing = self.bridge.dispatch('browse', {'path': parent})
            if not any(item.get('name', '').casefold() == name.casefold()
                       for item in listing.get('files') or []):
                raise FtpError('Path not found on console.')
            dest_parent, dest_name = console_parent_and_name(dest)
            dest_listing = self.bridge.dispatch('browse', {'path': dest_parent})
            meta = dest_listing.get('listing') if isinstance(dest_listing, dict) else None
            if not isinstance(meta, dict) or meta.get('truncated') or meta.get('rejected'):
                raise FtpError('Cannot establish destination absence from incomplete listing.')
            if any(item.get('name', '').casefold() == dest_name.casefold()
                   for item in dest_listing.get('files') or []):
                raise FtpError('Destination exists. Overwrite is disabled.')
            self.bridge.adapter('rename-transfer', path=source, destination=dest)
            return dest


class _FtpSession(threading.Thread):
    def __init__(self, connection, address, service):
        super().__init__(daemon=True, name='nebulah-ftp-session')
        self.connection = connection
        self.address = address
        self.service = service
        self.backend = service.backend
        self.cwd = '/'
        self.binary = True
        self.user = None
        self.authed = False
        self._pasv = None
        self._rest = 0
        self._rnfr = None

    def run(self):
        try:
            self.connection.settimeout(120)
            self._reply(220, 'Nebulah Link Pro FTP proxy')
            while not self.service._stop.is_set():
                line = self._readline()
                if line is None:
                    break
                command, _, argument = line.partition(' ')
                command = command.upper()
                argument = argument.strip()
                handler = getattr(self, '_cmd_' + command, None)
                if handler is None:
                    self._reply(502, 'Command not implemented.')
                else:
                    try:
                        handler(argument)
                    except FtpError as error:
                        self._reply(550, str(error)[:200])
                    except OSError:
                        self._reply(425, 'Data connection failed.')
                    except Exception:
                        self._reply(451, 'Local processing error.')
        finally:
            self._close_pasv()
            try:
                self.connection.close()
            except OSError:
                pass

    def _readline(self):
        buffer = bytearray()
        while len(buffer) < 1024:
            try:
                chunk = self.connection.recv(1)
            except OSError:
                return None
            if not chunk:
                return None
            if chunk == b'\n':
                break
            if chunk != b'\r':
                buffer.extend(chunk)
        try:
            return buffer.decode('ascii', 'strict')
        except UnicodeDecodeError:
            self._reply(500, 'Use ASCII commands.')
            return None

    def _reply(self, code, message):
        payload = f'{code} {message}\r\n'.encode('ascii', 'replace')
        self.connection.sendall(payload)

    def _require_auth(self):
        if not self.authed:
            raise FtpError('Log in first.')

    def _cmd_USER(self, argument):
        self.user = argument
        self.authed = False
        self._reply(331, 'Password required.')

    def _cmd_PASS(self, argument):
        if self.user != self.service.username or not secrets.compare_digest(argument, self.service.password):
            self.authed = False
            self._reply(530, 'Login incorrect.')
            return
        self.authed = True
        self._reply(230, 'Logged in.')

    def _cmd_QUIT(self, _argument):
        self._reply(221, 'Closing.')
        self.connection.close()

    def _cmd_NOOP(self, _argument):
        self._reply(200, 'OK.')

    def _cmd_SYST(self, _argument):
        self._reply(215, 'UNIX Type: L8')

    def _cmd_FEAT(self, _argument):
        self.connection.sendall(b'211-Features:\r\n SIZE\r\n PASV\r\n UTF8\r\n211 End\r\n')

    def _cmd_OPTS(self, argument):
        if argument.upper() in ('UTF8 ON', 'UTF8'):
            self._reply(200, 'UTF8 set.')
        else:
            self._reply(501, 'Option not understood.')

    def _cmd_TYPE(self, argument):
        kind = argument[:1].upper()
        if kind == 'I':
            self.binary = True
            self._reply(200, 'Type set to I.')
        elif kind == 'A':
            self.binary = False
            self._reply(200, 'Type set to A.')
        else:
            self._reply(504, 'Type not implemented.')

    def _cmd_PWD(self, _argument):
        self._require_auth()
        self._reply(257, f'"{self.cwd}"')

    def _cmd_CWD(self, argument):
        self._require_auth()
        target = join_virtual(self.cwd, argument or '/')
        if not self.backend.is_directory(target):
            raise FtpError('Not a directory.')
        self.cwd = target if target == '/' else target.rstrip('/')
        self._reply(250, 'Directory changed.')

    def _cmd_CDUP(self, _argument):
        self._cmd_CWD('..')

    def _cmd_PASV(self, _argument):
        self._require_auth()
        self._close_pasv()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        host = self.service.host
        if host == '0.0.0.0':
            host = '127.0.0.1'
        listener.bind((host, 0))
        listener.listen(1)
        listener.settimeout(30)
        port = listener.getsockname()[1]
        self._pasv = listener
        ip = host.replace('.', ',')
        self._reply(227, f'Entering Passive Mode ({ip},{port // 256},{port % 256}).')

    def _data_socket(self):
        if self._pasv is None:
            raise FtpError('Use PASV before data transfer.')
        try:
            connection, _address = self._pasv.accept()
        finally:
            self._close_pasv()
        connection.settimeout(120)
        return connection

    def _close_pasv(self):
        if self._pasv is not None:
            try:
                self._pasv.close()
            except OSError:
                pass
            self._pasv = None

    def _cmd_LIST(self, argument):
        self._require_auth()
        target = join_virtual(self.cwd, argument) if argument else self.cwd
        entries = self.backend.list_entries(target)
        self._reply(150, 'Opening data connection.')
        with self._data_socket() as data:
            lines = []
            for item in entries:
                stamp = time.strftime('%b %d %H:%M', time.gmtime())
                mode = 'drwxr-xr-x' if item['directory'] else '-rw-r--r--'
                size = 0 if item['directory'] else item['size']
                lines.append(f'{mode} 1 owner group {size} {stamp} {item["name"]}\r\n')
            data.sendall(''.join(lines).encode('utf-8', 'replace'))
        self._reply(226, 'Transfer complete.')

    def _cmd_NLST(self, argument):
        self._require_auth()
        target = join_virtual(self.cwd, argument) if argument else self.cwd
        entries = self.backend.list_entries(target)
        self._reply(150, 'Opening data connection.')
        with self._data_socket() as data:
            data.sendall(''.join(f'{item["name"]}\r\n' for item in entries).encode('utf-8', 'replace'))
        self._reply(226, 'Transfer complete.')

    def _cmd_SIZE(self, argument):
        self._require_auth()
        size = self.backend.file_size(join_virtual(self.cwd, argument))
        self._reply(213, str(size))

    def _cmd_RETR(self, argument):
        self._require_auth()
        target = join_virtual(self.cwd, argument)
        with tempfile.TemporaryDirectory(prefix='nebulah-ftp-get-') as folder:
            local = Path(folder) / 'file.bin'
            self.backend.download(target, local)
            self._reply(150, 'Opening data connection.')
            with self._data_socket() as data, open(local, 'rb') as stream:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    data.sendall(chunk)
        self._reply(226, 'Transfer complete.')

    def _cmd_STOR(self, argument):
        self._require_auth()
        target = join_virtual(self.cwd, argument)
        self._reply(150, 'Opening data connection.')
        with tempfile.TemporaryDirectory(prefix='nebulah-ftp-put-') as folder:
            local = Path(folder) / 'file.bin'
            size = 0
            with self._data_socket() as data, open(local, 'wb') as stream:
                while True:
                    chunk = data.recv(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_TRANSFER:
                        raise FtpError('Transfer limit is 128 MiB per file.')
                    stream.write(chunk)
            self.backend.upload(target, local, size)
        self._reply(226, 'Transfer complete.')

    def _cmd_MKD(self, argument):
        self._require_auth()
        path = self.backend.mkdir(join_virtual(self.cwd, argument))
        self._reply(257, f'"{path}" created.')

    def _cmd_DELE(self, argument):
        self._require_auth()
        self.backend.delete(join_virtual(self.cwd, argument))
        self._reply(250, 'Deleted.')

    def _cmd_RMD(self, argument):
        self._require_auth()
        self.backend.rmdir(join_virtual(self.cwd, argument))
        self._reply(250, 'Directory removed.')

    def _cmd_XRMD(self, argument):
        self._cmd_RMD(argument)

    def _cmd_RNFR(self, argument):
        self._require_auth()
        target = join_virtual(self.cwd, argument)
        console = virtual_to_console(target, self.service.bridge.drives)
        if console is None or console.endswith('\\'):
            raise FtpError('Choose a path under a discovered root.')
        # is_directory raises when the leaf is missing; True/False both accept RNFR.
        self.backend.is_directory(target)
        self._rnfr = target
        self._reply(350, 'Ready for RNTO.')

    def _cmd_RNTO(self, argument):
        self._require_auth()
        if self._rnfr is None:
            raise FtpError('Send RNFR first.')
        source = self._rnfr
        self._rnfr = None
        self.backend.rename(source, join_virtual(self.cwd, argument))
        self._reply(250, 'Renamed.')

    def _cmd_REST(self, argument):
        if argument != '0':
            self._reply(350, 'Restart not supported; send from offset 0.')
            return
        self._rest = 0
        self._reply(350, 'Restart marker ok.')


class FtpService:
    """Thread-backed FTP listener owned by the bridge for one console session."""

    def __init__(self, bridge):
        self.bridge = bridge
        self.backend = FtpBackend(bridge)
        self.host = DEFAULT_HOST
        self.port = DEFAULT_PORT
        self.username = USERNAME
        self.password = ''
        self._stop = threading.Event()
        self._listener = None
        self._thread = None
        self._lock = threading.Lock()

    def status(self):
        running = self._thread is not None and self._thread.is_alive() and not self._stop.is_set()
        return {
            'pro_only': False,
            'enabled': running,
            'host': self.host,
            'port': self.port if running else None,
            'username': self.username if running else None,
            'password': self.password if running else None,
            'bind': f'{self.host}:{self.port}' if running else None,
            'roots': map_roots(self.bridge.drives) if self.bridge.target else {},
            'writes': writes_permitted(self.bridge),
            'max_bytes': MAX_TRANSFER,
            'note': ('PC proxy only (cleartext FTP; TLS not enabled). Empty-directory RMD and '
                     'RNFR/RNTO rename when writes are on. Executable uploads need File transfer. '
                     'DashLaunch ftpserv is not managed here.'),
        }

    def start(self, host=DEFAULT_HOST, port=DEFAULT_PORT, confirmed=False):
        if confirmed is not True:
            raise FtpError('Confirm FTP start on this bridge PC.')
        if self.bridge.target is None:
            raise FtpError('Connect a console first.')
        if self.bridge.recovery_hold is not None:
            raise FtpError('Console recovery is required before FTP can start.')
        try:
            address = ipaddress.ip_address(host)
        except ValueError as error:
            raise FtpError('Bind to 127.0.0.1 or a private IPv4 address.') from error
        if address.is_loopback:
            pass
        elif not address.is_private or address.is_link_local or address.is_multicast or address.is_unspecified:
            raise FtpError('Bind to 127.0.0.1 or a private IPv4 address.')
        if type(port) is not int or not 0 <= port <= 65535:
            raise FtpError('Choose a TCP port from 0 to 65535 (0 picks a free port).')
        with self._lock:
            if self._thread is not None and self._thread.is_alive() and not self._stop.is_set():
                return self.status()
            self.stop()
            self.host = str(address)
            self.port = port
            self.password = secrets.token_urlsafe(12)
            self._stop.clear()
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind((self.host, self.port))
                listener.listen(5)
                listener.settimeout(0.5)
            except OSError as error:
                listener.close()
                raise FtpError('FTP bind address or port is unavailable.') from error
            self.port = listener.getsockname()[1]
            self._listener = listener
            self._thread = threading.Thread(target=self._serve, name='nebulah-ftp', daemon=True)
            self._thread.start()
            return self.status()

    def stop(self):
        self._stop.set()
        listener = self._listener
        self._listener = None
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=2)
        self.password = ''
        return self.status()

    def _serve(self):
        while not self._stop.is_set():
            try:
                connection, address = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            _FtpSession(connection, address, self).start()


def dispatch(bridge, action, data):
    """Bridge terminal routes: ftp/status, ftp/start, ftp/stop."""
    if not isinstance(data, dict):
        raise FtpError('FTP options must be an object.')
    if getattr(bridge, 'ftp_service', None) is None:
        bridge.ftp_service = FtpService(bridge)
    service = bridge.ftp_service
    if action == 'ftp/status':
        if data:
            raise FtpError('FTP status takes no options.')
        return service.status()
    if action == 'ftp/start':
        host = data.get('host', DEFAULT_HOST)
        port = data.get('port', DEFAULT_PORT)
        if set(data) - {'host', 'port', 'confirmed'}:
            raise FtpError('Unsupported FTP start options.')
        if not isinstance(host, str):
            raise FtpError('Bind to 127.0.0.1 or a private IPv4 address.')
        return service.start(host=host, port=port, confirmed=data.get('confirmed') is True)
    if action == 'ftp/stop':
        if data:
            raise FtpError('FTP stop takes no options.')
        return service.stop()
    raise FtpError('Unknown FTP operation.')
