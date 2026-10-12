"""Writes extension.json and SHA256SUMS next to the image archive. usage: package.py <dir> <version> <image> <image-id> <archive>"""
import hashlib
import json
import sys
from pathlib import Path

out, version, image, image_id, archive = Path(sys.argv[1]), *sys.argv[2:6]
blob = (out / archive).read_bytes()
sha = hashlib.sha256(blob).hexdigest()
manifest = {'id': 'media', 'version': version, 'platform': 'linux/amd64', 'image': image, 'image_id': image_id,
            'archive': {'file': archive, 'sha256': sha, 'size': len(blob)}, 'requires': {'core_api': 1},
            'service': {'port': 9301, 'shared_data': True}, 'notes': (Path(__file__).resolve().parents[1] / 'RELEASE_NOTES.md').read_text()}
(out / 'extension.json').write_text(json.dumps(manifest, indent=2) + '\n')
(out / 'SHA256SUMS').write_text(f'{sha}  {archive}\n')
print(json.dumps({k: manifest[k] for k in ('version', 'image_id')}))
