RNG RESCUE: FAIL — CPU CONTENTION

## 최종 성능 요약

| 항목 | 실제 결과 |
|---|---|
| Best steady-state pipeline p99 | NOT MEASURED — D2 진입 불가 |
| 최선의 반복 안정성 D1 side p99 | 57.726 ms (`d1-b1-p2-rotated`) |
| Worst tested workload p99 | 163.480 ms — D1 side, 2T zero-copy baseline |
| Worst strong-workload p99 | 73.887 ms — D1 side |
| Sustained neural/wall | NOT CERTIFIED — 60초 pipeline 미실시 |
| Headroom | -7.726 ms — D1 side 기준, pipeline margin 아님 |
| Equivalent realtime factor | 0.8662× — 50/p99 D1 side 환산, sustained factor 아님 |
| Producer starvation | NOT MEASURED — 0으로 간주하지 않음 |
| Pipeline deadline miss rate | NOT MEASURED |

질문에 대한 답: 현재 Ryzen 3 4100에서 noise 공급 경로만으로 실용적인 realtime headroom을 확보하지 못했다. producer 단독 처리량은 해결했지만, full MaleCNS consumer는 producer 없이도 35ms 기준에 미달하며 동시 실행에서 더 느려졌다. FAIL 분류는 이번에 시험한 concurrent 구성에 대한 판정이다. CPU의 모든 구성이나 향후 최적화가 불가능하다는 결론은 아니다.

50ms hard floor / 35ms adoption target / 30ms ideal stop. 어느 유효 D1 구성도 두 workload의 세 반복 모두에서 양쪽 p99 ≤50ms를 유지하지 못했다. 따라서 D2 금지 조건을 적용했다. 기존 backend, core, body, ecology는 교체하거나 배포하지 않았다.

## D-1 — native float32 audit

`standard_normal(dtype=np.float32, out=preallocated_contiguous_float32)` 직접 생성. 50×165122 = 8256100 samples, 33024400 bytes/block. float64→float32 cast 없음, fill 내부 output allocation 없음. baseline heterogeneity draw 이후 단일 PCG64 stream; buffer 재사용. Gate C 경로도 이미 native float32였다.

## D0 — 최소 persistent worker 수

모든 행: warmup 10 blocks 제외, 연속 200 measured blocks; dispatch/completion synchronization 포함.

| 경로 | mean ms | p50 | p95 | p99 | max | blocks/s | neural/wall | speedup vs D0 1w |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| d-minus1 | 60.244 | 59.889 | 61.277 | 65.955 | 87.270 | 16.599 | 0.830 | N/A |
| d0-1w | 59.584 | 59.526 | 60.071 | 60.696 | 61.347 | 16.783 | 0.839 | 1.0000× |
| d0-2w | 30.205 | 30.133 | 30.587 | 31.129 | 32.432 | 33.107 | 1.655 | 1.9726× |

