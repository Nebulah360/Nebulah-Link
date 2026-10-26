"""Bounded, read-only inspection of Xbox 360 profile packages. No console writes."""
import base64
import hashlib
import hmac
import re
import secrets
import struct
import tempfile
import time
from pathlib import Path

from title_updates import HEADER_LEN, _header_name
from diagnostics import BridgeDiagnostic


MAX_PROFILE_PACKAGE = 8 * 1024 * 1024
PROFILE_PATH = re.compile(r'^(?:HDD\d*|USB\d+):\\Content\\([0-9A-Fa-f]{16})\\FFFE07D1\\00010000\\([0-9A-Fa-f]{16})$', re.I)
PROFILE_NAME = re.compile(r'[0-9A-Fa-f]{16}')
ACCOUNT_KEY = bytes.fromhex('E1BC159C73B1EAE9AB3170F3AD47EBF3')  # Public format key, not a console key.

def _stfs_block(package, block):
    total = int.from_bytes(package[0x395:0x399], 'big')
    if not 0 <= block < total or total > 170 * 170:
        return None
    root = (package[0x37B] >> 1) & 1
    top = 0xB6000 if total > 170 else 0xA000
    root_table = package[top + root * 0x1000:top + (root + 1) * 0x1000]
    if len(root_table) != 0x1000 or hashlib.sha1(root_table).digest() != package[0x381:0x395]:
        return None
    shift = 2 * (block // 170 + 1) if block >= 170 else 0
    offset = 0xC000 + (block + shift) * 0x1000
    data = package[offset:offset + 0x1000]
    hash_base = offset - (block % 170) * 0x1000 - 0x2000
    if total > 170:
        level_one = root_table[(block // 170) * 0x18:(block // 170 + 1) * 0x18]
        if len(level_one) != 0x18 or level_one[20] & 0x80 == 0:
            return None
        active = (level_one[20] >> 6) & 1
        hash_table = package[hash_base + active * 0x1000:hash_base + (active + 1) * 0x1000]
        if len(hash_table) != 0x1000 or hashlib.sha1(hash_table).digest() != level_one[:20]:
            return None
    else:
        hash_table = root_table
    entry = hash_table[(block % 170) * 0x18:(block % 170 + 1) * 0x18]
    if (len(data) != 0x1000 or len(entry) != 0x18 or
            entry[:20] != hashlib.sha1(data).digest() or entry[20] & 0xC0 not in (0x80, 0xC0)):
        return None
    return data, int.from_bytes(entry[21:24], 'big')


def _dashboard_gpd(package):
    # shortcut: only the measured two-hash-table CON layout; add other layouts after hardware validation.
    if (len(package) < 0xD000 or (int.from_bytes(package[0x340:0x344], 'big') + 0xFFF) & ~0xFFF != 0xA000 or
            package[0x37B] & ~2 or package[0x37C:0x37E] != b'\x01\x00'):
        return None
    table_block = int.from_bytes(package[0x37E:0x381], 'little')
    table = _stfs_block(package, table_block)
    if table is None:
        return None
    for offset in range(0, 0x1000, 0x40):
        entry = table[0][offset:offset + 0x40]
        if entry[:0x28].split(b'\0', 1)[0] != b'FFFE07D1.gpd' or entry[0x28] & 0x80:
            continue
        blocks = int.from_bytes(entry[0x29:0x2C], 'little')
        size = int.from_bytes(entry[0x34:0x38], 'big')
        if (entry[0x29:0x2C] != entry[0x2C:0x2F] or
                not 0 < size <= 2 * 1024 * 1024 or blocks != (size + 0xFFF) // 0x1000):
            return None
        block = int.from_bytes(entry[0x2F:0x32], 'little')
        seen = set()
        content = bytearray()
        for _ in range(blocks):
            if block in seen:
                return None
            seen.add(block)
            current = _stfs_block(package, block)
            if current is None:
                return None
            content.extend(current[0])
            block = current[1]
        return bytes(content[:size]) if block == 0xFFFFFF else None
    return None


def _dashboard_summary(package, include_games=False):
    gpd = _dashboard_gpd(package)
    if not gpd or len(gpd) < 24 or gpd[:4] != b'XDBF':
        return None
    version, capacity, count, free_capacity, free_count = struct.unpack_from('>5I', gpd, 4)
    data_base = 24 + capacity * 18 + free_capacity * 8
    if (version != 0x10000 or count > capacity or free_count > free_capacity or
            24 + count * 18 > len(gpd) or data_base > len(gpd)):
        return None
    titles = set()
    score = 0
    games = []
    for index in range(count):
        namespace, ident, offset, length = struct.unpack_from('>HQII', gpd, 24 + index * 18)
        if namespace != 4 or ident in (0x100000000, 0x200000000):
            continue
        start = data_base + offset
        if ident > 0xFFFFFFFF or length < 0x28 or start > len(gpd) or length > len(gpd) - start:
            return None
        title, achievements, unlocked, total, earned = struct.unpack_from('>5I', gpd, start)
        if title != ident or title in titles or unlocked > achievements or earned > total or total > 100000:
            return None
        titles.add(title)
        score += earned
        if include_games and len(games) < 100:
            games.append({'title_id': f'{title:08X}', 'achievements': achievements,
                          'unlocked': unlocked, 'total_score': total, 'earned_score': earned})
    summary = {'games_played': len(titles), 'earned_score': score}
    if include_games:
        summary.update(games=games, games_truncated=len(titles) > len(games))
    return summary


def _picture(prefix):
    size = int.from_bytes(prefix[0x1712:0x1716], 'big')
    if not 33 <= size <= 0x4000:
        return None
    image = prefix[0x171A:0x171A + size]
    if (len(image) != size or not image.startswith(b'\x89PNG\r\n\x1a\n') or
            image[12:16] != b'IHDR' or image[-8:-4] != b'IEND' or
            not 1 <= int.from_bytes(image[16:20], 'big') <= 256 or
            not 1 <= int.from_bytes(image[20:24], 'big') <= 256):
        return None
    return 'data:image/png;base64,' + base64.b64encode(image).decode('ascii')


def _account_gamertag(package):
    if len(package) < 0xD000 or package[0x37C:0x37E] != b'\x01\x00':
        return None
    table_block = int.from_bytes(package[0x37E:0x381], 'little')
    if not 0 <= table_block <= 4:
        return None
    for table_base in (0xB000, 0xC000):
        table = table_base + table_block * 0x1000
        for offset in range(table, min(table + 0x1000, len(package)), 0x40):
            entry = package[offset:offset + 0x40]
            if len(entry) != 0x40 or entry[:0x28].split(b'\0', 1)[0] != b'Account' or entry[0x28] & 0x80:
                continue
            block = int.from_bytes(entry[0x2F:0x32], 'little')
            if int.from_bytes(entry[0x34:0x38], 'big') != 404:
                continue
            tables = 2 if ((int.from_bytes(package[0x340:0x344], 'big') + 0xFFF) & 0xF000) == 0xA000 else 1
            skipped = ((block // 0xAA) + 1) * tables if block >= 0xAA else 0
            start = 0xC000 + (block + skipped) * 0x1000
            encrypted = package[start:start + 404]
            if len(encrypted) != 404:
                continue
            key = hmac.new(ACCOUNT_KEY, encrypted[:16], hashlib.sha1).digest()[:16]
            permutation = list(range(256))
            index = 0
            for position in range(256):
                index = (index + permutation[position] + key[position % 16]) & 255
                permutation[position], permutation[index] = permutation[index], permutation[position]
            left = right = 0
            name = bytearray()
            for position, value in enumerate(encrypted[16:16 + 0x2E]):
                left = (left + 1) & 255
                right = (right + permutation[left]) & 255
                permutation[left], permutation[right] = permutation[right], permutation[left]
                if 0x10 <= position < 0x2E:
                    name.append(value ^ permutation[(permutation[left] + permutation[right]) & 255])
            try:
                decoded = name.decode('utf-16-be')
            except UnicodeDecodeError:
                continue
            gamertag, _, padding = decoded.partition('\0')
            if padding.strip('\0'):
                continue
            if 1 <= len(gamertag) <= 15 and all(char.isprintable() for char in gamertag):
                return gamertag
    return None


def inspect_profile_package(bridge, path, include_games=True):
    match = PROFILE_PATH.fullmatch(path)
    if not match or match[1].lower() != match[2].lower():
        raise ValueError('Choose a profile package from Content on a discovered storage root.')
    info = bridge.adapter('file-info', path=path)
    size = info.get('size')
    if info.get('directory') is not False or type(size) is not int or not HEADER_LEN <= size <= MAX_PROFILE_PACKAGE:
        raise ValueError('Selected profile package is outside the inspection limit.')
    with tempfile.TemporaryDirectory(prefix='nebulah-profile-') as folder:
        local = Path(folder) / 'package.bin'
        bridge.adapter('download-file', path=path, local=str(local), size=size)
        if local.stat().st_size != size:
            raise ValueError('Profile package changed during read.')
        package = local.read_bytes()
    prefix = package[:0x571A]
    header = prefix[:HEADER_LEN]
    if (header[:4] != b'CON ' or header[0x344:0x348] != b'\0\1\0\0' or
            header[0x360:0x364] != bytes.fromhex('FFFE07D1') or
            header[0x371:0x379] != bytes.fromhex(match[1])):
        raise ValueError('Selected file is not a supported profile package.')
    display_name = _account_gamertag(package) or _header_name(header, 0x411)
    if display_name and PROFILE_NAME.fullmatch(display_name):
        display_name = None  # Profile package headers can label themselves with the account ID.
    return {'display_name': display_name, 'picture': _picture(prefix), 'dashboard': _dashboard_summary(package, include_games), 'size': size,
            'sha256': hashlib.sha256(package).hexdigest(),
            'note': 'Structural profile inspection only. This does not verify a signature, current membership, signed-in profile, or account sync.'}


def _binding_challenge(account_id):
    nonce = secrets.token_hex(16)
    return {'nonce': nonce, 'digest': hashlib.sha1((nonce + account_id.lower()).encode('ascii')).hexdigest()}


def _offline_name(bridge, account_id):
    try:
        raw = bytearray()
        for index in range(5):
            word = bridge.adapter('component-profile-name-word', word=index,
                                  **_binding_challenge(account_id)).get('word')
            if type(word) is not int or not 0 <= word <= 0xFFFFFF:
                return None
            raw.extend(word.to_bytes(3, 'big'))
        name, _, padding = raw.partition(b'\0')
        if padding.strip(b'\0') or not 1 <= len(name) <= 15 or not all(32 <= byte <= 126 for byte in name):
            return None
        return name.decode('ascii')
    except BridgeDiagnostic:
        return None


def current_profile(bridge):
    """Signed-in match needs Companion profile adapters; Basic returns none without them."""
    saved = getattr(bridge, 'profile_identity_candidates', None)
    if not saved or saved[0] != bridge.target or saved[1] != getattr(bridge, 'connection_generation', 0):
        return {'active': None}
    try:
        if bridge.adapter('component-session').get('state') != 'ready':
            return {'active': None}
        offline = [(account_id, profile) for account_id, profile in saved[2] if bridge.adapter(
            'component-profile-match', **_binding_challenge(account_id)).get('matched') is True]
        if offline:
            if len(offline) != 1:
                return {'active': None}
            account_id, profile = offline[0]
            active = dict(profile, account_type='offline')
            if not active['display_name']:
                active['display_name'] = _offline_name(bridge, account_id) or 'Signed-in offline profile'
            return {'active': active}
        live = []
        for account_id, profile in saved[2]:
            match = bridge.adapter('component-profile-live-match', **_binding_challenge(account_id))
            if match.get('matched') is True and match.get('session') in ('online', 'local'):
                live.append(dict(profile, account_type='live', live_session=match['session']))
        return {'active': live[0] if len(live) == 1 else None}
    except (BridgeDiagnostic, ValueError):
        return {'active': None}



def list_profile_packages(bridge):
    if not bridge.target:
        raise ValueError('Connect a console first.')
    roots = [root + 'Content\\' for root in bridge.drives if re.fullmatch(r'(?:HDD\d*|USB\d+):\\', root, re.I)]
    folders = []
    for index in range(0, len(roots), 8):
        listings = bridge.dispatch('browse-many', {'paths': roots[index:index + 8]})['listings']
        for root, listing in zip(roots[index:index + 8], listings):
            for item in listing.get('files', []):
                if item['directory'] and PROFILE_NAME.fullmatch(item['name']):
                    folders.append((root, item['name']))
    truncated = len(folders) > 32
    folders = folders[:32]
    locations = [root + ident + '\\FFFE07D1\\00010000\\' for root, ident in folders]
    profiles = []
    unavailable = 0
    unavailable_ids = set()
    for index in range(0, len(locations), 8):
        listings = bridge.dispatch('browse-many', {'paths': locations[index:index + 8]})['listings']
        for (root, ident), location, listing in zip(folders[index:index + 8], locations[index:index + 8], listings):
            if not any(not item['directory'] and item['name'].lower() == ident.lower()
                       for item in listing.get('files', [])):
                continue
            path = location + ident
            try:
                result = inspect_profile_package(bridge, path, include_games=False)
            except BridgeDiagnostic as error:
                if error.code != 'TRANSFER_READ_FAILED' or bridge.recovery_hold is not None:
                    raise
                unavailable += 1
                unavailable_ids.add(ident.lower())
                continue
            except ValueError:
                unavailable += 1
                continue
            profiles.append({'path': path, 'display_name': result['display_name'] or 'Name unavailable',
                             'picture': result['picture'], 'dashboard': result['dashboard'],
                             'storage': root[:-len('Content\\')]})
    bridge.profile_selections = {}
    candidates = []
    for profile in profiles:
        path = profile.pop('path')
        selection = secrets.token_urlsafe(18)
        bridge.profile_selections[selection] = path
        profile['selection'] = selection
        if profile['display_name'] != 'Name unavailable':
            candidates.append((PROFILE_PATH.fullmatch(path)[1], {
                'display_name': profile['display_name'], 'picture': profile['picture'], 'selection': selection}))
    previous = getattr(bridge, 'profile_identity_candidates', None)
    if previous and previous[:2] == (bridge.target, getattr(bridge, 'connection_generation', 0)):
        found = {account_id.lower() for account_id, _ in candidates}
        candidates.extend((account_id, dict(profile, selection=None)) for account_id, profile in previous[2]
                          if account_id.lower() in unavailable_ids and account_id.lower() not in found)
    known = {account_id.lower() for account_id, _ in candidates}
    candidates.extend((account_id, {'display_name': None, 'picture': None, 'selection': None})
                      for account_id in unavailable_ids if account_id not in known)
    bridge.profile_identity_candidates = (bridge.target, getattr(bridge, 'connection_generation', 0), candidates)
    return {'profiles': profiles, **current_profile(bridge), 'unavailable': unavailable, 'truncated': truncated}
