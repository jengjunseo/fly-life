"""Same seed/input, full-state comparisons against unchanged production Brain."""
import json
import sys
import time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from braincore.core import Brain
from remaster.fastbrain import FastBrain

def main():
    cfg = json.loads((ROOT/'config.json').read_text())
    reference = Brain.load(ROOT/'data/runtime', cfg, seed=20260913)
    candidate = FastBrain(reference.w, cfg['model'], seed=20260913, neurons=reference.neurons)
    inputs = [None]
    for types in [['LC4','LPLC2'], ['ORN_DM1','GNG540'], ['ORN_VA1v','ORN_VA1d'],
                  ['TRN_VP2','TRN_VP3a','TRN_VP3b'], ['DNp09'], ['DNa01','DNa02']]:
        inputs.append(reference.current(reference.resolve({'types':types}), 3.))
    timings = {'reference':[], 'candidate':[]}
    mismatch = None
    fields = ['v','syn','spikes','refractory','activity','baseline']
    for step in range(1000):
        current = inputs[min(step//140, len(inputs)-1)]
        for name, brain in [('reference',reference),('candidate',candidate)]:
            start=time.perf_counter();brain.step(current)
            timings[name].append((time.perf_counter()-start)*1000)
        for field in fields:
            a,b=getattr(reference,field),getattr(candidate,field)
            if not np.array_equal(a,b):
                mismatch={'step':step+1,'field':field,'different':int(np.count_nonzero(a!=b)),
                          'max_error':float(np.max(np.abs(a-b)))}
                break
        if mismatch:break
        if reference.rng.bit_generator.state != candidate.rng.bit_generator.state:
            mismatch={'step':step+1,'field':'PCG64 state'};break
        if (step+1)%140==0:print('Compared',step+1,'full steps',flush=True)
    result={'passed':mismatch is None,'steps':step+1,'mismatch':mismatch,
            'scope':'Full float32 membrane, synaptic, spikes, refractory, activity, baseline and PCG64 state. Same actual graph, seed and currents.',
            'milliseconds_per_neural_ms':{name:{'p50':float(np.percentile(values[10:],50)),
                                              'p95':float(np.percentile(values[10:],95))}
                                         for name,values in timings.items() if len(values)>10}}
    dest=ROOT/'reports/remaster';dest.mkdir(parents=True,exist_ok=True)
    (dest/'equivalence.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
    raise SystemExit(not result['passed'])

if __name__=='__main__':main()
