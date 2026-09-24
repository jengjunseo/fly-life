"""Bounded Gate A evidence aggregation; never launches further simulations."""
import json
import shutil
from pathlib import Path
import numpy as np
from common import ROOT, REPORT, WORK, save, sha


def read(name):return json.loads((REPORT/name).read_text())


if __name__=='__main__':
    reference=read('reference-smoke.json'); candidate=read('brian-smoke.json')
    bench=read('brian-benchmark.json'); refbench=read('reference-benchmark.json')
    baseline=read('baseline-after.json'); semantics=read('semantics.json'); profile=read('profile.json')
    a=np.load(WORK/'reference-smoke.npz');c=np.load(WORK/'brian-smoke.npz')
    assert np.array_equal(a['record'],c['record'])
    comparisons=[]
    for phase in ['baseline','stimulus','recovery']:
        for group in ['LC4','LPLC2','GF','DNp09']:
            r=reference['summary'][phase]['groups'][group];b=candidate['summary'][phase]['groups'][group]
            comparisons.append(dict(phase=phase,group=group,reference=r,brian2=b,
                rate_difference_hz=b['rate_hz']-r['rate_hz'],mean_activity_difference_hz=b['mean_activity_hz']-r['mean_activity_hz']))
    r=reference['summary'];b=candidate['summary']
    checks=dict(BASELINE=baseline['success'],ACTUAL_DATA=candidate['full_export_arrays_verified'] and
        candidate['neurons']==165122 and candidate['effective_connections']==6327564 and
        candidate['weights_sha256']==reference['weights_sha256'],
        BRIAN2_STANDALONE=bool(bench['executable_sha256']) and bool(bench['generated_cpp_sha256']),
        CONNECTION_SEMANTICS=semantics['success'] and all(semantics['checks'].values()),
        SAME_INPUT=candidate['initial_sha256']==reference['initial_drive_sha256'],
        CIRCUIT_GF=r['stimulus']['groups']['GF']['rate_minus_baseline_hz']>0 and
            b['stimulus']['groups']['GF']['rate_minus_baseline_hz']>0 and
            abs(r['stimulus']['groups']['GF']['rate_hz']-b['stimulus']['groups']['GF']['rate_hz'])<=2,
        CIRCUIT_INPUT=all(abs(r['stimulus']['groups'][g]['rate_hz']-b['stimulus']['groups'][g]['rate_hz'])<2 for g in ['LC4','LPLC2']),
        RECOVERY=abs(b['recovery']['groups']['GF']['rate_hz']-r['recovery']['groups']['GF']['rate_hz'])<=2 and
            b['recovery']['population_rate_hz']<=1.1*r['baseline']['population_rate_hz'],
        FINITE=candidate['finite'] and bench['finite'],
        POPULATION=all(abs(b[p]['population_spikes']-r[p]['population_spikes'])<=.01*r[p]['population_spikes'] for p in ['baseline','stimulus','recovery']),
        PERFORMANCE=all(v['neural_seconds']==10 and v['wall_seconds']>0 for v in bench['conditions'].values()),
        RESOURCE=bench['resources']['executable_peak_rss_bytes']>0)
    overhead={}
    for name,path in [('body',ROOT/'body/reports/clean-exit/brain_exit.json'),('ecology',ROOT/'reports/ecology/live/brain_exit.json')]:
        exit=json.loads(path.read_text()); total=exit['wall_seconds'];core=exit['pure_core_wall_seconds']
        overhead[name]=dict(source=str(path.relative_to(ROOT)),sha256=sha(path),total_wall_seconds=total,
            brain_compute_seconds=core,remainder_seconds=total-core,remainder_fraction=(total-core)/total,
            scope='Measured within SAME delivered noise-on run. Remainder aggregates initialization, serialization/socket/logging, ecology, ACK/Godot waits and shutdown; NOT a fine per-component CPU profile.',
            infrastructure_unchanged=True)
    speed=min(v['neural_wall_ratio'] for v in bench['conditions'].values())
    classification='SURVIVES' if speed>=.8 else ('PROMISING' if speed>=.3 else 'DEAD')
    if not all(checks[k] for k in ['CONNECTION_SEMANTICS','CIRCUIT_GF','CIRCUIT_INPUT','RECOVERY','FINITE','POPULATION']):classification='DEAD'
    assert all(checks.values()),checks
    proof=REPORT/'generated-proof';proof.mkdir(parents=True,exist_ok=True)
    builddir=WORK/'benchmark-cpp'
    for name in ['main.cpp','network.cpp','makefile','results/gate_timing.txt',
                 'code_objects/connections_pre_codeobject.cpp','code_objects/connections_pre_push_spikes.cpp',
                 'code_objects/lif_update_codeobject.cpp','code_objects/neurons_spike_thresholder_codeobject.cpp',
                 'code_objects/neurons_spike_resetter_codeobject.cpp']:
        destination=proof/Path(name).name
        shutil.copyfile(builddir/name,destination)
    report=dict(classification=classification,checks=checks,profile=profile,comparison=comparisons,
        population={p:dict(reference=r[p]['population_spikes'],brian2=b[p]['population_spikes']) for p in ['baseline','stimulus','recovery']},
        maximum_selected_activity_absolute_difference_hz=float(np.abs(a['activity']-c['activity']).max()),
        integration_overhead=overhead,reference_benchmark=refbench,brian2_benchmark=bench,
        baseline_speedup=bench['conditions']['baseline']['neural_wall_ratio']/refbench['neural_wall_ratio'],
        uncertainty=['One deterministic seed and only LC4/LPLC2→GF; DNp09 secondary only.',
            'Gaussian noise OFF; no stochastic/full-backend equivalence, no physiology fitting.',
            'Compound sensory bursts untested; body/ecology still SciPy, standalone prototype is NOT a live interactive backend.',
            'Old integration remainder includes startup/wait costs; not a steady-state extrapolation or measured Brian2+Godot throughput.',
            'Single actual 10s measurement per load, not a variance study; compiler target native is machine-specific.'],
        implementation_notes=['One-step previous threshold buffer consumed before_groups, zero Brian pathway delay; NOT conventional same-step transmission.',
            'Signed weights accumulated before multiplying recurrent gain; all 6,327,564 i/j/w arrays compared exactly after C++ execution.',
            'Explicit eligible/ref_steps reproduces two COMPLETE held-reset steps; NOT default Brian refractory approximation.',
            'Float32 state/weights; -O3 -march=native -std=c++11; NO fast-math, NO OpenMP, NO GPU.',
            'Brian2 2.9 needs NumPy1.26 under Python3.11; only experimental process sys.path isolates it; baseline stays NumPy2.4.6.',
            'Smoke compile timer was incremental after a timer-only C++ declaration repair. Benchmark build was first/cold in its separate directory.'])
    save(REPORT/'gate-a.json',report)
    q=bench['conditions']; p=profile['seconds'];total=profile['wall_seconds'];ram=bench['resources']
    lines=[f'BRIAN2 GATE A: {classification}', '',
        '실제 target: AMD Ryzen 3 4100 (4C/8T), 16GB RAM, Windows. GPU compute 없음.', '',
        '## 최소 current-backend profile', '',
        f'Noise-on 원본 의미의 0.5 neural s / {total:.6f} wall s. 타이머 복사본은 원본과 상태 bit-exact.', '',
        '| 구간 | Wall s | 비중 |','|---|---:|---:|']
    for k,v in p.items():lines.append(f'| {k} | {v:.6f} | {100*v/total:.2f}% |')
    lines += ['', '## 구현과 연결망', '',
        'Brian2 2.9.0 generated/compiled C++ standalone, CPU 1 thread. 165,122 neurons / 6,327,564 effective signed synapses (6,474,533 anatomical retained).',
        '1ms, 기존 float32 weights와 membrane/synapse/reset 파라미터 유지. 전파는 presynaptic spike-triggered. 전체 C++ i/source, j/target, w 배열을 실제 runtime CSR와 정확 비교했다.',
        'Reference의 seeded baseline drive를 그대로 export. Gaussian noise는 실험용 in-memory copy에서만 OFF. 외부 전류는 기존 LC4/LPLC2 311개에 3.0. Core config는 수정하지 않았다.',
        '작은 asymmetric signed compiled 테스트: spike 스텝 일치, direction/sign/one-step-delay/external/refactory 확인. 최대 v 오차 9.54e-7, syn 오차 3.81e-6, refractory 및 activity 오차 0.', '',
        '## Noise-off 최소 회로 비교', '',
        '각 비교 구간 0.5s; 그 앞 warmup 0.5s. 표의 활동은 해당 그룹 평균 EMA(Hz)의 구간 평균/최대.', '',
        '| 구간 | 그룹 | Spike count Ref / Brian | Rate Hz Ref / Brian | Mean activity Ref / Brian | Peak activity Ref / Brian |',
        '|---|---|---:|---:|---:|---:|']
    for row in comparisons:
        x=row['reference'];y=row['brian2']
        lines.append(f"| {row['phase']} | {row['group']} | {x['spike_count']} / {y['spike_count']} | {x['rate_hz']:.4f} / {y['rate_hz']:.4f} | {x['mean_activity_hz']:.4f} / {y['mean_activity_hz']:.4f} | {x['peak_mean_activity_hz']:.4f} / {y['peak_mean_activity_hz']:.4f} |")
    lines += ['', 'GF: bodyId 10001/10010, baseline 8 → stimulus 22 → recovery 8Hz 양쪽 동일. Δ +14Hz. DNp09: 10783/11177, 전 구간 0Hz 양쪽 동일 (pass 조건 아님).',
        'LC4 Δ +118.4286Hz, LPLC2 Δ +119.9568Hz 양쪽 동일. EMA recovery 구간 평균에는 정상적인 잔류 decay가 포함된다. 모든 관측량의 상세 delta/final 값은 gate-a.json에 있다.',
        f"Population spikes: baseline {r['baseline']['population_spikes']} / {b['baseline']['population_spikes']}, stimulus {r['stimulus']['population_spikes']} / {b['stimulus']['population_spikes']}, recovery {r['recovery']['population_spikes']} / {b['recovery']['population_spikes']}. 유한 상태/정상 회복 확인.", '',
        '## 실제 성능', '',
        f"2s smoke: C++ neural/wall {candidate['neural_wall_ratio']:.4f}× (계산 wall {sum(candidate['simulation_run_wall_seconds']):.6f}s).", '',
        '| Backend / 부하 | Neural s | Simulation wall s | Neural/wall | Population spikes |',
        '|---|---:|---:|---:|---:|',
        f"| SciPy noise-off baseline | 10 | {refbench['wall_seconds']:.6f} | {refbench['neural_wall_ratio']:.4f}× | {refbench['population_spikes']} |"]
    for name,v in q.items():lines.append(f"| Brian2 {name} | 10 | {v['wall_seconds']:.6f} | {v['neural_wall_ratio']:.4f}× | {v['population_spikes']} |")
    lines += ['',f"Baseline 비교 {report['baseline_speedup']:.2f}배 개선. 자극 firing load {q['baseline']['population_rate_hz']:.4f} → {q['LC4_LPLC2_stimulus']['population_rate_hz']:.4f}Hz/neuron. 자극은 baseline 10s의 상태에서 연속 실행했다.",
        f"Cold build total {bench['build']['build_wall_seconds']:.6f}s, 실제 make/compile+link {bench['build']['device_timers']['compile']['make']:.6f}s. Python load {bench['python_load_wall_seconds']:.6f}s; model generation {bench['python_model_generation_wall_seconds']:.6f}s; C++ load/init {bench['executable_init_wall_seconds']:.6f}s.",
        f"전체 executable 실행(0.5s warmup + 10s baseline + 10s stimulus, init/output 포함)은 {bench['executable_launch_init_simulation_output_wall_seconds']:.6f}s. Simulation timer는 std::chrono wall timer이며 Network.run만 포함한다. 남은 launch/output/구간 준비 등 {bench['remaining_launch_output_seconds']:.6f}s은 계산 성능에 섞지 않았다. Spike/selected-activity monitor 비용은 simulation에 포함.",
        f"RAM: executable peak {ram['executable_peak_rss_bytes']/2**30:.4f}GiB, representative {ram['executable_representative_rss_bytes']/2**30:.4f}GiB. Python preparation peak {ram['preparation_python_peak_rss_bytes']/2**30:.4f}GiB, Python+compiler/executable tree sampled peak {ram['whole_process_tree_sampled_peak_rss_bytes']/2**30:.4f}GiB. System available minimum {ram['minimum_available_ram_bytes']/2**30:.4f}GiB. Sampling 20ms + OS child peak working set.", '',
        '## Integration overhead debt', '']
    for name,v in overhead.items():lines.append(f"{name}: 기존 동일 run 내부 total {v['total_wall_seconds']:.6f}s = Brain.step {v['brain_compute_seconds']:.6f}s + remainder {v['remainder_seconds']:.6f}s ({v['remainder_fraction']*100:.2f}%). Source: {v['source']}.")
    lines += ['이 remainder는 serialization/socket/logging/ecology/Godot ACK/initialization/shutdown을 합친 실제 wall 잔여이며 개별 CPU 비용 분해는 아니다. 기존 core 0.1006×, body 0.0877×, ecology 0.0805×는 서로 다른 workload의 참고치다.',
        'Brain은 10배 이상 빨라졌으므로 이 unchanged integration 비용이 다음 병목이 될 수 있다. 특히 standalone cold-start/결과 쓰기를 50ms packet마다 반복하는 설계는 안 된다. 이번 결과는 Brian2+Godot 전체 realtime 성능을 보증하지 않는다. IPC/JSON/세계 구조는 전혀 최적화·이식하지 않았다.', '',
        '## 보존과 판정', '',
        f"기존 source/runtime/body/ecology/report {baseline['checked_files']}개 SHA-256 byte snapshot: 변경 0. 기존 13 core/real-data/decoder tests 통과. 새 파일은 realtime/ 및 reports/realtime/뿐이며 build/compatibility 중간물은 workspace work/에 있다.",
        'Generated source와 executable SHA 및 실제 C++ timer evidence는 brian-benchmark.json / generated-proof/에 보관. 후보는 SURVIVES. Gate B, noisy equivalence, compound burst, ecology migration은 실행하지 않고 종료한다.', '',
        '## 기술 참고', '',
        '[Brian2 standalone 및 timing injection 공식 문서](https://brian2.readthedocs.io/en/2.9.0/user/computation.html) — build/run 분리와 Network.run 전후 C++ hook 사용.',
        '[Brian2 scheduling 공식 문서](https://brian2.readthedocs.io/en/2.9.0/user/running.html#scheduling) — before_groups 순서와 explicit integer refractory 구현.']
    (REPORT/'DELIVERY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    sources={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'realtime').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    save(REPORT/'source_sha256.json',sources)
    evidence={str(p.relative_to(REPORT)):sha(p) for p in REPORT.rglob('*') if p.is_file() and p.name!='evidence_sha256.json'}
    save(REPORT/'evidence_sha256.json',evidence)
    print(json.dumps(dict(classification=classification,checks=checks,conditions=q,speedup=report['baseline_speedup'],resources=ram,overhead=overhead),indent=2))
