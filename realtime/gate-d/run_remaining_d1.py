import json,subprocess,sys,time
from env import ROOT,REPORT,save
if __name__=='__main__':
    save(REPORT/'d1-excluded.json',dict(excluded_configuration='d1-b2-p2',reason='Controller was launched before all builds completed; possible compiler contention. Retain raw records but exclude this entire exploratory run, repeat fixed same allocation with no compiler.'))
    history=[]
    for label,t,brain,prod in [('d1-b2-p2-clean',2,'0,2','4,6'),('d1-b1-p2-rotated',1,'6','2,4')]:
        start=time.perf_counter();print('START '+label,flush=True)
        with (REPORT/(label+'-controller-console.txt')).open('w') as f:r=subprocess.run([sys.executable,str(ROOT/'realtime/gate-d/contention.py'),label,str(t),brain,prod],stdout=f,stderr=subprocess.STDOUT)
        r.check_returncode();d=json.loads((REPORT/(label+'-decision.json')).read_text());history.append(dict(label=label,wall_seconds=time.perf_counter()-start,decision=d));save(REPORT/'d1-execution.json',history)
        print(label,d,flush=True)
        if d['headroom']:break
    valid=['d1-b1-p2']+[x['label'] for x in history]
    def worst(label):
        d=json.loads((REPORT/(label+'-decision.json')).read_text());records=[json.loads((REPORT/f).read_text()) for f in d['trials']]
        return max(max(r['brain_statistics']['p99_ms'],r['producer_statistics']['p99_ms']) for r in records)
    selected=min(valid,key=worst);d=json.loads((REPORT/(selected+'-decision.json')).read_text())
    save(REPORT/'d1-final-decision.json',dict(selected_configuration=selected,headroom=d['headroom'],realtime_feasible=d['realtime_feasible'],worst_side_p99_ms=worst(selected),d2_allowed=d['realtime_feasible'],valid_configurations=valid,
        stop_reason='Concurrent feasibility confirmed; minimal D2 needed' if d['realtime_feasible'] else 'No tested allocation maintains hard realtime in every repeat/workload; D2 forbidden.'))
