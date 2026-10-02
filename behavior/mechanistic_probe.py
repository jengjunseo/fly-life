"""Independent receptor, excitability and readout diagnostics; no target policy."""
import argparse
import json
import time
from pathlib import Path
import numpy as np
from behavior.model import CountBrain, load_connectivity, parameters

ROOT = Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',default='reports/behavior-retry/mechanistic-probe.json')
    p.add_argument('--steps',type=int,default=1000)
    p.add_argument('--profiles',nargs='+',default=['uniform','kc_quiet','central_subthreshold'])
    p.add_argument('--conditions',nargs='+',default=['control','odor_L','all_orn_L','warm_L','opponent_warm_L','cool_L'])
    p.add_argument('--gain',type=float,default=.002)
    p.add_argument('--tonic',type=float,default=1.5)
    p.add_argument('--restore-weak',action='store_true')
    p.add_argument('--psi-literature',action='store_true')
    a=p.parse_args()
    cfg=json.loads((ROOT/'config.json').read_text())
    w,n,evidence=load_connectivity(cfg,unpruned=a.restore_weak,psi_literature=a.psi_literature)
    groups={k:np.flatnonzero(n.type.fillna('').str.match(regex).to_numpy()) for k,regex in {
        'odor':'^ORN_(DM1|VA2)$','all_orn':'^ORN_', 'warm':'^TRN_VP2$',
        'cool':'^TRN_VP3[ab]$', 'a1':'^DNa01$', 'a2':'^DNa02$',
        'p9':'^DNp09$', 'mb32':'^MBON32$', 'kc':'^KC', 'gf':'^DNp01$', 'object':'^LC10a$',
        'ppl3':'^PPL103$', 'warm_pn':'^VP2.*PN$', 'cool_pn':'^VP3.*PN$',
        'p6':'^DNp06$', 'tlhon':'^LHPV2g', 'lhad1':'^LHAD1(?:[^0-9]|$)',
        'pvlp76':'^PVLP076$', 'avlp53':'^AVLP053$'}.items()}
    for k,idx in list(groups.items()):
        side=n.iloc[idx].somaSide.fillna(n.iloc[idx].rootSide)
        for s in ['L','R']:groups[k+'_'+s]=idx[side.eq(s).to_numpy()]
    profiles=a.profiles;conditions=a.conditions
    out=ROOT/a.out;out.parent.mkdir(parents=True,exist_ok=True)
    result=dict(evidence=evidence,assumptions={
        'kc_quiet':'KC tonic current set to zero; literature motivates sparse KC baseline, exact value is a hypothesis',
        'central_subthreshold':'non-peripheral tonic 0.95 except identified DNs 1.5; assumed locomotor state, not measured arousal circuit',
        'opponent_warm_L':'current +3 to warming TRNs and -1.5 to cooling TRNs on same antenna; receptor hypothesis',
        'all_orn_L':'artificial broad ORN stimulation, not certified food identity'},
        group_counts={k:len(v) for k,v in groups.items()},results=[])
    for profile in profiles:
        for condition in conditions:
            params=parameters(cfg,a.tonic);params['recurrent_gain']=a.gain
            b=CountBrain(w,params,seed=20260913,neurons=n)
            if profile=='kc_quiet':b.baseline[groups['kc']]=0.
            if profile.startswith('kc_') and profile!='kc_quiet':b.baseline[groups['kc']]=float(profile[3:])
            if profile=='central_subthreshold':
                b.baseline[:]=.95
                for k in ['all_orn','warm','cool','p9','a1','a2']:b.baseline[groups[k]]=1.5
                b.baseline[groups['kc']]=0.
            if profile in ['sparse_background','selective_arousal']:
                b.baseline[:]=.95 if profile=='sparse_background' else 1.05
                afferent=n.superclass.isin(['cb_sensory','ol_sensory','vnc_sensory','sensory_ascending','sensory_descending']).to_numpy()
                b.baseline[afferent]=0.
                b.baseline[groups['all_orn']]=1.
                for k in ['warm','cool','p9','a1','a2']:b.baseline[groups[k]]=1.5
                b.baseline[groups['gf']]=1.1
                b.baseline[groups['kc']]=.85
            current=np.zeros(b.n,np.float32)
            if condition!='control':
                group=condition.replace('opponent_warm','warm').replace('strong_warm','warm')
                current[groups[group]]=3.
                if condition=='opponent_warm_L':current[groups['cool_L']]=-1.5
                if condition=='opponent_warm_R':current[groups['cool_R']]=-1.5
                if condition.startswith('strong_warm_'):
                    side=condition[-1];current[groups['warm_'+side]]=5.;current[groups['cool_'+side]]=-3.
            sums={k:0 for k in groups};samples=[];begin=time.perf_counter()
            for t in range(a.steps):
                sp=b.step(current if t>=500 else None)
                if t>=a.steps-300:
                    for k,idx in groups.items():sums[k]+=int(sp[idx].sum())
                if t%20==19:
                    samples.append(dict(ms=t+1,**{k:float(b.activity[groups[k]].mean()) for k in ['a1_L','a1_R','a2_L','a2_R','p9','mb32_L','mb32_R','ppl3_L','ppl3_R']}))
            row=dict(profile=profile,condition=condition,gain=a.gain,tonic=a.tonic,wall_s=time.perf_counter()-begin,
                rates_hz={k:total/len(groups[k])/.3 if len(groups[k]) else None for k,total in sums.items()},samples=samples)
            result['results'].append(row)
            out.write_text(json.dumps(result,indent=2),encoding='utf-8')
            h=row['rates_hz'];print(json.dumps(dict(profile=profile,condition=condition,
                a1_left_minus_right=h['a1_L']-h['a1_R'],a2_left_minus_right=h['a2_L']-h['a2_R'],
                forward=h['p9'],kc=h['kc'],mb32_L=h['mb32_L'],mb32_R=h['mb32_R'],ppl3_L=h['ppl3_L'],ppl3_R=h['ppl3_R'],wall_s=row['wall_s'])),flush=True)

if __name__=='__main__':main()
