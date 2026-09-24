CONSUMER HEADROOM: FAIL

consumer 비용의 주 항목은 LIF full-population update, synaptic delivery, threshold 검사였다. 싼 semantics-preserving 변경 두 개와 consumer-only 1T/2T/4T 모두 strong p99 ≤35ms를 안정적으로 만들지 못했다. 최선 구성조차 hard floor50ms를 반복해서 넘었으므로 채택하지 않았다. 더 깊은 custom backend/architecture work는 시작하지 않았다.

| Headroom 항목 | 결과 |
|---|---|
| 최선 short consumer 반복-worst p99 | 63.161 ms (`current-1t-looming-p0-2s-q50`) |
| 50ms floor 대비 margin / 환산 factor | -13.161 ms / 0.7916× (side 환산, sustained factor 아님) |
| 35ms actual adoption / 30ms ideal | 미달 / 미달 |
| Optimized concurrent consumer / producer p99 | NOT MEASURED — 생존 candidate 없음 |
| Optimized concurrent contention % | NOT MEASURED — Gate D 13–18%를 외삽하지 않음 |
| Streaming pipeline / Godot headroom | NOT CERTIFIED — 이번 범위 아님 |

## 1. Existing-path audit / benchmark hygiene

`COMPILE FLAG OPTIMIZATION: ALREADY SATISFIED`. Actual generated makefile와 실행된 Gate E compiler command에서 `g++ -c ... -O3 -march=native -std=c++17 -I. ...` 확인. 2T/4T만 `-fopenmp`; `-ffast-math`, `-Ofast`, unsafe math flags 없음. 동일 플래그를 재적용한 speedup 주장은 하지 않는다. [existing-generated-build-commands.txt](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-e/existing-generated-build-commands.txt) 및 각 build-console/proof makefile.

`NO PER-STEP PYTHON ROUNDTRIP`. C++ main에서 2s tape를 C++ vector로 preload한 뒤 Network.run을 시작한다. 각 1ms는 C++ row memcpy로 소비한다. timed run 도중 Python callback/IPC/file noise read 없음. ready/go 파일은 시작 전에만 사용. TimedArray migration이나 공급 redesign은 하지 않았다.

각 owned consumer에 HIGH_PRIORITY_CLASS(128), 실제 process affinity를 설정·확인했다. REALTIME_PRIORITY_CLASS는 사용하지 않았다. consumer-only 1T CPU6(mask64), 2T CPUs4,6(mask80), 4T CPUs0,2,4,6(mask85), 즉 기존 실측 SMT core pair마다 하나의 logical CPU. 각 trial JSON에 actual PID/mask/thread count/logical CPUs가 있다. 외부 사용자 process를 종료하거나 설정하지 않았다.

Active power plan: `전원 구성표 GUID: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  (고성능)`. 전역 plan 변경 없음, 종료 후 동일 확인. 모든 trial PDH _Total Processor Performance 102.21–107.02%. 관측된 aggregate counter에서는 심한 clock-down 신호가 없지만 direct per-core frequency 측정은 아니므로 완전한 배제는 아니다. [power-plan-after.json](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-e/power-plan-after.json).

Synaptic delay: explicit delay assignment 없음; 실제 6327564 stored values의 default delay min/max 0.0/0.0ms, 균일0. 이전 spike-buffer를 before_groups에 전달하는 기존 scheduling 유지. delay/queue semantics 변경 없음. [delay-audit.json](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-e/delay-audit.json).

## 2. Brian2 built-in profile FIRST

