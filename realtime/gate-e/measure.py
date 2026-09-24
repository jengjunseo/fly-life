import ctypes, importlib.util, json, os, shutil, subprocess, sys, time
import numpy as np
import psutil
from env import ROOT, WORK, REPORT, COMPILER, Brain, save, sha
spec=importlib.util.spec_from_file_location('gate_d_producer',ROOT/'realtime/gate-d/producer.py')
pd=importlib.util.module_from_spec(spec);spec.loader.exec_module(pd)

class PowerCounter:
    def __init__(self):
        self.error=None;self.samples=[]
        try:
            self.api=ctypes.WinDLL('pdh');self.query=ctypes.c_void_p();self.counter=ctypes.c_void_p()
            assert self.api.PdhOpenQueryW(None,0,ctypes.byref(self.query))==0
            self.api.PdhAddEnglishCounterW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_void_p)]
            status=self.api.PdhAddEnglishCounterW(self.query,r'\Processor Information(_Total)\% Processor Performance',0,ctypes.byref(self.counter))
            assert status==0, f'PDH add {status}'
            self.api.PdhCollectQueryData(self.query)
        except Exception as e:self.error=repr(e)
    def sample(self):
        if self.error:return
        class Value(ctypes.Structure):
            _fields_=[('status',ctypes.c_ulong),('value',ctypes.c_double)]
        try:
            self.api.PdhCollectQueryData(self.query);v=Value()
            self.api.PdhGetFormattedCounterValue.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_void_p,ctypes.POINTER(Value)]
            status=self.api.PdhGetFormattedCounterValue(self.counter,0x200,None,ctypes.byref(v))
            if status==0 and v.status in [0,1]:self.samples.append(dict(qpc=time.perf_counter(),processor_performance_percent=v.value))
        except Exception as e:self.error=repr(e)
    def close(self):
        if getattr(self,'query',None):
            self.api.PdhCloseQuery.argtypes=[ctypes.c_void_p];self.api.PdhCloseQuery(self.query)

def wait_file(path,child):
    started=time.perf_counter()
    while not path.exists() or path.stat().st_size==0:
        if child.poll() is not None:raise RuntimeError(f'Child exited {child.returncode} before {path.name}')
        if time.perf_counter()-started>120:raise TimeoutError(str(path))
        time.sleep(.005)

