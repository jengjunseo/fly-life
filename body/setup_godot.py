"""Acquire the self-contained official Godot Windows build, not a system installer."""
import hashlib
import json
import urllib.request
import urllib.parse
import zipfile
from pathlib import Path

ROOT=Path(__file__).parent
URL='https://github.com/godotengine/godot-builds/releases/download/4.6.1-stable/Godot_v4.6.1-stable_win64.exe.zip'
tools=ROOT/'tools'
tools.mkdir(parents=True,exist_ok=True)
archive=tools/'godot.zip'
if not archive.exists():
    with urllib.request.urlopen(URL,timeout=120) as response, archive.open('wb') as f:
        final_url=urllib.parse.urlsplit(response.url)._replace(query='',fragment='').geturl()
        while block:=response.read(4*1024*1024):
            f.write(block)
else:
    final_url=URL
with zipfile.ZipFile(archive) as z:
    for info in z.infolist():
        target=(tools/info.filename).resolve()
        if not target.is_relative_to(tools.resolve()):
            raise ValueError('Unsafe archive path')
    z.extractall(tools)
h=hashlib.sha256()
with archive.open('rb') as f:
    for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
report=dict(source=URL,download_url=final_url,bytes=archive.stat().st_size,sha256=h.hexdigest())
(ROOT/'reports').mkdir(exist_ok=True)
(ROOT/'reports/godot_acquisition.json').write_text(json.dumps(report,indent=2))
print(report)
