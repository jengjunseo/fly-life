"""Unchanged Gate B neural translation with Gate E-only benchmark hooks."""
import importlib.util, json, shutil, sys, time
import numpy as np
from env import ROOT, WORK, REPORT, OLD, Brain, sha, save
spec=importlib.util.spec_from_file_location('gate_e_verified_translation',ROOT/'realtime/gate-b/engine.py')
engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
b=engine.b

if __name__ == '__main__':
    threads=int(sys.argv[1]);scenario=sys.argv[2];profile=bool(int(sys.argv[3]))
    variant=sys.argv[4] if len(sys.argv)>4 else 'current'
    seconds=int(sys.argv[5]) if len(sys.argv)>5 else 2
    quantum=int(sys.argv[6]) if len(sys.argv)>6 else 50
    assert threads in [1,2,4,8] and scenario in ['baseline','looming']
    assert variant in ['current','zero','clear-fused'] and quantum in [50,100]
    tag=f'{variant}-{threads}t-{scenario}-p{int(profile)}-{seconds}s-q{quantum}'
    directory=WORK/(tag+'-cpp');assert not(directory/'main.exe').exists()
    original=engine.setup
    def setup(path):
        original(path);b.prefs.devices.cpp_standalone.openmp_threads=threads if threads>1 else 0
    engine.setup=setup;engine.WORK=OLD
    cfg=json.loads((ROOT/'config.json').read_text());brain=Brain.load(ROOT/'data/runtime',cfg)
    initial=np.load(OLD/'initial.npz');brain.baseline=initial['baseline'].copy()
    groups={k:initial['group_'+k] for k in ['LC4','LPLC2','GF','DNp09']}
    inputs=np.load(OLD/'inputs.npz');windows=seconds*1000//quantum
    # Original strong waveform is steady for the entire 2s. Longer diagnostic
    # holds that same known sensory input; no future world/input calculation.
    base=inputs[scenario][:40]@inputs['matrix']
    stimuli=np.asarray([base[min(i*quantum//50,39)] for i in range(windows)],np.float32)
    start=time.perf_counter()
    g,s,net,spikes=engine.create(brain,groups,inputs['pool'],stimuli,directory,'frozen',cfg['experiment']['seed'])
    if variant=='clear-fused':
        # The incoming scratch accumulator has one consumer, lif_update.
        # Clear it immediately after use instead of a separate full-N pass at
        # next start. Neural arithmetic and previous-spike scheduling unchanged.
        net['clear_incoming'].active=False
        net['lif_update'].abstract_code += '\nincoming = 0'
    header=directory/'gate_hooks.h';text=header.read_text()
    if quantum!=50:
        text=text.replace('step % 50','step % 100').replace('step/50','step/100').replace('(step-50)','(step-100)').replace('sum_LC4/50','sum_LC4/100').replace('sum_LPLC2/50','sum_LPLC2/100').replace('sum_GF/50','sum_GF/100').replace('sum_DNp09/50','sum_DNp09/100')
    a=text.index('inline double gate_noise_read()');z=text.index('\n        }',a)+10
    pointer='brian::_array_neurons_noise_sample=gate_e_noise.data()+row*165122LL;' if variant=='zero' else 'std::memcpy(brian::_array_neurons_noise_sample,gate_e_noise.data()+row*165122LL,165122*4);'
    row='gate_e_step%2000' if seconds>2 else 'gate_e_step'
    replacement=f'''inline std::vector<float> gate_e_noise;
inline float* gate_e_owned_noise=nullptr;
inline long long gate_e_step=0;
inline double gate_noise_read() {{
    const long long row={row};
    if(row>=2000)throw std::runtime_error("Shared noise exhausted");
    {pointer}
    ++gate_e_step;return 0;
}}
inline double gate_e_qpc() {{LARGE_INTEGER c,f;QueryPerformanceCounter(&c);QueryPerformanceFrequency(&f);return double(c.QuadPart)/f.QuadPart;}}
'''
    header.write_text('#ifndef WIN32_LEAN_AND_MEAN\n#define WIN32_LEAN_AND_MEAN\n#endif\n#include <windows.h>\n#include <cstring>\n'+text[:a]+replacement+text[z:],encoding='utf-8')
    b.device.insert_code('main','''gate_e_noise.resize(2000LL*165122);
gate_b::noise_file.read(reinterpret_cast<char*>(gate_e_noise.data()),2000LL*165122*4);
if(!gate_b::noise_file)throw std::runtime_error("Tape preload");gate_b::noise_file.close();gate_e_owned_noise=brian::_array_neurons_noise_sample;''')
    if variant=='zero':
        b.device.insert_code('before_end','std::memcpy(gate_e_owned_noise,brian::_array_neurons_noise_sample,165122*4);brian::_array_neurons_noise_sample=gate_e_owned_noise;')
        if seconds>2:raise ValueError('Do not replay in-place scaled zero-copy tape')
    b.device.insert_code('before_network_run','''
{std::ofstream f(brian::results_dir+"ready");f<<GetCurrentProcessId();}
while(GetFileAttributesA((brian::results_dir+"go").c_str())==INVALID_FILE_ATTRIBUTES)Sleep(1);
{DWORD_PTR pm,sm;GetProcessAffinityMask(GetCurrentProcess(),&pm,&sm);std::ofstream f(brian::results_dir+"affinity");f<<pm;}
{std::ofstream f(brian::results_dir+"compute-start");f.precision(17);f<<gate_e_qpc();}
gate_b::window_start=gate_b::GateClock::now();simulation_started=gate_b::window_start;
''')
    b.device.insert_code('after_network_run','{std::ofstream f(brian::results_dir+"compute-done");f.precision(17);f<<gate_e_qpc();}')
    net.run(seconds*b.second,namespace={},profile=profile);model=time.perf_counter()-start
    start=time.perf_counter();b.device.build(directory=str(directory),compile=False,run=False);codegen=time.perf_counter()-start
    # debug=True here controls compile_source console visibility only; the
    # generated makefile above is already the release build, not DEBUG flags.
    start=time.perf_counter();b.device.compile_source(str(directory),'mingw32',True,False);compilation=time.perf_counter()-start
    flags=(directory/'makefile').read_text();assert '-ffast-math' not in flags
    save(REPORT/(tag+'-build.json'),dict(tag=tag,executable=str(directory/'main.exe'),threads=threads,scenario=scenario,
        profile=profile,variant=variant,seconds=seconds,quantum=quantum,neurons=brain.n,synapses=brain.w.nnz,model=brain.p,
        noise_sha256=sha(OLD/'noise-b0-float32.bin'),translation_sha256=sha(ROOT/'realtime/gate-b/engine.py'),
        timing=dict(model_setup=model,codegen=codegen,compile=compilation),executable_sha256=sha(directory/'main.exe'),
        noise_replay=seconds>2,noise_qualification='Exact nonperiodic shared2s input' if seconds==2 else 'Long timeline diagnostic repeats frozen2s noise; known 40-window input period, not independent20s Gaussian certification',
        source_sha256={str(p.relative_to(directory)):sha(p) for p in directory.rglob('*') if p.suffix in ['.cpp','.h']}))
    proof=REPORT/'generated-proof'/tag;proof.mkdir(parents=True,exist_ok=True)
    for name in ['main.cpp','gate_hooks.h','makefile','code_objects/lif_update_codeobject.cpp','code_objects/connections_pre_codeobject.cpp','code_objects/connections_pre_push_spikes.cpp','code_objects/spikes_codeobject.cpp','network.cpp']:
        shutil.copyfile(directory/name,proof/name.split('/')[-1])
    print('BUILT',tag,flush=True)
