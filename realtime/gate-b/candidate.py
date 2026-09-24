import json
import sys
import time
import numpy as np
from env import ROOT,REPORT,WORK,Brain,save,sha,machine
from candidate import ChildrenRSS
from engine import b,create


def statistics(windows,compute_seconds):
    times=np.array([x['wall_compute_ms'] for x in windows]);miss=times>50
    longest=run=0
    for m in miss:run=run+1 if m else 0;longest=max(longest,run)
    result=dict(windows=len(times),mean_ms=float(times.mean()),p50_ms=float(np.median(times)),p95_ms=float(np.percentile(times,95)),
        p99_ms=float(np.percentile(times,99)),max_ms=float(times.max()),deadline_misses=int(miss.sum()),deadline_miss_rate=float(miss.mean()),
        longest_consecutive_misses=longest,neural_seconds=len(times)*.05,network_compute_seconds=compute_seconds,
        window_compute_seconds=float(times.sum()*.001),neural_wall_ratio=len(times)*.05/compute_seconds)
    result['compute_realtime']=compute_seconds<=len(times)*.05 and result['p99_ms']<=50
    result['clean_quality']=result['deadline_miss_rate']<.01 and longest<=2
    return result


if __name__=='__main__':
    name=sys.argv[1];assert name in ['b0-native','b0-frozen','b0-performance','baseline','looming','real_predator','compound','b2']
    inputname='b0' if name.startswith('b0-') and name!='b0-performance' else 'b0_performance' if name=='b0-performance' else name
    noise='off' if name=='b2' else 'frozen' if name=='b0-frozen' else 'native'
    with ChildrenRSS() as resources:
        begin=time.perf_counter();cfg=json.loads((ROOT/'config.json').read_text());brain=Brain.load(ROOT/'data/runtime',cfg);load=time.perf_counter()-begin
        initial=np.load(WORK/'initial.npz');brain.baseline=initial['baseline'].copy()
        if noise=='off':brain.p['noise_std']=0.
        groups={k:initial['group_'+k] for k in ['LC4','LPLC2','GF','DNp09']}
        inputs=np.load(WORK/'inputs.npz');schedule=inputs[inputname]
        # B1 baseline gets the required actual 60s run (1200 windows). Each other
        # workload gets 20s/400 consecutive windows, not a single 10s mean proxy.
        if name in ['looming','real_predator','compound']:schedule=schedule[:400]
        currents=schedule@inputs['matrix']
        directory=WORK/(name+'-cpp');begin=time.perf_counter()
        g,s,net,spikes=create(brain,groups,inputs['pool'],currents,directory,noise,cfg['experiment']['seed'],record_spikes=inputname=='b0')
        net.run(len(schedule)*50*b.ms,namespace={});model_wall=time.perf_counter()-begin
        begin=time.perf_counter();b.device.build(directory=str(directory),compile=False,run=False);generation=time.perf_counter()-begin
        begin=time.perf_counter();b.device.compile_source(str(directory),'mingw32',False,False);compilation=time.perf_counter()-begin
        begin=time.perf_counter();b.device.run(directory=str(directory));binary=time.perf_counter()-begin
        timing={k:float(v) for k,v in (line.split() for line in (directory/'results/timing.txt').read_text().splitlines())}
        raw=np.loadtxt(directory/'results/windows.txt');records=[]
        for row in raw:
            records.append(dict(window_index=int(row[0]),neural_start_s=float(row[1]),neural_end_s=float(row[2]),wall_compute_ms=float(row[3]),
                realtime_factor=float(50/row[3]),slack_ms=float(50-row[3]),population_spikes=int(row[4]),cumulative_population_spikes=int(row[5]),
                cumulative_active_fraction=float(row[6]/brain.n),max_simultaneous_spiking_fraction=float(row[7]/brain.n),finite=bool(row[8]),
                groups={name:dict(cumulative_spikes=int(row[9+5*j]),mean_ema_hz=float(row[10+5*j]),cumulative_active_fraction=float(row[11+5*j]/len(idx)),
                    peak_mean_ema_hz=float(row[12+5*j]),window_mean_ema_hz=float(row[13+5*j])) for j,(name,idx) in enumerate(groups.items())}))
        assert len(records)==len(schedule) and [x['window_index'] for x in records]==list(range(len(schedule)))
        targets=np.repeat(np.arange(brain.n,dtype=np.int32),np.diff(brain.w.indptr))
        full=bool(np.array_equal(s.i[:],brain.w.indices) and np.array_equal(s.j[:],targets) and np.array_equal(s.w[:],brain.w.data))
        report=dict(name=name,noise_policy=noise,noise_std=brain.p['noise_std'],seed=cfg['experiment']['seed'],
            native_rng='Actual generated objects.h: std::mt19937 + polar Box-Muller; same numeric seed, DIFFERENT stream from NumPy PCG64. Independent standard_normal per neuron per ms, float32 cast/scaling before external current; not xi voltage diffusion.',
            neurons=brain.n,effective_connections=brain.w.nnz,dt_ms=1,full_connection_arrays_verified=full,
            initial_sha256=sha(WORK/'initial.npz'),inputs_sha256=sha(WORK/'inputs.npz'),weights_sha256=sha(ROOT/'data/runtime/weights.npz'),
            load_wall_seconds=load,python_model_setup_wall_seconds=model_wall,code_generation_wall_seconds=generation,
            compile_link_wall_seconds=compilation,timings=timing,binary_launch_init_compute_output_wall_seconds=binary,
            launcher_and_unattributed_seconds=binary-sum(timing[k] for k in ['init','network_compute','brian_output']),
            statistics=statistics(records,timing['network_compute']),windows=records,finite=all(x['finite'] for x in records),
            executable_sha256=sha(directory/'main.exe'),generated_source_sha256={str(p.relative_to(directory)):sha(p) for p in directory.rglob('*') if p.suffix in ['.cpp','.h']},
            machine=machine(),brian2_version=b.__version__,compiler='TDM-GCC 9.2.0, -O3 -march=native -std=c++17; no fast-math/OpenMP/GPU',
            timing_scope='Per 50 real 1ms Brian steps inside one persistent Network.run. Per-window input/log/stat boundary maintenance excluded; whole Network.run including it also reported. No Python launcher in quantum timings.')
        if inputname=='b0':
            ids=np.asarray(spikes.i[:],np.int32);steps=np.rint(spikes.t[:]/b.ms).astype(int);phases={}
            for phase,start,end in [('baseline',500,1000),('stimulus',1000,1500),('recovery',1500,2000)]:
                firing=ids[(steps>=start)&(steps<end)];rows=records[start//50:end//50]
                phases[phase]=dict(population_spikes=len(firing),population_rate_hz=len(firing)/brain.n/.5,
                    active_fraction=len(np.unique(firing))/brain.n,groups={k:dict(spike_count=int(np.isin(firing,idx).sum()),
                        mean_hz=float(np.isin(firing,idx).sum()/len(idx)/.5),active_fraction=len(np.intersect1d(firing,idx))/len(idx),
                        mean_ema_hz=float(np.mean([r['groups'][k]['window_mean_ema_hz'] for r in rows])),
                        peak_mean_ema_hz=max(r['groups'][k]['peak_mean_ema_hz'] for r in rows),final_ema_hz=rows[-1]['groups'][k]['mean_ema_hz']) for k,idx in groups.items()})
            report['phases']=phases
        if name=='b0-performance':
            report['conditions']={phase:statistics(records[lo:hi],sum(r['wall_compute_ms']*.001 for r in records[lo:hi])) for phase,lo,hi in [('baseline',10,210),('stimulus',210,410)]}
            for phase,lo,hi in [('baseline',10,210),('stimulus',210,410)]:
                report['conditions'][phase]['population_spikes']=sum(r['population_spikes'] for r in records[lo:hi])
                report['conditions'][phase]['compute_timing_scope']='Sum of 200 internal 50ms compute windows; excludes per-boundary logging/stat/input maintenance. Full Network.run wall above includes it.'
    report['resources']=resources.report();save(REPORT/(name+'.json'),report)
    # Raw C++ boundary output and timers retained under reports, not only summary JSON.
    import shutil
    shutil.copyfile(directory/'results/windows.txt',REPORT/(name+'-windows.txt'))
    shutil.copyfile(directory/'results/timing.txt',REPORT/(name+'-timing.txt'))
    print(json.dumps({k:v for k,v in report.items() if k not in ['windows','generated_source_sha256','phases']},indent=2))
