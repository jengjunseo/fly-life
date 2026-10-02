"""Lossless, reproducible archives for new large traces; keep local originals."""
import gzip
import hashlib
import json
import argparse
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'reports/behavior'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--folders',nargs='+',default=['assays','model-controls-final','frozen-path','final-smoke'])
    args=parser.parse_args();root=args.root.resolve()
    records=[]
    for name in args.folders:
        folder=(root/name).resolve()
        if not folder.is_relative_to(root):raise ValueError('Archive folder must be inside report root')
        if any(not (p.parent/'resources.json').exists() for p in folder.rglob('brain_console.txt')):
            raise ValueError('Refusing to archive a live or unfinished trial')
        paths=[]
        for pattern in ['*.jsonl','sensory_mapping.json','engine.log','godot_console.txt','brain_console.txt']:
            paths.extend(folder.rglob(pattern))
        for path in sorted(paths):
            out=Path(str(path)+'.gz')
            original_hash=hashlib.sha256();original_bytes=0
            with path.open('rb') as original:
                for block in iter(lambda:original.read(8*1024*1024),b''):
                    original_hash.update(block);original_bytes+=len(block)
            with out.open('wb') as f:
                with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:
                    with path.open('rb') as original:shutil.copyfileobj(original,z,8*1024*1024)
            restored_hash=hashlib.sha256();restored_bytes=0
            with gzip.open(out,'rb') as restored:
                for block in iter(lambda:restored.read(8*1024*1024),b''):
                    restored_hash.update(block);restored_bytes+=len(block)
            if restored_bytes!=original_bytes or restored_hash.digest()!=original_hash.digest():raise ValueError('Archive differs from original evidence')
            records.append(dict(source=str(path.relative_to(root)).replace('\\','/'),
                archive=str(out.relative_to(root)).replace('\\','/'),sha256=original_hash.hexdigest(),
                original_bytes=original_bytes,archive_bytes=out.stat().st_size))
    report=dict(lossless_verified=True,originals_preserved_locally=True,files=records,
                original_bytes=sum(r['original_bytes'] for r in records),archive_bytes=sum(r['archive_bytes'] for r in records))
    (root/'archive-integrity.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'}))

if __name__=='__main__':main()
