"""Install the pinned official Godot archive without rewriting historical evidence."""
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    evidence=json.loads((ROOT/'body/reports/godot_acquisition.json').read_text())
    folder=ROOT/'body/tools';folder.mkdir(exist_ok=True)
    archive=folder/'godot.zip'
    if not archive.exists():
        partial=folder/'godot.zip.partial'
        with urllib.request.urlopen(evidence['source'],timeout=120) as response,partial.open('wb') as f:
            while block:=response.read(4*1024*1024):f.write(block)
        if sha(partial)!=evidence['sha256']:raise ValueError('Official archive checksum mismatch; not installed')
        partial.replace(archive)
    if sha(archive)!=evidence['sha256']:raise ValueError('Archive checksum mismatch; not installed')
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if not (folder/item.filename).resolve().is_relative_to(folder.resolve()):raise ValueError('Unsafe archive member')
        z.extractall(folder)
    print('Pinned Godot ready: '+str(folder/'Godot_v4.6.1-stable_win64.exe'))
if __name__=='__main__':main()
