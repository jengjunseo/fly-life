"""Test transmitter efficacy hypotheses without changing identities or signs."""
import json
from pathlib import Path
import numpy as np
from scipy import sparse
from braincore.core import Brain
from behavior.model import CountBrain,parameters

ROOT=Path(__file__).resolve().parents[1]

def main():
    cfg=json.loads((ROOT/'config.json').read_text());reference=Brain.load(ROOT/'data/runtime',cfg)
    n=reference.neurons;counts=sparse.load_npz(ROOT/'data/runtime/counts.npz').astype(np.float32)
    nt=n.consensus_nt;sign=nt.map(cfg['sign_policy']['signs']).fillna(0).to_numpy(np.float32)
    groups={k:reference.resolve(dict(types=v)) for k,v in dict(odor=['ORN_DM1','ORN_VA2'],heat=['TRN_VP2'],
        a1=['DNa01'],a2=['DNa02'],p9=['DNp09']).items()}
    for k,idx in list(groups.items()):
        side=n.iloc[idx].somaSide.fillna(n.iloc[idx].rootSide)
        for s in ['L','R']:groups[k+'_'+s]=idx[side.eq(s).to_numpy()]
    results=[];out=ROOT/'reports/behavior/probe-transmitter-efficacy.json'
    for tonic in [1.2,1.5]:
        for transmitter in ['gaba','glutamate']:
            for efficacy in [.25,.5,2.,4.]:
                scale=sign.copy();scale[nt.eq(transmitter).to_numpy()]*=efficacy
                w=counts.multiply(scale[None,:]).tocsr();w.eliminate_zeros();w.sort_indices()
                for condition in ['control','odor_L','odor_R','heat_L','heat_R']:
                    p=parameters(cfg,tonic);p['noise_std']=0.
                    b=CountBrain(w,p,seed=20260913,neurons=n)
                    current=None if condition=='control' else b.current(groups[condition],3.)
                    sums={k:0 for k in ['a1_L','a1_R','a2_L','a2_R','p9']}
                    for t in range(700):
                        sp=b.step(current if t>=300 else None)
                        if t>=400:
                            for k in sums:sums[k]+=int(sp[groups[k]].sum())
                    row=dict(tonic=tonic,transmitter=transmitter,efficacy=efficacy,condition=condition,
                        hz={k:total/len(groups[k])/.3 for k,total in sums.items()})
                    results.append(row)
                    out.write_text(json.dumps(dict(assumptions='Free transmitter efficacies, fitted screen; not biological certification',results=results),indent=2))
                trial=results[-5:];base=trial[0]['hz']
                def lr(h):return h['a1_L']+h['a2_L']-h['a1_R']-h['a2_R']
                effects=[lr(r['hz'])-lr(base) for r in trial[1:]]
                print(json.dumps(dict(tonic=tonic,nt=transmitter,efficacy=efficacy,forward_hz=base['p9'],effects=effects,
                    screen_passed=effects[0]>0 and effects[1]<0 and effects[2]<0 and effects[3]>0)),flush=True)

if __name__=='__main__':main()
