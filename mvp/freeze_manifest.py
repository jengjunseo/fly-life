"""Create/verify the exact-byte Git freeze manifest, excluding itself."""
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'reports/mvp/freeze-hashes.json'
VERIFICATION=ROOT/'reports/mvp/freeze-verification.json'

def sha_bytes(data):
    h=hashlib.sha256()
    h.update(data)
    return h.hexdigest()

def index_hashes():
    raw=subprocess.check_output(['git','ls-files','--stage','-z'],cwd=ROOT)
    entries=[]
    for record in raw.split(b'\0'):
        if not record:continue
        metadata,path=record.split(b'\t',1)
        mode,oid,stage=metadata.split()
        if stage!=b'0':raise RuntimeError('Git index contains an unresolved merge')
        entries.append((path.decode('utf-8','surrogateescape'),oid))
    proc=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    packed,stderr=proc.communicate(b''.join(oid+b'\n' for _,oid in entries))
    hashes={}
    offset=0
    for name,oid in entries:
        end=packed.find(b'\n',offset)
        header=packed[offset:end].split()
        if len(header)!=3 or header[0]!=oid or header[1]!=b'blob':
            raise RuntimeError(f'Could not read indexed blob: {name}')
        start=end+1;size=int(header[2]);stop=start+size
        if stop>=len(packed) or packed[stop:stop+1]!=b'\n':
            raise RuntimeError(f'Truncated or malformed indexed blob: {name}')
        h=hashlib.sha256();h.update(memoryview(packed)[start:stop])
        offset=stop+1
        hashes[name]=h.hexdigest()
    if proc.returncode:raise RuntimeError(stderr.decode('utf-8','replace'))
    if offset!=len(packed):raise RuntimeError('Unexpected trailing bytes from Git object reader')
    return hashes

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['create','verify']);a=p.parse_args()
    indexed=index_hashes()
    if a.mode=='create':
        exclude={'reports/mvp/freeze-hashes.json','reports/mvp/freeze-verification.json'}
        hashes={name:digest for name,digest in indexed.items() if name not in exclude}
        meta=json.loads((ROOT/'data/runtime/metadata.json').read_text())
        result=dict(version='male-cns-mvp-v0.1',timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    scope='All indexed deliverables except this manifest and its verification result. Exact bytes; Git EOL conversion disabled.',
                    dataset=meta['dataset'],files=hashes)
        MANIFEST.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(dict(files=len(hashes),manifest_sha256=sha_bytes(MANIFEST.read_bytes()))))
    else:
        data=json.loads(MANIFEST.read_text(encoding='utf-8'))
        bad=[name for name,digest in data['files'].items() if indexed.get(name)!=digest]
        result=dict(passed=not bad,files=len(data['files']),mismatches=bad,
                    manifest_sha256=indexed['reports/mvp/freeze-hashes.json'])
        VERIFICATION.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result));raise SystemExit(bool(bad))
if __name__=='__main__':main()
