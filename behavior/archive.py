"""Lossless, reproducible archives for new large traces; keep local originals."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'reports/behavior'

def main():
    records=[]
    for name in ['assays','model-controls-final','frozen-path','final-smoke']:
        paths=[]
        for pattern in ['*.jsonl','sensory_mapping.json','engine.log','godot_console.txt','brain_console.txt']:
            paths.extend((ROOT/name).rglob(pattern))
        for path in sorted(paths):
            payload=path.read_bytes();out=Path(str(path)+'.gz')
            with out.open('wb') as f:
                with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:z.write(payload)
            restored=gzip.decompress(out.read_bytes())
            if restored!=payload:raise ValueError('Archive differs from original evidence')
            records.append(dict(source=str(path.relative_to(ROOT)).replace('\\','/'),
                archive=str(out.relative_to(ROOT)).replace('\\','/'),sha256=hashlib.sha256(payload).hexdigest(),
                original_bytes=len(payload),archive_bytes=out.stat().st_size))
    report=dict(lossless_verified=True,originals_preserved_locally=True,files=records,
                original_bytes=sum(r['original_bytes'] for r in records),archive_bytes=sum(r['archive_bytes'] for r in records))
    (ROOT/'archive-integrity.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'}))

if __name__=='__main__':main()
