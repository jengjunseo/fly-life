"""Produce Gate E report/plots from finished evidence; no benchmarks."""
import json, subprocess
from statistics import mean, median
import numpy as np
from env import ROOT, WORK, REPORT, sha, save

def read(name):
    return json.loads((REPORT/(name+'.json')).read_text(encoding='utf-8'))

def fmt(x):
    return f'{x:.3f}'

def link(name):
    return f'[{name}]({(REPORT/name).as_posix()})'

def corr(a,b):
    return float(np.corrcoef(a,b)[0,1]) if np.std(a)>0 and np.std(b)>0 else None

def main():
    audit=read('e0-audit');scale=read('e2-decision');cheap=read('e3-decision')
    timeline=read('e4-runs');z=read('plan-z');preserved=read('preservation-after')
    assert preserved['success'] and not preserved['changed_files']
    generated=read('gate-d-generated-integrity')
    assert generated['success'] and not generated['changed']
    assert not scale['headroom_candidate'] and not cheap['headroom_candidate']
    candidates=scale['records']+cheap['records']
    best=min(candidates,key=lambda x:x['worst_p99_ms']);worst=best['worst_p99_ms']
    assert worst>50
    for record in candidates:
        for n in record['repeats']:
            assert read(n+'-correctness')['success']
    runs=[read(n) for n in timeline['repeats']]
    # Actual post-run delay storage audit, without changing delay settings.
    p=list((WORK/runs[0]['label']).glob('_dynamic_array_connections_delay_*'));assert len(p)==1
    delays=np.fromfile(p[0],np.float32)
    delay=dict(explicit_assignment=False,stored_values=len(delays),
               min_ms=float(delays.min()*1000) if len(delays) else 0,
               max_ms=float(delays.max()*1000) if len(delays) else 0,
               classification='No explicit delay; all stored default delays uniformly zero',modified=False)
    save(REPORT/'delay-audit.json',delay)
    diagnostics=[]
    for i,run in enumerate(runs):
        raw=np.loadtxt(REPORT/(run['label']+'-windows.txt'));steady=raw[10:]
        t=steady[:,3];spikes=steady[:,4]
        noise_phase=(steady[:,0].astype(int)%40)
        phase_mean=np.array([np.mean(t[noise_phase==k]) for k in range(40)])
        residual=t-phase_mean[noise_phase]
        outlier=steady[t>50,0].astype(int).tolist()
        d=dict(label=run['label'],samples=len(t),spike_timing_pearson=corr(t,spikes),
               timing_lag40_autocorrelation=corr(t[40:],t[:-40]),spike_lag40_autocorrelation=corr(spikes[40:],spikes[:-40]),
               phase_adjusted_timing_lag40_autocorrelation=corr(residual[40:],residual[:-40]),
               deadline_miss_indices=outlier,timing_mad_ms=float(np.median(np.abs(t-np.median(t)))),
               hist_counts=np.histogram(t,bins=20)[0].tolist(),hist_edges_ms=np.histogram(t,bins=20)[1].tolist(),
               qualification='Known2s/40-window frozen-noise replay may imprint activity periods. Correlation is descriptive, not hardware-causal proof. Boundary scan/log flush excluded from per-quantum compute, included in Network.run wall.')
        diagnostics.append(d)
        save(REPORT/(run['label']+'-timeline-data.json'),dict(rows=[dict(window_index=int(r[0]),neural_start_s=float(r[1]),
            neural_end_s=float(r[2]),wall_compute_ms=float(r[3]),spike_count=int(r[4]),population_cumulative=int(r[5]),
            gf_activity_hz=float(r[20]),finite=bool(r[8])) for r in raw],diagnosis=d))
    import os
    plot_python=os.environ.get('GATE_E_PLOT_PYTHON','C:/Users/PC/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
    subprocess.run([plot_python,str(ROOT/'realtime/gate-e/plot.py'),str(REPORT)],check=True)
    save(REPORT/'e4-diagnosis.json',dict(repeats=diagnostics,
        interpretation='Broad principal compute band plus variable slow episodes/tails. No demonstrated repeat-stable period100 flush/allocation event; no evidence justifies a periodic-event fix. Spike/timing correlations and known40 input period reported separately. Cannot distinguish scheduler/cache/pagefault causes with this evidence.'))
    all_runs=[]
    for p in REPORT.glob('*.json'):
        d=json.loads(p.read_text(encoding='utf-8'))
        if 'brain_statistics' in d:all_runs.append(d)
    peak=max(d['peak_consumer_sampled_rss'] for d in all_runs)
    powers=[s['processor_performance_percent'] for d in all_runs for s in d['power_counter']['samples']]
    plan=subprocess.check_output(['powercfg','/getactivescheme']).decode('utf-8',errors='replace').strip()
    assert audit['active_power_plan'].split('GUID:')[-1].strip()==plan.split('GUID:')[-1].strip()
    save(REPORT/'power-plan-after.json',dict(before=audit['active_power_plan'],after=plan,changed=False,
        processor_performance_percent_min=min(powers),processor_performance_percent_max=max(powers),
        qualification='No severe aggregate PDH clock-down signal; _Total not per-core direct frequency, cannot rule out per-core scheduling/thermal events.'))
    summary=dict(classification='CONSUMER HEADROOM: FAIL',best_short_consumer_tag=best['tag'],
                 best_robust_short_consumer_p99_ms=worst,headroom_ms=50-worst,
                 equivalent_side_factor=50/worst,strong_20s_repeat_p99_ms=[r['brain_statistics']['p99_ms'] for r in runs],
                 e5='NOT RUN: no sufficiently improved/HEADROOM consumer candidate after cheap trials; stop rule4',
                 concurrent_consumer_p99_ms=None,concurrent_producer_p99_ms=None,concurrent_contention_percent=None,
                 pipeline_certified=False,production_adopted=False,baseline_checked_files=preserved['checked_files'],
                 baseline_changed_files=[],regression_tests=preserved['tests'],peak_cpp_sampled_rss_bytes=peak,
                 peak_controller_os_rss_bytes=max(d['python_os_peak_rss'] for d in all_runs),plan_z=z['classification'])
    save(REPORT/'gate-e-summary.json',summary)
    lines=[summary['classification'],'',
        'consumer 비용의 주 항목은 LIF full-population update, synaptic delivery, threshold 검사였다. '
        '싼 semantics-preserving 변경 두 개와 consumer-only 1T/2T/4T 모두 strong p99 ≤35ms를 안정적으로 만들지 못했다. '
        '최선 구성조차 hard floor50ms를 반복해서 넘었으므로 채택하지 않았다. 더 깊은 custom backend/architecture work는 시작하지 않았다.','',
        '| Headroom 항목 | 결과 |','|---|---|',
        f"| 최선 short consumer 반복-worst p99 | {fmt(worst)} ms (`{best['tag']}`) |",
        f'| 50ms floor 대비 margin / 환산 factor | {fmt(50-worst)} ms / {50/worst:.4f}× (side 환산, sustained factor 아님) |',
        '| 35ms actual adoption / 30ms ideal | 미달 / 미달 |',
        '| Optimized concurrent consumer / producer p99 | NOT MEASURED — 생존 candidate 없음 |',
        '| Optimized concurrent contention % | NOT MEASURED — Gate D 13–18%를 외삽하지 않음 |',
        '| Streaming pipeline / Godot headroom | NOT CERTIFIED — 이번 범위 아님 |','',
        '## 1. Existing-path audit / benchmark hygiene','',
        '`COMPILE FLAG OPTIMIZATION: ALREADY SATISFIED`. Actual generated makefile와 실행된 Gate E compiler command에서 '
        '`g++ -c ... -O3 -march=native -std=c++17 -I. ...` 확인. 2T/4T만 `-fopenmp`; '
        '`-ffast-math`, `-Ofast`, unsafe math flags 없음. 동일 플래그를 재적용한 speedup 주장은 하지 않는다. '
        +link('existing-generated-build-commands.txt')+' 및 각 build-console/proof makefile.', '',
        '`NO PER-STEP PYTHON ROUNDTRIP`. C++ main에서 2s tape를 C++ vector로 preload한 뒤 Network.run을 시작한다. '
        '각 1ms는 C++ row memcpy로 소비한다. timed run 도중 Python callback/IPC/file noise read 없음. '
        'ready/go 파일은 시작 전에만 사용. TimedArray migration이나 공급 redesign은 하지 않았다.', '',
        '각 owned consumer에 HIGH_PRIORITY_CLASS(128), 실제 process affinity를 설정·확인했다. '
        'REALTIME_PRIORITY_CLASS는 사용하지 않았다. consumer-only 1T CPU6(mask64), 2T CPUs4,6(mask80), '
        '4T CPUs0,2,4,6(mask85), 즉 기존 실측 SMT core pair마다 하나의 logical CPU. '
        '각 trial JSON에 actual PID/mask/thread count/logical CPUs가 있다. 외부 사용자 process를 종료하거나 설정하지 않았다.', '',
        f"Active power plan: `{audit['active_power_plan']}`. 전역 plan 변경 없음, 종료 후 동일 확인. "
        f"모든 trial PDH _Total Processor Performance {min(powers):.2f}–{max(powers):.2f}%. "
        '관측된 aggregate counter에서는 심한 clock-down 신호가 없지만 direct per-core frequency 측정은 아니므로 완전한 배제는 아니다. '
        +link('power-plan-after.json')+'.','',
        f"Synaptic delay: explicit delay assignment 없음; 실제 {len(delays)} stored values의 default delay min/max "
        f"{delay['min_ms']}/{delay['max_ms']}ms, 균일0. 이전 spike-buffer를 before_groups에 전달하는 기존 scheduling 유지. "
        'delay/queue semantics 변경 없음. '+link('delay-audit.json')+'.','',
        '## 2. Brian2 built-in profile FIRST','',
        '`net.run(..., profile=True)`로 actual Brian2 standalone `profiling_info.txt`를 읽었다. '
        '이는 CPPStandaloneDevice가 Network.profiling_info를 위해 읽는 지원 output이다. '
        'custom CodeObject profiler를 만들지 않았다. [Brian2 profiling](https://brian2.readthedocs.io/en/2.9.0/user/running.html#profiling).', '',
        '아래 PROFILED RUN은 병목 분해용이다. 실제 generated timer는 1T `std::clock()/CLOCKS_PER_SEC`(coarse milliseconds), '
        'OpenMP 2T/4T `omp_get_wtime()`; 서로 다른 timer/overhead와 실행 간 환경 변동 때문에 작은 차이를 정밀 speedup으로 해석하지 않는다. '
        'percent의 분모는 profiled CodeObject 합이며 Network.run 전체 timer와 동일하지 않다. '
        '모든 p99 판정은 PROFILER OFF steady_clock wall timing으로 별도 실행했다.','']
    for s in ['baseline','looming']:
        d=read(f'current-1t-{s}-p1-2s-q50-off-0')
        lines += [f'### {s} / 1T / producer OFF','',
            '| Actual CodeObject | Built-in time s | % profiled total | Calls |','|---|---:|---:|---:|']
        for obj in d['profile']:
            lines.append(f"| {obj['codeobject']} | {fmt(obj['seconds'])} | {obj['percent']:.2f} | {obj['calls']} |")
        lines += ['',f"Top3 share {sum(o['percent'] for o in d['profile'][:3]):.2f}%. "
            f"Profiled total {sum(o['seconds'] for o in d['profile']):.3f}s; measured Network.run wall {d['timings']['network_compute']:.3f}s.",'']
    lines += ['## 3. Consumer-only OpenMP scaling','',
        'strong LC4+LPLC2, 동일 shared2s noise, first0.5s excluded → 30 measured windows/repeat; 각 세 반복. '
        '아래 p50/p95/p99/max는 ms, misses는 30개 >50ms 횟수.','',
        '| Threads / repeat | mean | p50 | p95 | p99 | max | misses | Synaptic delivery profile s (separate profiled run) |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    syn_times=[]
    for record in scale['records']:
        prof=read(record['profile']);syn_time=next(x['seconds'] for x in prof['profile'] if x['codeobject']=='connections_pre_codeobject')
        syn_times.append(syn_time)
        for n in record['repeats']:
            r=read(n);s=r['brain_statistics']
            lines.append(f"| {record['threads']}T/{r['trial']} | "+' | '.join(fmt(s[k]) for k in ['mean_ms','p50_ms','p95_ms','p99_ms','max_ms'])+f" | {s['deadline_misses']}/30 | {fmt(syn_time)} |")
    lines += ['',f'Synaptic delivery 1/2/4T: {", ".join(fmt(t) for t in syn_times)}s: flat/slightly slower, not faster. '
        'generated `connections_pre_codeobject.cpp`는 `#pragma omp parallel` 안에 `#pragma omp master` delivery loop를 사용한다. '
        '이 경로에 atomic/critical은 없지만 accumulation은 master 직렬 처리다. queue push는 thread region에 존재한다. '
        '따라서 LIF kernel 하나의 scaling만으로 full consumer scaling을 기대할 수 없다. 4T scaling 불량으로 8T는 미실시. '
        '[Brian2 OpenMP caution](https://brian2.readthedocs.io/en/2.9.0/user/computation.html#multi-threading-with-openmp).','',
        '| CodeObject | 1T profile s | 2T profile s | 4T profile s |','|---|---:|---:|---:|']
    profiles=[read(r['profile'])['profile'] for r in scale['records']]
    for name in [o['codeobject'] for o in profiles[0]]:
        values=[next(o['seconds'] for o in p if o['codeobject']==name) for p in profiles]
        lines.append(f'| {name} | '+' | '.join(fmt(x) for x in values)+' |')
    lines += ['', '## 4. Cheap optimization trials','',
        '현재 SpikeMonitor는 `record=False`이며 N개 cumulative count만 저장한다. StateMonitor/PopulationRateMonitor/full spike-time 기록 없음. '
        'spikes_codeobject는 <1%, custom quantum_boundary도 작은 항목이었다. 따라서 motor/readout이나 cumulative observation 제거는 하지 않았다. '
        'delay audit는 diagnostic-only로 유지했다.', '',
        '| Variant | One change / measured reason | mean ms (3 repeats) | p99 ms (3 repeats) | Correctness | Keep/reject |',
        '|---|---|---|---|---|---|']
    for v,tag,reason in [('current',scale['records'][0]['tag'],'unchanged control'),
        ('clear-fused',cheap['records'][0]['tag'],'Top LIF pass에 incoming scratch clear를 융합, 별도 full-N clear pass 제거'),
        ('zero',cheap['records'][1]['tag'],'noise-reader 약8%: 검증된 row-pointer 소비를 consumer-only로 비교')]:
        rows=[read(tag+f'-off-{i}') for i in range(3)]
        lines.append(f'| {v} | {reason} | '+', '.join(fmt(r['brain_statistics']['mean_ms']) for r in rows)+' | '
            +', '.join(fmt(r['brain_statistics']['p99_ms']) for r in rows)+' | exact full dynamics/circuit PASS | '+('control retained, not adopted as realtime' if v=='current' else 'REJECT: no stable35ms headroom')+' |')
    lines += ['', 'Clear-fused는 incoming scratch를 다음 start에서 zero하는 대신 현재 LIF 사용 직후 zero한다. '
        '초기 incoming=0, synaptic delivery 이후 LIF만 이를 소비하며 intervening reader 없음. '
        '따라서 v/syn/noise/activity/ref/eligible 및 spike/circuit 출력은 모든 반복에서 full-array exact same. '
        '최종 incoming scratch 값 자체는0으로 달라지지만 다음 step 전에 원래도 clear되는 bookkeeping이며 dynamics/readout state 변화로 숨기지 않는다. '
        '이 변형은 성능이 안정적으로 개선되지 않아 버렸다.', '',
        'zero-copy는 원래 allocation pointer를 serialization/deallocation 전에 복구했다. '
        '동일 frozen input에서 full neural states, population/LC4/LPLC2/GF/DNp09, circuit EMA/peaks exact PASS. '
        'producer를 붙이지 않았으므로 packing 비용은 없지만 단독 p99도 개선되지 않았다. '
        '여러 변경을 섞거나 native RNG/model parameter를 변경하지 않았다. p99 >50ms outlier는 삭제하지 않았다.', '',
        '## 5. Quantum timeline / histogram diagnosis','',
        '각 profiler-OFF persistent20s run에서400 windows, warmup10 제외390 measured; 세 반복. '
        '전체20s 독립 Gaussian tape는 약13.21GB로 current available RAM(~4.4GB)보다 커서 paging 병목을 추가할 위험이 있었다. '
        '따라서 고정 resident2s tape의40-window noise replay를 명시적인 진단 input으로 사용했다. '
        '이것은 Gaussian current equation을 바꾸거나 production noise replay를 채택한 것이 아니며, 독립20s noise regime/최종 realtime 인증이 아니다. '
        'known40 input period와 activity autocorrelation을 별도로 표시해 OS periodicity와 혼동하지 않는다.', '',
        '!['+'Timeline'+']('+ (REPORT/'timeline.png').as_posix()+')','',
        '!['+'Histogram'+']('+ (REPORT/'histogram.png').as_posix()+')','',
        '| Repeat | mean | p50 | p95 | p99 | max | >50ms /390 | spike/timing r | timing lag40 r | spike lag40 r |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r,d in zip(runs,diagnostics):
        s=r['brain_statistics']
        lines.append(f"| {r['trial']} | "+' | '.join(fmt(s[k]) for k in ['mean_ms','p50_ms','p95_ms','p99_ms','max_ms'])+
            f" | {s['deadline_misses']}/390 ({s['deadline_miss_rate']*100:.2f}%) | {fmt(d['spike_timing_pearson'])} | {fmt(d['timing_lag40_autocorrelation'])} | {fmt(d['spike_lag40_autocorrelation'])} |")
    lines += ['', '주 compute band 위에 느린 episode/tail과 큰 repeat-to-repeat shift가 존재한다. 단일 p99로 steady kernel 비용만 설명할 수 없다. '
        '반면 같은 input의 모든 final neural state와 circuit 출력은 정확히 같았다. '
        '단순 spike count correlation은 인과성 증명이 아니며 spike당 fanout 차이도 있어 synaptic delivery 비용을 배제하지 않는다. '
        '재현 가능한 100-window flush/resize/logging event가 입증되지 않아 speculative periodic-event fix는 하지 않았다. '
        'boundary count/finite scans와 flush는 per-quantum timer 밖, 전체 Network.run timer 안이다. '
        '현재 자료만으로 scheduler/cache/page-fault 원인을 확정할 수 없다. '+link('e4-diagnosis.json')+'.', '',
        '## 6. Concurrent producer retest','',
        'NOT RUN. E2/E3에서 충분히 개선된 consumer HEADROOM 후보가 생기지 않아 STOP4/Done(NO) 조건으로 E5에 진입하지 않았다. '
        'Gate D producer-only 성공을 consumer concurrent PASS로 사용하지 않고, 13–18% contention을 optimized consumer에 외삽하지 않았다. '
        '새 producer count/affinity 탐색, double buffer, generic ring, IPC/Godot/ecology integration 없음. '
        'future world/sensory/motor state도 계산하지 않았다.', '',
        '## 7. Headroom decision','',
        'CONSUMER HEADROOM: FAIL. Cheap no-semantics 옵션 이후에도 어떤 반복 안정성 구성도 35ms 목표 또는50ms hard floor를 충족하지 못했다. '
        '이는 테스트한 싼 옵션의 실패이며 CPU 하드웨어나 모든 최적화에 대한 불가능성 정리는 아니다. '
        'No new backend / Rust/GPU rewrite / neural equation / dt / weights / pruning / connectivity / delay/noise amplitude changes. '
        '아래100ms도 production architecture로 채택하지 않았다.', '',
        '## 8. Plan Z — diagnostic only','',z['classification'],'',
        '실행 조건: consumer1T 세 반복의 median mean이40–50ms, cheap 옵션으로35ms 실패. '
        'dt1ms 그대로, 100ms에서100 neural steps를 계산한다. 동일20s frozen replay/strong input/CPU6/HIGH priority, 각 세 반복. '
        '모든 final full dynamics state SHA는 50ms/100ms 각각 exact same. 아래 boundary-inclusive Network.run cost로 비교한다. '
        '시간 간격 확장으로 pure neural compute budget이 공짜로 생긴다는 주장은 하지 않는다.', '',
        '| Repeat | 50ms network ms/neural-ms | 100ms network ms/neural-ms | Speedup pair | 50ms mean quantum ms | 100ms mean quantum ms |',
        '|---|---:|---:|---:|---:|---:|']
    runs100=[read(n) for n in z['q100_repeats']]
    for i,(a,b) in enumerate(zip(runs,runs100)):
        lines.append(f"| {i} | {fmt(z['q50_network_ms_per_neural_ms'][i])} | {fmt(z['q100_network_ms_per_neural_ms'][i])} | {z['pair_speedups'][i]:.4f}× | {fmt(a['brain_statistics']['mean_ms'])} | {fmt(b['brain_statistics']['mean_ms'])} |")
    lines += ['', f"Median pair factor {median(z['pair_speedups']):.4f}×. 판정 기준은 측정 전 median ratio≥1.10 및 모든 pair≥1.05로 정했다. "
        'sequential run-to-run variation이 커서 control period 자체의 인과적 이득으로 단정하지 않는다. '
        'producer/synchronization/IPC/world overhead는 포함되지 않는다. '+link('plan-z.json')+'.', '',
        '| 100ms repeat | p50 ms | p95 ms | p99 ms | max ms | >100ms/195 |',
        '|---|---:|---:|---:|---:|---:|']
    for r in runs100:
        s=r['brain_statistics']
        lines.append(f"| {r['trial']} | "+' | '.join(fmt(s[k]) for k in ['p50_ms','p95_ms','p99_ms','max_ms'])+f" | {s['deadline_misses']}/195 |")
    lines += ['', '100ms p99도 세 반복 모두100ms floor를 초과했다. mean neural/wall이1× 이상인 것만으로 deadline/jitter를 해결했다고 하지 않는다.', '',
        '## 9. Integrity / resources','',
        '모든 cheap variant의 population/LC4/LPLC2/GF/DNp09 counts, circuit activity, final v/syn/ref/activity/noise/eligible는 '
        'same-input1T control과 exact same. OpenMP thread variants도 현재 same-input 검사에서 circuit/count 및 selected state guardrail PASS; '
        '각 correctness JSON에 exact 여부와 max difference가 있다. OpenMP 검증은 existing engineering equivalence이며 3-seed stochastic natural variability 인증이 아니다. '
        'all effective i/j/w 원본 CSR 일치, finite/no-runaway PASS. Original previous-spike scheduling 및 dt1ms 유지.', '',
        f"기존 Core/Body/Ecology/Gate A/B/C/D {preserved['checked_files']} files SHA 동일, changed0. regression {preserved['tests']}/{preserved['tests']} PASS. "
        'Gate E 전용 source/report/work만 추가했다. Baseline NumPy2.4.6 유지; isolated NumPy1.26.4/Brian2 2.9.0 실험. '
        +link('preservation-after.json')+'.', '',
        f"추가 Gate D generated source/executable {generated['checked_generated_source_and_executables']} SHA 검증도 changed0. "
        '초기 make dry-run 감사는 GNU make의 included dependency 재작성 동작 때문에 work/의 make.deps 캐시 하나를 비웠다. '
        'compiler PATH 오류로 compile은 성공하지 않았으며, 정상 동일1T dependency graph의 byte-copy로 캐시를 복구했다. '
        'original cache before-SHA는 없으므로 그 캐시의 원래 byte identity를 주장하지 않는다. '
        'verified neural source/executable/result/data는 모두 동일하고, 수정한 감사는 기존 makefile만 읽는다. '
        +link('gate-d-generated-integrity.json')+'.', '',
        f'C++ sampled peak RSS {peak} bytes ({peak/2**30:.3f}GiB); '
        f"controller OS peak RSS {summary['peak_controller_os_rss_bytes']} bytes ({summary['peak_controller_os_rss_bytes']/2**30:.3f}GiB). "
        '별도 process들의 peak를 동시에 측정한 전체 tree peak로 주장하지 않는다. Compiler peak는 미측정.', '',
        '| Long diagnostic / repeat | init s | network s | output s | 20/network (brain-only) |', '|---|---:|---:|---:|---:|']
    for r in runs+runs100:
        t=r['timings'];lines.append(f"| q{r['quantum_ms']}/{r['trial']} | {fmt(t['init'])} | {fmt(t['network_compute'])} | {fmt(t['brian_output'])} | {20/t['network_compute']:.4f}× |")
    lines += ['', 'Cold/preload/init, model setup/codegen/compile, output serialize는 steady quantum compute와 분리했다. '
        '전 run parameter/compile flags/PID/mask/priority/power metadata는 raw JSON/build proof에 보존했다. '
        'source-sha256.json 및 evidence-sha256.json에 새 Gate E artifact SHA가 있다. '
        '기존 Body/Ecology composite remainder와 이 brain-only factor를 합쳐 end-to-end 성능을 추정하지 않는다.','',
        '종료: 실용적35ms headroom NO. production 변경 없이 결과를 Human Decision에 전달한다. '
        '본편 복귀,100ms control frequency 채택,추가 최적화 중 어떤 것도 이번 Gate E에서 임의로 실행하지 않았다.']
    text='\n'.join(lines)+'\n'
    (REPORT/'DELIVERY.md').write_text(text,encoding='utf-8')
    save(REPORT/'source-sha256.json',{p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'realtime/gate-e').iterdir()) if p.is_file()})
    save(REPORT/'evidence-sha256.json',{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(REPORT.rglob('*')) if p.is_file() and p.name!='evidence-sha256.json'})
    print(json.dumps(summary,ensure_ascii=True,indent=2))

if __name__=='__main__':main()
