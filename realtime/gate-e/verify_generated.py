"""Verify all delivered Gate D generated source/executables, no builds/writes."""
import json
from pathlib import Path
from env import ROOT, REPORT, sha, save

if __name__=='__main__':
    checked=0;changes=[]
    for p in (ROOT/'reports/realtime/gate-d').glob('d1-build-*.json'):
        meta=json.loads(p.read_text());exe=Path(meta['executable']);checked+=1
        if sha(exe)!=meta['executable_sha256']:changes.append(str(exe))
        for name,digest in meta['source_sha256'].items():
            source=exe.parent/name;checked+=1
            if sha(source)!=digest:changes.append(str(source))
    normal=ROOT.parents[1]/'work/brian2-gate-d/d1-1t-baseline-cpp/make.deps'
    repaired=ROOT.parents[1]/'work/brian2-gate-d/d1-1t-looming-cpp/make.deps'
    same=ROOT.parents[1]/'work/brian2-gate-e/current-1t-looming-p0-2s-q50-cpp/make.deps'
    assert sha(normal)==sha(repaired)==sha(same)
    d=dict(success=not changes,checked_generated_source_and_executables=checked,changed=changes,
        cache_incident='Initial make-n-B audit attempted included make.deps regeneration; missing compiler PATH left one generated work dependency cache empty. No compile succeeded. Cache restored by exact byte copy from normal identical1T dependency graph; corrected audit only reads old makefile.',
        dependency_cache_sha256=sha(repaired),baseline1t_and_current_E1t_dependency_graph_exact_match=True,
        qualification='Generated dependency cache is not neural source, executable, result, or verified scientific data. Original pre-incident cache SHA was not captured; restored dependency graph matches two normal same-layout builds, not a claimed original pre-incident byte audit.')
    save(REPORT/'gate-d-generated-integrity.json',d);print(json.dumps(d,indent=2));assert d['success']
