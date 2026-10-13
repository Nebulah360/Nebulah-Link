"""Proof that public routes cannot dispatch a console write."""
import ast
import http.client
import json
from pathlib import Path
import re
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bridge'))
import access_policy
import app_settings
import server
from browser_sessions import BrowserSessions

BLOCKED = ('launch','console/power','console/notify','controller/pulse','plugins/load',
           'plugins/unload','console/launch-ini-switch','console/launch-ini/plugins/save',
           'rte/status','rte/read','rte/poke-apply','transfer/start','transfer/finish',
           'transfer/mkdir','stream360/start','settings/admin','unknown/write')


class ReadOnlyTests(unittest.TestCase):
    def test_public_bridge_rejects_all_paid_and_unknown_actions_before_adapter(self):
        bridge=server.Bridge('powershell')
        with patch.object(bridge,'_adapter') as adapter:
            for action in BLOCKED:
                with self.subTest(action=action),self.assertRaises(ValueError):
                    bridge.dispatch(action,{'direction':'upload','confirmed':True})
            adapter.assert_not_called()

    def test_both_adapter_entrypoints_reject_mutations_before_process_launch(self):
        bridge=server.Bridge('powershell')
        with patch('server.subprocess.run') as run:
            for method in (bridge.adapter,bridge._adapter):
                for action in ('upload-file','upload-empty','rename-transfer','delete-file',
                               'create-directory','launch','power','notify','component-load','plugin-load','custom'):
                    with self.subTest(method=method.__name__,action=action),self.assertRaises(ValueError):method(action)
            run.assert_not_called()

    def test_legacy_settings_cannot_enable_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json'
            path.write_text(json.dumps({'schema':1,'default_console_ip':'192.168.1.20','allow_writes':True}))
            self.assertFalse(app_settings.load(path)['allow_writes'])
            with self.assertRaises(ValueError):app_settings.save({'allow_writes':True},path)

    def test_connect_and_status_never_send_notification_or_cleanup(self):
        bridge=server.Bridge('powershell')
        reply={'resolved_target':'192.168.1.20','drives':['USB0:'],
               'storage':{'state':'OK','source':'xdevkit'},'adapter_version':10,
               'current_title':{'title_id':'415607E6','executable':'USB0:\\Game\\default.xex'},
               'plugin_support':{'observed':['jrpc2.xex'],'jrpc':'responding'}}
        with patch.object(bridge,'_adapter',return_value=reply) as adapter:
            self.assertTrue(bridge.dispatch('connect',{})['read_only'])
            self.assertTrue(bridge.dispatch('status',{})['read_only'])
            self.assertEqual([c.args[0] for c in adapter.call_args_list],['status','status'])

    def test_http_rejects_direct_requests_even_with_admin_attribute(self):
        endpoint=server.HTTPServer(('127.0.0.1',0),server.Handler)
        port=endpoint.server_address[1]
        endpoint.allowed_hosts={f'127.0.0.1:{port}'}
        endpoint.token='test-token';endpoint.browser_sessions=BrowserSessions()
        endpoint.bridge=server.Bridge('powershell');endpoint.admin_control=True
        thread=threading.Thread(target=endpoint.serve_forever,daemon=True);thread.start()
        try:
            with patch.object(endpoint.bridge,'dispatch') as dispatch:
                for action in BLOCKED:
                    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
                    connection.request('POST','/api/'+action,body='{}',headers={
                        'Host':f'127.0.0.1:{port}','Origin':f'http://127.0.0.1:{port}',
                        'Content-Type':'application/json','Authorization':'Bearer test-token'})
                    response=connection.getresponse();response.read()
                    self.assertEqual(response.status,403,action);connection.close()
                dispatch.assert_not_called()
        finally:endpoint.shutdown();thread.join();endpoint.server_close()

    def test_public_manifest_and_adapter_have_no_paid_implementations(self):
        for path in ROOT.rglob('*'):
            if path.is_file():self.assertNotIn(path.name,('rte.py','rte.js','plugin_adapter.py','module_runtime.ps1','upload_checkpoint.py','controller.js'))
        ps=(ROOT/'bridge/neighborhood.ps1').read_text()
        cases=set(re.findall(r"^    '([^']+)' \{",ps,re.M))
        self.assertEqual(cases,set(access_policy.ADAPTER_ACTIONS))
        self.assertLess(ps.index('Read-only adapter operation required'),ps.index('New-Object -ComObject'))
        cs=(ROOT/'bridge/ComDispatch.cs').read_text()
        for name in ('SendFile','DeleteFile','RenameFile','Reboot'):
            self.assertNotRegex(cs,r'\bvoid\s+'+name+r'\s*\(')
        for file in (ROOT/'bridge').glob('*.py'):
            tree=ast.parse(file.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='adapter' and node.args:
                    self.assertIsInstance(node.args[0],ast.Constant)
                    self.assertIn(node.args[0].value,access_policy.ADAPTER_ACTIONS)

    def test_existing_inspection_and_workspace_imports(self):
        from companion import Workspace
        with tempfile.TemporaryDirectory() as folder:
            store=Workspace(Path(folder)/'companion.sqlite3')
            store.profile_save({'name':'Living room','target':'192.168.1.20'})
            self.assertEqual(store.profiles()[0]['name'],'Living room')


if __name__=='__main__':unittest.main()
