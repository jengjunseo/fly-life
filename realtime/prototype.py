"""Brian2 spike-triggered C++ standalone translation of Brain.step (noise-off only)."""
import os
import time
import numpy as np
import brian2 as b
from common import COMPILER


def setup(directory):
    os.environ['PATH'] = str(COMPILER) + os.pathsep + os.environ['PATH']
    b.prefs.core.default_float_dtype = np.float32
    b.prefs.codegen.cpp.compiler = 'mingw32'
    # Brian2 has no default release flags for the distutils mingw32 identifier.
    # Ordinary release build, NOT fast-math (preserve signed arithmetic/finiteness).
    b.prefs.codegen.cpp.extra_compile_args = ['-O3', '-march=native', '-std=c++11']
    b.prefs.devices.cpp_standalone.make_cmd_unix = 'mingw32-make'
    # OpenMP disabled: one CPU thread; no alternate backend, no parameter tuning.
    b.set_device('cpp_standalone', directory=str(directory), build_on_run=False)
    b.defaultclock.dt = 1*b.ms


def translate(brain, external, record, directory):
    setup(directory)
    p = brain.p
    assert p['noise_std'] == 0 and p['dt_ms'] == 1
    namespace = dict(decay=brain.syn_decay, activity_decay=brain.activity_decay,
        activity_jump=np.float32((1-brain.activity_decay)*np.float32(1000/p['dt_ms'])),
        alpha=np.float32(p['dt_ms']/p['tau_m_ms']), rest=np.float32(p['rest']),
        reset_value=np.float32(p['reset']), threshold_value=np.float32(p['threshold']),
        refractory_steps=brain.refractory_steps, gain=np.float32(p['recurrent_gain']))
    g = b.NeuronGroup(brain.n, '''
        v : 1
        syn : 1
        incoming : 1
        activity : 1
        baseline : 1 (constant)
        external : 1
        eligible : integer
        ref_steps : integer
        ''', threshold='eligible > 0 and v >= threshold_value',
        reset='v = reset_value; ref_steps = refractory_steps; activity += activity_jump',
        namespace=namespace, name='neurons')
    g.v = brain.v; g.syn = brain.syn; g.baseline = brain.baseline
    g.external = external; g.ref_steps = brain.refractory; g.activity = brain.activity
    # Consume previous threshold buffer BEFORE it is overwritten this timestep.
    # Accumulate W@previous_spikes first; then gain * sum, matching reference ordering.
    clear = g.run_regularly('incoming = 0', when='start', name='clear_incoming')
    syn = b.Synapses(g, g, 'w : 1 (constant)', on_pre='incoming_post += w', name='connections')
    syn.connect(i=brain.w.indices, j=np.repeat(np.arange(brain.n, dtype=np.int32), np.diff(brain.w.indptr)))
    syn.w = brain.w.data
    syn.pre.when = 'before_groups'; syn.pre.order = -1
    update = g.run_regularly('''
        syn = syn * decay
        syn += gain * incoming
        eligible = int(ref_steps == 0)
        ref_steps -= int(ref_steps > 0)
        drive = baseline + syn
        drive += external
        v = v + eligible * alpha * (rest - v + drive)
        v = eligible * v + (1 - eligible) * reset_value
        activity = activity * activity_decay
        ''', when='groups', order=0, name='lif_update')
    spikes = b.SpikeMonitor(g, name='spikes')
    states = b.StateMonitor(g, ['activity', 'v', 'syn', 'ref_steps'] if brain.n < 100 else ['activity'],
                           record=record, when='end', name='states')
    net = b.Network(g, clear, syn, update, spikes, states)
    # std::chrono wall timers (Brian's default single-thread timer is std::clock).
    b.device.insert_code('before_start', 'auto gate_started = std::chrono::steady_clock::now(); auto gate_run_start = gate_started; bool gate_first = true;')
    b.device.insert_code('main', '''
        std::ofstream gate_timing(brian::results_dir + "gate_timing.txt");
        gate_timing.precision(17);
        ''')
    b.device.insert_code('before_network_run', '''
        if (gate_first) {
            gate_timing << "init " << std::chrono::duration<double>(std::chrono::steady_clock::now()-gate_started).count() << std::endl;
            gate_first = false;
        }
        gate_run_start = std::chrono::steady_clock::now();
        ''')
    b.device.insert_code('after_network_run', '''
        gate_timing << "run " << std::chrono::duration<double>(std::chrono::steady_clock::now()-gate_run_start).count() << std::endl;
        ''')
    b.prefs.codegen.cpp.headers += ['<chrono>']
    return g, syn, net, spikes, states


def build(directory):
    t = time.perf_counter()
    b.device.build(directory=str(directory), compile=True, run=False)
    return dict(build_wall_seconds=time.perf_counter()-t, device_timers=b.device.timers)
