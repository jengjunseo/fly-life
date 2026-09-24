"""Bounded sensory-range scout; never changes LIF, matrix or decoder gains."""
import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from braincore import Brain
from braincore.evidence import save

if __name__=='__main__':
    b=Brain.load(ROOT/'data/runtime',json.loads((ROOT/'config.json').read_text()));b.warmup(500)
    target=b.resolve(dict(types=['DNa01','DNa02','DNp09','DNp01']));out=[]
    for types in [['LC4','LPLC2'],['LC4','LPLC2','LC9']]:
        sensor=b.resolve(dict(types=types))
        for amp in [0.,3.,6.,10.]:
            r=copy.deepcopy(b);current=r.current(sensor,amp);counts=np.zeros(len(target));peak=np.zeros(len(target));sens=pop=0
            for k in range(1500):
                spikes=r.step(current if k<1000 else None)
                if k<1000:
                    counts+=spikes[target];peak=np.maximum(peak,r.activity[target]);sens+=spikes[sensor].sum();pop+=spikes.sum()
            row=dict(types=types,amp=amp,targets=json.loads(r.neurons.iloc[target][['bodyId','type','somaSide']].to_json(orient='records')),
                spikes=counts.tolist(),peak_hz=peak.tolist(),sensor_hz=float(sens/len(sensor)),population_hz=float(pop/r.n),
                recovery_hz=r.activity[target].tolist(),finite=bool(np.isfinite(r.v).all()))
            out.append(row);print(json.dumps(row),flush=True)
    save(ROOT/'reports/ecology/research/calibration-rerun.json',out)
