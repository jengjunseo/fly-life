"""Diagnose propagation, never manufacture an actuator command or target policy."""
import argparse
import json
import time
from pathlib import Path
import numpy as np
from scipy import sparse
from braincore.core import Brain
from remaster.fastbrain import FastBrain
from behavior.conductance import ConductanceBrain
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='reports/behavior/probe-normalized.json')
    p.add_argument('--counts',action='store_true');p.add_argument('--calibrate',action='store_true');p.add_argument('--unpruned',action='store_true');p.add_argument('--conductance',action='store_true');p.add_argument('--walk',action='store_true');p.add_argument('--grid',action='store_true');a=p.parse_args()
    cfg=json.loads((ROOT/'config.json').read_text());original=Brain.load(ROOT/'data/runtime',cfg)
    cells=original.neurons
    groups={name:original.resolve({'types':types}) for name,types in {
        'odor':['ORN_DM1','ORN_VA2'] if a.grid else ['ORN_DM1'],'heat':['TRN_VP2'],'loom':['LC4','LPLC2'],
        'DNp09':['DNp09'],'DNa01':['DNa01'],'DNa02':['DNa02'],
        'GF':['DNp01'],'MBON32':['MBON32']}.items()}
    for name,idx in list(groups.items()):
        side=cells.iloc[idx].somaSide.fillna(cells.iloc[idx].rootSide)
        for s in ['L','R']:groups[name+'_'+s]=idx[side.eq(s).to_numpy()]
    counts=sparse.load_npz(ROOT/('data/behavior/counts.npz' if a.unpruned else 'data/runtime/counts.npz'))
    signs=cells.consensus_nt.map(cfg['sign_policy']['signs']).fillna(0).to_numpy(np.float32)
    base=counts.astype(np.float32).multiply(signs[None,:]).tocsr() if a.counts else original.w
    topology={target:{source:dict(contacts=int(counts[groups[target],:][:,groups[source]].sum()),
        normalized_weight=float(original.w[groups[target],:][:,groups[source]].sum()))
        for source in ['odor','heat','loom']} for target in ['DNp09','DNa01','DNa02','GF','MBON32']}
    cases=[(2.,.65),(8.,.65),(16.,.65),(8.,1.),(16.,1.)] if not a.counts else [(.002,.65),(.006,.65),(.015,.65),(.0392857,0.)]
    if a.calibrate:cases=[(.006,1.05),(.015,.95),(.0392857,0.),(.0392857,.95),(.0392857,1.05)]
    if a.conductance:cases=[(.0005,.95),(.002,.95),(.006,.95),(.002,1.05),(.006,1.05)]
    if a.walk:cases=[(g,b) for g in [.0001,.0003,.001,.002] for b in [1.2,1.5]]
    if a.grid:cases=[(g,b) for g in [.001,.002,.004,.006] for b in [.95,1.05,1.2,1.5]]
    results=[];out=ROOT/a.out;out.parent.mkdir(parents=True,exist_ok=True)
    for gain,baseline in cases:
        for stimulus in ['control','odor_L','odor_R','heat_L','heat_R','loom_L']:
            params=dict(cfg['model'],recurrent_gain=gain,baseline_current=baseline)
            if a.calibrate:params.update(baseline_heterogeneity=0.,noise_std=0.)
            b=(ConductanceBrain if a.conductance else FastBrain)(base,params,seed=20260913,neurons=cells)
            external=None if stimulus=='control' else b.current(groups[stimulus],3.)
            sums={name:0 for name in groups};population=0;begin=time.perf_counter()
            for step in range(600):
                spikes=b.step(external if step>=300 else None)
                if a.calibrate and not a.conductance:b.syn[spikes!=0]=0.
                if step>=400:
                    population+=spikes.sum()
                    for name,idx in groups.items():sums[name]+=int(spikes[idx].sum())
            row=dict(gain=gain,baseline=baseline,stimulus=stimulus,
                     population_hz=float(population/b.n/.2),
                     rates_hz={name:float(total/len(groups[name])/.2) if len(groups[name]) else None for name,total in sums.items()},
                     voltage={name:float(b.v[idx].mean()) if len(idx) else None for name,idx in groups.items()},
                     wall_s=time.perf_counter()-begin)
            results.append(row);out.write_text(json.dumps(dict(topology=topology,results=results),indent=2),encoding='utf-8')
            print(json.dumps({k:row[k] for k in ['gain','baseline','stimulus','rates_hz']}),flush=True)

if __name__=='__main__':main()
