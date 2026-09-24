RNG RESCUE: FAIL — RNG GENERATION TOO SLOW

실제 target: AMD Ryzen 3 4100, 4 physical cores / 8 logical threads, RAM 15.79GiB, Windows, TDM-GCC9.2, Brian2 2.9. CPU only, GPU 없음. 8T는 SMT 사용이며 oversubscription으로 취급하지 않았다.

## 1. C0 frozen evidence audit

PASS. 실제 Network.run 2s, 165122 neurons, 6327564 effective signed synapses. dt1ms, threshold1/reset0/refractory2ms, 기존 sign/weights/float32 모델. Baseline은 NumPy2.4 seed20260913의 원래 heterogeneity draw와 동일하다.
0-.5s warmup / .5-1s baseline / 1-1.5s LC4+LPLC2 current3 / 1.5-2s recovery. Noise tape는 [2000,165122] unscaled little-endian float32 C-order; 매 ms 한 N-row, amplitude0.1을 external current 이전에 적용하고 refractory 중에도 draw를 소비한다.
기존 frozen compute 1.899932s (1.0527×)는 동일한 full network의 consumption evidence다. Noise pre-generation은 빠져 있으므로 sustained realtime 인증이 아니다. Runtime weight/baseline/input/tape SHA와 full graph 확인은 c0-audit.json에 있다.

## 2. C1 isolated Gaussian generation

실제 Gate B generated objects.h의 RandomGenerator class를 수정 없이 추출했다. std::mt19937 + stored-pair polar Box-Muller의 double log/sqrt 후 float32 cast. 네트워크 계산 없이 timestep당165122 sample, 50ms warmup 뒤 실제1000ms를 두 번 측정했다. Compile/startup/checksum은 throughput timer 밖이다.
1T는 1 neural초분 생성에 5.420759 / 5.391695 wall초, 평균 0.1850×. 생성기 자체가 realtime budget을 초과한다. Full noise-on 비용 전체가 RNG만이라고 추정하지는 않는다.

## 3. C2 native OpenMP scaling / full timing

| Method | Threads | RNG Msamples/s / neural-wall / scaling | Full mean / p50 / p95 / p99 / max ms | Deadline miss count / rate | Longest misses |
|---|---:|---:|---:|---:|---:|
| Native Brian2 | 1 | 30.543 / 0.1850× / 1.000× | 332.264 / 331.202 / 337.857 / 354.540 / 398.948 | 400 / 100.000% | 400 |
| Native Brian2 | 2 | 59.592 / 0.3609× / 1.951× | 261.743 / 259.268 / 276.702 / 299.512 / 355.474 | 400 / 100.000% | 400 |
| Native Brian2 | 4 | 112.329 / 0.6803× / 3.678× | 159.506 / 154.290 / 186.685 / 193.692 / 289.761 | 400 / 100.000% | 400 |
| Native Brian2 | 8 | 161.392 / 0.9774× / 5.284× | 123.881 / 119.323 / 150.725 / 176.163 / 293.693 | 400 / 100.000% | 400 |

각 thread 설정에서 실제 20 neural초 / 400개 consecutive quantum. 개별 50ms timer는 C++ Network.run 내부에서 측정하며 경계 input/stat/log maintenance를 제외한다. 전체 Network.run은 maintenance 포함 값으로 JSON에 별도 기록했다. Python 시작/build를 quantum에 섞지 않았다.
실제 per-thread RNG vector와 omp_get_thread_num 선택, parallel for를 generated source에서 확인했다. RNG class 내부 locking/critical은 없다. 수치 scaling은 실제 두 trial 결과이며, C2에는 producer가 동시 실행되지 않았다.
C2 candidate: NONE. 모든 수치·개별 quantum·source proof는 raw txt/JSON 및 generated-proof/에 있다.

## 4. C3 pre-generation feasibility

RUN — C2 native-noise p99 failed for all configurations

| PCG64 float32 block, neural ms | Bytes | Mean / p50 / p95 / max generation wall ms | Neural/wall |
|---|---:|---:|---:|---:|
| 50 | 33024400 | 59.679 / 59.712 / 59.834 / 59.855 | 0.8378× |
| 100 | 66048800 | 119.899 / 119.597 / 120.953 / 121.228 | 0.8340× |
| 500 | 330244000 | 603.150 / 600.534 / 614.116 / 616.637 | 0.8290× |
| 1000 | 660488000 | 1211.032 / 1212.745 / 1229.783 / 1232.537 | 0.8257× |

