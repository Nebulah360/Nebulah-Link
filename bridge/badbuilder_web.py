"""PC-only web control for the vendored BadBuilder engine."""
import ctypes
import json
import os
import re
import secrets
import subprocess
import threading
import time
from pathlib import Path

from runtime_paths import ROOT
from usb_inventory import inventory

BUILD_DIR = ROOT / '.local' / 'badbuilder'
JOBS_DIR = BUILD_DIR / 'jobs'
ACTIVE_PATH = JOBS_DIR / 'active'
EXECUTABLE = BUILD_DIR / 'BadBuilder.exe'
ASSEMBLY = BUILD_DIR / 'BadBuilder.dll'
DOTNET = BUILD_DIR / 'dotnet.exe'
_lock = threading.Lock()
_active = None
_BUILTIN = {'homebrew-aurora', 'homebrew-xexmenu', 'homebrew-simple360nandflasher'}
_EXPLOITS = {'BadUpdate', 'ABadAvatar', 'ABadAvatarUpdate'}
_BOOTSTRAPS = {'XeUnshackle', 'FreeMyXe'}


def availability(data=None):
    if data:
        raise ValueError('BadBuilder availability takes no options.')
    ready = os.name == 'nt' and all(path.is_file() for path in (EXECUTABLE, ASSEMBLY, DOTNET))
    return {'state': 'ready' if ready else 'build_required', 'version': 'v2.1.0',
            'message': 'BadBuilder web engine is ready on this PC.' if ready else
                       'Build the included BadBuilder engine with tools/build_badbuilder.ps1 on this PC.'}


def _status_path(job_id):
    if not isinstance(job_id, str) or not re.fullmatch(r'[0-9a-f]{24}', job_id):
        raise ValueError('BadBuilder job ID is invalid.')
    return JOBS_DIR / (job_id + '.status.json')


def status(data=None):
    if set(data or {}) != {'job_id'}:
        raise ValueError('Choose one BadBuilder job.')
    path = _status_path(data['job_id'])
    try:
        if path.stat().st_size > 8192:
            raise ValueError('BadBuilder job status is invalid.')
        result = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        raise ValueError('BadBuilder job status is unavailable.') from None
    if result.get('state') not in ('queued', 'running', 'complete', 'error') or not isinstance(result.get('message'), str):
        raise ValueError('BadBuilder job status is invalid.')
    return {'state': result['state'], 'message': result['message'][:500]}


def scan(data=None, runner=subprocess.run):
    if set(data or {}) != {'path'} or not isinstance(data['path'], str):
        raise ValueError('Choose a local homebrew archive.')
    path = Path(data['path']).expanduser().resolve()
    if path.suffix.lower() not in ('.zip', '.rar', '.7z') or not path.is_file() or path.stat().st_size > 10 * 1024**3:
        raise ValueError('Choose an existing ZIP, RAR, or 7z archive under 10 GB.')
    if not DOTNET.is_file() or not ASSEMBLY.is_file():
        raise ValueError('Build the included BadBuilder engine before scanning archives.')
    result = runner([str(DOTNET), str(ASSEMBLY), '--web-scan', str(path)],
                    capture_output=True, text=True, timeout=60, check=False)
    if result.returncode or len(result.stdout) > 64 * 1024:
        raise ValueError('BadBuilder could not scan that archive.')
    try:
        entries = json.loads(result.stdout)
    except ValueError:
        raise ValueError('BadBuilder archive scan was incomplete.') from None
    if not isinstance(entries, list) or len(entries) > 256 or any(not isinstance(e, str) or len(e) > 500 for e in entries):
        raise ValueError('BadBuilder archive entry points are invalid.')
    return {'entry_points': entries}


