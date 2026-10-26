"""PC-local Cherry-style virtual profile. This never edits an Xbox profile."""
import json
import os
import tempfile
from pathlib import Path

from runtime_paths import ROOT


PATH = ROOT / '.local' / 'cherry-profile.json'
DEFAULT = {'gamertag': '', 'gamerscore': 0, 'membership': 'Free', 'isGold': False,
           'motto': '', 'bio': '', 'location': '', 'theme': '', 'avatarId': 0,
           'bypass': False}
TEXT_LIMITS = {'gamertag': 15, 'motto': 100, 'bio': 500, 'location': 100, 'theme': 100}
EDITABLE = set(DEFAULT) - {'isGold'}


def _validate(patch):
    if not isinstance(patch, dict) or not patch or set(patch) - EDITABLE:
        raise ValueError('Choose supported Cherry virtual profile fields.')
    for key, limit in TEXT_LIMITS.items():
        if key in patch and (not isinstance(patch[key], str) or len(patch[key]) > limit or
                             any(ord(char) < 32 for char in patch[key])):
            raise ValueError('Cherry profile text is invalid or too long.')
    if 'gamerscore' in patch and (type(patch['gamerscore']) is not int or
                                  not 0 <= patch['gamerscore'] <= 999999):
        raise ValueError('Gamerscore must be from 0 to 999999.')
    if 'avatarId' in patch and (type(patch['avatarId']) is not int or
                                not 0 <= patch['avatarId'] <= 0xFFFFFFFF):
        raise ValueError('Avatar ID is invalid.')
    if 'membership' in patch and patch['membership'] not in ('Gold', 'Silver', 'Bronze', 'Free'):
        raise ValueError('Choose a supported virtual membership.')
    if 'bypass' in patch and type(patch['bypass']) is not bool:
        raise ValueError('Virtual bypass must be on or off.')
    return patch


def load(path=PATH):
    if not path.exists():
        return dict(DEFAULT)
    if path.stat().st_size > 4096:
        raise ValueError('Cherry profile file is too large.')
    try:
        profile = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('Cherry profile file could not be read.') from error
    if not isinstance(profile, dict) or set(profile) != set(DEFAULT):
        raise ValueError('Cherry profile file has an unsupported schema.')
    fields = _validate({key: profile[key] for key in EDITABLE})
    if profile['isGold'] is not (fields['membership'] == 'Gold'):
        raise ValueError('Cherry profile membership is inconsistent.')
    return profile


def save(patch, path=PATH):
    fields = _validate(patch)
    profile = {**load(path), **fields}
    profile['isGold'] = profile['membership'] == 'Gold'
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='\n',
                                         dir=path.parent, prefix='.cherry-profile-', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(profile, stream, separators=(',', ':'))
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return profile


def dispatch(bridge, action, data):
    if action == 'cherry/status':
        if data:
            raise ValueError('Cherry status takes no options.')
        return {'enabled': bridge.cherry_local_enabled, 'scope': 'pc-local-virtual-profile'}
    if action == 'cherry/switch':
        if set(data) != {'enabled'} or type(data['enabled']) is not bool:
            raise ValueError('Choose whether the local Cherry profile API is on or off.')
        bridge.cherry_local_enabled = data['enabled']
        return {'enabled': bridge.cherry_local_enabled, 'scope': 'pc-local-virtual-profile'}
    if not bridge.cherry_local_enabled:
        raise ValueError('Enable the local Cherry profile API first.')
    if action == 'cherry/profile':
        return save(data) if data else load()
    field = action.removeprefix('cherry/profile/')
    if field not in ('gamertag', 'gamerscore', 'membership', 'motto', 'bio') or set(data) != {field}:
        raise ValueError('Choose one supported Cherry profile field.')
    return save(data)
