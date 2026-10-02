"""Diagnostic background-rate calibration, never fitted to stimulus outcomes."""
import argparse
import json
from pathlib import Path
import numpy as np
from behavior.model import CountBrain, load_connectivity, parameters

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='reports/behavior-retry/homeostasis-probe.json')
    p.add_argument('--gain',type=float,default=.002);a=p.parse_args()
    cfg=json.loads((ROOT/'config.json').read_text());w,n,evidence=load_connectivity(cfg,psi_literature=True)
    patterns=dict(odor='^ORN_(DM1|VA2)$',warm='^TRN_VP2$',cool='^TRN_VP3[ab]$',object='^LC10a$',
        a1='^DNa01$',a2='^DNa02$',p9='^DNp09$',gf='^DNp01$',mb32='^MBON32$',ppl3='^PPL103$',kc='^KC')
    groups={k:np.flatnonzero(n.type.fillna('').str.match(v).to_numpy()) for k,v in patterns.items()}
    for k,idx in list(groups.items()):
        side=n.iloc[idx].somaSide.fillna(n.iloc[idx].rootSide)
        for s in ['L','R']:groups[k+'_'+s]=idx[side.eq(s).to_numpy()]
    params=parameters(cfg);params['recurrent_gain']=a.gain
    calibration=CountBrain(w,params,seed=20260913,neurons=n)
    target=np.full(calibration.n,3.,np.float32)
    sensory=n.superclass.isin(['cb_sensory','ol_sensory','vnc_sensory']).to_numpy();target[sensory]=10.
    for key,rate in [('warm',100.),('cool',100.),('p9',40.),('a1',50.),('a2',50.),('gf',5.),('kc',.5)]:target[groups[key]]=rate
    progress=[]
    for t in range(3000):
        calibration.step()
        if t>=250:calibration.baseline+=np.float32(.0001)*(target-calibration.activity);np.clip(calibration.baseline,-5.,5.,out=calibration.baseline)
        if t%500==499:
            progress.append(dict(ms=t+1,mean_hz=float(calibration.activity.mean()),
                rates={k:float(calibration.activity[v].mean()) for k,v in groups.items() if len(v)}))
            print(json.dumps(dict(calibration_ms=t+1,mean_hz=progress[-1]['mean_hz'])),flush=True)
    initial={k:getattr(calibration,k).copy() for k in ['v','syn','spikes','activity','refractory','baseline']}
    rng_state=calibration.rng.bit_generator.state
    report=dict(evidence=evidence,gain=a.gain,calibration=progress,
        assumptions='3Hz central, 10Hz unmodeled afferents, .5Hz KC, 100Hz thermal, assumed walking DN targets. A hypothesis, not measured per-cell physiology or behavior fitting.',results=[])
    out=ROOT/a.out;out.parent.mkdir(parents=True,exist_ok=True)
    for condition in ['control','odor_L','odor_R','object_L','object_R','warm_L','warm_R']:
        b=CountBrain(w,params,seed=20260913,neurons=n)
        for k,v in initial.items():getattr(b,k)[:]=v
        b.rng.bit_generator.state=rng_state
        current=np.zeros(b.n,np.float32)
        if condition!='control':current[groups[condition]]=3.
        if condition.startswith('warm_'):current[groups['cool_'+condition[-1]]]=-1.5
        accumulated={k:0. for k in groups}
        for t in range(1500):
            b.step(current)
            if t>=500:
                for k,idx in groups.items():
                    if len(idx):accumulated[k]+=float(b.activity[idx].mean())
        rates={k:v/1000. for k,v in accumulated.items()}
        row=dict(condition=condition,rates_hz=rates)
        report['results'].append(row);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(dict(condition=condition,left_minus_right=rates['a2_L']-rates['a2_R'],forward=rates['p9'],
            mb32_L=rates['mb32_L'],mb32_R=rates['mb32_R'],ppl3_L=rates['ppl3_L'],ppl3_R=rates['ppl3_R'])),flush=True)

if __name__=='__main__':main()
