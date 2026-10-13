import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
from server import normalize_directory_entries, safe_path, Bridge
from diagnostics import BridgeDiagnostic

class DirectoryEntries(unittest.TestCase):
    def test_adapter_decodes_nonbreaking_space_from_powershell_as_utf8(self):
        path='Hdd:\\Screenshot 2025-10-11 at 3.38.24\u00a0PM.pdf'
        b=Bridge('unused');b.target='ConsoleA'
        b.platform_supported=True
        response=SimpleNamespace(stdout=json.dumps({'files':[{'name':path,'directory':False,'size':3}]},ensure_ascii=False).encode('utf-8'),stderr=b'',returncode=0)
        with patch('server.subprocess.run',return_value=response) as run:
            result=b._adapter('browse',path='Hdd:\\')
        self.assertEqual(result['files'][0]['name'],path)
        self.assertIsInstance(run.call_args.kwargs['input'],bytes)
        self.assertNotIn('text',run.call_args.kwargs)

    def test_adapter_rejects_invalid_output_bytes_without_thread_decode_error(self):
        b=Bridge('unused');b.target='ConsoleA';b.platform_supported=True
        response=SimpleNamespace(stdout=b'{"files":[{"name":"bad\xff.pdf"}]}',stderr=b'',returncode=0)
        with patch('server.subprocess.run',return_value=response):
            with self.assertRaises(BridgeDiagnostic) as error:b._adapter('browse',path='Hdd:\\')
        self.assertEqual(error.exception.code,'ADAPTER_RESPONSE_INVALID')

    def test_download_path_accepts_spaces_and_multiple_dots(self):
        path='Hdd:\\Screenshot 2025-10-11 at 3.38.24 PM.pdf'
        self.assertEqual(safe_path(path,['Hdd:\\']),path)

    def test_full_sdk_paths_and_leaf_names(self):
        raw=[{'name':'Hdd:\\Games\\Halo','directory':True},
             {'name':'hdd:\\games\\default.xex','size':512},
             {'name':'notes.txt','size':12},
             {'name':'Hdd:\\Games\\Other\\','directory':True}]
        result=normalize_directory_entries(raw,'Hdd:\\Games\\')
        self.assertEqual([x['name'] for x in result['files']],['Halo','default.xex','notes.txt','Other'])
        self.assertEqual(result['listing']['rejected'],0)

    def test_do_not_flatten_traversal_other_roots_or_nested_paths(self):
        names=['Usb0:\\Games\\wrong.xex','Hdd:\\GamesExtra\\wrong.xex','Hdd:\\Games\\nested\\wrong.xex',
               'Hdd:\\Games\\..\\wrong.xex','..','bad\nname','Hdd:\\Games\\','bad:name','bad"name']
        raw=[{'name':name} for name in names]+[{'name':'good.xex','size':1}]
        result=normalize_directory_entries(raw,'Hdd:\\Games')
        self.assertEqual([x['name'] for x in result['files']],['good.xex'])
        self.assertEqual(result['listing']['rejected'],len(names))

    def test_empty_and_invalid_are_different(self):
        self.assertEqual(normalize_directory_entries([],'Hdd:\\')['files'],[])
        for raw in (None,{},[None],[{'name':'Usb0:\\other.xex'}]):
            with self.assertRaises(BridgeDiagnostic) as error:normalize_directory_entries(raw,'Hdd:\\')
            self.assertEqual(error.exception.code,'STORAGE_LIST_INVALID')

    def test_bridge_browse_normalizes_real_adapter_shape(self):
        b=Bridge('unused');b.target='';b.drives=['Hdd:\\']
        b.adapter=lambda action,**kwargs: {'files':[{'name':'Hdd:\\Games','directory':True,'size':0}]}
        self.assertEqual(b.dispatch('browse',{'path':'Hdd:\\'})['files'],[{'name':'Games','directory':True,'size':0}])

    def test_batch_browse_validates_paths_and_keeps_individual_failure(self):
        b=Bridge('unused');b.target='ConsoleA';b.drives=['Hdd:\\']
        calls=[]
        def adapter(action,**kwargs):
            calls.append((action,kwargs))
            return {'listings':[{'files':[{'name':'Hdd:\\Games\\default.xex','size':10}]},
                                {'error':True}]}
        b.adapter=adapter
        result=b.dispatch('browse-many',{'paths':['Hdd:\\Games\\','Hdd:\\Missing\\']})
        self.assertEqual(result['listings'][0]['files'][0]['name'],'default.xex')
        self.assertEqual(result['listings'][1],{'error':True})
        for paths in ([],['Usb0:\\'],['Hdd:\\']*9):
            with self.assertRaises(ValueError):b.dispatch('browse-many',{'paths':paths})
        self.assertEqual(len(calls),1)