NumPy2.4 PCG64 float32 Gaussian, baseline draw 뒤의 state. Warmup과 측정은 분리했다.
Consumption은 동일 network/동일 shared noise 입력의 새 실제 2s / 40 quantum 실행. Mean/p50/p95/p99/max 38.173/38.190/43.831/45.287/45.331ms; miss 0.000%. Scope/정확한 input·memory 정책은 c3-consumption.json.
C3 shared-input correctness PASS: baseline/stimulus/recovery population spikes 45181/65209/45148이 SciPy와 동일. LC4 stimulus7490 / LPLC2 stimulus11118 / GF8→25→8 / DNp09 0이며 모든 구간의 group count와 active fraction도 동일하다. c3-correctness.json에 33개 검사와 나란한 metric을 저장했다. 40-window 진단을 sustained realtime 인증으로 주장하지 않는다.
Generation realtime feasible=False. 50ms generation 평균 59.679ms와 consumption 평균 38.173ms를 독립 측정했다. 이론적인 max(producer,consumer)는 가능성 판단일 뿐, concurrent pipeline 실측으로 과장하지 않는다.

## 5. C4 producer/consumer

NOT RUN — C3 generation lacks sustained realtime throughput; buffer cannot rescue it
Producer starvation: NOT MEASURED (C4 not run); buffer depth: 0; CPU allocation: C3 generator1T와 consumer1T를 각각 독립 측정, concurrent producer 없음. Starvation을 0회라고 주장하지 않는다.

## 6. Chosen implementation

NONE — keep verified baseline; no deployment/backend migration

## 7. Multi-seed equivalence

NOT RUN — no realtime candidate survived; validation requires a final candidate

## 8. Resources / build integrity

Peak executable RSS 1.5330GiB; preparation/compiler/executable process-tree sampled peak 2.0667GiB. 각각의 범위는 resources에 명시했다.

| Run | Python load / model / codegen / compile-link s | C++ init / Network.run / output s | Launcher + unattributed s |
|---|---:|---:|---:|
| c2-native-1t | 0.514 / 0.412 / 0.671 / 6.004 | 0.461 / 133.499 / 0.184 | 0.261 |
| c2-native-2t | 0.490 / 0.331 / 0.496 / 5.574 | 0.387 / 104.814 / 0.152 | 0.297 |
| c2-native-4t | 0.509 / 0.342 / 0.480 / 5.836 | 0.400 / 64.066 / 0.208 | 0.338 |
| c2-native-8t | 0.501 / 0.320 / 0.487 / 5.390 | 0.330 / 49.892 / 0.192 | 0.366 |
| c3-consumption | 0.491 / 0.328 / 0.528 / 5.655 | 1.175 / 1.547 / 0.178 | 0.386 |

## 9. Baseline preservation

275 existing artifact SHA checked; changed files=[]; existing tests 13 PASS. Core/body/ecology/Gate A/Gate B unchanged. 새 source/report는 Gate C 전용 경로에만 저장했다.

## 10. Remaining debt / stop

Native MT seed integer는 PCG64 random stream identity가 아니다. Shared noise 조건에서만 exact stream equivalence를 주장한다. 기존 body/ecology remainder 약8.5%/19.4%는 느린 SciPy 아래의 composite startup/socket/log/ACK/wait 등을 포함하며 이 라운드에서 최적화하거나 외삽하지 않았다.
다음 별도 검토 후보: SeedSequence.spawn으로 분리한 소수 PCG64 float32 worker streams의 block-generation 병렬화. NumPy는 독립 Generator stream 생성 기능을 제공하지만, 이 PC에서의 throughput·brain과의 CPU 경쟁·3-seed 동등성은 미검증이다. 단일 reference PCG64 stream과 exact identity도 달라진다. 이번 C3 STOP에 따라 구현하지 않았다. [NumPy parallel RNG documentation](https://numpy.org/doc/2.4/reference/random/parallel.html)
실패 판정은 측정한 native OpenMP와 단일-worker PCG64 전략에 한정한다. 모든 RNG 전략이나 이 hardware에서의 realtime이 원천 불가능하다는 증명은 아니다. 추가 buffer/새 backend/Godot migration/행동 변경 없이 종료한다.

[Brian2 standalone/OpenMP preferences and warning](https://brian2.readthedocs.io/en/2.9.0/user/computation.html) — 실제 generated source와 실측 scaling을 source of truth로 사용했다.
