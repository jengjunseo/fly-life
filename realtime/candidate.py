"""Run only smoke or contiguous 10s baseline/stimulus probes; no ecology migration."""
import json
import sys
import threading
import time
import numpy as np
import psutil
from common import load, REPORT, WORK, ROOT, save, sha, summarize, machine, COMPILER
from prototype import b, translate, build


class ChildrenRSS:
    """Sample transient compiler/executable children, separately from Python preparation."""
    def __init__(self):
        self.done=threading.Event();self.samples=[];self.process=psutil.Process()
    def sample(self):
        while not self.done.is_set():
            child=[]
            for p in self.process.children(recursive=True):
                try:child.append(dict(pid=p.pid,name=p.name(),rss=p.memory_info().rss,
                    peak=getattr(p.memory_info(),'peak_wset',p.memory_info().rss)))
                except(psutil.NoSuchProcess,psutil.AccessDenied):pass
            self.samples.append(dict(t=time.perf_counter(),python_rss=self.process.memory_info().rss,
                children=child,available_ram=psutil.virtual_memory().available))
            self.done.wait(.02)
    def __enter__(self):
        self.thread=threading.Thread(target=self.sample,daemon=True);self.thread.start();return self
    def __exit__(self,*_):
        self.done.set();self.thread.join()
    def report(self):
        executable=[c for x in self.samples for c in x['children'] if c['name'].lower()=='main.exe']
        return dict(sampling_interval_seconds=.02,samples=len(self.samples),
            executable_peak_rss_bytes=max((c['peak'] for c in executable),default=0),
            executable_representative_rss_bytes=int(np.median([c['rss'] for c in executable])) if executable else 0,
            preparation_python_peak_rss_bytes=max(x['python_rss'] for x in self.samples),
            whole_process_tree_sampled_peak_rss_bytes=max(x['python_rss']+sum(c['rss'] for c in x['children']) for x in self.samples),
            minimum_available_ram_bytes=min(x['available_ram'] for x in self.samples),
            observed_child_names=sorted(set(c['name'] for x in self.samples for c in x['children'])))


if __name__=='__main__':
    mode=sys.argv[1]; assert mode in ['smoke','benchmark']
    with ChildrenRSS() as rss:
        start=time.perf_counter();brain,cfg,groups=load();load_wall=time.perf_counter()-start
        initial=np.load(WORK/'initial.npz');brain.baseline=initial['baseline'].copy()
        external=initial['external'];record=initial['record']
        directory=WORK/(mode+'-cpp')
        start=time.perf_counter();g,s,net,spikes,states=translate(brain,np.zeros(brain.n,np.float32),record,directory)
        if mode=='smoke':
            net.run(1000*b.ms, namespace={});g.external=external;net.run(500*b.ms, namespace={});g.external=0;net.run(500*b.ms, namespace={})
        else:
            net.run(500*b.ms, namespace={});net.run(10*b.second, namespace={});g.external=external;net.run(10*b.second, namespace={})
        generation_wall=time.perf_counter()-start
        construction=build(directory)
        start=time.perf_counter();b.device.run(directory=str(directory));binary_wall=time.perf_counter()-start
        timings=[line.split() for line in (directory/'results/gate_timing.txt').read_text().splitlines()]
        init=float(timings[0][1]);run_times=[float(v) for k,v in timings if k=='run']
        spike_i=np.asarray(spikes.i[:],np.int32);spike_steps=np.rint(spikes.t[:]/b.ms).astype(np.int32)
        activity=np.asarray(states.activity[:],np.float32)
        finite=bool(np.isfinite(g.v[:]).all() and np.isfinite(g.syn[:]).all() and np.isfinite(activity).all())
        # Verify the generated C++ constructed the exact full signed edge arrays, not a substitute.
        targets=np.repeat(np.arange(brain.n,dtype=np.int32),np.diff(brain.w.indptr))
        export_verified=(np.array_equal(s.i[:],brain.w.indices) and np.array_equal(s.j[:],targets) and
                         np.array_equal(s.w[:],brain.w.data))
        assert export_verified and finite
        report=dict(mode=mode,neurons=brain.n,effective_connections=brain.w.nnz,
            anatomical_connections=6474533,dtype='float32',dt_ms=1,noise_policy='OFF ONLY; NumPy2.4 reference baseline exported; no stochastic equivalence claimed',
            brian2_version=b.__version__,candidate_numpy=np.__version__,machine=machine(),
            compiler=str(COMPILER/'g++.exe'),compiler_version='TDM-GCC 9.2.0',openmp_threads=0,
            weights_sha256=sha(ROOT/'data/runtime/weights.npz'),initial_sha256=sha(WORK/'initial.npz'),
            generated_cpp_sha256={str(p.relative_to(directory)):sha(p) for p in directory.rglob('*.cpp')},
            executable_sha256=sha(directory/'main.exe'),full_export_arrays_verified=bool(export_verified),
            finite=finite,python_load_wall_seconds=load_wall,python_model_generation_wall_seconds=generation_wall,
            build=construction,executable_init_wall_seconds=init,simulation_run_wall_seconds=run_times,
            executable_launch_init_simulation_output_wall_seconds=binary_wall,
            remaining_launch_output_seconds=binary_wall-init-sum(run_times),scheduler=str(net.scheduling_summary()))
        if mode=='smoke':
            report['neural_seconds']=2.;report['neural_wall_ratio']=2/sum(run_times)
            report['summary']=summarize(spike_i,spike_steps,activity,record,groups,
                [('baseline',500,1000),('stimulus',1000,1500),('recovery',1500,2000)])
            np.savez_compressed(WORK/'brian-smoke.npz',spike_i=spike_i,spike_steps=spike_steps,activity=activity,record=record)
        else:
            report['conditions']={name:dict(neural_seconds=10.,wall_seconds=run_times[k],neural_wall_ratio=10/run_times[k],
                population_spikes=int(((spike_steps>=lo)&(spike_steps<hi)).sum()),
                population_rate_hz=float(((spike_steps>=lo)&(spike_steps<hi)).sum()/brain.n/10))
                for name,k,lo,hi in [('baseline',1,500,10500),('LC4_LPLC2_stimulus',2,10500,20500)]}
            report['note']='baseline 10s follows 0.5s warmup, stimulus 10s continues that state; all-spike and selected activity monitors included'
    report['resources']=rss.report();save(REPORT/('brian-'+mode+'.json'),report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['generated_cpp_sha256','scheduler']},indent=2))
