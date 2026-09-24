import json, subprocess
from env import ROOT, REPORT, WORK, sha, save, machine

if __name__ == '__main__':
    droot=ROOT.parents[1]/'work/brian2-gate-d/d1-1t-looming-cpp'
    make=(droot/'makefile').read_text()
    assert '-O3' in make and '-march=native' in make and '-ffast-math' not in make
    # Read the actual generated rules. Do not invoke make in frozen old work:
    # GNU make may regenerate included dependency files even under -n.
    commands=make
    (REPORT/'existing-generated-build-commands.txt').write_text(commands,encoding='utf-8')
    hooks=(droot/'gate_hooks.h').read_text();main=(droot/'main.cpp').read_text()
    assert 'gate_d_noise.resize(2000LL*165122)' in main
    assert 'gate_d_noise.data()+gate_d_step*165122LL' in hooks
    engine=(ROOT/'realtime/gate-b/engine.py').read_text()
    assert "syn=b.Synapses(g,g,'w : 1 (constant)',on_pre='incoming_post += w',name='connections')" in engine
    d=dict(machine=machine(),active_power_plan=subprocess.check_output(['powercfg','/getactivescheme']).decode('utf-8',errors='replace').strip(),
           power_plan_changed=False,priority_policy='HIGH_PRIORITY_CLASS on owned benchmark processes only; never REALTIME',
           compile_flag_status='COMPILE FLAG OPTIMIZATION: ALREADY SATISFIED',flags='-O3 -march=native -std=c++17; no unsafe math flags',
           generated_makefile_sha256=sha(droot/'makefile'),actual_build_commands_sha256=sha(REPORT/'existing-generated-build-commands.txt'),
           build_command_source='Actual generated makefile OPTIMISATIONS/CXXFLAGS and compile rule, not assumed library defaults; new E build consoles record executed commands',
           noise_path='Full 2s tape preloaded into C++ vector before Network.run; each 1ms step reads next row in C++ memory; no per-step Python callback/IPC/file read',
           roundtrip_status='NO PER-STEP PYTHON ROUNDTRIP',delay_status='No explicit delay assignment; Brian2 default zero delay, existing previous-spike scheduling preserved',
           monitors='SpikeMonitor(record=False), cumulative count-only all neurons; no StateMonitor or PopulationRateMonitor. Certification custom boundary scans v/syn and spike counts each50ms; small circuit activity sampled each1ms.',
           no_redundant_flag_or_timedarray_redesign=True)
    save(REPORT/'e0-audit.json',d);print(json.dumps(d,ensure_ascii=True,indent=2))
