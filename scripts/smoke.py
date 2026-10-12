"""Proof against the running container, with a data folder shared like in c9n:
OCR of a real image, ffmpeg writing a file into the data folder, ffprobe reading it, and refusals.
usage: smoke.py <host:port> <token> <data-dir>     (needs pillow)"""
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

address, token, data = sys.argv[1], sys.argv[2], Path(sys.argv[3])


def call(route, body, method='POST'):
    request = urllib.request.Request(f'http://{address}/{token}/{route}', data=body, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def run(tool, *args):
    status, result = call('exec', json.dumps({'tool': tool, 'args': list(args)}).encode())
    assert status == 200, (tool, status, result)
    return result['code'], base64.b64decode(result['stdout']).decode(errors='replace'), result['stderr']


# 1. OCR of a real picture
image = Image.new('RGB', (900, 160), 'white')
draw = ImageDraw.Draw(image)
try:
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 72)
except OSError:
    font = ImageFont.load_default(size=72)
draw.text((20, 30), 'c9n media 2026', fill='black', font=font)
image.save(data / 'ocr.png')
status, result = call('ocr?lang=deu%2Beng&psm=11', (data / 'ocr.png').read_bytes())
assert status == 200 and 'media' in result['text'].lower() and '2026' in result['text'], (status, result)

# 2. ffmpeg writes a file into the shared folder, ffprobe reads it
code, _, err = run('ffmpeg', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', '/data/tone.wav')
assert code == 0 and (data / 'tone.wav').stat().st_size > 1000, err
code, out, err = run('ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', '/data/tone.wav')
assert code == 0 and 0.9 < float(out.strip()) < 1.2, (out, err)

# 3. poppler and qpdf on a real PDF
image.save(data / 'doc.pdf')
assert run('pdfinfo', '/data/doc.pdf')[0] == 0
assert run('qpdf', '--check', '/data/doc.pdf')[0] == 0

# 4. refusals: outside the data folder, network input, unknown tool, wrong token
for body in ({'tool': 'ffmpeg', 'args': ['-i', '/etc/passwd', '/data/x.wav']}, {'tool': 'ffmpeg', 'args': ['-i', 'http://127.0.0.1:9301/x']},
             {'tool': 'ffmpeg', 'args': ['-i', '../etc/passwd']}):
    assert call('exec', json.dumps(body).encode())[0] == 403, body
assert call('exec', json.dumps({'tool': 'bash', 'args': ['-c', 'id']}).encode())[0] == 422
request = urllib.request.Request(f'http://{address}/wrong-{token}/health')
try:
    urllib.request.urlopen(request, timeout=10)
    raise SystemExit('ohne richtiges Token darf nichts antworten')
except urllib.error.HTTPError as error:
    assert error.code == 404
print('OK: OCR, ffmpeg/ffprobe, poppler/qpdf und die Ablehnungen funktionieren über den Dienst')
