"""Snapshot historical evidence before development; verify without rewriting it."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'reports/mvp'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

def historical():
    for folder in ('braincore','tests','body','ecology','realtime','reports','data/runtime'):
        for p in (ROOT/folder).rglob('*'):
            if not p.is_file(): continue
            rel=p.relative_to(ROOT)
            if any(x in rel.parts for x in ('__pycache__','.godot','tools','logs','mvp')):continue
            yield p
    yield ROOT/'config.json'

if __name__=='__main__':
    DEST.mkdir(exist_ok=True)
    path=DEST/'historical-before.json'
    if sys.argv[1]=='before':
        with path.open('x',encoding='utf-8') as f:
            json.dump({p.relative_to(ROOT).as_posix():sha(p) for p in historical()},f,indent=2)
    else:
        original=json.loads(path.read_text())
        changed=[name for name,digest in original.items() if not (ROOT/name).exists() or sha(ROOT/name)!=digest]
        result=dict(count=len(original),changed=changed,passed=not changed)
        (DEST/'historical-after.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result));sys.exit(bool(changed))
