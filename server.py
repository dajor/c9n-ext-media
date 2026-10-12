"""c9n extension "media": the tools of ffmpeg, Tesseract, poppler and qpdf behind HTTP, reachable only under /<token>/.

POST /<token>/ocr?lang=deu+eng   body: image bytes             -> {"text": "..."}
POST /<token>/exec               body: {"tool","args","cwd","timeout"} -> {"code","stdout"(base64),"stderr"}
GET  /<token>/health

`exec` runs one allowlisted tool on files in the shared data volume (/data). Absolute paths must lie inside /data,
no ".." segments, no network inputs: the service must not become a way to read the host or call other services.
"""
import base64
import hmac
import json
import os
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

TOKEN = os.environ.get('C9N_EXT_TOKEN', '')
DATA = Path(os.environ.get('C9N_MEDIA_DATA', '/data')).resolve()
TOOLS = {'ffmpeg', 'ffprobe', 'tesseract', 'pdftotext', 'pdftoppm', 'pdfinfo', 'qpdf'}
IMAGE_LIMIT = 30 * 1024 * 1024
OUTPUT_LIMIT = 8 * 1024 * 1024
SCHEME = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')  # "http://x", "tcp:host:80", "concat:a|b", "subfile:..."


def inside(path):
    try:
        Path(os.path.realpath(path)).relative_to(DATA)
        return True
    except ValueError:
        return False


def refuse(cwd, args):
    """Why this call is not allowed, or None."""
    if not inside(cwd):
        return 'Das Arbeitsverzeichnis muss im Datenordner liegen.'
    for arg in args:
        if '\x00' in arg or len(arg) > 4096:
            return 'Ungültiges Argument.'
        if arg.startswith('-') and '=' not in arg and '/' not in arg:
            continue  # a plain option such as -y, -f or -c:v
        value = arg.split('=', 1)[1] if arg.startswith('-') and '=' in arg else arg
        if '..' in Path(value).parts:
            return 'Pfade mit „..“ sind nicht erlaubt.'
        if SCHEME.match(value) and not value.startswith('file:'):
            return 'Netzwerk-Eingaben sind nicht erlaubt.'
        if value.startswith('file:'):
            value = value[5:]
        if value.startswith('/') and value != '/dev/null' and not inside(value):
            return 'Absolute Pfade müssen im Datenordner liegen.'
    return None


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def route(self):
        parts = urlsplit(self.path)
        segments = parts.path.split('/')
        if len(segments) != 3 or not TOKEN or not hmac.compare_digest(segments[1], TOKEN):
            self.reply(404, {'error': 'not found'})
            return None, None
        return segments[2], parse_qs(parts.query)

    def do_GET(self):
        name, _ = self.route()
        if name == 'health':
            self.reply(200, {'ok': True})
        elif name:
            self.reply(404, {'error': 'not found'})

    def do_POST(self):
        name, query = self.route()
        if not name:
            return
        length = int(self.headers.get('Content-Length') or 0)
        if length > IMAGE_LIMIT:
            return self.reply(413, {'error': 'Die Datei ist zu groß.'})
        body = self.rfile.read(length)
        if name == 'ocr':
            lang = (query.get('lang') or ['deu+eng'])[0]
            if not re.fullmatch(r'[a-z]{3}(\+[a-z]{3})*', lang):
                return self.reply(422, {'error': 'Ungültige Sprache.'})
            try:
                done = subprocess.run(['tesseract', 'stdin', 'stdout', '-l', lang], input=body, capture_output=True, timeout=180)
            except (OSError, subprocess.TimeoutExpired):
                return self.reply(500, {'error': 'Texterkennung nicht verfügbar.'})
            if done.returncode:
                return self.reply(422, {'error': done.stderr.decode(errors='replace')[-2000:] or 'Texterkennung fehlgeschlagen.'})
            return self.reply(200, {'text': done.stdout.decode(errors='replace')})
        if name == 'exec':
            try:
                call = json.loads(body)
                tool, args = call['tool'], call.get('args', [])
                cwd = str(Path(call.get('cwd') or DATA))
                timeout = max(1, min(int(call.get('timeout', 600)), 3600))
                if tool not in TOOLS or not isinstance(args, list) or len(args) > 400 or not all(isinstance(a, str) for a in args):
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                return self.reply(422, {'error': 'Ungültige Anfrage.'})
            why = refuse(cwd, args)
            if why:
                return self.reply(403, {'error': why})
            try:
                done = subprocess.run([tool, *args], cwd=cwd, capture_output=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                return self.reply(408, {'error': 'Zeitüberschreitung.'})
            except OSError:
                return self.reply(500, {'error': 'Das Werkzeug ist in dieser Erweiterung nicht installiert.'})
            if len(done.stdout) > OUTPUT_LIMIT:
                return self.reply(413, {'error': 'Die Ausgabe ist zu groß. In eine Datei schreiben.'})
            return self.reply(200, {'code': done.returncode, 'stdout': base64.b64encode(done.stdout).decode(), 'stderr': done.stderr.decode(errors='replace')[-20000:]})
        self.reply(404, {'error': 'not found'})

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    if not TOKEN:
        raise SystemExit('C9N_EXT_TOKEN fehlt')
    ThreadingHTTPServer(('0.0.0.0', 9301), Handler).serve_forever()
