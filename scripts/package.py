"""Writes extension.json and SHA256SUMS next to the image archive. usage: package.py <dir> <version> <image> <image-id> <archive>"""
import hashlib
import json
import re
import sys
import tarfile
from pathlib import Path

out, version, image, docker_id, archive = Path(sys.argv[1]), *sys.argv[2:6]


def archive_ids(path):
    """The identities inside a docker save archive: config digest (classic image store) and index digest (containerd store)."""
    config = index = None
    with tarfile.open(path, 'r|gz') as tar:
        for member in tar:
            if member.name == 'manifest.json':
                config = 'sha256:' + re.search(r'([0-9a-f]{64})', json.loads(tar.extractfile(member).read())[0]['Config'])[1]
            elif member.name == 'index.json':
                index = json.loads(tar.extractfile(member).read())['manifests'][0]['digest']
    return config, index


# c9n checks a loaded image against the identities in the archive; the release names the config digest, which every Docker can check.
image_id, index_id = archive_ids(out / archive)
assert docker_id in (image_id, index_id), 'Die Image-Kennung von Docker steht nicht im Archiv'
blob = (out / archive).read_bytes()
sha = hashlib.sha256(blob).hexdigest()
manifest = {'id': 'media', 'version': version, 'platform': 'linux/amd64', 'image': image, 'image_id': image_id,
            'image_index_id': index_id, 'archive': {'file': archive, 'sha256': sha, 'size': len(blob)}, 'requires': {'core_api': 1},
            'service': {'port': 9301, 'shared_data': True}, 'notes': (Path(__file__).resolve().parents[1] / 'RELEASE_NOTES.md').read_text()}
(out / 'extension.json').write_text(json.dumps(manifest, indent=2) + '\n')
(out / 'SHA256SUMS').write_text(f'{sha}  {archive}\n')
print(json.dumps({k: manifest[k] for k in ('version', 'image_id')}))
