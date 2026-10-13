"""Synthetic read-only console fixtures; no console-write adapter exists."""
import struct
import tempfile
from pathlib import Path
from companion import Companion
from server import Bridge, validate_xex

def game_fixture():
    data=bytearray(600);data[:4]=b'XEX2'
    struct.pack_into('>5I',data,4,1,512,0,64,1)
    struct.pack_into('>2I',data,24,0x00040006,32)
    struct.pack_into('>4I4BI',data,32,0x12345678,1,1,0x415608C3,2,0,1,1,0)
    struct.pack_into('>I',data,64,0x180)
    return bytes(data)

class Console(Bridge):
    def __init__(self):
        super().__init__('unused');self.target='test-console';self.drives=['Test:\\']
        self.files={'Test:\\unknown.xex':game_fixture()};self.calls=[]
        self.test_workspace=tempfile.TemporaryDirectory()
        self.companion=Companion(self,Path(self.test_workspace.name)/'companion.sqlite3')

    def adapter(self,action,**kwargs):
        self.calls.append(action)
        if action=='receive':Path(kwargs['local']).write_bytes(self.files[kwargs['path']]);return {}
        if action=='status':return {'drives':self.drives}
        raise AssertionError('Unexpected console operation: '+action)

class Fake(Console):
    def __init__(self):
        super().__init__();self.target='demo'
