"""D1 actual subprocess affinity + persistent pinned producer threads, no buffering.
Named contention.py to avoid shadowing Python's concurrent.futures package.
"""
import ctypes,json,os,shutil,subprocess,sys,time
import numpy as np
import psutil
from env import ROOT,WORK,REPORT,OLD,COMPILER,Brain,save
from producer import Producer,statistics,pin_thread
def wait_file(path,child,limit=60):
    start=time.perf_counter()
    while not path.exists() or path.stat().st_size==0:
        if child.poll() is not None:raise RuntimeError(f'Consumer exited {child.returncode} before {path.name}')
        if time.perf_counter()-start>limit:raise TimeoutError(str(path))
        time.sleep(.005)
def verify_graph(result):
    cfg=json.loads((ROOT/'config.json').read_text());brain=Brain.load(ROOT/'data/runtime',cfg)
    targets=np.repeat(np.arange(brain.n,dtype=np.int32),np.diff(brain.w.indptr));checks={}
    for label,prefix,expected in [('source','_dynamic_array_connections__synaptic_pre_',brain.w.indices),('target','_dynamic_array_connections__synaptic_post_',targets),('weight','_dynamic_array_connections_w_',brain.w.data)]:
        files=list(result.glob(prefix+'*'));assert len(files)==1
        checks[label]=bool(np.array_equal(np.fromfile(files[0],dtype=expected.dtype),expected))
    assert all(checks.values());return checks
def run_trial(label,threads,brain_cpus,worker_cpus,scenario,trial,producer_on=True,zero=False):
    result=WORK/f'{label}-{scenario}-{trial}';result.mkdir(exist_ok=False)
    suffix='-zero' if zero else '';exe=WORK/f'd1-{threads}t-{scenario}{suffix}-cpp/main.exe'
    process_env=os.environ.copy();process_env['PATH']=str(COMPILER)+os.pathsep+process_env['PATH']
    coordinator_affinity=pin_thread([worker_cpus[0]]) if zero else None
    producer=Producer(20260913,len(worker_cpus),worker_cpus,packed=zero) if producer_on else None
    if producer:
        for _ in range(10):producer.fill()
    logs=(REPORT/f'{label}-{scenario}-{trial}-console.txt').open('w')
    child=subprocess.Popen([str(exe),'--results_dir',str(result)+'\\'],cwd=exe.parent,stdout=logs,stderr=subprocess.STDOUT,env=process_env)
    intervals=[];rss=[]
    try:
        wait_file(result/'ready',child);pid=int((result/'ready').read_text());assert pid==child.pid
        proc=psutil.Process(pid);proc.cpu_affinity(brain_cpus);actual=proc.cpu_affinity();assert actual==sorted(brain_cpus)
        (result/'go').write_text('go')
        compute_watch_started=time.perf_counter()
        while not(result/'compute-done').exists():
            if child.poll() is not None:raise RuntimeError('Brain exited during compute')
            if time.perf_counter()-compute_watch_started>60:raise TimeoutError('D1 consumer compute stalled')
            if producer:
                start=time.perf_counter();elapsed=producer.fill();end=time.perf_counter();intervals.append(dict(start=start,end=end,generation_ms=elapsed))
            else:time.sleep(.005)
            rss.append(proc.memory_info().rss)
        child.wait(timeout=30);assert child.returncode==0
    finally:
        if producer:producer.close()
        if child.poll() is None:child.kill();child.wait()
        logs.close()
    begin=float((result/'compute-start').read_text());end=float((result/'compute-done').read_text())
    contained=[r for r in intervals if r['start']>=begin and r['end']<=end];raw=np.loadtxt(result/'windows.txt');steady=raw[10:]
    timings={k:float(v) for k,v in (line.split() for line in (result/'timing.txt').read_text().splitlines())}
    d=dict(label=label,scenario=scenario,trial=trial,threads=threads,zero_copy_noise_row=zero,packing_coordinator_affinity=coordinator_affinity,brain_pid=pid,brain_cpus=actual,brain_affinity_mask=int((result/'affinity').read_text()),producer=producer.metadata() if producer else None,
        brain_statistics=statistics(steady[:,3]),producer_statistics=statistics([r['generation_ms'] for r in contained]) if contained else None,
        brain_all_window_ms=raw[:,3].tolist(),producer_intervals=intervals,overlap_start_qpc=begin,overlap_end_qpc=end,contained_producer_blocks=len(contained),warmup_brain_windows=10,
        neural_seconds=2,timings=timings,peak_consumer_rss=max(rss),finite=bool(np.all(raw[:,8])),max_simultaneous_spiking_fraction=float(raw[:,7].max()/165122),graph_verified=verify_graph(result),
        qualification='D1 concurrency feasibility only, exact nonperiodic preloaded noise, 0.5s brain warmup then30 windows; producer output deliberately discarded, no producer/consumer queue. QPC/perf_counter same system clock for strict-contained producer intervals. Not pipeline certification.')
    save(REPORT/f'{label}-{scenario}-{trial}.json',d);shutil.copyfile(result/'windows.txt',REPORT/f'{label}-{scenario}-{trial}-windows.txt')
    return d
def topology():
    class Entry(ctypes.Structure):_fields_=[('mask',ctypes.c_size_t),('relationship',ctypes.c_int),('reserved',ctypes.c_uint64*2)]
    api=ctypes.WinDLL('kernel32',use_last_error=True);length=ctypes.c_ulong(0);api.GetLogicalProcessorInformation(None,ctypes.byref(length))
    buffer=ctypes.create_string_buffer(length.value)
    if not api.GetLogicalProcessorInformation(buffer,ctypes.byref(length)):raise ctypes.WinError(ctypes.get_last_error())
    entries=(Entry*(length.value//ctypes.sizeof(Entry))).from_buffer(buffer)
    return [dict(mask=int(e.mask),logical_cpus=[i for i in range(8) if int(e.mask)&(1<<i)]) for e in entries if e.relationship==0]
if __name__=='__main__':
    label=sys.argv[1];threads=int(sys.argv[2]);brain_cpus=list(map(int,sys.argv[3].split(',')));worker_cpus=list(map(int,sys.argv[4].split(',')))
    # A metadata file is written only AFTER compilation/link completes.
    zero=len(sys.argv)>5 and sys.argv[5]=='zero';suffix='-zero' if zero else ''
    assert all((REPORT/f'd1-build-{threads}t-{s}{suffix}.json').exists() for s in ['baseline','looming']), 'Finish all builds before concurrency measurements'
    records=[]
    for scenario in ['baseline','looming']:
        for trial in range(3):
            d=run_trial(label,threads,brain_cpus,worker_cpus,scenario,trial,zero=zero);records.append(d)
            print(label,scenario,trial,'brain',d['brain_statistics']['p99_ms'],'producer',d['producer_statistics']['p99_ms'],flush=True)
    headroom=all(d['brain_statistics']['p99_ms']<=35 and d['producer_statistics']['p99_ms']<=35 for d in records)
    marginal=all(d['brain_statistics']['p99_ms']<=50 and d['producer_statistics']['p99_ms']<=50 for d in records)
    save(REPORT/(label+'-decision.json'),dict(headroom=headroom,realtime_feasible=marginal,trials=[f"{label}-{d['scenario']}-{d['trial']}.json" for d in records],brain_cpus=brain_cpus,worker_cpus=worker_cpus,threads=threads))
    if not headroom:save(REPORT/'cpu-topology-after-contention.json',dict(reason='D1 measured insufficient headroom/jitter; now inspect actual SMT layout',physical_cores=topology()))
