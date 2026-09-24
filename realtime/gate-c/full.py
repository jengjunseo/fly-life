"""Unchanged Gate B Brian2 translation, experimental OpenMP setting only."""
import importlib.util,json,shutil,sys,time
from pathlib import Path
import numpy as np
from env import ROOT,REPORT,WORK,OLD,Brain,sha,save,machine
from candidate import ChildrenRSS

spec=importlib.util.spec_from_file_location('gate_c_frozen_translation',ROOT/'realtime/gate-b/engine.py')
engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
engine.WORK=WORK
b=engine.b
def stats(rows,total):
    a=np.array([r['wall_compute_ms'] for r in rows]);miss=a>50;longest=run=0
    for v in miss:run=run+1 if v else 0;longest=max(longest,run)
    return dict(windows=len(a),neural_seconds=len(a)*.05,mean_ms=float(a.mean()),p50_ms=float(np.median(a)),p95_ms=float(np.percentile(a,95)),
        p99_ms=float(np.percentile(a,99)),max_ms=float(a.max()),deadline_misses=int(miss.sum()),deadline_miss_rate=float(miss.mean()),longest_consecutive_misses=longest,
        window_compute_seconds=float(a.sum()/1000),network_compute_seconds=total,neural_wall_ratio=len(a)*.05/total,
        compute_realtime=bool(total<=len(a)*.05 and np.percentile(a,99)<=50),clean_quality=bool(miss.mean()<.01 and longest<=2))

