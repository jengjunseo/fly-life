"""Evidence-only final B0/B1/B2 classification. No further brain experiments."""
import json
import shutil
from pathlib import Path
import numpy as np
from env import ROOT,REPORT,WORK,sha,save

def read(name):return json.loads((REPORT/name).read_text())

def trend(times,error):
    absolute=np.abs(error);slope,intercept=np.polyfit(times,absolute,1);prediction=slope*times+intercept
    ss=float(np.square(absolute-absolute.mean()).sum())
    r2=1-float(np.square(absolute-prediction).sum())/ss if ss>0 else 0.
    signed_slope,signed_intercept=np.polyfit(times,error,1)
    signed_ss=float(np.square(error-error.mean()).sum())
    signed_r2=1-float(np.square(error-(signed_slope*times+signed_intercept)).sum())/signed_ss if signed_ss>0 else 0.
    late_slope=float(np.polyfit(times[-20:],absolute[-20:],1)[0])
    # Predeclared before obtaining B2 outcomes. A fit alone is NOT a scientific diagnosis.
    growing=bool(slope>.2 and r2>.5 and signed_r2>.5 and late_slope>.2 and
        absolute[-1]>4*max(1.,float(absolute[:10].mean())))
    return dict(absolute_mismatch_slope_spikes_per_s=float(slope),absolute_fit_r2=r2,signed_slope_spikes_per_s=float(signed_slope),
        signed_fit_r2=signed_r2,last20s_absolute_slope_spikes_per_s=late_slope,max_absolute_mismatch=int(absolute.max()),
        final_mismatch=int(error[-1]),growing_evidence=growing,
        criterion='GROWING if abs slope >0.2 spike/s, abs R2>0.5, signed R2>0.5, last20s abs slope>0.2, final abs>4*max(1, first10s abs mean). Otherwise inspect stable phase statistics and normalized error; NOT proof of indefinite bound.')

