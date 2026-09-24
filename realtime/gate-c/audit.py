"""C0 source/artifact audit, no optimized simulation and no old report mutations."""
import json,re,shutil
import numpy as np
from env import ROOT,REPORT,WORK,OLD,Brain,sha,save,machine
if __name__=='__main__':
    cfg=json.loads((ROOT/'config.json').read_text());brain=Brain.load(ROOT/'data/runtime',cfg)
    old_report=ROOT/'reports/realtime/gate-b'
    frozen=json.loads((old_report/'b0-frozen.json').read_text());native=json.loads((old_report/'b0-native.json').read_text())
    tape=json.loads((old_report/'noise-tape.json').read_text())
    generated=OLD/'b0-frozen-cpp';source=(generated/'main.cpp').read_text()
    run_seconds=float(re.search(r'network\.run\(([0-9.]+),',source).group(1))
    initial=np.load(OLD/'initial.npz');assert np.array_equal(brain.baseline,initial['baseline'])
    checks=dict(duration_2s=run_seconds==2 and frozen['statistics']['neural_seconds']==2,
        neurons=frozen['neurons']==brain.n==165122,synapses=frozen['effective_connections']==brain.w.nnz==6327564,
        full_graph_verified=frozen['full_connection_arrays_verified'] and native['full_connection_arrays_verified'],
        runtime_weights_sha_match=frozen['weights_sha256']==sha(ROOT/'data/runtime/weights.npz'),
        same_initial=frozen['initial_sha256']==native['initial_sha256']==sha(OLD/'initial.npz'),
        same_inputs=frozen['inputs_sha256']==native['inputs_sha256']==sha(OLD/'inputs.npz'),
        tape_sha_match=tape['sha256']==sha(OLD/'noise-b0-float32.bin'),
        model_dt_1ms=brain.p['dt_ms']==1 and frozen['dt_ms']==1)
    # Exact actual RNG class extraction: standalone microbenchmark, NOT a new SNN backend.
    objects=(OLD/'baseline-cpp/objects.h').read_text()
    start=objects.index('class RandomGenerator {');end=objects.index('\n};',start)+3
    actual_class=objects[start:end]
    (WORK/'native_rng.h').write_text('#pragma once\n#include <random>\n#include <cmath>\n'+actual_class+'\n',encoding='utf-8')
    # Brian translation imported unchanged; only experimental adapter sets OpenMP preference.
    for name in ['initial.npz','inputs.npz']:shutil.copyfile(OLD/name,WORK/name)
    audit=dict(success=all(checks.values()),checks=checks,machine=machine(),neural_seconds=run_seconds,
        neurons=brain.n,effective_connections=brain.w.nnz,retained_anatomical_connections=6474533,model_parameters=brain.p,
        sign_policy=cfg['sign_policy'],weights_sha256=sha(ROOT/'data/runtime/weights.npz'),
        baseline_sha256=sha(OLD/'initial.npz'),baseline_policy='NumPy2.4 PCG64 seed 20260913, 0.65+0.18*N(0,1) float32, baseline drawn before noise',
        initial_state='v/syn/incoming/spikes/activity=0; refractory=0',
        stimulus='0-.5 warmup; .5-1 baseline; 1-1.5 LC4/LPLC2 current3; 1.5-2 recovery',
        noise_tape=tape,noise_policy='unscaled standard normals [2000,165122] little-endian float32 C-order; read one N row each ms, scale .1f before external current, even refractory',
        propagation='CSR target/source signed weights; previous step spikes before groups; zero Brian path delay implements reference one-step delay',
        frozen_compute_seconds=frozen['timings']['network_compute'],frozen_equivalent_ratio=2/frozen['timings']['network_compute'],
        qualification='Identical full Gate B model. Frozen 2s evidence includes file consumption but excludes noise pre-generation; not sustained realtime certification. C3 will remeasure if C2 fails.',
        native_rng='Actual generated std::mt19937, stored-pair polar Box-Muller, double log/sqrt, float32 cast; one state per OpenMP thread, no locking in randn()',
        rng_class_source_sha256=sha(OLD/'baseline-cpp/objects.h'),extracted_header_sha256=sha(WORK/'native_rng.h'),
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'realtime/gate-b').glob('*.py')})
    save(REPORT/'c0-audit.json',audit);print(json.dumps({k:v for k,v in audit.items() if k not in ['noise_tape','source_sha256']},indent=2));raise SystemExit(not audit['success'])
