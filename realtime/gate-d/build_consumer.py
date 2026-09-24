"""D1 preloaded exact noise consumer; no producer/consumer buffer yet."""
import importlib.util,json,shutil,sys,time
import numpy as np
from env import ROOT,WORK,REPORT,OLD,Brain,sha,save
spec=importlib.util.spec_from_file_location('verified_translation',ROOT/'realtime/gate-b/engine.py');engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
b=engine.b
if __name__=='__main__':
    threads=int(sys.argv[1]);scenario=sys.argv[2];zero=len(sys.argv)>3 and sys.argv[3]=='zero';assert threads in [1,2] and scenario in ['baseline','looming']
    original=engine.setup
    def setup(path):
        original(path);b.prefs.devices.cpp_standalone.openmp_threads=threads if threads>1 else 0
    engine.setup=setup;engine.WORK=OLD
    cfg=json.loads((ROOT/'config.json').read_text());brain=Brain.load(ROOT/'data/runtime',cfg);initial=np.load(OLD/'initial.npz');brain.baseline=initial['baseline'].copy()
    groups={k:initial['group_'+k] for k in ['LC4','LPLC2','GF','DNp09']};inputs=np.load(OLD/'inputs.npz')
    suffix='-zero' if zero else '';directory=WORK/f'd1-{threads}t-{scenario}{suffix}-cpp';start=time.perf_counter()
    g,s,net,spikes=engine.create(brain,groups,inputs['pool'],inputs[scenario][:40]@inputs['matrix'],directory,'frozen',cfg['experiment']['seed'])
    header=directory/'gate_hooks.h';text=header.read_text();a=text.index('inline double gate_noise_read()');z=text.index('\n        }',a)+10
    replacement='''inline std::vector<float> gate_d_noise;
inline float* gate_d_owned_noise=nullptr;
inline long long gate_d_step=0;
inline double gate_noise_read() {
    if(gate_d_step>=2000)throw std::runtime_error("Nonperiodic shared noise exhausted");
    std::memcpy(brian::_array_neurons_noise_sample,gate_d_noise.data()+gate_d_step*165122LL,165122*4);
    ++gate_d_step;return 0;
}
inline double gate_d_qpc() {LARGE_INTEGER c,f;QueryPerformanceCounter(&c);QueryPerformanceFrequency(&f);return double(c.QuadPart)/f.QuadPart;}
'''
    if zero:
        replacement=replacement.replace('std::memcpy(brian::_array_neurons_noise_sample,gate_d_noise.data()+gate_d_step*165122LL,165122*4);','brian::_array_neurons_noise_sample=gate_d_noise.data()+gate_d_step*165122LL;')
    header.write_text('#ifndef WIN32_LEAN_AND_MEAN\n#define WIN32_LEAN_AND_MEAN\n#endif\n#include <windows.h>\n#include <cstring>\n'+text[:a]+replacement+text[z:])
    b.device.insert_code('main','''gate_d_noise.resize(2000LL*165122);
gate_b::noise_file.read(reinterpret_cast<char*>(gate_d_noise.data()),2000LL*165122*4);
if(!gate_b::noise_file)throw std::runtime_error("Tape preload");gate_b::noise_file.close();gate_d_owned_noise=brian::_array_neurons_noise_sample;''')
    if zero:b.device.insert_code('before_end','std::memcpy(gate_d_owned_noise,brian::_array_neurons_noise_sample,165122*4);brian::_array_neurons_noise_sample=gate_d_owned_noise;')
    b.device.insert_code('before_network_run','''
{std::ofstream f(brian::results_dir+"ready");f<<GetCurrentProcessId();}
while(GetFileAttributesA((brian::results_dir+"go").c_str())==INVALID_FILE_ATTRIBUTES)Sleep(1);
{DWORD_PTR processmask,systemmask;GetProcessAffinityMask(GetCurrentProcess(),&processmask,&systemmask);
std::ofstream f(brian::results_dir+"affinity");f<<processmask;}
{std::ofstream f(brian::results_dir+"compute-start");f.precision(17);f<<gate_d_qpc();}
gate_b::window_start=gate_b::GateClock::now();simulation_started=gate_b::window_start;
''')
    b.device.insert_code('after_network_run','{std::ofstream f(brian::results_dir+"compute-done");f.precision(17);f<<gate_d_qpc();}')
    net.run(2*b.second,namespace={});model=time.perf_counter()-start
    start=time.perf_counter();b.device.build(directory=str(directory),compile=False,run=False);codegen=time.perf_counter()-start
    start=time.perf_counter();b.device.compile_source(str(directory),'mingw32',False,False);compile_time=time.perf_counter()-start
    save(REPORT/f'd1-build-{threads}t-{scenario}{suffix}.json',dict(executable=str(directory/'main.exe'),neurons=brain.n,synapses=brain.w.nnz,threads=threads,scenario=scenario,neural_seconds=2,zero_copy_noise_row=zero,
        model=brain.p,weights_sha256=sha(ROOT/'data/runtime/weights.npz'),initial_sha256=sha(OLD/'initial.npz'),input_sha256=sha(OLD/'inputs.npz'),noise_sha256=sha(OLD/'noise-b0-float32.bin'),
        translation_sha256=sha(ROOT/'realtime/gate-b/engine.py'),model_setup_seconds=model,codegen_seconds=codegen,compile_seconds=compile_time,executable_sha256=sha(directory/'main.exe'),
        timing='Persistent actual 2s, 40 nonperiodic exact noise windows; offline preload and controller wait outside simulation clocks; baseline/strong LC4+LPLC2 schedule unchanged.',
        source_sha256={str(p.relative_to(directory)):sha(p) for p in directory.rglob('*') if p.suffix in ['.cpp','.h']}))
    proof=REPORT/'generated-proof'/directory.name;proof.mkdir(parents=True,exist_ok=True)
    for name in ['main.cpp','objects.h','gate_hooks.h','makefile','code_objects/lif_update_codeobject.cpp']:shutil.copyfile(directory/name,proof/name.split('/')[-1])
    print('BUILT',threads,scenario,flush=True)