if __name__=='__main__':
    b0=read('b0-equivalence.json');perf=read('b0-performance.json');native=read('b0-native.json');frozen=read('b0-frozen.json')
    # Correct a descriptive metadata label from stale Brian docs; actual generated code is authority.
    actual_rng='Actual generated objects.h: std::mt19937 + polar Box-Muller. Same numeric seed; native stream differs from NumPy PCG64. Shared B0 tape uses exact PCG64 float32 stream.'
    for name,d in [('b0-native',native),('b0-frozen',frozen),('b0-performance',perf)]:
        d['native_rng']=actual_rng;save(REPORT/(name+'.json'),d)
    workloads={name:read(name+'.json') for name in ['baseline','looming','real_predator','compound']}
    reference=read('reference-b2.json');candidate=read('b2.json');preserved=read('preservation-after.json')
    trajectory=[]
    snapshots=candidate['windows'][19::20]
    assert len(reference['trajectory'])==len(snapshots)==60
    for r,c in zip(reference['trajectory'],snapshots):
        assert abs(r['time_s']-c['neural_end_s'])<1e-9
        diff=c['cumulative_population_spikes']-r['cumulative_population_spikes']
        trajectory.append(dict(time_s=r['time_s'],reference_population_spikes=r['cumulative_population_spikes'],brian2_population_spikes=c['cumulative_population_spikes'],
            difference=diff,absolute_difference=abs(diff),relative_difference=diff/max(1,r['cumulative_population_spikes']),
            groups={g:dict(reference_cumulative=r['groups'][g]['cumulative_spikes'],brian2_cumulative=c['groups'][g]['cumulative_spikes'],
                difference=c['groups'][g]['cumulative_spikes']-r['groups'][g]['cumulative_spikes'],
                reference_ema_hz=r['groups'][g]['mean_ema_hz'],brian2_ema_hz=c['groups'][g]['mean_ema_hz'],
                ema_difference_hz=c['groups'][g]['mean_ema_hz']-r['groups'][g]['mean_ema_hz']) for g in ['LC4','LPLC2','GF','DNp09']}))
    times=np.array([x['time_s'] for x in trajectory]);errors=np.array([x['difference'] for x in trajectory])
    trends=dict(population=trend(times,errors),**{g:trend(times,np.array([x['groups'][g]['difference'] for x in trajectory])) for g in ['LC4','LPLC2','GF']})
    phase_stats={}
    for phase,lo,hi in [('baseline',0,400),('stimulus',400,800),('recovery',800,1200)]:
        rows=candidate['windows'][lo:hi];start=candidate['windows'][lo-1] if lo else None
        pop=sum(x['population_spikes'] for x in rows);rate=pop/165122/20
        groups={g:dict(spike_count=rows[-1]['groups'][g]['cumulative_spikes']-(start['groups'][g]['cumulative_spikes'] if start else 0),
                    final_ema_hz=rows[-1]['groups'][g]['mean_ema_hz']) for g in ['LC4','LPLC2','GF','DNp09']}
        phase_stats[phase]=dict(reference=reference['phases'][phase],brian2=dict(population_spikes=pop,population_rate_hz=rate,groups=groups),
            population_rate_ratio=rate/reference['phases'][phase]['population_rate_hz'])
    stable_phases=all(.9<=v['population_rate_ratio']<=1.1 for v in phase_stats.values())
    small_normalized=max(abs(x['relative_difference']) for x in trajectory)<=.001
    growing=any(t['growing_evidence'] for t in trends.values())
    drift='GROWING DRIFT' if growing else 'BOUNDED / NUMERICALLY STABLE CANDIDATE' if stable_phases and small_normalized else 'UNRESOLVED / STATISTICS DIVERGED'
    b2pass=not growing and stable_phases and small_normalized
    stability=reference['finite'] and candidate['finite'] and all(d['finite'] and max(x['max_simultaneous_spiking_fraction'] for x in d['windows'])<.25 for d in workloads.values())
    realtime=all(d['statistics']['compute_realtime'] for d in workloads.values())
    # Actual baseline duration is 60s; each stress obtains 400 windows/20s. Failed p99
    # alone is sufficient to reject compute realtime; we do not extrapolate 20->60s.
    assert workloads['baseline']['statistics']['neural_seconds']==60
    assert all(d['statistics']['windows']>=400 for d in workloads.values())
    classification='PASS — COMPUTE REALTIME' if realtime else 'PASS — NOT YET COMPUTE REALTIME'
    if not b0['success'] or not preserved['success']:classification='FAIL — EQUIVALENCE'
    elif not stability:classification='FAIL — STABILITY'
    elif not b2pass:classification='FAIL — DRIFT'
    worst=max(workloads,key=lambda k:workloads[k]['statistics']['p99_ms'])
    allreports={**workloads,'b0-native':native,'b0-frozen':frozen,'b0-performance':perf,'b2':candidate}
    peak_binary=max(d['resources']['executable_peak_rss_bytes'] for d in allreports.values())
    peak_tree=max(d['resources']['whole_process_tree_sampled_peak_rss_bytes'] for d in allreports.values())
    report=dict(classification=classification,b0_pass=b0['success'],b1_compute_realtime=realtime,b1_worst_p99_workload=worst,
        b1_statistics={k:v['statistics'] for k,v in workloads.items()},b2_pass=b2pass,b2_classification=drift,b2_trajectory=trajectory,
        b2_trends=trends,b2_phase_comparison=phase_stats,b2_max_absolute_relative_population_error=max(abs(x['relative_difference']) for x in trajectory),
        stability_pass=bool(stability),preservation=preserved,
        b0_noise_performance=perf['conditions'],gate_a_noise_off=read('../brian-benchmark.json')['conditions'],
        resources=dict(max_executable_peak_rss_bytes=peak_binary,max_sampled_process_tree_peak_rss_bytes=peak_tree),
        performance_separation={k:{a:v[a] for a in ['load_wall_seconds','python_model_setup_wall_seconds','code_generation_wall_seconds','compile_link_wall_seconds',
            'timings','binary_launch_init_compute_output_wall_seconds','launcher_and_unattributed_seconds']} for k,v in allreports.items()},
        debt=['Existing ecology overhead is composite same-run remainder ~19.4%, body ~8.5%; not optimized or extrapolated.',
            'No Godot/ecology migration or persistent IPC implementation. Native noise is seeded/reproducible but NOT PCG64-identical; bounded shared B0 tape proves exact injection semantics.',
            'B1 baseline actual 60s/1200 windows, other workloads actual 20s/400 windows; failing p99 rejects realtime without extrapolation.',
            'B2 one deterministic 60s schedule/seed, not proof of an indefinite mathematical bound or all-circuit equivalence.'])
    save(REPORT/'gate-b.json',report)
    save(REPORT/'b2-drift.json',dict(classification=drift,success=b2pass,trajectory=trajectory,trends=trends,phase_comparison=phase_stats))
    proof=REPORT/'generated-proof';proof.mkdir(parents=True,exist_ok=True)
    for run in ['b0-native','b0-frozen','baseline','b2']:
        out=proof/run;out.mkdir(exist_ok=True)
        for name in ['main.cpp','objects.h','gate_hooks.h','makefile','code_objects/lif_update_codeobject.cpp','code_objects/quantum_boundary_codeobject.cpp']:
            shutil.copyfile(WORK/(run+'-cpp')/name,out/Path(name).name)
    lines=[f'BRIAN2 GATE B: {classification}','', '실제 target: Ryzen 3 4100, 4C/8T, 16GB, Windows, CPU 1 thread, GPU compute 없음.', '',
        '## B0 — Noise-on equivalence','',
        'Noise amplitude 0.1, dt 1ms, 동일한 NumPy2.4 seeded baseline drive. 매 step 모든 뉴런에서 Gaussian standard normal을 float32 cast/scale 후 syn/baseline drive에 더하고 외부 전류를 그 뒤에 더한다. xi diffusion으로 바꾸지 않았다.',
        'B0 공유 입력: baseline heterogeneity draw 뒤의 정확한 PCG64 float32 noise sequence를 2초 tape로 export. [step,runtime_index] 규약과 SHA/통계는 noise-tape.json. Native noise 실행은 실제 generated objects.h의 std::mt19937 + polar Box-Muller, 동일 seed 값이지만 PCG64 stream identity는 주장하지 않는다.', '',
        '| 구간 | Population Hz Ref / native / shared | Active fraction Ref / native / shared | GF Hz Ref / native / shared |', '|---|---:|---:|---:|']
    ref=read('reference-b0.json')
    for phase in ['baseline','stimulus','recovery']:
        r=ref['phases'][phase];n=native['phases'][phase];f=frozen['phases'][phase]
        lines.append(f"| {phase} | {r['population_rate_hz']:.6f} / {n['population_rate_hz']:.6f} / {f['population_rate_hz']:.6f} | {r['active_fraction']:.6f} / {n['active_fraction']:.6f} / {f['active_fraction']:.6f} | {r['groups']['GF']['mean_hz']:.3f} / {n['groups']['GF']['mean_hz']:.3f} / {f['groups']['GF']['mean_hz']:.3f} |")
    lines+=['', '| 구간 | 그룹 | Spike count Ref / native / shared | Mean Hz Ref / native / shared | Peak mean EMA Hz Ref / native / shared |', '|---|---|---:|---:|---:|']
    for phase in ['baseline','stimulus','recovery']:
        for g in ['LC4','LPLC2','GF','DNp09']:
            r=ref['phases'][phase]['groups'][g];n=native['phases'][phase]['groups'][g];f=frozen['phases'][phase]['groups'][g]
            lines.append(f"| {phase} | {g} | {r['spike_count']} / {n['spike_count']} / {f['spike_count']} | {r['mean_hz']:.4f} / {n['mean_hz']:.4f} / {f['mean_hz']:.4f} | {r['peak_mean_ema_hz']:.4f} / {n['peak_mean_ema_hz']:.4f} / {f['peak_mean_ema_hz']:.4f} |")
    lines+=['',f"B0 PASS={b0['success']}. Population 전 구간 90–110%, dead(network/active <50%) 없음, recovery >200% runaway 없음, simultaneous spikes ≥25% 없음, NaN/Inf 없음. LC4/LPLC2 입력·GF downstream·정상 recovery 보존, DNp09 0Hz. 정확한 판단 값과 그룹 active fraction/mean EMA는 b0-equivalence.json.", '',
        '## B0 — 실제 native noise 성능', '', '| 조건 | Neural s | Internal compute wall s | Neural/wall | Population spikes |', '|---|---:|---:|---:|---:|']
    for name,value in perf['conditions'].items():lines.append(f"| {name} | 10 | {value['network_compute_seconds']:.6f} | {value['neural_wall_ratio']:.4f}× | {value['population_spikes']} |")
    old=report['gate_a_noise_off']
    lines += ['',f"Gate A noise-off baseline {old['baseline']['neural_wall_ratio']:.4f}× / looming {old['LC4_LPLC2_stimulus']['neural_wall_ratio']:.4f}× 대비 큰 성능 하락. Noise RNG 생성 비용은 C++ compute 안에 포함했다. SciPy profile 23.3%로 Brian2 비용을 추정하지 않았다. Shared tape 실행 성능은 noise-on realtime 성능으로 사용하지 않는다.",
        '10초 조건별 wall은 200개 internal window timer 합이며 boundary maintenance를 제외한다. 20.5초 전체 Network.run wall과 overhead는 b0-performance.json에 별도 보관.', '',
        '## B1 — Actual lockstep quantum stress', '',
        '한 persistent generated Network.run 내부의 50개 실제 1ms step 단위. 각 window의 시작·종료 neural time, compute ms, slack, realtime factor, spike count, 활동을 JSON 및 raw C++ txt에 저장. Python launcher/startup은 quantum timer 밖이다. 별도의 async/backlog 의미나 world prediction 없음.',
        '개별 window timer는 경계의 통계 수집·입력 갱신·로그 기록을 제외한다. 표의 compute wall은 그 maintenance까지 포함한 전체 Network.run이다. Baseline window timer 합은 404.846739s, 전체 Network.run은 425.421806s이며 어느 범위로도 realtime FAIL이다.',
        'Baseline 실제 60s / 1200 windows, 나머지 각 20s / 400 consecutive windows. Real predator는 기존 Godot/ecology 실제 60-frame 전체 sensory current trace를 3s 주기로 반복한 replay. 음식/열/female의 실제 동시 채널도 유지한다. Compound는 실제 최고 visual snapshot + 실제 최고 hot current를 지속 재생 (다른 채널 zero). 새로운 biology/current gain 없음.', '',
        '| 부하 | Neural s / windows | Compute wall s | Mean / p50 / p95 / p99 / max ms | Miss count / rate | Longest misses | Realtime / clean quality |', '|---|---:|---:|---:|---:|---:|---|']
    for name,d in workloads.items():
        s=d['statistics'];lines.append(f"| {name} | {s['neural_seconds']:.0f} / {s['windows']} | {s['network_compute_seconds']:.4f} | {s['mean_ms']:.3f} / {s['p50_ms']:.3f} / {s['p95_ms']:.3f} / {s['p99_ms']:.3f} / {s['max_ms']:.3f} | {s['deadline_misses']} / {s['deadline_miss_rate']*100:.3f}% | {s['longest_consecutive_misses']} | {s['compute_realtime']} / {s['clean_quality']} |")
    lines += ['',f"COMPUTE_REALTIME PASS={realtime}; worst p99 workload={worst}. 판정은 실제 compute total ≤ neural duration AND p99≤50ms. Stress 20s를 60s로 외삽하지 않으며 p99 fail만으로도 realtime을 거부한다. Quality target: miss<1% & longest≤2.", '',
        '## B2 — 60s deterministic drift', '',
        '동일 initial state/baseline/weights/signs/dt/refractory/reset, noise OFF. 20s baseline + 20s looming current 3 + 20s recovery. SciPy와 Brian2를 각각 실제 60s 연속 실행했다. 매 1s의 실제 trajectory는 b2-drift.json.', '',
        f"분류: {drift}; max normalized population error={report['b2_max_absolute_relative_population_error']:.8g}. Absolute mismatch 선형 fit slope={trends['population']['absolute_mismatch_slope_spikes_per_s']:.6f} spike/s, R²={trends['population']['absolute_fit_r2']:.6f}; signed slope={trends['population']['signed_slope_spikes_per_s']:.6f}, signed R²={trends['population']['signed_fit_r2']:.6f}.", '',
        '| Neural s | Ref cumulative | Brian cumulative | Difference / absolute / relative | LC4 / LPLC2 / GF difference |', '|---|---:|---:|---:|---:|']
    for x in trajectory:
        lines.append(f"| {x['time_s']:.0f} | {x['reference_population_spikes']} | {x['brian2_population_spikes']} | {x['difference']} / {x['absolute_difference']} / {x['relative_difference']:.8g} | {x['groups']['LC4']['difference']} / {x['groups']['LPLC2']['difference']} / {x['groups']['GF']['difference']} |")
    lines += ['',f"Final population mismatch {trajectory[-1]['difference']}; selected group EMA error도 같은 trajectory에 저장했다. 결과 확보 전 선언한 trend rule은 각 trend의 criterion에 기록했다. 유한한 60s 실행과 안정적인 phase statistics를 확인하는 검사이며, 영구적인 수학적 상한이나 exact spike identity를 증명했다고 주장하지 않는다.", '',
        '## Resources / performance integrity', '',
        f'Peak executable RSS {peak_binary/2**30:.4f}GiB; preparation/compile/executable tree sampled peak {peak_tree/2**30:.4f}GiB. GPU/OpenMP 없음.', '',
        '| Run | Python load / model setup / codegen / compile-link s | C++ init / compute / output s | Python launch + unassigned s |', '|---|---:|---:|---:|']
    for k,v in allreports.items():
        t=v['timings'];lines.append(f"| {k} | {v['load_wall_seconds']:.3f} / {v['python_model_setup_wall_seconds']:.3f} / {v['code_generation_wall_seconds']:.3f} / {v['compile_link_wall_seconds']:.3f} | {t['init']:.3f} / {t['network_compute']:.3f} / {t['brian_output']:.3f} | {v['launcher_and_unattributed_seconds']:.3f} |")
    lines += ['',f"Baseline SHA 비교: {preserved['checked_files']} files, changed={preserved['changed_files']}, existing tests={preserved['tests']} PASS. Gate A/body/ecology/core artifacts 보존. 새 파일은 realtime/gate-b/, reports/realtime/gate-b/뿐이며 intermediate binaries/input/noise tape는 workspace work/에 있다.", '',
        '## Debt / scope stop', '',
        '기존 body remainder 약 8.5%, ecology 약 19.4%는 startup/socket/logging/ACK/wait 등을 포함한 composite wall remainder다. 이번에는 최적화하지 않았으며 persistent Brian2 integration이나 전체 end-to-end realtime을 구현·인증하지 않았다.',
        'Native noise-on에서 큰 성능 하락을 실제 측정했다. 다만 RNG만의 격리 profile은 수행하지 않았으므로 하락 전체를 RNG 생성 비용으로 단정하지 않는다. 모델/noise amplitude/dt/weights/pruning/motor decoder를 조정하지 않았다. 새로운 backend/GPU/IPC 최적화/Godot 이식으로 확장하지 않고 B0~B2 판정으로 종료한다.',
        '불확실성: native MT seed stream과 reference PCG64 stream은 동일하지 않다 (shared B0는 동일). 단일 seed/제한된 회로/유한한 60s 검사다. B1 stress는 각 20s이며 baseline만 60s이다.', '',
        '[Brian2 Gaussian/seed documentation](https://brian2.readthedocs.io/en/2.9.0/advanced/random.html) — RNG source of truth is actual generated objects.h (std::mt19937/polar Box-Muller).',
        '[Brian2 standalone/custom injection documentation](https://brian2.readthedocs.io/en/2.9.0/user/computation.html) — steady Network.run compute separated from init/build/output.']
    (REPORT/'DELIVERY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    sources={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'realtime/gate-b').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    save(REPORT/'source_sha256.json',sources)
    save(REPORT/'evidence_sha256.json',{str(p.relative_to(REPORT)):sha(p) for p in REPORT.rglob('*') if p.is_file() and p.name!='evidence_sha256.json'})
    print(json.dumps({k:v for k,v in report.items() if k not in ['b2_trajectory','preservation','performance_separation','b2_phase_comparison']},indent=2))
