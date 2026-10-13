"""PC-owned default console selection. Public console access is always read-only."""
import ipaddress
import json
import os
import tempfile
from pathlib import Path
from runtime_paths import ROOT

SETTINGS_PATH = ROOT / '.local' / 'app-settings.json'
DEFAULTS = {'default_console_ip':'','allow_writes':False}


def validate(value):
    if not isinstance(value,dict) or set(value)-set(DEFAULTS):raise ValueError('Invalid settings.')
    if value.get('allow_writes',False) is not False:raise ValueError('Free console access is always read-only.')
    address=value.get('default_console_ip','')
    if not isinstance(address,str):raise ValueError('Use a private IPv4 console address.')
    if address:
        ip=ipaddress.IPv4Address(address)
        if not ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            raise ValueError('Use a private IPv4 console address.')
    return {'default_console_ip':address,'allow_writes':False}


def load(path=SETTINGS_PATH):
    if not path.exists():return dict(DEFAULTS)
    if path.stat().st_size>4096:raise ValueError('Settings file is too large.')
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict) or value.get('schema')!=1:raise ValueError('Unsupported settings.')
    # Ignore any saved legacy write switch. It cannot enable a public write.
    return validate({'default_console_ip':value.get('default_console_ip','')})


def save(value,path=SETTINGS_PATH):
    value=validate(value)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as stream:
            temporary=Path(stream.name)
            json.dump({'schema':1,**value},stream)
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    return value