D-1 >35ms로 D0 진행. D0 2w p99 ≤35ms에서 STOP: 3/4 workers 미실시. persistent worker마다 root SeedSequence(20260913).spawn(2)의 child stream을 유지했다. worker 0 → child [0] → runtime [0,82561), worker 1 → child [1] → [82561,165122). 각 worker의 [50,82561] contiguous float32를 worker-major preallocated storage에 고정 배치한다. 고정 worker count에서 scheduling에 따른 neuron assignment 변경이 없다. 단일 reference PCG64와 같은 random sequence라는 주장은 하지 않는다. [NumPy multithreaded generation](https://numpy.org/doc/2.4/reference/random/multithreading.html), [independent child streams](https://numpy.org/doc/2.4/reference/random/parallel.html).

## D1 — 실제 concurrent feasibility

별도 full Brian2 C++ process와 Python persistent producer threads를 실제 동시 실행했다. consumer는 기존 shared 비주기 PCG64 2초 tape를 시작 전에 읽고, producer 출력은 폐기한다. 이것은 throughput/contention 검사이며 producer가 brain에 noise를 공급하는 pipeline은 아니다. consumer 2 neural seconds / 40×50ms 중 처음 10 windows(0.5 neural s)를 제외하여 각 반복 30 windows; baseline/strong LC4+LPLC2(기존 amplitude 3) 각 세 반복. producer는 10-block warmup 후 C++ compute interval 안에 완전히 포함된 generation intervals만 집계했다. QPC/perf_counter의 같은 system clock으로 실제 overlap을 확인했다. startup·output serialization은 quantum compute 밖이다.

| 구성 | Brain logical CPUs | Producer logical CPUs | baseline worst side p99 | strong worst side p99 | 판정 |
|---|---|---|---:|---:|---|
| d1-b1-p2 | [0] | [[2], [4]] | 44.335 | 73.887 | FAIL |
| d1-b2-p2-clean | [0, 2] | [[4], [6]] | 55.234 | 67.402 | FAIL |
| d1-b1-p2-rotated | [6] | [[2], [4]] | 56.927 | 57.726 | FAIL |
| d1-zero-b1-p2 | [6] | [[2], [4]] | 58.883 | 59.559 | FAIL |
| d1-zero-b2-p2 | [0, 2] | [[4], [6]] | 163.480 | 63.922 | FAIL |

초기 탐색 `d1-b2-p2` 전체는 controller 시작 당시 build 완료를 보장하지 못해 compiler contention 가능성이 있어 제외했다. raw evidence는 보존했고 동일 allocation을 `d1-b2-p2-clean`으로 재실시했다. 특정 느린 반복만 제외하지 않았다. [d1-excluded.json](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-d/d1-excluded.json).

### 실제 affinity 증거

Win32 topology 조회는 D1 jitter 확인 후 수행했다: physical-core logical pairs [0,1], [2,3], [4,5], [6,7]. 단순 process affinity만으로 worker placement를 주장하지 않고 각 worker 안에서 SetThreadAffinityMask 후 GetThreadGroupAffinity로 실제 mask를 기록했다. [Windows thread affinity API](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadaffinitymask).

예: `d1-b1-p2-rotated` strong trial 1의 종료된 brain PID 20104, actual process mask 64 (CPU [6]).

| Worker | 실제 OS thread ID | actual mask | logical CPU | child | runtime range |
|---|---:|---:|---|---|---|
| 0 | 18988 | 4 | [2] | [0] | [0,82561) |
| 1 | 16220 | 16 | [4] | [1] | [82561,165122) |

[d1-b1-p2-rotated-looming-1.json](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-d/d1-b1-p2-rotated-looming-1.json) 및 각 trial JSON에 모든 PID, mask, stream/layout metadata가 있다.

### matched producer OFF 비교

동일 best 1T executable, CPU6 affinity, scenario, input, warmup에서 ON/OFF 각각 세 반복. 시간순 반복 비교이며 instruction-level profiling이나 외부 시스템의 완전한 통제는 아니다.

| Workload | ON mean ms | OFF mean ms | ON/OFF mean slowdown | ON repeat p99 ms | OFF repeat p99 ms |
|---|---:|---:|---:|---|---|
| baseline | 41.144 | 34.948 | 17.73% | 50.999, 56.927, 40.580 | 39.695, 49.591, 37.189 |
| looming | 47.247 | 41.869 | 12.85% | 52.608, 57.726, 49.708 | 46.704, 42.905, 45.168 |

producer-only matched 200-block 세 반복 p99: 31.064, 32.145, 30.833 ms. 2-worker producer 자체는 반복해서 HEADROOM PASS지만 consumer OFF도 strong p99 42.905–46.704ms로 이미 headroom 부족이다. 실패를 Gaussian 생산 비용 하나로만 설명할 수 없다. [d1-contention-comparison.json](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-d/d1-contention-comparison.json).

### row-pointer zero-copy 공급 변형

기존 preloaded noise row를 직접 참조하여 timestep마다 N개 memcpy를 제거하는 noise-supply-only 변형도 시험했다. 원래 owned noise_sample pointer를 serialization/deallocation 전에 복구했다. 동일 입력 1T copy/zero 비교의 모든 quantum observation(시간 제외), final v/syn/refractory/noise_sample 10 checks가 exact PASS. 단, worker-major 출력을 C-order [50,N]으로 packing하는 추가 copy 비용을 producer timer에 포함했고, packing coordinator affinity도 기록했다. 이 변형도 두 CPU allocation에서 FAIL이었다. exact shared-input proof를 parallel child-stream network equivalence로 확대하지 않는다. [zero-copy-correctness.json](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-d/zero-copy-correctness.json).

## D2 / D3 / D4 — 조건부 미실시

- D2: NOT RUN. 모든 시험 allocation이 적어도 한 workload/repeat에서 side p99 >50ms. concurrent feasibility 미확인으로 A/B double buffer 구현 금지.
- D3: NOT RUN. D2 pipeline 없음. warmup 후 60s/1200 windows, cadence p50/p95/p99/max, wait/swap, starvation, sustained neural/wall 인증값 없음.
- D4: NOT RUN. concurrent HEADROOM 후보 없음. 3 root-seed reference/candidate baseline/stimulus/recovery population/active fraction/LC4/LPLC2/GF/DNp09 natural variability 인증 없음. 미실시를 PASS로 간주하지 않는다.

future world/sensory/motor state를 계산하지 않았고 world authority나 lockstep을 변경하지 않았다. 본편 4번째 탄환, Console UI, world resize, Godot/IPC/ecology migration, GPU/backend/weight/dt/noise amplitude 변경 없음.

## Integrity / resource / startup

기존 Brain Core/Body/Ecology/Gate A/B/C 및 runtime data 369 files SHA before/after 동일, changed files 0. regression 13/13 PASS. [preservation-after.json](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/realtime/gate-d/preservation-after.json).

실제 graph source/target/weight는 모든 유효 D1 trial에서 원본 CSR와 비교해 일치했고 state는 finite였다. 165122 neurons / 6327564 effective signed synapses; anatomical 6474533. float32, dt1ms, noise_std0.1, recurrent gain2 등 기존 parameter 유지. weights SHA `3fb657efc33922829dea821d3fd08ac516a7db2fc471182a73b841844915aaf3`; shared noise SHA `17b3194eac1301c7e15976f0ceedba26f435503230af0f263565181b4b6d38d0`.

Hardware: Ryzen 3 4100 4C/8T SMT, 15.79 GiB RAM, Windows, CPU only. Baseline Python3.11.9/NumPy2.4.6 미변경. Brian2 2.9.0 실험은 기존 isolated NumPy1.26.4를 entry.py에서 사용. TDM-GCC9.2, O3/native C++17, 2T만 OpenMP; fast-math 없음.

유효 D1 C++ process sampled peak RSS: 1649324032 bytes (1.536 GiB). matched measurement Python process OS peak RSS: 430723072 bytes (0.401 GiB). 둘을 동시에 측정한 전체 process-tree peak라고 주장하지 않는다. compiler tree peak 미측정. offline preloaded 2s tape 1320976000 bytes; producer buffer 33024400 bytes, packed variant 추가 33024400 bytes. 이 대용량 tape는 D1 검사 전용이며 최종 streaming buffer 구현이 아니다.

| Build | Model setup s | Codegen s | Compile s |
|---|---:|---:|---:|
| d1-build-1t-baseline-zero | 0.292 | 4.263 | 8.243 |
| d1-build-1t-baseline | 0.270 | 0.397 | 4.784 |
| d1-build-1t-looming-zero | 0.273 | 4.956 | 7.501 |
| d1-build-1t-looming | 0.269 | 0.406 | 4.745 |
| d1-build-2t-baseline-zero | 1.165 | 21.957 | 7.737 |
| d1-build-2t-baseline | 0.272 | 1.002 | 7.567 |
| d1-build-2t-looming-zero | 0.270 | 4.820 | 7.949 |
| d1-build-2t-looming | 0.273 | 0.431 | 7.589 |

| Best allocation trial | Init s | Actual 2s network compute s | Output s | 2/network wall (brain only) |
|---|---:|---:|---:|---:|
| baseline-0 | 1.057 | 1.759 | 0.146 | 1.1373× |
| baseline-1 | 1.018 | 1.755 | 0.151 | 1.1396× |
| baseline-2 | 0.986 | 1.584 | 0.139 | 1.2626× |
| looming-0 | 0.996 | 1.923 | 0.139 | 1.0403× |
| looming-1 | 0.977 | 1.962 | 0.139 | 1.0192× |
| looming-2 | 0.982 | 1.899 | 0.676 | 1.0533× |

Init includes preloading; controller GO wait is outside compute. OS disk/cache cold-start은 별도 인증하지 않았다. 2s brain-only factor는 producer 공급, sync/swap, startup, Godot, ecology를 포함하는 end-to-end factor가 아니다. 기존 Body 8.5% / Ecology 19.4% composite remainder는 startup/socket/logging/ACK wait/shutdown을 포함하므로 이 fast-brain 수치에 steady-state overhead로 투영하지 않는다.

## D1 per-repeat detailed timing evidence

아래 mean/p50/p95/p99/max는 ms. brain miss는 warmup 제외 30 windows의 >50ms 횟수이며 pipeline miss가 아니다. 각 producer의 sample count는 actual overlap의 strict-contained block 수이다.

| Configuration / workload / repeat | Side | Samples | mean | p50 | p95 | p99 | max | Brain misses |
|---|---|---:|---:|---:|---:|---:|---:|---|
| d1-b1-p2/baseline/0 | brain | 30 | 38.717 | 38.339 | 41.692 | 43.116 | 43.348 | 0/30 (0.0%) |
| d1-b1-p2/baseline/0 | producer | 49 | 31.070 | 30.991 | 31.540 | 31.899 | 31.987 | N/A |
| d1-b1-p2/baseline/1 | brain | 30 | 37.927 | 37.761 | 39.309 | 40.095 | 40.364 | 0/30 (0.0%) |
| d1-b1-p2/baseline/1 | producer | 48 | 31.115 | 30.997 | 31.566 | 31.787 | 31.789 | N/A |
| d1-b1-p2/baseline/2 | brain | 30 | 38.004 | 37.440 | 40.134 | 44.335 | 45.902 | 0/30 (0.0%) |
| d1-b1-p2/baseline/2 | producer | 49 | 31.345 | 31.029 | 34.236 | 34.865 | 34.874 | N/A |
| d1-b1-p2/looming/0 | brain | 30 | 47.489 | 46.935 | 52.788 | 54.174 | 54.444 | 5/30 (16.7%) |
| d1-b1-p2/looming/0 | producer | 63 | 31.592 | 31.086 | 33.149 | 34.404 | 36.058 | N/A |
| d1-b1-p2/looming/1 | brain | 30 | 45.883 | 45.582 | 47.506 | 47.613 | 47.630 | 0/30 (0.0%) |
| d1-b1-p2/looming/1 | producer | 60 | 31.237 | 31.040 | 32.436 | 33.600 | 34.661 | N/A |
| d1-b1-p2/looming/2 | brain | 30 | 54.649 | 52.054 | 69.801 | 73.887 | 74.903 | 18/30 (60.0%) |
| d1-b1-p2/looming/2 | producer | 66 | 32.074 | 31.212 | 34.748 | 44.721 | 48.189 | N/A |
| d1-b2-p2-clean/baseline/0 | brain | 30 | 44.458 | 42.982 | 53.406 | 55.234 | 55.782 | 4/30 (13.3%) |
| d1-b2-p2-clean/baseline/0 | producer | 58 | 31.249 | 31.130 | 32.610 | 32.816 | 32.911 | N/A |
| d1-b2-p2-clean/baseline/1 | brain | 30 | 43.661 | 43.062 | 48.783 | 51.188 | 51.334 | 2/30 (6.7%) |
| d1-b2-p2-clean/baseline/1 | producer | 67 | 31.350 | 31.081 | 32.355 | 37.133 | 40.189 | N/A |
| d1-b2-p2-clean/baseline/2 | brain | 30 | 43.626 | 42.882 | 47.936 | 50.294 | 51.230 | 1/30 (3.3%) |
| d1-b2-p2-clean/baseline/2 | producer | 57 | 31.307 | 31.141 | 32.202 | 32.597 | 32.887 | N/A |
| d1-b2-p2-clean/looming/0 | brain | 30 | 50.464 | 49.878 | 53.888 | 54.250 | 54.355 | 14/30 (46.7%) |
| d1-b2-p2-clean/looming/0 | producer | 68 | 31.216 | 31.020 | 32.191 | 32.673 | 32.872 | N/A |
| d1-b2-p2-clean/looming/1 | brain | 30 | 50.521 | 50.075 | 53.032 | 55.391 | 56.319 | 15/30 (50.0%) |
| d1-b2-p2-clean/looming/1 | producer | 67 | 31.149 | 31.077 | 31.727 | 31.968 | 32.000 | N/A |
| d1-b2-p2-clean/looming/2 | brain | 30 | 53.974 | 51.193 | 63.587 | 67.402 | 68.626 | 23/30 (76.7%) |
| d1-b2-p2-clean/looming/2 | producer | 68 | 31.744 | 31.449 | 33.550 | 34.221 | 34.268 | N/A |
| d1-b1-p2-rotated/baseline/0 | brain | 30 | 41.820 | 41.258 | 50.251 | 50.999 | 51.196 | 2/30 (6.7%) |
| d1-b1-p2-rotated/baseline/0 | producer | 53 | 31.955 | 31.339 | 34.292 | 34.924 | 35.101 | N/A |
| d1-b1-p2-rotated/baseline/1 | brain | 30 | 43.892 | 41.236 | 56.751 | 56.927 | 56.950 | 6/30 (20.0%) |
| d1-b1-p2-rotated/baseline/1 | producer | 53 | 32.027 | 31.485 | 34.335 | 36.396 | 37.493 | N/A |
| d1-b1-p2-rotated/baseline/2 | brain | 30 | 37.721 | 37.418 | 39.623 | 40.580 | 40.897 | 0/30 (0.0%) |
| d1-b1-p2-rotated/baseline/2 | producer | 49 | 31.178 | 31.014 | 31.825 | 32.320 | 32.646 | N/A |
| d1-b1-p2-rotated/looming/0 | brain | 30 | 47.359 | 46.538 | 51.532 | 52.608 | 52.795 | 3/30 (10.0%) |
| d1-b1-p2-rotated/looming/0 | producer | 60 | 31.073 | 30.977 | 31.602 | 31.733 | 31.735 | N/A |
| d1-b1-p2-rotated/looming/1 | brain | 30 | 48.190 | 47.008 | 54.480 | 57.726 | 58.243 | 6/30 (20.0%) |
| d1-b1-p2-rotated/looming/1 | producer | 61 | 31.508 | 31.250 | 33.467 | 34.037 | 34.387 | N/A |
| d1-b1-p2-rotated/looming/2 | brain | 30 | 46.192 | 45.816 | 48.732 | 49.708 | 49.913 | 0/30 (0.0%) |
| d1-b1-p2-rotated/looming/2 | producer | 59 | 30.906 | 30.803 | 31.363 | 31.979 | 32.058 | N/A |
| d1-zero-b1-p2/baseline/0 | brain | 30 | 39.538 | 39.288 | 40.552 | 42.165 | 42.797 | 0/30 (0.0%) |
| d1-zero-b1-p2/baseline/0 | producer | 41 | 39.179 | 38.755 | 41.099 | 44.282 | 44.630 | N/A |
| d1-zero-b1-p2/baseline/1 | brain | 30 | 39.319 | 39.092 | 41.841 | 42.861 | 43.096 | 0/30 (0.0%) |
| d1-zero-b1-p2/baseline/1 | producer | 40 | 39.348 | 38.956 | 41.511 | 42.638 | 43.208 | N/A |
| d1-zero-b1-p2/baseline/2 | brain | 30 | 39.942 | 39.312 | 44.073 | 47.967 | 49.485 | 0/30 (0.0%) |
| d1-zero-b1-p2/baseline/2 | producer | 40 | 39.883 | 38.846 | 40.666 | 58.883 | 69.460 | N/A |
| d1-zero-b1-p2/looming/0 | brain | 30 | 48.105 | 47.400 | 51.413 | 59.559 | 62.647 | 4/30 (13.3%) |
| d1-zero-b1-p2/looming/0 | producer | 50 | 38.424 | 38.179 | 39.483 | 40.088 | 40.459 | N/A |
| d1-zero-b1-p2/looming/1 | brain | 30 | 48.415 | 47.654 | 53.123 | 55.226 | 55.582 | 6/30 (20.0%) |
| d1-zero-b1-p2/looming/1 | producer | 50 | 38.649 | 38.392 | 39.945 | 41.172 | 42.195 | N/A |
| d1-zero-b1-p2/looming/2 | brain | 30 | 48.257 | 46.825 | 53.081 | 57.043 | 58.512 | 6/30 (20.0%) |
| d1-zero-b1-p2/looming/2 | producer | 50 | 38.670 | 38.334 | 40.633 | 41.356 | 41.433 | N/A |
| d1-zero-b2-p2/baseline/0 | brain | 30 | 47.061 | 44.914 | 54.686 | 58.069 | 59.079 | 9/30 (30.0%) |
| d1-zero-b2-p2/baseline/0 | producer | 47 | 40.449 | 39.915 | 43.127 | 48.024 | 52.029 | N/A |
| d1-zero-b2-p2/baseline/1 | brain | 30 | 59.018 | 54.724 | 69.211 | 163.480 | 201.376 | 18/30 (60.0%) |
| d1-zero-b2-p2/baseline/1 | producer | 53 | 42.484 | 41.255 | 44.554 | 70.796 | 72.312 | N/A |
| d1-zero-b2-p2/baseline/2 | brain | 30 | 47.211 | 44.686 | 53.841 | 54.364 | 54.520 | 10/30 (33.3%) |
| d1-zero-b2-p2/baseline/2 | producer | 47 | 40.167 | 39.963 | 41.057 | 41.372 | 41.515 | N/A |
| d1-zero-b2-p2/looming/0 | brain | 30 | 53.952 | 52.681 | 63.758 | 63.922 | 63.931 | 29/30 (96.7%) |
| d1-zero-b2-p2/looming/0 | producer | 55 | 39.492 | 39.434 | 40.672 | 41.275 | 41.436 | N/A |
| d1-zero-b2-p2/looming/1 | brain | 30 | 54.428 | 52.502 | 63.116 | 63.560 | 63.701 | 30/30 (100.0%) |
| d1-zero-b2-p2/looming/1 | producer | 54 | 40.220 | 39.898 | 41.766 | 52.057 | 63.481 | N/A |
| d1-zero-b2-p2/looming/2 | brain | 30 | 53.575 | 52.464 | 60.775 | 61.637 | 61.864 | 30/30 (100.0%) |
| d1-zero-b2-p2/looming/2 | producer | 54 | 39.715 | 39.527 | 41.084 | 41.362 | 41.394 | N/A |

## 재현 및 artifact

Gate D sources are experimental only; no adoption or ecology wiring. source-sha256.json hashes all Gate D Python/README; evidence-sha256.json hashes reports/generated proof except its own manifest. Build JSONs separately include generated C++ and executable SHA. preservation-before.json contains the frozen 369-file baseline hashes. Run commands and safe ordering are in the Gate D source README.
