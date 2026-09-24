"""Sequential actual target runs; no concurrent brain workloads or extra optimizations."""
import json
import subprocess
import sys
import time
from env import ROOT,REPORT,save

if __name__=='__main__':
    assert json.loads((REPORT/'b0-equivalence.json').read_text())['success']
    assert (REPORT/'b0-performance.json').is_file()
    steps=[('candidate',n) for n in ['baseline','looming','real_predator','compound']]+[('reference','b2'),('candidate','b2')]
    history=[]
    for script,name in steps:
        filename='reference.py' if script=='reference' else 'entry.py'
        args=[sys.executable,str(ROOT/'realtime/gate-b'/filename)]+([name] if script=='reference' else ['candidate',name])
        start=time.perf_counter();print('START '+script+' '+name,flush=True)
        log=REPORT/(script+'-'+name+'-console.txt')
        with log.open('w',encoding='utf-8') as f:
            result=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,cwd=ROOT.parents[1])
        history.append(dict(script=script,name=name,wall_seconds=time.perf_counter()-start,exit_code=result.returncode))
        save(REPORT/'execution-progress.json',history)
        print('FINISH '+script+' '+name+' '+str(result.returncode),flush=True)
        if result.returncode:raise SystemExit(result.returncode)
