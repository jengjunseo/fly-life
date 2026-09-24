"""Classify only completed Gate C experiments; never launch neural work."""
import json
from env import ROOT,REPORT,WORK,sha,save
def read(name):return json.loads((REPORT/name).read_text())
if __name__=='__main__':
    audit=read('c0-audit.json');decision=read('c2-decision.json');preserved=read('preservation-after.json')
    assert audit['success'] and preserved['success']
    rng={t:read(f'rng-{t}t.json') for t in [1,2,4,8]}
    full={t:read(f'c2-native-{t}t.json') for t in [1,2,4,8] if (REPORT/f'c2-native-{t}t.json').exists()}
    for t,d in rng.items():
        assert len(d['trials'])==2 and all(x['samples']==165122000 and x['actual_threads']==t for x in d['trials'])
    for t,d in full.items():assert d['full_connection_arrays_verified'] and len(d['windows'])==400
    generation=consumption=validation=None
    if decision['candidate']:
        validation=read('multi-seed.json');assert len(validation['seeds'])>=3
        classification='PASS — NATIVE OPENMP' if validation['success'] else 'FAIL — STOCHASTIC EQUIVALENCE'
        stage_c3=stage_c4='NOT RUN — earlier C2 stop condition satisfied'
    else:
        assert len(full)==4
        generation=read('c3-generation.json');consumption=read('c3-consumption.json')
        assert read('c3-correctness.json')['success']
        if not generation['realtime_feasible']:
            classification='FAIL — RNG GENERATION TOO SLOW'
            stage_c4='NOT RUN — C3 generation lacks sustained realtime throughput; buffer cannot rescue it'
        elif not consumption['statistics']['compute_realtime']:
            classification='FAIL — CONSUMPTION TOO SLOW'
            stage_c4='NOT RUN — C3 consumption lacks realtime throughput'
        else:
            raise RuntimeError('Both C3 sides feasible: conditional C4 / final validation is required before delivery')
        stage_c3='RUN — C2 native-noise p99 failed for all configurations'
    source_proof={}
    for t,d in full.items():
        directory=WORK/f'c2-native-{t}t-cpp';header=(directory/'objects.h').read_text();lif=(directory/'code_objects/lif_update_codeobject.cpp').read_text()
        thread_selector='omp_get_thread_num()' in lif;parallel_loop='#pragma omp parallel for' in lif
        source_proof[t]=dict(generator_vector_present='std::vector< RandomGenerator > _random_generators' in header,
            normal_uses_thread_id=thread_selector,parallel_loop_present=parallel_loop,
            expected_generator_selection_verified=thread_selector if t>1 else '_random_generators[0].randn()' in lif,
            expected_parallel_configuration_verified=parallel_loop==(t>1),
            no_randn_lock='critical' not in header[header.index('class RandomGenerator'):header.index('// In OpenMP')])
        assert all(source_proof[t][k] for k in ['generator_vector_present','expected_generator_selection_verified','expected_parallel_configuration_verified','no_randn_lock'])
    binary_peak=max(d['resources']['executable_peak_rss_bytes'] for d in [*full.values(),*([consumption] if consumption else [])])
    tree_peak=max(d['resources']['whole_process_tree_sampled_peak_rss_bytes'] for d in [*full.values(),*([consumption] if consumption else [])])
    report=dict(classification=classification,c0=audit,c2=decision,rng_scaling={t:dict(samples_per_second=d['mean_samples_per_second'],equivalent_neural_wall_ratio=d['mean_equivalent_neural_wall_ratio'],scaling=d['mean_samples_per_second']/rng[1]['mean_samples_per_second']) for t,d in rng.items()},
        c2_statistics={t:d['statistics'] for t,d in full.items()},rng_parallelism_source=source_proof,c3_status=stage_c3,c4_status=stage_c4,
        generation=generation,consumption_statistics=consumption['statistics'] if consumption else None,
        multi_seed=validation if validation else dict(status='NOT RUN — no realtime candidate survived; validation requires a final candidate'),
        resources=dict(executable_peak_rss_bytes=binary_peak,sampled_process_tree_peak_rss_bytes=tree_peak),preservation=preserved,
        chosen_implementation=decision['candidate'] or 'NONE — keep verified baseline; no deployment/backend migration',
        remaining_debt=['Native MT and PCG64 seeds are not stream-identical; shared input only can assert exact sequence.',
            'Existing body/ecology composite remainder ~8.5% / ~19.4% untouched; not extrapolated to a fast brain.',
            'No Godot migration, world behavior changes, JSON bridge changes or persistent ecology process.'])
    save(REPORT/'gate-c.json',report)
    lines=[f'RNG RESCUE: {classification}','',
        '실제 target: AMD Ryzen 3 4100, 4 physical cores / 8 logical threads, RAM 15.79GiB, Windows, TDM-GCC9.2, Brian2 2.9. CPU only, GPU 없음. 8T는 SMT 사용이며 oversubscription으로 취급하지 않았다.', '',
        '## 1. C0 frozen evidence audit','',
        f"PASS. 실제 Network.run {audit['neural_seconds']:.0f}s, {audit['neurons']} neurons, {audit['effective_connections']} effective signed synapses. dt1ms, threshold1/reset0/refractory2ms, 기존 sign/weights/float32 모델. Baseline은 NumPy2.4 seed20260913의 원래 heterogeneity draw와 동일하다.",
        '0-.5s warmup / .5-1s baseline / 1-1.5s LC4+LPLC2 current3 / 1.5-2s recovery. Noise tape는 [2000,165122] unscaled little-endian float32 C-order; 매 ms 한 N-row, amplitude0.1을 external current 이전에 적용하고 refractory 중에도 draw를 소비한다.',
        f"기존 frozen compute {audit['frozen_compute_seconds']:.6f}s ({audit['frozen_equivalent_ratio']:.4f}×)는 동일한 full network의 consumption evidence다. Noise pre-generation은 빠져 있으므로 sustained realtime 인증이 아니다. Runtime weight/baseline/input/tape SHA와 full graph 확인은 c0-audit.json에 있다.", '',
        '## 2. C1 isolated Gaussian generation','',
        '실제 Gate B generated objects.h의 RandomGenerator class를 수정 없이 추출했다. std::mt19937 + stored-pair polar Box-Muller의 double log/sqrt 후 float32 cast. 네트워크 계산 없이 timestep당165122 sample, 50ms warmup 뒤 실제1000ms를 두 번 측정했다. Compile/startup/checksum은 throughput timer 밖이다.',
        f"1T는 1 neural초분 생성에 {rng[1]['trials'][0]['wall_seconds']:.6f} / {rng[1]['trials'][1]['wall_seconds']:.6f} wall초, 평균 {rng[1]['mean_equivalent_neural_wall_ratio']:.4f}×. 생성기 자체가 realtime budget을 초과한다. Full noise-on 비용 전체가 RNG만이라고 추정하지는 않는다.", '',
        '## 3. C2 native OpenMP scaling / full timing','',
        '| Method | Threads | RNG Msamples/s / neural-wall / scaling | Full mean / p50 / p95 / p99 / max ms | Deadline miss count / rate | Longest misses |',
        '|---|---:|---:|---:|---:|---:|']
    for t,d in full.items():
        r=report['rng_scaling'][t];s=d['statistics']
        lines.append(f"| Native Brian2 | {t} | {r['samples_per_second']/1e6:.3f} / {r['equivalent_neural_wall_ratio']:.4f}× / {r['scaling']:.3f}× | {s['mean_ms']:.3f} / {s['p50_ms']:.3f} / {s['p95_ms']:.3f} / {s['p99_ms']:.3f} / {s['max_ms']:.3f} | {s['deadline_misses']} / {s['deadline_miss_rate']*100:.3f}% | {s['longest_consecutive_misses']} |")
    lines+=['',
        '각 thread 설정에서 실제 20 neural초 / 400개 consecutive quantum. 개별 50ms timer는 C++ Network.run 내부에서 측정하며 경계 input/stat/log maintenance를 제외한다. 전체 Network.run은 maintenance 포함 값으로 JSON에 별도 기록했다. Python 시작/build를 quantum에 섞지 않았다.',
        '실제 per-thread RNG vector와 omp_get_thread_num 선택, parallel for를 generated source에서 확인했다. RNG class 내부 locking/critical은 없다. 수치 scaling은 실제 두 trial 결과이며, C2에는 producer가 동시 실행되지 않았다.',
        f"C2 candidate: {decision['candidate'] or 'NONE'}. 모든 수치·개별 quantum·source proof는 raw txt/JSON 및 generated-proof/에 있다.", '',
        '## 4. C3 pre-generation feasibility','',stage_c3]
    if generation:
        lines+=['', '| PCG64 float32 block, neural ms | Bytes | Mean / p50 / p95 / max generation wall ms | Neural/wall |', '|---|---:|---:|---:|---:|']
        for q in generation['blocks']:
            lines.append(f"| {q['neural_ms']} | {q['bytes']} | {q['mean_ms']:.3f} / {q['p50_ms']:.3f} / {q['p95_ms']:.3f} / {q['max_ms']:.3f} | {q['neural_wall_ratio']:.4f}× |")
        s=consumption['statistics']
        lines+=['', 'NumPy2.4 PCG64 float32 Gaussian, baseline draw 뒤의 state. Warmup과 측정은 분리했다.',
            f"Consumption은 동일 network/동일 shared noise 입력의 새 실제 {s['neural_seconds']:.0f}s / {s['windows']} quantum 실행. Mean/p50/p95/p99/max {s['mean_ms']:.3f}/{s['p50_ms']:.3f}/{s['p95_ms']:.3f}/{s['p99_ms']:.3f}/{s['max_ms']:.3f}ms; miss {s['deadline_miss_rate']*100:.3f}%. Scope/정확한 input·memory 정책은 c3-consumption.json.",
            'C3 shared-input correctness PASS: baseline/stimulus/recovery population spikes 45181/65209/45148이 SciPy와 동일. LC4 stimulus7490 / LPLC2 stimulus11118 / GF8→25→8 / DNp09 0이며 모든 구간의 group count와 active fraction도 동일하다. c3-correctness.json에 33개 검사와 나란한 metric을 저장했다. 40-window 진단을 sustained realtime 인증으로 주장하지 않는다.',
            f"Generation realtime feasible={generation['realtime_feasible']}. 50ms generation 평균 {generation['blocks'][0]['mean_ms']:.3f}ms와 consumption 평균 {s['mean_ms']:.3f}ms를 독립 측정했다. 이론적인 max(producer,consumer)는 가능성 판단일 뿐, concurrent pipeline 실측으로 과장하지 않는다."]
    lines+=['', '## 5. C4 producer/consumer','',stage_c4,
        'Producer starvation: NOT MEASURED (C4 not run); buffer depth: 0; CPU allocation: C3 generator1T와 consumer1T를 각각 독립 측정, concurrent producer 없음. Starvation을 0회라고 주장하지 않는다.','',
        '## 6. Chosen implementation','',report['chosen_implementation'],'',
        '## 7. Multi-seed equivalence','', 'PASS/FAIL 및 metric ranges는 multi-seed.json.' if validation else report['multi_seed']['status'], '',
        '## 8. Resources / build integrity','',
        f"Peak executable RSS {binary_peak/2**30:.4f}GiB; preparation/compiler/executable process-tree sampled peak {tree_peak/2**30:.4f}GiB. 각각의 범위는 resources에 명시했다.", '',
        '| Run | Python load / model / codegen / compile-link s | C++ init / Network.run / output s | Launcher + unattributed s |','|---|---:|---:|---:|']
    for d in [*full.values(),*([consumption] if consumption else [])]:
        t=d['timings'];lines.append(f"| {d['name']} | {d['load_wall_seconds']:.3f} / {d['python_model_setup_wall_seconds']:.3f} / {d['code_generation_wall_seconds']:.3f} / {d['compile_link_wall_seconds']:.3f} | {t['init']:.3f} / {t['network_compute']:.3f} / {t['brian_output']:.3f} | {d['launcher_and_unattributed_seconds']:.3f} |")
    lines+=['', '## 9. Baseline preservation','',
        f"{preserved['checked_files']} existing artifact SHA checked; changed files={preserved['changed_files']}; existing tests {preserved['tests']} PASS. Core/body/ecology/Gate A/Gate B unchanged. 새 source/report는 Gate C 전용 경로에만 저장했다.", '',
        '## 10. Remaining debt / stop','',
        'Native MT seed integer는 PCG64 random stream identity가 아니다. Shared noise 조건에서만 exact stream equivalence를 주장한다. 기존 body/ecology remainder 약8.5%/19.4%는 느린 SciPy 아래의 composite startup/socket/log/ACK/wait 등을 포함하며 이 라운드에서 최적화하거나 외삽하지 않았다.',
        '다음 별도 검토 후보: SeedSequence.spawn으로 분리한 소수 PCG64 float32 worker streams의 block-generation 병렬화. NumPy는 독립 Generator stream 생성 기능을 제공하지만, 이 PC에서의 throughput·brain과의 CPU 경쟁·3-seed 동등성은 미검증이다. 단일 reference PCG64 stream과 exact identity도 달라진다. 이번 C3 STOP에 따라 구현하지 않았다. [NumPy parallel RNG documentation](https://numpy.org/doc/2.4/reference/random/parallel.html)',
        '실패 판정은 측정한 native OpenMP와 단일-worker PCG64 전략에 한정한다. 모든 RNG 전략이나 이 hardware에서의 realtime이 원천 불가능하다는 증명은 아니다. 추가 buffer/새 backend/Godot migration/행동 변경 없이 종료한다.', '',
        '[Brian2 standalone/OpenMP preferences and warning](https://brian2.readthedocs.io/en/2.9.0/user/computation.html) — 실제 generated source와 실측 scaling을 source of truth로 사용했다.']
    (REPORT/'DELIVERY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    save(REPORT/'source_sha256.json',{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'realtime/gate-c').rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    save(REPORT/'evidence_sha256.json',{str(p.relative_to(REPORT)):sha(p) for p in REPORT.rglob('*') if p.is_file() and p.name!='evidence_sha256.json'})
    print(json.dumps({k:v for k,v in report.items() if k not in ['c0','generation','preservation','multi_seed']},indent=2))