`net.run(..., profile=True)`로 actual Brian2 standalone `profiling_info.txt`를 읽었다. 이는 CPPStandaloneDevice가 Network.profiling_info를 위해 읽는 지원 output이다. custom CodeObject profiler를 만들지 않았다. [Brian2 profiling](https://brian2.readthedocs.io/en/2.9.0/user/running.html#profiling).

아래 PROFILED RUN은 병목 분해용이다. 실제 generated timer는 1T `std::clock()/CLOCKS_PER_SEC`(coarse milliseconds), OpenMP 2T/4T `omp_get_wtime()`; 서로 다른 timer/overhead와 실행 간 환경 변동 때문에 작은 차이를 정밀 speedup으로 해석하지 않는다. percent의 분모는 profiled CodeObject 합이며 Network.run 전체 timer와 동일하지 않다. 모든 p99 판정은 PROFILER OFF steady_clock wall timing으로 별도 실행했다.

### baseline / 1T / producer OFF

| Actual CodeObject | Built-in time s | % profiled total | Calls |
|---|---:|---:|---:|
| lif_update_codeobject | 0.765 | 53.57 | 2000 |
| neurons_spike_thresholder_codeobject | 0.209 | 14.64 | 2000 |
| connections_pre_codeobject | 0.194 | 13.59 | 2000 |
| shared_noise_reader_codeobject | 0.146 | 10.22 | 2000 |
| clear_incoming_codeobject | 0.054 | 3.78 | 2000 |
| connections_pre_push_spikes | 0.047 | 3.29 | 2000 |
| quantum_boundary_codeobject | 0.012 | 0.84 | 2000 |
| spikes_codeobject | 0.001 | 0.07 | 2000 |
| neurons_spike_resetter_codeobject | 0.000 | 0.00 | 2000 |

Top3 share 81.79%. Profiled total 1.428s; measured Network.run wall 1.429s.

### looming / 1T / producer OFF

| Actual CodeObject | Built-in time s | % profiled total | Calls |
|---|---:|---:|---:|
| lif_update_codeobject | 0.753 | 42.95 | 2000 |
| connections_pre_codeobject | 0.483 | 27.55 | 2000 |
| neurons_spike_thresholder_codeobject | 0.216 | 12.32 | 2000 |
| shared_noise_reader_codeobject | 0.140 | 7.99 | 2000 |
| connections_pre_push_spikes | 0.067 | 3.82 | 2000 |
| clear_incoming_codeobject | 0.058 | 3.31 | 2000 |
| quantum_boundary_codeobject | 0.029 | 1.65 | 2000 |
| spikes_codeobject | 0.004 | 0.23 | 2000 |
| neurons_spike_resetter_codeobject | 0.003 | 0.17 | 2000 |

Top3 share 82.83%. Profiled total 1.753s; measured Network.run wall 1.756s.

## 3. Consumer-only OpenMP scaling

strong LC4+LPLC2, 동일 shared2s noise, first0.5s excluded → 30 measured windows/repeat; 각 세 반복. 아래 p50/p95/p99/max는 ms, misses는 30개 >50ms 횟수.

| Threads / repeat | mean | p50 | p95 | p99 | max | misses | Synaptic delivery profile s (separate profiled run) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1T/0 | 51.350 | 51.028 | 56.280 | 63.161 | 65.698 | 16/30 | 0.483 |
| 1T/1 | 47.144 | 48.043 | 49.296 | 49.925 | 50.162 | 1/30 | 0.483 |
| 1T/2 | 47.173 | 47.834 | 49.796 | 51.110 | 51.573 | 1/30 | 0.483 |
| 2T/0 | 50.727 | 50.079 | 53.953 | 54.238 | 54.347 | 16/30 | 0.512 |
| 2T/1 | 47.257 | 46.640 | 53.772 | 55.359 | 55.784 | 4/30 | 0.512 |
| 2T/2 | 58.707 | 51.916 | 81.568 | 162.711 | 190.572 | 27/30 | 0.512 |
| 4T/0 | 58.826 | 56.852 | 70.237 | 72.568 | 73.338 | 29/30 | 0.502 |
| 4T/1 | 59.443 | 54.071 | 90.581 | 98.632 | 100.158 | 27/30 | 0.502 |
| 4T/2 | 83.457 | 72.600 | 171.585 | 189.991 | 193.552 | 29/30 | 0.502 |

Synaptic delivery 1/2/4T: 0.483, 0.512, 0.502s: flat/slightly slower, not faster. generated `connections_pre_codeobject.cpp`는 `#pragma omp parallel` 안에 `#pragma omp master` delivery loop를 사용한다. 이 경로에 atomic/critical은 없지만 accumulation은 master 직렬 처리다. queue push는 thread region에 존재한다. 따라서 LIF kernel 하나의 scaling만으로 full consumer scaling을 기대할 수 없다. 4T scaling 불량으로 8T는 미실시. [Brian2 OpenMP caution](https://brian2.readthedocs.io/en/2.9.0/user/computation.html#multi-threading-with-openmp).

| CodeObject | 1T profile s | 2T profile s | 4T profile s |
|---|---:|---:|---:|
| lif_update_codeobject | 0.753 | 0.567 | 0.552 |
| connections_pre_codeobject | 0.483 | 0.512 | 0.502 |
| neurons_spike_thresholder_codeobject | 0.216 | 0.442 | 0.369 |
| shared_noise_reader_codeobject | 0.140 | 0.223 | 0.234 |
| connections_pre_push_spikes | 0.067 | 0.097 | 0.140 |
| clear_incoming_codeobject | 0.058 | 0.118 | 0.096 |
| quantum_boundary_codeobject | 0.029 | 0.071 | 0.068 |
| spikes_codeobject | 0.004 | 0.001 | 0.006 |
| neurons_spike_resetter_codeobject | 0.003 | 0.095 | 0.045 |

## 4. Cheap optimization trials

현재 SpikeMonitor는 `record=False`이며 N개 cumulative count만 저장한다. StateMonitor/PopulationRateMonitor/full spike-time 기록 없음. spikes_codeobject는 <1%, custom quantum_boundary도 작은 항목이었다. 따라서 motor/readout이나 cumulative observation 제거는 하지 않았다. delay audit는 diagnostic-only로 유지했다.

| Variant | One change / measured reason | mean ms (3 repeats) | p99 ms (3 repeats) | Correctness | Keep/reject |
|---|---|---|---|---|---|
| current | unchanged control | 51.350, 47.144, 47.173 | 63.161, 49.925, 51.110 | exact full dynamics/circuit PASS | control retained, not adopted as realtime |
| clear-fused | Top LIF pass에 incoming scratch clear를 융합, 별도 full-N clear pass 제거 | 45.923, 41.049, 56.436 | 51.827, 42.501, 81.529 | exact full dynamics/circuit PASS | REJECT: no stable35ms headroom |
| zero | noise-reader 약8%: 검증된 row-pointer 소비를 consumer-only로 비교 | 57.875, 44.494, 57.148 | 80.957, 46.713, 78.033 | exact full dynamics/circuit PASS | REJECT: no stable35ms headroom |

Clear-fused는 incoming scratch를 다음 start에서 zero하는 대신 현재 LIF 사용 직후 zero한다. 초기 incoming=0, synaptic delivery 이후 LIF만 이를 소비하며 intervening reader 없음. 따라서 v/syn/noise/activity/ref/eligible 및 spike/circuit 출력은 모든 반복에서 full-array exact same. 최종 incoming scratch 값 자체는0으로 달라지지만 다음 step 전에 원래도 clear되는 bookkeeping이며 dynamics/readout state 변화로 숨기지 않는다. 이 변형은 성능이 안정적으로 개선되지 않아 버렸다.

zero-copy는 원래 allocation pointer를 serialization/deallocation 전에 복구했다. 동일 frozen input에서 full neural states, population/LC4/LPLC2/GF/DNp09, circuit EMA/peaks exact PASS. producer를 붙이지 않았으므로 packing 비용은 없지만 단독 p99도 개선되지 않았다. 여러 변경을 섞거나 native RNG/model parameter를 변경하지 않았다. p99 >50ms outlier는 삭제하지 않았다.

## 5. Quantum timeline / histogram diagnosis

각 profiler-OFF persistent20s run에서400 windows, warmup10 제외390 measured; 세 반복. 전체20s 독립 Gaussian tape는 약13.21GB로 current available RAM(~4.4GB)보다 커서 paging 병목을 추가할 위험이 있었다. 따라서 고정 resident2s tape의40-window noise replay를 명시적인 진단 input으로 사용했다. 이것은 Gaussian current equation을 바꾸거나 production noise replay를 채택한 것이 아니며, 독립20s noise regime/최종 realtime 인증이 아니다. known40 input period와 activity autocorrelation을 별도로 표시해 OS periodicity와 혼동하지 않는다.

![Timeline](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-e/timeline.png)

![Histogram](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-e/histogram.png)

| Repeat | mean | p50 | p95 | p99 | max | >50ms /390 | spike/timing r | timing lag40 r | spike lag40 r |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 44.211 | 43.153 | 49.817 | 61.447 | 76.622 | 19/390 (4.87%) | 0.070 | 0.116 | 0.675 |
| 1 | 61.488 | 56.671 | 86.312 | 90.625 | 95.533 | 289/390 (74.10%) | -0.022 | -0.038 | 0.675 |
| 2 | 50.250 | 46.570 | 75.786 | 81.741 | 91.493 | 127/390 (32.56%) | 0.012 | 0.318 | 0.675 |

주 compute band 위에 느린 episode/tail과 큰 repeat-to-repeat shift가 존재한다. 단일 p99로 steady kernel 비용만 설명할 수 없다. 반면 같은 input의 모든 final neural state와 circuit 출력은 정확히 같았다. 단순 spike count correlation은 인과성 증명이 아니며 spike당 fanout 차이도 있어 synaptic delivery 비용을 배제하지 않는다. 재현 가능한 100-window flush/resize/logging event가 입증되지 않아 speculative periodic-event fix는 하지 않았다. boundary count/finite scans와 flush는 per-quantum timer 밖, 전체 Network.run timer 안이다. 현재 자료만으로 scheduler/cache/page-fault 원인을 확정할 수 없다. [e4-diagnosis.json](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-e/e4-diagnosis.json).

## 6. Concurrent producer retest

NOT RUN. E2/E3에서 충분히 개선된 consumer HEADROOM 후보가 생기지 않아 STOP4/Done(NO) 조건으로 E5에 진입하지 않았다. Gate D producer-only 성공을 consumer concurrent PASS로 사용하지 않고, 13–18% contention을 optimized consumer에 외삽하지 않았다. 새 producer count/affinity 탐색, double buffer, generic ring, IPC/Godot/ecology integration 없음. future world/sensory/motor state도 계산하지 않았다.

## 7. Headroom decision

CONSUMER HEADROOM: FAIL. Cheap no-semantics 옵션 이후에도 어떤 반복 안정성 구성도 35ms 목표 또는50ms hard floor를 충족하지 못했다. 이는 테스트한 싼 옵션의 실패이며 CPU 하드웨어나 모든 최적화에 대한 불가능성 정리는 아니다. No new backend / Rust/GPU rewrite / neural equation / dt / weights / pruning / connectivity / delay/noise amplitude changes. 아래100ms도 production architecture로 채택하지 않았다.

## 8. Plan Z — diagnostic only

100MS QUANTUM: NO MATERIAL BENEFIT

실행 조건: consumer1T 세 반복의 median mean이40–50ms, cheap 옵션으로35ms 실패. dt1ms 그대로, 100ms에서100 neural steps를 계산한다. 동일20s frozen replay/strong input/CPU6/HIGH priority, 각 세 반복. 모든 final full dynamics state SHA는 50ms/100ms 각각 exact same. 아래 boundary-inclusive Network.run cost로 비교한다. 시간 간격 확장으로 pure neural compute budget이 공짜로 생긴다는 주장은 하지 않는다.

| Repeat | 50ms network ms/neural-ms | 100ms network ms/neural-ms | Speedup pair | 50ms mean quantum ms | 100ms mean quantum ms |
|---|---:|---:|---:|---:|---:|
| 0 | 0.893 | 0.882 | 1.0133× | 44.211 | 87.660 |
| 1 | 1.231 | 0.883 | 1.3936× | 61.488 | 87.812 |
| 2 | 1.023 | 0.956 | 1.0703× | 50.250 | 95.279 |

Median pair factor 1.0703×. 판정 기준은 측정 전 median ratio≥1.10 및 모든 pair≥1.05로 정했다. sequential run-to-run variation이 커서 control period 자체의 인과적 이득으로 단정하지 않는다. producer/synchronization/IPC/world overhead는 포함되지 않는다. [plan-z.json](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-e/plan-z.json).

| 100ms repeat | p50 ms | p95 ms | p99 ms | max ms | >100ms/195 |
|---|---:|---:|---:|---:|---:|
| 0 | 85.277 | 100.113 | 106.454 | 136.022 | 10/195 |
| 1 | 85.301 | 97.803 | 100.551 | 104.407 | 3/195 |
| 2 | 94.117 | 112.048 | 131.064 | 163.480 | 39/195 |

100ms p99도 세 반복 모두100ms floor를 초과했다. mean neural/wall이1× 이상인 것만으로 deadline/jitter를 해결했다고 하지 않는다.

## 9. Integrity / resources

모든 cheap variant의 population/LC4/LPLC2/GF/DNp09 counts, circuit activity, final v/syn/ref/activity/noise/eligible는 same-input1T control과 exact same. OpenMP thread variants도 현재 same-input 검사에서 circuit/count 및 selected state guardrail PASS; 각 correctness JSON에 exact 여부와 max difference가 있다. OpenMP 검증은 existing engineering equivalence이며 3-seed stochastic natural variability 인증이 아니다. all effective i/j/w 원본 CSR 일치, finite/no-runaway PASS. Original previous-spike scheduling 및 dt1ms 유지.

기존 Core/Body/Ecology/Gate A/B/C/D 592 files SHA 동일, changed0. regression 13/13 PASS. Gate E 전용 source/report/work만 추가했다. Baseline NumPy2.4.6 유지; isolated NumPy1.26.4/Brian2 2.9.0 실험. [preservation-after.json](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-e/preservation-after.json).

추가 Gate D generated source/executable 320 SHA 검증도 changed0. 초기 make dry-run 감사는 GNU make의 included dependency 재작성 동작 때문에 work/의 make.deps 캐시 하나를 비웠다. compiler PATH 오류로 compile은 성공하지 않았으며, 정상 동일1T dependency graph의 byte-copy로 캐시를 복구했다. original cache before-SHA는 없으므로 그 캐시의 원래 byte identity를 주장하지 않는다. verified neural source/executable/result/data는 모두 동일하고, 수정한 감사는 기존 makefile만 읽는다. [gate-d-generated-integrity.json](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-e/gate-d-generated-integrity.json).

C++ sampled peak RSS 1661554688 bytes (1.547GiB); controller OS peak RSS 474673152 bytes (0.442GiB). 별도 process들의 peak를 동시에 측정한 전체 tree peak로 주장하지 않는다. Compiler peak는 미측정.

| Long diagnostic / repeat | init s | network s | output s | 20/network (brain-only) |
|---|---:|---:|---:|---:|
| q50/0 | 1.115 | 17.867 | 0.161 | 1.1194× |
| q50/1 | 0.997 | 24.618 | 0.200 | 0.8124× |
| q50/2 | 1.271 | 20.454 | 0.139 | 0.9778× |
| q100/0 | 1.061 | 17.633 | 0.193 | 1.1343× |
| q100/1 | 0.996 | 17.665 | 0.194 | 1.1322× |
| q100/2 | 1.056 | 19.111 | 0.209 | 1.0465× |

Cold/preload/init, model setup/codegen/compile, output serialize는 steady quantum compute와 분리했다. 전 run parameter/compile flags/PID/mask/priority/power metadata는 raw JSON/build proof에 보존했다. source-sha256.json 및 evidence-sha256.json에 새 Gate E artifact SHA가 있다. 기존 Body/Ecology composite remainder와 이 brain-only factor를 합쳐 end-to-end 성능을 추정하지 않는다.

종료: 실용적35ms headroom NO. production 변경 없이 결과를 Human Decision에 전달한다. 본편 복귀,100ms control frequency 채택,추가 최적화 중 어떤 것도 이번 Gate E에서 임의로 실행하지 않았다.
