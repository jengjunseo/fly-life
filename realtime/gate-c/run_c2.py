"""Serial CPU experiments. Stops immediately at native p99<=50; no producer."""
import json,subprocess,sys,time
from env import ROOT,REPORT,save
history=[]
def run(script,args,experimental=False):
    command=[sys.executable,str(ROOT/'realtime/gate-c/entry.py'),script,*map(str,args)] if experimental else [sys.executable,str(ROOT/'realtime/gate-c'/f'{script}.py'),*map(str,args)]
    label=script+'-'+str(args[0]);print('START '+label,flush=True);begin=time.perf_counter()
    with (REPORT/(label+'-console.txt')).open('w',encoding='utf-8') as f:result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,cwd=ROOT)
    history.append(dict(label=label,wall_seconds=time.perf_counter()-begin,returncode=result.returncode));save(REPORT/'c2-execution.json',history)
    print('FINISH '+label+' '+str(result.returncode),flush=True);result.check_returncode()
if __name__=='__main__':
    assert json.loads((REPORT/'c0-audit.json').read_text())['success'] and (REPORT/'rng-1t.json').exists()
    for t in [2,4,8]:run('rng_bench',[t])
    candidate=None
    for t in [1,2,4,8]:
        name=f'c2-native-{t}t';run('full',[name,t,400,'baseline','native'],True)
        d=json.loads((REPORT/(name+'.json')).read_text())
        if d['statistics']['p99_ms']<=50:
            candidate=name;print('HARD STOP C2: '+name,flush=True);break
    save(REPORT/'c2-decision.json',dict(candidate=candidate,c3_allowed=candidate is None,c4_implemented=False,stop_reason='Native p99<=50; C3/C4 forbidden, proceed multi-seed' if candidate else 'Native OpenMP unsuccessful; proceed C3 feasibility only'))
