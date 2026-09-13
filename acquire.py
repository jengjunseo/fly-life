"""Download only three official public bulk files; no credentials required."""
import hashlib
import json
import time
import urllib.request
from pathlib import Path

BASE = 'https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/'
FILES = [
    'body-annotations-male-cns-v1.0-minconf-0.5.feather',
    'body-neurotransmitters-male-cns-v1.0.feather',
    'connectome-weights-male-cns-v1.0-minconf-0.5.feather',
]
# Pins measured from the official public objects on 2026-09-13, not synthetic data.
EXPECTED_SHA256 = {
    FILES[0]: '2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2',
    FILES[1]: '95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621',
    FILES[2]: 'e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1',
}

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    root = Path(__file__).parent / 'data' / 'raw'
    root.mkdir(parents=True, exist_ok=True)
    previous = {}
    if (root / 'manifest.json').exists():
        previous = {x['file']:x for x in json.loads((root / 'manifest.json').read_text())['files']}
    manifest = []
    for name in FILES:
        path = root / name
        url = BASE + name
        if not path.exists():
            partial = path.with_suffix('.partial')
            offset = partial.stat().st_size if partial.exists() else 0
            req = urllib.request.Request(url, headers={'Range': f'bytes={offset}-'})
            with urllib.request.urlopen(req, timeout=120) as response:
                append = offset > 0 and response.status == 206
                total = int(response.headers.get('Content-Length', 0)) + (offset if append else 0)
                received = offset if append else 0
                last = time.monotonic()
                with partial.open('ab' if append else 'wb') as f:
                    while block := response.read(4 * 1024 * 1024):
                        f.write(block)
                        received += len(block)
                        if time.monotonic() - last > 5:
                            print(f'{name}: {received:,}/{total:,} bytes', flush=True)
                            last = time.monotonic()
                if total and received != total:
                    raise IOError('Incomplete download')
                headers = {k: response.headers.get(k) for k in ['ETag', 'Last-Modified', 'x-goog-hash']}
            partial.replace(path)
        else:
            headers = previous.get(name, {}).get('headers', {})
        item = dict(file=name, url=url, bytes=path.stat().st_size, sha256=digest(path), headers=headers)
        if item['sha256'] != EXPECTED_SHA256[name]:
            raise IOError(f'Official object checksum changed or corrupt file: {name}; investigate before repinning')
        manifest.append(item)
        print(json.dumps(item), flush=True)
    (root / 'manifest.json').write_text(json.dumps(dict(dataset='male-cns:v1.0', files=manifest), indent=2))

if __name__ == '__main__':
    main()