if __name__=='__main__':
    name=sys.argv[1];threads=int(sys.argv[2]);count=int(sys.argv[3]);inputname=sys.argv[4] if len(sys.argv)>4 else 'baseline'
    noise=sys.argv[5] if len(sys.argv)>5 else 'native';seed=int(sys.argv[6]) if len(sys.argv)>6 else 20260913
    assert threads in [1,2,3,4,8] and noise in ['native','frozen','off']
    original_setup=engine.setup
    def setup(directory):
        original_setup(directory)
        b.prefs.devices.cpp_standalone.openmp_threads=threads if threads>1 else 0
    engine.setup=setup
    with ChildrenRSS() as resources:
        begin=time.perf_counter();cfg=json.loads((ROOT/'config.json').read_text());cfg['experiment']['seed']=seed
        brain=Brain.load(ROOT/'data/runtime',cfg);load=time.perf_counter()-begin
        initial=np.load(WORK/('initial.npz' if seed==20260913 else f'initial-{seed}.npz'));brain.baseline=initial['baseline'].copy()
        groups={k:initial['group_'+k] for k in ['LC4','LPLC2','GF','DNp09']}
        inputs=np.load(WORK/'inputs.npz');schedule=inputs[inputname][:count];assert len(schedule)==count
        directory=WORK/(name+'-cpp');begin=time.perf_counter()
        if noise=='frozen':
            assert json.loads((REPORT/'c2-decision.json').read_text())['c3_allowed']
            assert count==40 and inputname=='b0', 'Bounded exact 2s diagnostic, never periodic noise replay'
            engine.WORK=OLD  # Existing tape opened READ-ONLY, no disk duplication.
        g,s,net,spikes=engine.create(brain,groups,inputs['pool'],schedule@inputs['matrix'],directory,noise,seed,record_spikes=inputname=='b0')
        if noise=='frozen':
            # Only Gate C's generated reader is replaced. Neural equations/arrays untouched.
            header=directory/'gate_hooks.h';content=header.read_text()
            start=content.index('inline double gate_noise_read()');end=content.index('\n        }',start)+10
            replacement='''inline std::vector<float> gate_c_shared_noise;
inline long long gate_c_noise_step=0;
inline double gate_noise_read() {
    if(gate_c_noise_step>=2000)throw std::runtime_error("Exact shared noise exhausted");
    std::memcpy(brian::_array_neurons_noise_sample,
        gate_c_shared_noise.data()+gate_c_noise_step*165122LL,165122*4);
    ++gate_c_noise_step;
    return 0;
}'''
            header.write_text('#include <cstring>\n'+content[:start]+replacement+content[end:]+'\n',encoding='utf-8')
            b.prefs.codegen.cpp.headers+=['<cstring>']
            # This queue entry precedes net.run, so entire tape load is C++ initialization.
            b.device.insert_code('main','''
gate_c_shared_noise.resize(2000LL*165122);
gate_b::noise_file.read(reinterpret_cast<char*>(gate_c_shared_noise.data()),2000LL*165122*4);
if(!gate_b::noise_file)throw std::runtime_error("Exact shared tape preload failed");
gate_b::noise_file.close();
''')
        net.run(count*50*b.ms,namespace={});model=time.perf_counter()-begin
        begin=time.perf_counter();b.device.build(directory=str(directory),compile=False,run=False);generation=time.perf_counter()-begin
        begin=time.perf_counter();b.device.compile_source(str(directory),'mingw32',False,False);compilation=time.perf_counter()-begin
        begin=time.perf_counter();b.device.run(directory=str(directory));binary=time.perf_counter()-begin
        timings={k:float(v) for k,v in (line.split() for line in (directory/'results/timing.txt').read_text().splitlines())}
        raw=np.atleast_2d(np.loadtxt(directory/'results/windows.txt'));rows=[]
        for r in raw:
            rows.append(dict(window_index=int(r[0]),neural_start_s=float(r[1]),neural_end_s=float(r[2]),wall_compute_ms=float(r[3]),
                realtime_factor=50/float(r[3]),slack_ms=50-float(r[3]),population_spikes=int(r[4]),cumulative_population_spikes=int(r[5]),cumulative_active_fraction=float(r[6]/brain.n),
                max_simultaneous_spiking_fraction=float(r[7]/brain.n),finite=bool(r[8]),
                groups={k:dict(cumulative_spikes=int(r[9+5*j]),mean_ema_hz=float(r[10+5*j]),cumulative_active_fraction=float(r[11+5*j]/len(idx)),peak_mean_ema_hz=float(r[12+5*j]),window_mean_ema_hz=float(r[13+5*j])) for j,(k,idx) in enumerate(groups.items())}))
        assert len(rows)==count and [r['window_index'] for r in rows]==list(range(count))
        targets=np.repeat(np.arange(brain.n,dtype=np.int32),np.diff(brain.w.indptr))
        full=bool(np.array_equal(s.i[:],brain.w.indices) and np.array_equal(s.j[:],targets) and np.array_equal(s.w[:],brain.w.data));assert full
        phases={}
        if inputname=='b0':
            ids=np.asarray(spikes.i[:],np.int32);steps=np.rint(spikes.t[:]/b.ms).astype(int)
            for phase,start,end in [('baseline',500,1000),('stimulus',1000,1500),('recovery',1500,2000)]:
                fired=ids[(steps>=start)&(steps<end)];part=rows[start//50:end//50]
                phases[phase]=dict(population_spikes=len(fired),population_rate_hz=len(fired)/brain.n/.5,active_fraction=len(np.unique(fired))/brain.n,
                    groups={k:dict(spike_count=int(np.isin(fired,idx).sum()),mean_hz=float(np.isin(fired,idx).sum()/len(idx)/.5),active_fraction=len(np.intersect1d(fired,idx))/len(idx),mean_ema_hz=float(np.mean([r['groups'][k]['window_mean_ema_hz'] for r in part])),peak_mean_ema_hz=max(r['groups'][k]['peak_mean_ema_hz'] for r in part)) for k,idx in groups.items()})
        report=dict(name=name,threads=threads,noise_policy=noise,seed=seed,neurons=brain.n,effective_connections=brain.w.nnz,dt_ms=brain.p['dt_ms'],noise_std=brain.p['noise_std'],
            full_connection_arrays_verified=full,model_parameters=brain.p,weights_sha256=sha(ROOT/'data/runtime/weights.npz'),inputs_sha256=sha(WORK/'inputs.npz'),
            translation_source_sha256=sha(ROOT/'realtime/gate-b/engine.py'),load_wall_seconds=load,python_model_setup_wall_seconds=model,code_generation_wall_seconds=generation,compile_link_wall_seconds=compilation,
            timings=timings,binary_wall_seconds=binary,launcher_and_unattributed_seconds=binary-sum(timings[k] for k in ['init','network_compute','brian_output']),statistics=stats(rows,timings['network_compute']),
            windows=rows,phases=phases,finite=all(r['finite'] for r in rows),machine=machine(),brian2_version=b.__version__,compiler='TDM-GCC9.2, O3 march=native C++17; fopenmp only when >1T; no fastmath',
            native_rng='Actual generated std::mt19937 polar Box-Muller; per-thread generator selected with omp_get_thread_num, seeded per thread. Same seed integer does not mean PCG64 identity.',
            timing_scope='Independent nonoverlapping 50ms windows inside persistent C++ Network.run, boundary input/stat/log maintenance excluded per window, whole Network.run includes it; no Python startup in window.',
            executable_sha256=sha(directory/'main.exe'),generated_source_sha256={str(p.relative_to(directory)):sha(p) for p in directory.rglob('*') if p.suffix in ['.cpp','.h']})
        if noise=='frozen':
            report['pre_generated_noise_policy']=dict(source_sha256=sha(OLD/'noise-b0-float32.bin'),shape=[2000,brain.n],bytes=2000*brain.n*4,
                layout='Unscaled little-endian float32 C-order [step,runtime_index], each row copied once to same Brian noise_sample array before model scaling .1f',
                initialization='Whole bounded 2s tape loaded before Network.run; preload included in C++ init, not quantum compute. Resident memory and N-row memcpy included in executable RSS / quantum timing respectively.',
                qualification='40 exact nonperiodic 50ms windows. Independent consumption diagnostic/correctness, not a sustained producer pipeline or long-run realtime certification.')
    report['resources']=resources.report();save(REPORT/(name+'.json'),report)
    for f in ['windows.txt','timing.txt']:shutil.copyfile(directory/'results'/f,REPORT/(name+'-'+f))
    proof=REPORT/'generated-proof'/name;proof.mkdir(parents=True,exist_ok=True)
    for f in ['objects.h','objects.cpp','main.cpp','makefile','gate_hooks.h','code_objects/lif_update_codeobject.cpp','code_objects/connections_pre_codeobject.cpp','code_objects/spikes_codeobject.cpp']:
        shutil.copyfile(directory/f,proof/Path(f).name)
    print(json.dumps({k:v for k,v in report.items() if k not in ['windows','generated_source_sha256','phases']},indent=2))