def _request(data):
    expected = {'disk_number', 'disk_bytes', 'disk_model', 'exploit', 'bootstrap',
                'firmware_update', 'homebrew_ids', 'custom_homebrew', 'launch_id',
                'archive_paths', 'confirmation'}
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError('BadBuilder configuration is incomplete.')
    number, size, model = data['disk_number'], data['disk_bytes'], data['disk_model']
    if (type(number) is not int or not 0 <= number < 256 or type(size) is not int or not 0 < size <= 2**60
            or not isinstance(model, str) or not 0 < len(model) <= 100):
        raise ValueError('USB disk identity is invalid.')
    if (not isinstance(data['exploit'], str) or data['exploit'] not in _EXPLOITS
            or not isinstance(data['bootstrap'], str) or data['bootstrap'] not in _BOOTSTRAPS
            or type(data['firmware_update']) is not bool):
        raise ValueError('Choose a supported exploit, bootstrap, and update mode.')
    homebrew = data['homebrew_ids']
    custom = data['custom_homebrew']
    paths = data['archive_paths']
    if (not isinstance(homebrew, list) or len(homebrew) > len(_BUILTIN)
            or any(not isinstance(item, str) or item not in _BUILTIN for item in homebrew)
            or len(set(homebrew)) != len(homebrew)):
        raise ValueError('Included homebrew selection is invalid.')
    if not isinstance(custom, list) or len(custom) > 16:
        raise ValueError('Custom homebrew selection is invalid.')
    for item in custom:
        if (not isinstance(item, dict) or set(item) != {'path', 'entry_point'}
                or not isinstance(item['path'], str) or len(item['path']) > 1000
                or item['entry_point'] is not None and (not isinstance(item['entry_point'], str) or len(item['entry_point']) > 500)):
            raise ValueError('Custom homebrew entry is invalid.')
    if (not isinstance(paths, dict) or len(paths) > 24
            or any(not isinstance(k, str) or not re.fullmatch(r'[a-z0-9-]{1,80}', k)
                   or not isinstance(v, str) or len(v) > 1000 for k, v in paths.items())):
        raise ValueError('Local archive paths are invalid.')
    launch = data['launch_id']
    valid_launch = (_BUILTIN - {'homebrew-xexmenu'}) | {f'homebrew-custom-{i}' for i in range(len(custom))}
    if launch is not None and (not isinstance(launch, str) or launch not in valid_launch or data['bootstrap'] != 'XeUnshackle'):
        raise ValueError('Default launch must be installed homebrew with XeUnshackle.')
    if data['firmware_update'] and (homebrew or custom or launch is not None):
        raise ValueError('Dashboard update mode cannot include homebrew.')
    if data['confirmation'] != f'ERASE DISK {number}':
        raise ValueError('Type the exact disk erase confirmation.')
    disks = inventory({})['disks']
    disk = next((item for item in disks if item['number'] == number and item['bytes'] == size and item['model'] == model), None)
    if disk is None or disk['system'] or disk['boot'] or disk['read_only'] or disk['operational_status'] != 'Online':
        raise ValueError('Selected USB disk changed or is not safe to format. Refresh USB disks.')
    return {'DiskNumber': number, 'DiskBytes': size, 'DiskModel': model,
            'Exploit': data['exploit'], 'Bootstrap': data['bootstrap'], 'FirmwareUpdate': data['firmware_update'],
            'HomebrewIds': homebrew, 'CustomHomebrew': [{'Path': item['path'], 'EntryPoint': item['entry_point']} for item in custom],
            'LaunchId': launch, 'ArchivePaths': paths, 'Confirmation': data['confirmation']}


def _start_elevated(path):
    arguments = f'--web-build "{path}"'
    result = ctypes.windll.shell32.ShellExecuteW(None, 'runas', str(EXECUTABLE), arguments, str(BUILD_DIR), 0)
    if result <= 32:
        raise ValueError('Windows did not approve the BadBuilder Administrator prompt.')


def start(data, launcher=_start_elevated):
    global _active
    if os.name != 'nt' or not EXECUTABLE.is_file():
        raise ValueError('Build the included BadBuilder engine on Windows before preparing a USB disk.')
    request = _request(data)
    with _lock:
        if ACTIVE_PATH.is_file():
            persisted = ACTIVE_PATH.read_text(encoding='ascii').strip()
            if status({'job_id': persisted})['state'] in ('queued', 'running'):
                raise ValueError('A BadBuilder USB job is already active.')
        if _active is not None:
            old = status({'job_id': _active})
            if old['state'] in ('queued', 'running'):
                raise ValueError('A BadBuilder USB job is already active.')
        job_id = secrets.token_hex(12)
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        path = JOBS_DIR / (job_id + '.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump(request, stream)
        _status_path(job_id).write_text(json.dumps({'state': 'queued', 'message': 'Waiting for the Windows Administrator prompt.'}), encoding='utf-8')
        ACTIVE_PATH.write_text(job_id, encoding='ascii')
        _active = job_id
        try:
            launcher(path)
        except Exception:
            _status_path(job_id).write_text(json.dumps({'state': 'error', 'message': 'Windows did not start BadBuilder.'}), encoding='utf-8')
            raise
    return {'job_id': job_id, 'state': 'queued'}