def run(tag,trial,cpus,worker_cpus=None):
    meta=json.loads((REPORT/(tag+'-build.json')).read_text());label=tag+('-on' if worker_cpus else '-off')+f'-{trial}'
    result=WORK/label;result.mkdir(exist_ok=False);exe=__import__('pathlib').Path(meta['executable'])
    process_env=os.environ.copy();process_env['PATH']=str(COMPILER)+os.pathsep+process_env['PATH']
    producer=pd.Producer(20260913,2,worker_cpus) if worker_cpus else None
    if producer:
        for _ in range(10):producer.fill()
    logs=(REPORT/(label+'-console.txt')).open('w');child=subprocess.Popen([str(exe),'--results_dir',str(result)+'\\'],cwd=exe.parent,env=process_env,stdout=logs,stderr=subprocess.STDOUT)
    intervals=[];rss=[];counter=PowerCounter();last_sample=0
    try:
        wait_file(result/'ready',child);assert int((result/'ready').read_text())==child.pid
        proc=psutil.Process(child.pid);proc.cpu_affinity(cpus);proc.nice(psutil.HIGH_PRIORITY_CLASS)
        actual=proc.cpu_affinity();priority=proc.nice();assert actual==sorted(cpus) and priority==psutil.HIGH_PRIORITY_CLASS
        # Producer process priority is scoped to this disposable controller.
        if producer:psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS)
        (result/'go').write_text('go');started=time.perf_counter()
        while not (result/'compute-done').exists():
            if child.poll() is not None:raise RuntimeError('Consumer exited during compute')
            if time.perf_counter()-started>120:raise TimeoutError('Owned benchmark compute timeout')
            if producer:
                a=time.perf_counter();elapsed=producer.fill();z=time.perf_counter();intervals.append(dict(start=a,end=z,generation_ms=elapsed))
            else:time.sleep(.01)
            rss.append(proc.memory_info().rss)
            if time.perf_counter()-last_sample>.25:counter.sample();last_sample=time.perf_counter()
        child.wait(timeout=30);assert child.returncode==0
    finally:
        if producer:producer.close()
        if child.poll() is None:child.kill();child.wait()
        counter.close();logs.close()
    raw=np.loadtxt(result/'windows.txt');warm=500//meta['quantum'];steady=raw[warm:]
    begin=float((result/'compute-start').read_text());end=float((result/'compute-done').read_text())
    contained=[i for i in intervals if i['start']>=begin and i['end']<=end]
    stat=pd.statistics(steady[:,3]);stat['deadline_misses']=int(np.sum(steady[:,3]>meta['quantum']));stat['deadline_miss_rate']=stat['deadline_misses']/len(steady)
    if meta['quantum']==100:stat['neural_wall_ratio']=100/stat['mean_ms']
    # Inspect all dynamics states after run, independently of timed boundary checks.
    final={};finite=True
    for name,dtype in [('v',np.float32),('syn',np.float32),('activity',np.float32),('noise_sample',np.float32),('ref_steps',np.int32),('eligible',np.int32)]:
        paths=list(result.glob('_array_neurons_'+name+'_*'));assert len(paths)==1
        arr=np.fromfile(paths[0],dtype=dtype);finite=finite and bool(np.isfinite(arr).all())
        final[name]=dict(sha256=sha(paths[0]),min=float(arr.min()),max=float(arr.max()))
    timings={k:float(v) for k,v in (l.split() for l in (result/'timing.txt').read_text().splitlines())}
    profile=[]
    if meta['profile']:
        # Brian2 standalone's supported native output from profile=True.
        for line in (result/'profiling_info.txt').read_text().splitlines():
            name,value=line.split();profile.append(dict(codeobject=name,seconds=float(value),calls=meta['seconds']*1000))
        total=sum(x['seconds'] for x in profile)
        for x in profile:x['percent']=100*x['seconds']/total if total else 0
        profile.sort(key=lambda x:x['seconds'],reverse=True)
        shutil.copyfile(result/'profiling_info.txt',REPORT/(label+'-profiling_info.txt'))
    d=dict(label=label,tag=tag,trial=trial,threads=meta['threads'],scenario=meta['scenario'],variant=meta['variant'],profiled=meta['profile'],
        seconds=meta['seconds'],quantum_ms=meta['quantum'],warmup_windows=warm,brain_pid=child.pid,brain_cpus=actual,
        brain_affinity_mask=int((result/'affinity').read_text()),priority_class=int(priority),brain_statistics=stat,
        producer_statistics=pd.statistics([x['generation_ms'] for x in contained]) if contained else None,
        producer=producer.metadata() if producer else None,producer_intervals=intervals,compute_start_qpc=begin,compute_done_qpc=end,
        timings=timings,profile=profile,final_state=final,finite=finite,max_spiking_fraction=float(raw[:,7].max()/165122),
        peak_consumer_sampled_rss=max(rss),python_os_peak_rss=psutil.Process().memory_info().peak_wset,
        power_counter=dict(error=counter.error,samples=counter.samples,qualification='PDH _Total Processor Performance percent, not per-core direct frequency; no OS plan modification'),
        noise_qualification=meta['noise_qualification'],producer_output='Discarded: concurrent feasibility, no streaming pipeline' if producer else None)
    save(REPORT/(label+'.json'),d);shutil.copyfile(result/'windows.txt',REPORT/(label+'-windows.txt'))
    print(label,stat['mean_ms'],stat['p99_ms'],d['producer_statistics']['p99_ms'] if contained else 'OFF',flush=True)
    return d

if __name__=='__main__':
    tag=sys.argv[1];trial=int(sys.argv[2]);cpus=list(map(int,sys.argv[3].split(',')))
    workers=list(map(int,sys.argv[4].split(','))) if len(sys.argv)>4 else None
    run(tag,trial,cpus,workers)
