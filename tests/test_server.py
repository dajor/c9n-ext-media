import base64, json, os, subprocess, sys, tempfile, threading, unittest
import urllib.request, urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = tempfile.mkdtemp()
os.environ.update(C9N_EXT_TOKEN='tok', C9N_MEDIA_DATA=DATA)
sys.path.insert(0, str(ROOT))
import server  # noqa: E402


class Refusals(unittest.TestCase):
    def test_what_is_allowed(self):
        for args in (['-y', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', f'{DATA}/out.wav'], ['-i', 'in.mp4', '-vf', 'scale=640:-1', '-c:v', 'libx264', 'out.mp4'],
                     ['-map', '0:v', '-ss', '00:00:10', 'x.png'], ['-i', 'file:in.mp4', '/dev/null'], ['-l', 'deu+eng'], ['--check', f'{DATA}/a.pdf'],
                     ['-metadata', 'title=Hallo: Welt', 'o.mp4']):
            self.assertIsNone(server.refuse(DATA, args), args)

    def test_what_is_not(self):
        for args in (['-i', '/etc/passwd'], ['-i', 'http://intranet/x.mp4'], ['-i', 'concat:a|b'], ['-i', '../secret'], ['-i', 'a/../../b'],
                     ['-o=/etc/shadow'], ['-i', 'tcp:host:80'], ['-i', f'{DATA}/../x'], ['x\x00y']):
            self.assertIsNotNone(server.refuse(DATA, args), args)
        self.assertIsNotNone(server.refuse('/etc', ['-y']))
        link = Path(DATA) / 'link'
        if not link.exists():
            link.symlink_to('/etc')
        self.assertIsNotNone(server.refuse(DATA, ['-i', f'{DATA}/link/passwd']))


class Service(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def call(self, path, body=None):
        request = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', data=body, method='POST' if body is not None else 'GET')
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_wrong_or_missing_token_finds_nothing(self):
        for path in ('/wrong/health', '/health', '/tok/other/health', '/tok2/health'):
            self.assertEqual(self.call(path)[0], 404, path)
        self.assertEqual(self.call('/tok/health')[0], 200)

    def test_unknown_tool_and_bad_json_are_refused(self):
        self.assertEqual(self.call('/tok/exec', json.dumps({'tool': 'bash', 'args': ['-c', 'id']}).encode())[0], 422)
        self.assertEqual(self.call('/tok/exec', b'not json')[0], 422)
        self.assertEqual(self.call('/tok/exec', json.dumps({'tool': 'ffmpeg', 'args': ['-i', '/etc/passwd']}).encode())[0], 403)

    def test_an_allowed_tool_runs_in_the_data_folder(self):
        status, result = self.call('/tok/exec', json.dumps({'tool': 'qpdf', 'args': ['--version']}).encode())
        if status == 200:
            self.assertEqual(result['code'], 0)
            self.assertIn(b'qpdf', base64.b64decode(result['stdout']).lower())
        else:
            self.skipTest('qpdf nicht installiert (läuft im Container-Test)')


if __name__ == '__main__':
    unittest.main()
