"""Summarize completed Gate D evidence. Does not execute any simulation."""
import json
from statistics import mean
from env import ROOT, REPORT, sha, save


def read(name):
    return json.loads((REPORT / (name + '.json')).read_text(encoding='utf-8'))


def fmt(value):
    return f'{value:.3f}'


def link(name):
    return f'[{name}]({(REPORT / name).as_posix()})'


def main():
    decision = read('d1-final-decision')
    preservation = read('preservation-after')
    d0 = read('d0-decision')
    correctness = read('zero-copy-correctness')
    comparison = read('d1-contention-comparison')
    assert preservation['success'] and not preservation['changed_files']
    assert correctness['success'] and all(correctness['checks'].values())
    assert d0['selected_workers'] == 2 and d0['additional_worker_search_stopped']
    assert not decision['headroom'] and not decision['realtime_feasible']
    assert not decision['d2_allowed']
    valid = decision['valid_configurations']
    trials = {c: {s: [read(f'{c}-{s}-{i}') for i in range(3)]
                  for s in ('baseline', 'looming')} for c in valid}
    worst = lambda c: max(t[k]['p99_ms'] for rows in trials[c].values()
                         for t in rows for k in ('brain_statistics', 'producer_statistics'))
    selected = min(valid, key=worst)
    assert selected == decision['selected_configuration']
    assert abs(worst(selected) - decision['worst_side_p99_ms']) < 1e-8
    for c in valid:
        assert worst(c) > 50
        for rows in trials[c].values():
            for t in rows:
                assert t['finite'] and all(t['graph_verified'].values())
                assert t['brain_statistics']['blocks'] == 30
                assert len(t['brain_all_window_ms']) == 40
                assert t['brain_affinity_mask'] == sum(1 << x for x in t['brain_cpus'])
                for w in t['producer']['workers']:
                    a = w['affinity']
                    assert a['explicitly_pinned']
                    assert a['affinity_mask'] == sum(1 << x for x in a['logical_cpus'])
    maximum = max(worst(c) for c in valid)
    strong_max = max(t[k]['p99_ms'] for c in valid for t in trials[c]['looming']
                     for k in ('brain_statistics', 'producer_statistics'))
    peak_cpp = max(t['peak_consumer_rss'] for c in valid
                   for rows in trials[c].values() for t in rows)
    summary = dict(classification='RNG RESCUE: FAIL — CPU CONTENTION',
                   pipeline_p99_ms=None, pipeline_deadline_miss_rate=None,
                   producer_starvation=None, sustained_60s_neural_wall=None,
                   selected_configuration=selected, best_robust_d1_side_p99_ms=worst(selected),
                   worst_tested_d1_side_p99_ms=maximum, worst_strong_d1_side_p99_ms=strong_max,
                   d1_side_margin_ms=50-worst(selected), d1_side_equivalent_factor=50/worst(selected),
                   d2='NOT RUN — D1 concurrent feasibility failed',
                   d3='NOT RUN — no admitted D2 pipeline',
                   d4='NOT RUN — no concurrent HEADROOM candidate',
                   baseline_checked_files=preservation['checked_files'], baseline_changed_files=[],
                   regression_tests=preservation['tests'], peak_cpp_sampled_rss_bytes=peak_cpp,
                   measured_python_os_peak_rss_bytes=comparison['measured_python_process_peak_rss_bytes'],
                   qualification='D1 side timings are short feasibility measurements, not pipeline or 60s certification. Consumer already lacks 35ms headroom without producer; concurrent CPU/noise-memory activity further slows it. No network-level parallel-stream equivalence claim.')
    save(REPORT / 'gate-d-summary.json', summary)
    lines = [summary['classification'], '',
             '## 최종 성능 요약', '',
             '| 항목 | 실제 결과 |', '|---|---|',
             '| Best steady-state pipeline p99 | NOT MEASURED — D2 진입 불가 |',
             f'| 최선의 반복 안정성 D1 side p99 | {fmt(worst(selected))} ms (`{selected}`) |',
             f'| Worst tested workload p99 | {fmt(maximum)} ms — D1 side, 2T zero-copy baseline |',
             f'| Worst strong-workload p99 | {fmt(strong_max)} ms — D1 side |',
             '| Sustained neural/wall | NOT CERTIFIED — 60초 pipeline 미실시 |',
             f'| Headroom | {fmt(50-worst(selected))} ms — D1 side 기준, pipeline margin 아님 |',
             f'| Equivalent realtime factor | {50/worst(selected):.4f}× — 50/p99 D1 side 환산, sustained factor 아님 |',
             '| Producer starvation | NOT MEASURED — 0으로 간주하지 않음 |',
             '| Pipeline deadline miss rate | NOT MEASURED |', '',
             '질문에 대한 답: 현재 Ryzen 3 4100에서 noise 공급 경로만으로 실용적인 realtime headroom을 확보하지 못했다. '
             'producer 단독 처리량은 해결했지만, full MaleCNS consumer는 producer 없이도 35ms 기준에 미달하며 동시 실행에서 더 느려졌다. '
             'FAIL 분류는 이번에 시험한 concurrent 구성에 대한 판정이다. CPU의 모든 구성이나 향후 최적화가 불가능하다는 결론은 아니다.', '',
             '50ms hard floor / 35ms adoption target / 30ms ideal stop. 어느 유효 D1 구성도 두 workload의 세 반복 모두에서 양쪽 p99 ≤50ms를 유지하지 못했다. '
             '따라서 D2 금지 조건을 적용했다. 기존 backend, core, body, ecology는 교체하거나 배포하지 않았다.', '',
             '## D-1 — native float32 audit', '',
             '`standard_normal(dtype=np.float32, out=preallocated_contiguous_float32)` 직접 생성. '
             '50×165122 = 8256100 samples, 33024400 bytes/block. float64→float32 cast 없음, fill 내부 output allocation 없음. '
             'baseline heterogeneity draw 이후 단일 PCG64 stream; buffer 재사용. Gate C 경로도 이미 native float32였다.', '',
             '## D0 — 최소 persistent worker 수', '',
             '모든 행: warmup 10 blocks 제외, 연속 200 measured blocks; dispatch/completion synchronization 포함.', '',
             '| 경로 | mean ms | p50 | p95 | p99 | max | blocks/s | neural/wall | speedup vs D0 1w |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    one = read('d0-1w')['statistics']['mean_ms']
    for name in ('d-minus1', 'd0-1w', 'd0-2w'):
        s = read(name)['statistics']
        speed = 'N/A' if name == 'd-minus1' else f"{one/s['mean_ms']:.4f}×"
        lines.append(f"| {name} | " + ' | '.join(fmt(s[x]) for x in
                     ('mean_ms','p50_ms','p95_ms','p99_ms','max_ms','blocks_per_second','neural_wall_ratio')) + f' | {speed} |')
    lines += ['', 'D-1 >35ms로 D0 진행. D0 2w p99 ≤35ms에서 STOP: 3/4 workers 미실시. '
              'persistent worker마다 root SeedSequence(20260913).spawn(2)의 child stream을 유지했다. '
              'worker 0 → child [0] → runtime [0,82561), worker 1 → child [1] → [82561,165122). '
              '각 worker의 [50,82561] contiguous float32를 worker-major preallocated storage에 고정 배치한다. '
              '고정 worker count에서 scheduling에 따른 neuron assignment 변경이 없다. 단일 reference PCG64와 같은 random sequence라는 주장은 하지 않는다. '
              '[NumPy multithreaded generation](https://numpy.org/doc/2.4/reference/random/multithreading.html), '
              '[independent child streams](https://numpy.org/doc/2.4/reference/random/parallel.html).', '',
              '## D1 — 실제 concurrent feasibility', '',
              '별도 full Brian2 C++ process와 Python persistent producer threads를 실제 동시 실행했다. '
              'consumer는 기존 shared 비주기 PCG64 2초 tape를 시작 전에 읽고, producer 출력은 폐기한다. '
              '이것은 throughput/contention 검사이며 producer가 brain에 noise를 공급하는 pipeline은 아니다. '
              'consumer 2 neural seconds / 40×50ms 중 처음 10 windows(0.5 neural s)를 제외하여 각 반복 30 windows; '
              'baseline/strong LC4+LPLC2(기존 amplitude 3) 각 세 반복. producer는 10-block warmup 후 C++ compute interval 안에 완전히 포함된 generation intervals만 집계했다. '
              'QPC/perf_counter의 같은 system clock으로 실제 overlap을 확인했다. startup·output serialization은 quantum compute 밖이다.', '',
              '| 구성 | Brain logical CPUs | Producer logical CPUs | baseline worst side p99 | strong worst side p99 | 판정 |',
              '|---|---|---|---:|---:|---|']
    for c in valid:
        t = trials[c]['baseline'][0]
        cpus = [w['affinity']['logical_cpus'] for w in t['producer']['workers']]
        vals = [max(t[k]['p99_ms'] for t in trials[c][s]
                    for k in ('brain_statistics','producer_statistics')) for s in ('baseline','looming')]
        lines.append(f"| {c} | {t['brain_cpus']} | {cpus} | {fmt(vals[0])} | {fmt(vals[1])} | FAIL |")
    lines += ['', '초기 탐색 `d1-b2-p2` 전체는 controller 시작 당시 build 완료를 보장하지 못해 compiler contention 가능성이 있어 제외했다. '
              'raw evidence는 보존했고 동일 allocation을 `d1-b2-p2-clean`으로 재실시했다. 특정 느린 반복만 제외하지 않았다. '
              + link('d1-excluded.json') + '.', '',
              '### 실제 affinity 증거', '',
              'Win32 topology 조회는 D1 jitter 확인 후 수행했다: physical-core logical pairs [0,1], [2,3], [4,5], [6,7]. '
              '단순 process affinity만으로 worker placement를 주장하지 않고 각 worker 안에서 SetThreadAffinityMask 후 GetThreadGroupAffinity로 실제 mask를 기록했다. '
              '[Windows thread affinity API](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadaffinitymask).', '']
    sample = trials[selected]['looming'][1]
    lines += [f"예: `{selected}` strong trial 1의 종료된 brain PID {sample['brain_pid']}, actual process mask {sample['brain_affinity_mask']} (CPU {sample['brain_cpus']}).", '',
              '| Worker | 실제 OS thread ID | actual mask | logical CPU | child | runtime range |',
              '|---|---:|---:|---|---|---|']
    for w in sample['producer']['workers']:
        a = w['affinity']
        lines.append(f"| {w['worker_id']} | {a['thread_id']} | {a['affinity_mask']} | {a['logical_cpus']} | {w['spawn_key']} | [{w['runtime_start']},{w['runtime_end']}) |")
    lines += ['', link(f'{selected}-looming-1.json') + ' 및 각 trial JSON에 모든 PID, mask, stream/layout metadata가 있다.', '',
              '### matched producer OFF 비교', '',
              '동일 best 1T executable, CPU6 affinity, scenario, input, warmup에서 ON/OFF 각각 세 반복. '
              '시간순 반복 비교이며 instruction-level profiling이나 외부 시스템의 완전한 통제는 아니다.', '',
              '| Workload | ON mean ms | OFF mean ms | ON/OFF mean slowdown | ON repeat p99 ms | OFF repeat p99 ms |',
              '|---|---:|---:|---:|---|---|']
    for s, c in comparison['comparison'].items():
        lines.append(f"| {s} | {fmt(c['on_mean_ms'])} | {fmt(c['off_mean_ms'])} | {(c['mean_contention_slowdown']-1)*100:.2f}% | "
                     + ', '.join(fmt(x) for x in c['on_repeat_p99_ms']) + ' | '
                     + ', '.join(fmt(x) for x in c['off_repeat_p99_ms']) + ' |')
    lines += ['', 'producer-only matched 200-block 세 반복 p99: '
              + ', '.join(fmt(t['statistics']['p99_ms']) for t in comparison['producer_only']) + ' ms. '
              '2-worker producer 자체는 반복해서 HEADROOM PASS지만 consumer OFF도 strong p99 42.905–46.704ms로 이미 headroom 부족이다. '
              '실패를 Gaussian 생산 비용 하나로만 설명할 수 없다. ' + link('d1-contention-comparison.json') + '.', '',
              '### row-pointer zero-copy 공급 변형', '',
              '기존 preloaded noise row를 직접 참조하여 timestep마다 N개 memcpy를 제거하는 noise-supply-only 변형도 시험했다. '
              '원래 owned noise_sample pointer를 serialization/deallocation 전에 복구했다. 동일 입력 1T copy/zero 비교의 '
              '모든 quantum observation(시간 제외), final v/syn/refractory/noise_sample 10 checks가 exact PASS. '
              '단, worker-major 출력을 C-order [50,N]으로 packing하는 추가 copy 비용을 producer timer에 포함했고, packing coordinator affinity도 기록했다. '
              '이 변형도 두 CPU allocation에서 FAIL이었다. exact shared-input proof를 parallel child-stream network equivalence로 확대하지 않는다. '
              + link('zero-copy-correctness.json') + '.', '',
              '## D2 / D3 / D4 — 조건부 미실시', '',
              '- D2: NOT RUN. 모든 시험 allocation이 적어도 한 workload/repeat에서 side p99 >50ms. concurrent feasibility 미확인으로 A/B double buffer 구현 금지.',
              '- D3: NOT RUN. D2 pipeline 없음. warmup 후 60s/1200 windows, cadence p50/p95/p99/max, wait/swap, starvation, sustained neural/wall 인증값 없음.',
              '- D4: NOT RUN. concurrent HEADROOM 후보 없음. 3 root-seed reference/candidate baseline/stimulus/recovery population/active fraction/LC4/LPLC2/GF/DNp09 natural variability 인증 없음. 미실시를 PASS로 간주하지 않는다.', '',
              'future world/sensory/motor state를 계산하지 않았고 world authority나 lockstep을 변경하지 않았다. '
              '본편 4번째 탄환, Console UI, world resize, Godot/IPC/ecology migration, GPU/backend/weight/dt/noise amplitude 변경 없음.', '',
              '## Integrity / resource / startup', '',
              f"기존 Brain Core/Body/Ecology/Gate A/B/C 및 runtime data {preservation['checked_files']} files SHA before/after 동일, changed files 0. regression {preservation['tests']}/{preservation['tests']} PASS. "
              + link('preservation-after.json') + '.', '',
              '실제 graph source/target/weight는 모든 유효 D1 trial에서 원본 CSR와 비교해 일치했고 state는 finite였다. '
              '165122 neurons / 6327564 effective signed synapses; anatomical 6474533. float32, dt1ms, noise_std0.1, recurrent gain2 등 기존 parameter 유지. '
              'weights SHA `3fb657efc33922829dea821d3fd08ac516a7db2fc471182a73b841844915aaf3`; '
              'shared noise SHA `17b3194eac1301c7e15976f0ceedba26f435503230af0f263565181b4b6d38d0`.', '',
              f"Hardware: Ryzen 3 4100 4C/8T SMT, {read('preservation-before')['machine']['total_ram_bytes']/2**30:.2f} GiB RAM, Windows, CPU only. "
              'Baseline Python3.11.9/NumPy2.4.6 미변경. Brian2 2.9.0 실험은 기존 isolated NumPy1.26.4를 entry.py에서 사용. '
              'TDM-GCC9.2, O3/native C++17, 2T만 OpenMP; fast-math 없음.', '',
              f'유효 D1 C++ process sampled peak RSS: {peak_cpp} bytes ({peak_cpp/2**30:.3f} GiB). '
              f"matched measurement Python process OS peak RSS: {comparison['measured_python_process_peak_rss_bytes']} bytes "
              f"({comparison['measured_python_process_peak_rss_bytes']/2**30:.3f} GiB). "
              '둘을 동시에 측정한 전체 process-tree peak라고 주장하지 않는다. compiler tree peak 미측정. '
              'offline preloaded 2s tape 1320976000 bytes; producer buffer 33024400 bytes, packed variant 추가 33024400 bytes. '
              '이 대용량 tape는 D1 검사 전용이며 최종 streaming buffer 구현이 아니다.', '',
              '| Build | Model setup s | Codegen s | Compile s |', '|---|---:|---:|---:|']
    for p in sorted(REPORT.glob('d1-build-*.json')):
        b = json.loads(p.read_text(encoding='utf-8'))
        lines.append(f"| {p.stem} | {fmt(b['model_setup_seconds'])} | {fmt(b['codegen_seconds'])} | {fmt(b['compile_seconds'])} |")
    lines += ['', '| Best allocation trial | Init s | Actual 2s network compute s | Output s | 2/network wall (brain only) |',
              '|---|---:|---:|---:|---:|']
    for s, rows in trials[selected].items():
        for t in rows:
            x = t['timings']
            lines.append(f"| {s}-{t['trial']} | {fmt(x['init'])} | {fmt(x['network_compute'])} | {fmt(x['brian_output'])} | {2/x['network_compute']:.4f}× |")
    lines += ['', 'Init includes preloading; controller GO wait is outside compute. OS disk/cache cold-start은 별도 인증하지 않았다. '
              '2s brain-only factor는 producer 공급, sync/swap, startup, Godot, ecology를 포함하는 end-to-end factor가 아니다. '
              '기존 Body 8.5% / Ecology 19.4% composite remainder는 startup/socket/logging/ACK wait/shutdown을 포함하므로 이 fast-brain 수치에 steady-state overhead로 투영하지 않는다.', '',
              '## D1 per-repeat detailed timing evidence', '',
              '아래 mean/p50/p95/p99/max는 ms. brain miss는 warmup 제외 30 windows의 >50ms 횟수이며 pipeline miss가 아니다. '
              '각 producer의 sample count는 actual overlap의 strict-contained block 수이다.', '',
              '| Configuration / workload / repeat | Side | Samples | mean | p50 | p95 | p99 | max | Brain misses |',
              '|---|---|---:|---:|---:|---:|---:|---:|---|']
    for c in valid:
        for s, rows in trials[c].items():
            for t in rows:
                misses = sum(x > 50 for x in t['brain_all_window_ms'][10:])
                for side in ('brain', 'producer'):
                    stat = t[side + '_statistics']
                    count = f'{misses}/30 ({misses/30*100:.1f}%)' if side == 'brain' else 'N/A'
                    lines.append(f"| {c}/{s}/{t['trial']} | {side} | {stat['blocks']} | "
                                 + ' | '.join(fmt(stat[k]) for k in ('mean_ms','p50_ms','p95_ms','p99_ms','max_ms')) + f' | {count} |')
    lines += ['', '## 재현 및 artifact', '',
              'Gate D sources are experimental only; no adoption or ecology wiring. '
              'source-sha256.json hashes all Gate D Python/README; evidence-sha256.json hashes reports/generated proof except its own manifest. '
              'Build JSONs separately include generated C++ and executable SHA. '
              'preservation-before.json contains the frozen 369-file baseline hashes. '
              'Run commands and safe ordering are in the Gate D source README.']
    content = '\n'.join(lines) + '\n'
    (REPORT / 'DELIVERY.md').write_text(content, encoding='utf-8')
    save(REPORT / 'source-sha256.json', {p.relative_to(ROOT).as_posix(): sha(p)
         for p in sorted((ROOT / 'realtime/gate-d').iterdir()) if p.is_file()})
    save(REPORT / 'evidence-sha256.json', {p.relative_to(ROOT).as_posix(): sha(p)
         for p in sorted(REPORT.rglob('*')) if p.is_file() and p.name != 'evidence-sha256.json'})
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
