"""Minimal section timers on an unchanged copy of Brain.step; actual reference comparison."""
import json
import time
import numpy as np
from common import load, REPORT, WORK, save, summarize, ROOT, sha
from braincore.core import Brain
from braincore.evidence import Resources


def timed_step(brain, external, costs):
    p=brain.p; t=time.perf_counter()
    if external is not None:
        external=np.asarray(external,dtype=np.float32)
        if external.shape!=(brain.n,) or not np.isfinite(external).all():raise ValueError('external')
    costs['misc']+=time.perf_counter()-t;t=time.perf_counter()
    brain.syn*=brain.syn_decay
    brain.syn+=np.float32(p['recurrent_gain'])*(brain.w@brain.spikes)
    costs['propagation']+=time.perf_counter()-t;t=time.perf_counter()
    active=brain.refractory==0;brain.refractory[~active]-=1
    drive=brain.baseline+brain.syn
    if p['noise_std']:drive+=np.float32(p['noise_std'])*brain.rng.standard_normal(brain.n,dtype=np.float32)
    if external is not None:drive+=external
    brain.v[active]+=np.float32(p['dt_ms']/p['tau_m_ms'])*(p['rest']-brain.v[active]+drive[active])
    brain.v[~active]=p['reset'];fired=active&(brain.v>=p['threshold'])
    brain.spikes[:]=fired;brain.v[fired]=p['reset'];brain.refractory[fired]=brain.refractory_steps
    costs['neuron_noise_refractory_reset']+=time.perf_counter()-t;t=time.perf_counter()
    brain.activity*=brain.activity_decay
    brain.activity+=(1-brain.activity_decay)*brain.spikes*np.float32(1000/p['dt_ms'])
    brain.step_count+=1
    if brain.step_count%100==0 and not(np.isfinite(brain.v).all() and np.isfinite(brain.syn).all()):raise FloatingPointError()
    costs['misc']+=time.perf_counter()-t
    return brain.spikes


if __name__=='__main__':
    with Resources() as resources:
        t=time.perf_counter();brain,cfg,groups=load();load_wall=time.perf_counter()-t
        WORK.mkdir(parents=True,exist_ok=True)
        record=np.unique(np.concatenate(list(groups.values()))).astype(np.int32)
        external=brain.current(np.union1d(groups['LC4'],groups['LPLC2']),cfg['experiment']['stimulus_current'])
        np.savez(WORK/'initial.npz',baseline=brain.baseline,external=external,record=record)
        # Profile CURRENT noise-on reference parameters and verify copied step bit-for-bit.
        a=Brain(brain.w,cfg['model'],seed=20260913); c=Brain(brain.w,cfg['model'],seed=20260913)
        costs={k:0. for k in ('propagation','neuron_noise_refractory_reset','misc','readout')}
        t=time.perf_counter()
        for step in range(500):
            timed_step(a,None,costs)
            if (step+1)%50==0:
                r=time.perf_counter()
                for idx in groups.values():a.read_activity(idx)
                np.sum(a.spikes);costs['readout']+=time.perf_counter()-r
        profile_wall=time.perf_counter()-t
        for _ in range(500):c.step()
        exact=all(np.array_equal(getattr(a,k),getattr(c,k)) for k in ['v','syn','spikes','refractory','activity','baseline'])
        assert exact
        save(REPORT/'profile.json',dict(neural_seconds=.5,wall_seconds=profile_wall,seconds=costs,
            unassigned_loop_seconds=profile_wall-sum(costs.values()),copy_matches_reference_bit_exact=exact,
            noise_std=cfg['model']['noise_std'],timing_scope='syn decay + sparse matvec + gain; neuron includes noise; misc includes external validation/activity/finiteness; readout every 50 steps'))
        del a,c
        # Same initial state & NumPy2.4 seeded drive; full 2 seconds, including warmup.
        ii=[];tt=[];activity=np.empty((len(record),2000),np.float32);step_wall=0.;phase_wall={}
        for phase,start,end in [('warmup',0,500),('baseline',500,1000),('stimulus',1000,1500),('recovery',1500,2000)]:
            phase_start=time.perf_counter()
            for step in range(start,end):
                begin=time.perf_counter();sp=brain.step(external if phase=='stimulus' else None);step_wall+=time.perf_counter()-begin
                ids=np.flatnonzero(sp).astype(np.int32);ii.append(ids);tt.append(np.full(len(ids),step,np.int32));activity[:,step]=brain.activity[record]
            phase_wall[phase]=time.perf_counter()-phase_start
        ii=np.concatenate(ii);tt=np.concatenate(tt)
        phases=[('baseline',500,1000),('stimulus',1000,1500),('recovery',1500,2000)]
        summary=summarize(ii,tt,activity,record,groups,phases)
        np.savez_compressed(WORK/'reference-smoke.npz',spike_i=ii,spike_steps=tt,activity=activity,record=record)
        save(REPORT/'reference-smoke.json',dict(noise_policy='OFF in memory only',load_wall_seconds=load_wall,
            simulation_core_wall_seconds=step_wall,phase_wall_seconds=phase_wall,summary=summary,
            groups={k:dict(runtime_indices=v.tolist(),body_ids=brain.neurons.iloc[v].bodyId.tolist()) for k,v in groups.items()},
            neurons=brain.n,effective_connections=brain.w.nnz,weights_sha256=sha(ROOT/'data/runtime/weights.npz'),
            initial_drive_sha256=sha(WORK/'initial.npz'),finite=bool(np.isfinite(brain.v).all() and np.isfinite(brain.syn).all())))
        # Comparable contiguous 10s deterministic baseline, reset to same initialization.
        brain=Brain(brain.w,brain.p,seed=cfg['experiment']['seed'])
        for _ in range(500):brain.step()
        count=0;t=time.perf_counter()
        for _ in range(10000):count+=int(brain.step().sum())
        benchmark_wall=time.perf_counter()-t
        benchmark=dict(neural_seconds=10.,wall_seconds=benchmark_wall,neural_wall_ratio=10/benchmark_wall,
            population_spikes=count,noise_policy='OFF',warmup_seconds=.5,condition='baseline',includes_scalar_spike_count_readout=True)
    save(REPORT/'reference-benchmark.json',dict(**benchmark,resources=resources.report()))
    print(json.dumps(dict(profile=costs,summary=summary,benchmark=benchmark),indent=2))
