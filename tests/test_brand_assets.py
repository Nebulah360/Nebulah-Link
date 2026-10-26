"""The real bridge serves approved branding bytes without opening arbitrary paths."""
import http.client
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from server import Handler


class BrandAssetsTest(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.host = '127.0.0.1:' + str(self.server.server_port)
        self.server.allowed_hosts = {self.host}
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, path, host=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request('GET', path, headers={'Host': host or self.host})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_brand_assets_match_supplied_bytes_and_remain_same_origin(self):
        for name in ('logo-horizontal-dark.svg', 'logo-dark.svg', 'favicon.svg', 'favicon.ico', 'apple-touch-icon.png', 'icon-192.png'):
            with self.subTest(name=name):
                status, headers, body = self.request('/brand/' + name)
                self.assertEqual(status, 200)
                self.assertEqual(body, (ROOT / 'dist/brand' / name).read_bytes())
                self.assertIn("default-src 'self'", headers['Content-Security-Policy'])
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(self.request('/brand/favicon.svg', host='untrusted.example')[0], 403)

    def test_brand_prefix_does_not_expose_arbitrary_files(self):
        for path in ('/brand/../../bridge/server.py', '/brand/../app.js', '/brand/%2e%2e/server.py', '/.local/settings.json', '/brand/unknown.svg'):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)


if __name__ == '__main__':
    unittest.main()
