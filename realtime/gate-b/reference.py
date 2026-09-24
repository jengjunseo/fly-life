"""Unmodified Brain.step, actual NumPy2.4 reference; summaries every quantum/second."""
import json
import sys
import time
import numpy as np
from env import ROOT,REPORT,WORK,Brain,save
from braincore.evidence import Resources

if __name__=='__main__':
    mode=sys.argv[1];assert mode in ['b0','b2']
    cfg=json.loads((ROOT/'config.json').read_text());initial=np.load(WORK/'initial.npz');inputs=np.load(WORK/'inputs.npz')
    with Resources() as resources:
        begin=time.perf_counter();brain=Brain.load(ROOT/'data/runtime',cfg);load=time.perf_counter()-begin
        assert np.array_equal(brain.baseline,initial['baseline'])
        if mode=='b2':brain.p['noise_std']=0.
        groups={name:initial['group_'+name] for name in ['LC4','LPLC2','GF','DNp09']}
        counts=np.zeros(brain.n,np.int64);records=[];phase_counts={};phase_peak={};phase_ema={}
        schedule=inputs[mode];wall=0.;max_sync=0;finite=True
        for wi,amps in enumerate(schedule):
            ext=np.zeros(brain.n,np.float32);ext[inputs['pool']]=amps@inputs['matrix']
            phase=('warmup' if wi<10 else 'baseline' if wi<20 else 'stimulus' if wi<30 else 'recovery') if mode=='b0' else ('baseline' if wi<400 else 'stimulus' if wi<800 else 'recovery')
            if phase not in phase_counts:
                phase_counts[phase]=np.zeros(brain.n,np.int64);phase_peak[phase]={k:0. for k in groups};phase_ema[phase]={k:[] for k in groups}
            quantum=0;t=time.perf_counter()
            for _ in range(50):
                begin=time.perf_counter();sp=brain.step(ext);wall+=time.perf_counter()-begin
                ids=np.flatnonzero(sp);counts[ids]+=1;phase_counts[phase][ids]+=1;quantum+=len(ids);max_sync=max(max_sync,len(ids))
                if mode=='b0':
                    for name,idx in groups.items():
                        ema=float(brain.activity[idx].mean());phase_peak[phase][name]=max(phase_peak[phase][name],ema);phase_ema[phase][name].append(ema)
            finite=finite and bool(np.isfinite(brain.v).all() and np.isfinite(brain.syn).all())
            if mode=='b0' or (wi+1)%20==0:
                records.append(dict(time_s=(wi+1)*.05,cumulative_population_spikes=int(counts.sum()),
                    groups={k:dict(cumulative_spikes=int(counts[v].sum()),mean_ema_hz=float(brain.activity[v].mean())) for k,v in groups.items()}))
            if (wi+1)%100==0:print(f'{mode}: completed {(wi+1)*.05:.1f}s',flush=True)
        phases={}
        for phase,c in phase_counts.items():
            duration=.5 if mode=='b0' else 20.
            phases[phase]=dict(population_spikes=int(c.sum()),population_rate_hz=float(c.sum()/brain.n/duration),
                active_fraction=float(np.count_nonzero(c)/brain.n),groups={k:dict(spike_count=int(c[v].sum()),mean_hz=float(c[v].sum()/len(v)/duration),
                    active_fraction=float(np.count_nonzero(c[v])/len(v)),peak_mean_ema_hz=phase_peak[phase][k],
                    mean_ema_hz=float(np.mean(phase_ema[phase][k])) if phase_ema[phase][k] else None) for k,v in groups.items()})
    report=dict(mode=mode,noise_std=brain.p['noise_std'],rng='NumPy default_rng PCG64, float32 standard_normal; state advanced by baseline heterogeneity draw; seed read from config',
        seed=cfg['experiment']['seed'],neurons=brain.n,neural_seconds=len(schedule)*.05,load_wall_seconds=load,
        core_compute_wall_seconds=wall,whole_probe_wall_seconds=resources.elapsed,resources=resources.report(),
        phases=phases,trajectory=records,finite=finite,max_simultaneous_spiking_fraction=max_sync/brain.n)
    save(REPORT/('reference-'+mode+'.json'),report);print(json.dumps({k:v for k,v in report.items() if k not in ['trajectory']},indent=2))
