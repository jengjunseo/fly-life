import json,subprocess,sys
from env import ROOT,REPORT,save
if __name__=='__main__':
    selected=None
    for w in [1,2,3,4]:
        path=REPORT/f'd0-{w}w.json'
        if not path.exists():
            with (REPORT/f'd0-{w}w-console.txt').open('w') as f:r=subprocess.run([sys.executable,str(ROOT/'realtime/gate-d/generate_bench.py'),'parallel',str(w)],stdout=f,stderr=subprocess.STDOUT)
            r.check_returncode()
        d=json.loads(path.read_text());print(w,d['statistics'],flush=True)
        if d['statistics']['p99_ms']<=35:selected=w;break
    save(REPORT/'d0-decision.json',dict(selected_workers=selected,additional_worker_search_stopped=selected is not None))
