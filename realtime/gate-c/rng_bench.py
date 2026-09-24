import json,os,shutil,subprocess,sys,time
from env import ROOT,WORK,REPORT,COMPILER,sha,save,machine
if __name__=='__main__':
    threads=int(sys.argv[1]);assert threads in [1,2,4,8]
    os.environ['PATH']=str(COMPILER)+os.pathsep+os.environ['PATH']
    source=ROOT/'realtime/gate-c/rng_only.cpp';exe=WORK/'rng-only.exe'
    compilation=None
    if not exe.exists():
        started=time.perf_counter()
        command=[str(COMPILER/'g++.exe'),str(source),'-I'+str(WORK),'-O3','-march=native','-std=c++17','-fopenmp','-o',str(exe)]
        result=subprocess.run(command,capture_output=True,text=True);(REPORT/'rng-compile-console.txt').write_text(result.stdout+result.stderr)
        result.check_returncode();compilation=time.perf_counter()-started
    result=subprocess.run([str(exe),str(threads)],capture_output=True,text=True);result.check_returncode()
    (REPORT/f'rng-{threads}t-raw.txt').write_text(result.stdout)
    trials=[]
    for line in result.stdout.splitlines():
        t,actual,trial,samples,wall,warm,check=line.split();samples=int(samples);wall=float(wall)
        trials.append(dict(trial=int(trial),actual_threads=int(actual),samples=samples,wall_seconds=wall,samples_per_second=samples/wall,equivalent_neural_wall_ratio=1/wall,warmup_seconds=float(warm),checksum=float(check)))
    save(REPORT/f'rng-{threads}t.json',dict(threads=threads,trials=trials,mean_samples_per_second=sum(x['samples_per_second'] for x in trials)/len(trials),mean_equivalent_neural_wall_ratio=sum(x['equivalent_neural_wall_ratio'] for x in trials)/len(trials),compile_seconds=compilation,machine=machine(),mechanism='Unmodified actual Brian2 generated RandomGenerator class; N=165122 float32 stores per step, 50 warmup steps, 1000 measured steps per trial, no neural computation; per-thread states and omp static loop',source_sha256=sha(source),rng_header_sha256=sha(WORK/'native_rng.h'),executable_sha256=sha(exe)))
    print(json.dumps(trials,indent=2))
