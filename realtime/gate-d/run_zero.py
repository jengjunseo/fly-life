"""One copy-elimination trial per existing allocation; builds never overlap timings."""
import json,subprocess,sys,time
import numpy as np
from env import ROOT,WORK,REPORT,save
def call(args,label):
    with (REPORT/(label+'-console.txt')).open('w') as f:r=subprocess.run([sys.executable,*map(str,args)],stdout=f,stderr=subprocess.STDOUT)
    r.check_returncode()
if __name__=='__main__':
    history=[]
    for t,brain,prod in [(1,'6','2,4'),(2,'0,2','4,6')]:
        for scenario in ['baseline','looming']:
            print('BUILD zero',t,scenario,flush=True);call([ROOT/'realtime/gate-d/entry.py','build_consumer',t,scenario,'zero'],f'build-zero-{t}t-{scenario}')
        label=f'd1-zero-b{t}-p2';print('RUN '+label,flush=True)
        call([ROOT/'realtime/gate-d/contention.py',label,t,brain,prod,'zero'],label+'-controller')
        d=json.loads((REPORT/(label+'-decision.json')).read_text());history.append(dict(label=label,decision=d));save(REPORT/'zero-execution.json',history)
        if t==1:
            checks={}
            for scenario in ['baseline','looming']:
                a=np.loadtxt(WORK/f'd1-b1-p2-rotated-{scenario}-0/windows.txt');z=np.loadtxt(WORK/f'{label}-{scenario}-0/windows.txt')
                checks[scenario+'_all_observations_except_wall']=bool(np.array_equal(np.delete(a,3,axis=1),np.delete(z,3,axis=1)))
                for variable,dtype in [('v',np.float32),('syn',np.float32),('ref_steps',np.int32),('noise_sample',np.float32)]:
                    old=list((WORK/f'd1-b1-p2-rotated-{scenario}-0').glob('_array_neurons_'+variable+'_*'));new=list((WORK/f'{label}-{scenario}-0').glob('_array_neurons_'+variable+'_*'));assert len(old)==len(new)==1
                    checks[scenario+'_'+variable]=bool(np.array_equal(np.fromfile(old[0],dtype),np.fromfile(new[0],dtype)))
            save(REPORT/'zero-copy-correctness.json',dict(success=all(checks.values()),checks=checks,qualification='Exact same shared input, 1T copy versus row-pointer supply. All quantum counts/EMA/activity plus full final v/syn/refractory/noise_sample identical. Original allocation pointer restored before serialization/deallocation.'))
            assert all(checks.values())
        print(label,d,flush=True)
        if d['headroom']:break
    previous=json.loads((REPORT/'d1-final-decision.json').read_text());valid=previous['valid_configurations']+[x['label'] for x in history]
    def worst(label):
        d=json.loads((REPORT/(label+'-decision.json')).read_text());rs=[json.loads((REPORT/f).read_text()) for f in d['trials']]
        return max(max(r['brain_statistics']['p99_ms'],r['producer_statistics']['p99_ms']) for r in rs)
    selected=min(valid,key=worst);d=json.loads((REPORT/(selected+'-decision.json')).read_text())
    save(REPORT/'d1-final-decision.json',dict(selected_configuration=selected,headroom=d['headroom'],realtime_feasible=d['realtime_feasible'],worst_side_p99_ms=worst(selected),d2_allowed=d['realtime_feasible'],valid_configurations=valid,
        stop_reason='Concurrent feasibility confirmed; minimal D2 required' if d['realtime_feasible'] else 'No tested allocation maintains hard realtime across repeats/current workloads. D2 forbidden; stop without pipeline or 3-seed certification.'))
