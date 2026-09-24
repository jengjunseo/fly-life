"""Minimal Gate B extension of frozen Gate A, generated Brian2 C++ neural simulation."""
import time
import numpy as np
import brian2 as b
from env import ROOT,WORK,REPORT
from prototype import setup


def create(brain,groups,pool,stimuli,directory,noise,seed,record_spikes=False):
    setup(directory);p=brain.p;b.seed(seed)
    ns=dict(decay=brain.syn_decay,activity_decay=brain.activity_decay,
        activity_jump=np.float32((1-brain.activity_decay)*np.float32(1000)),alpha=np.float32(p['dt_ms']/p['tau_m_ms']),
        rest=np.float32(p['rest']),reset_value=np.float32(p['reset']),threshold_value=np.float32(p['threshold']),
        refractory_steps=brain.refractory_steps,gain=np.float32(p['recurrent_gain']),noise_amplitude=np.float32(p['noise_std']))
    g=b.NeuronGroup(brain.n,'''v : 1
        syn : 1
        incoming : 1
        activity : 1
        baseline : 1 (constant)
        external : 1
        noise_sample : 1
        eligible : integer
        ref_steps : integer''',threshold='eligible > 0 and v >= threshold_value',
        reset='v = reset_value; ref_steps = refractory_steps; activity += activity_jump',namespace=ns,name='neurons')
    g.baseline=brain.baseline;g.v=brain.v;g.syn=brain.syn;g.ref_steps=brain.refractory;g.activity=brain.activity
    g.external=0
    clear=g.run_regularly('incoming = 0',when='start',order=-2,name='clear_incoming')
    syn=b.Synapses(g,g,'w : 1 (constant)',on_pre='incoming_post += w',name='connections')
    syn.connect(i=brain.w.indices,j=np.repeat(np.arange(brain.n,dtype=np.int32),np.diff(brain.w.indptr)));syn.w=brain.w.data
    syn.pre.when='before_groups';syn.pre.order=-1
    noise_code=''
    if noise=='native':noise_code='noise_sample = randn()\nnoise_sample *= noise_amplitude\ndrive += noise_sample'
    if noise=='frozen':noise_code='noise_sample *= noise_amplitude\ndrive += noise_sample'
    update=g.run_regularly('''syn = syn * decay
        syn += gain * incoming
        eligible = int(ref_steps == 0)
        ref_steps -= int(ref_steps > 0)
        drive = baseline + syn
        '''+noise_code+'''
        drive += external
        v = v + eligible * alpha * (rest - v + drive)
        v = eligible * v + (1 - eligible) * reset_value
        activity = activity * activity_decay''',when='groups',order=0,name='lif_update')
    spikes=b.SpikeMonitor(g,record=record_spikes,name='spikes')
    # C++ boundary instrumentation: ticks once at END of each real Brian2 1ms step.
    literal_groups=[]
    for k,idx in groups.items():literal_groups.append(f'static const int group_{k}[] = {{{",".join(map(str,idx))}}};')
    for name in groups:literal_groups.append(f'static double peak_{name}=0, sum_{name}=0;')
    n=brain.n;windows=len(stimuli);k=len(pool)
    support='''
        #include "objects.h"
        #include <chrono>
        #include <fstream>
        #include <cmath>
        #include <stdexcept>
        namespace gate_b {
            typedef std::chrono::steady_clock GateClock;
            static GateClock::time_point begun, window_start, output_start;
            static std::ofstream windows_file, timing_file;
            static std::ifstream noise_file;
            static long long step=0, quantum_spikes=0, max_sync=0;
            static bool finite=true;
            static double wall_sum=0;
            static long long previous_population=0;
            static std::vector<float> input;
            static std::vector<int> pool;
            '''+'\n'.join(literal_groups)+'''
        }
        double gate_tick() {
            using namespace gate_b;
            ++step;
            long long sync=brian::_array_neurons__spikespace['''+str(n)+'''];
            quantum_spikes+=sync;if(sync>max_sync)max_sync=sync;
            '''
    for name,idx in groups.items():
        support+=f'''{{double ema=0;for(int i:group_{name})ema+=brian::_array_neurons_activity[i];ema/={len(idx)};
            sum_{name}+=ema;if(ema>peak_{name})peak_{name}=ema;}}\n'''
    support+='''
            if(step % 50 != 0) return 0;
            auto finish=GateClock::now();
            double ms=std::chrono::duration<double,std::milli>(finish-window_start).count();wall_sum+=ms;
            long long cumulative=0, active=0;
            for(int i=0;i<'''+str(n)+''';++i) {
                cumulative+=brian::_array_spikes_count[i];active+=brian::_array_spikes_count[i]>0;
                finite=finite && std::isfinite(brian::_array_neurons_v[i]) && std::isfinite(brian::_array_neurons_syn[i]);
            }
            windows_file << step/50-1 << " " << (step-50)*.001 << " " << step*.001 << " " << ms << " " << quantum_spikes << " " << cumulative << " " << active << " " << max_sync << " " << finite;
            '''
    for name,idx in groups.items():
        support+=f'''
            {{long long count=0,active_group=0;double ema=0;
            for(int i:group_{name}){{count+=brian::_array_spikes_count[i];active_group+=brian::_array_spikes_count[i]>0;ema+=brian::_array_neurons_activity[i];}}
            windows_file << " " << count << " " << ema/{len(idx)} << " " << active_group << " " << peak_{name} << " " << sum_{name}/50;
            peak_{name}=0;sum_{name}=0;}}
        '''
    support+='''
            windows_file << std::endl;
            quantum_spikes=0;
            if(step/50 < '''+str(windows)+''') {
                for(int j=0;j<'''+str(k)+''';++j)brian::_array_neurons_external[pool[j]]=input[(step/50)*'''+str(k)+'''+j];
            }
            // Boundary statistics/output/input maintenance excluded from EACH compute timer;
            // whole Network.run timer also reported, including maintenance.
            window_start=GateClock::now();
            return 0;
        }
        double gate_noise_read() {
            gate_b::noise_file.read(reinterpret_cast<char*>(brian::_array_neurons_noise_sample),'''+str(n*4)+''');
            if(!gate_b::noise_file)throw std::runtime_error("Shared noise tape exhausted");
            return 0;
        }
        '''
    @b.implementation('cpp','#include "gate_hooks.h"')
    @b.check_units(result=1)
    def gate_tick():return 0.
    @b.implementation('cpp','#include "gate_hooks.h"')
    @b.check_units(result=1)
    def gate_noise_read():return 0.
    # A 1-neuron CodeRunner calls each scalar native hook exactly once per ms.
    clock=b.NeuronGroup(1,'dummy : 1',name='boundary',namespace={'gate_tick':gate_tick,'gate_noise_read':gate_noise_read})
    tick=clock.run_regularly('dummy = gate_tick()',when='end',order=1000,name='quantum_boundary')
    objects=[g,clear,syn,update,spikes,clock,tick]
    if noise=='frozen':
        reader=clock.run_regularly('dummy = gate_noise_read()',when='start',order=-1,name='shared_noise_reader');objects.append(reader)
    # Initializing custom global streams outside CodeObject support would require headers;
    # main includes the SAME dedicated instrumentation header generated below.
    header=directory/'gate_hooks.h';directory.mkdir(parents=True,exist_ok=True)
    header.write_text('#pragma once\n'+support,encoding='utf-8')
    # Each CodeObject gets header declarations instead of duplicate support definitions.
    # Global definitions must be single across translation units. Header uses inline functions
    # and C++17 inline variables (instrumentation only, not neural arithmetic).
    content=header.read_text().replace('static ','inline ').replace('double gate_tick()', 'inline double gate_tick()').replace('double gate_noise_read()', 'inline double gate_noise_read()')
    header.write_text(content,encoding='utf-8')
    b.prefs.codegen.cpp.extra_compile_args=['-O3','-march=native','-std=c++17']
    b.prefs.codegen.cpp.headers+=['"gate_hooks.h"']
    stimfile=directory/'stimulus.bin';poolfile=directory/'pool.bin'
    np.asarray(stimuli,np.float32).tofile(stimfile);np.asarray(pool,np.int32).tofile(poolfile)
    def literal(path):return '"'+str(path.resolve()).replace('\\','/')+'"'
    b.device.insert_code('before_start','gate_b::begun = gate_b::GateClock::now();')
    b.device.insert_code('main',f'''
        gate_b::windows_file.open(brian::results_dir+"windows.txt");gate_b::windows_file.precision(17);
        gate_b::timing_file.open(brian::results_dir+"timing.txt");gate_b::timing_file.precision(17);
        gate_b::input.resize({windows*k});gate_b::pool.resize({k});
        {{std::ifstream f({literal(stimfile)},std::ios::binary);f.read(reinterpret_cast<char*>(gate_b::input.data()),{windows*k*4});if(!f)throw std::runtime_error("input read");}}
        {{std::ifstream f({literal(poolfile)},std::ios::binary);f.read(reinterpret_cast<char*>(gate_b::pool.data()),{k*4});if(!f)throw std::runtime_error("pool read");}}
        for(int j=0;j<{k};++j)brian::_array_neurons_external[gate_b::pool[j]]=gate_b::input[j];
        '''+(f'gate_b::noise_file.open({literal(WORK/"noise-b0-float32.bin")},std::ios::binary);' if noise=='frozen' else ''))
    b.device.insert_code('before_network_run','''
        gate_b::timing_file << "init " << std::chrono::duration<double>(gate_b::GateClock::now()-gate_b::begun).count() << std::endl;
        gate_b::window_start = gate_b::GateClock::now();
        auto simulation_started = gate_b::window_start;
        ''')
    b.device.insert_code('after_network_run','''
        gate_b::timing_file << "network_compute " << std::chrono::duration<double>(gate_b::GateClock::now()-simulation_started).count() << std::endl;
        gate_b::timing_file << "windows_compute " << gate_b::wall_sum*.001 << std::endl;
        ''')
    b.device.insert_code('before_end','gate_b::output_start = gate_b::GateClock::now();')
    b.device.insert_code('after_end','gate_b::timing_file << "brian_output " << std::chrono::duration<double>(gate_b::GateClock::now()-gate_b::output_start).count() << std::endl;')
    return g,syn,b.Network(*objects),spikes
