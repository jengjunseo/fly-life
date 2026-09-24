BRIAN2 GATE B: PASS — NOT YET COMPUTE REALTIME

실제 target: Ryzen 3 4100, 4C/8T, 16GB, Windows, CPU 1 thread, GPU compute 없음.

## B0 — Noise-on equivalence

Noise amplitude 0.1, dt 1ms, 동일한 NumPy2.4 seeded baseline drive. 매 step 모든 뉴런에서 Gaussian standard normal을 float32 cast/scale 후 syn/baseline drive에 더하고 외부 전류를 그 뒤에 더한다. xi diffusion으로 바꾸지 않았다.
B0 공유 입력: baseline heterogeneity draw 뒤의 정확한 PCG64 float32 noise sequence를 2초 tape로 export. [step,runtime_index] 규약과 SHA/통계는 noise-tape.json. Native noise 실행은 실제 generated objects.h의 std::mt19937 + polar Box-Muller, 동일 seed 값이지만 PCG64 stream identity는 주장하지 않는다.

| 구간 | Population Hz Ref / native / shared | Active fraction Ref / native / shared | GF Hz Ref / native / shared |
|---|---:|---:|---:|
| baseline | 0.547244 / 0.547680 / 0.547244 | 0.044095 / 0.044058 / 0.044095 | 8.000 / 8.000 / 8.000 |
| stimulus | 0.789828 / 0.789925 / 0.789828 | 0.046880 / 0.046868 / 0.046880 | 25.000 / 25.000 / 25.000 |
| recovery | 0.546844 / 0.545899 / 0.546844 | 0.044046 / 0.044058 / 0.044046 | 8.000 / 8.000 / 8.000 |

| 구간 | 그룹 | Spike count Ref / native / shared | Mean Hz Ref / native / shared | Peak mean EMA Hz Ref / native / shared |
|---|---|---:|---:|---:|
| baseline | LC4 | 50 / 50 / 50 | 0.7937 / 0.7937 / 0.7937 | 1.0657 / 1.0885 / 1.0657 |
| baseline | LPLC2 | 72 / 69 / 72 | 0.7784 / 0.7459 / 0.7784 | 1.0495 / 1.1149 / 1.0495 |
| baseline | GF | 8 / 8 / 8 | 8.0000 / 8.0000 / 8.0000 | 15.2234 / 14.8675 / 15.2234 |
| baseline | DNp09 | 0 / 0 / 0 | 0.0000 / 0.0000 / 0.0000 | 0.0000 / 0.0000 / 0.0000 |
| stimulus | LC4 | 7490 / 7488 / 7490 | 118.8889 / 118.8571 / 118.8889 | 121.9618 / 121.7649 / 121.9618 |
| stimulus | LPLC2 | 11118 / 11121 / 11118 | 120.1946 / 120.2270 / 120.1946 | 123.4461 / 123.4892 / 123.4461 |
| stimulus | GF | 25 / 25 / 25 | 25.0000 / 25.0000 / 25.0000 | 35.1731 / 34.8814 / 35.1731 |
| stimulus | DNp09 | 0 / 0 / 0 | 0.0000 / 0.0000 / 0.0000 | 0.0000 / 0.0000 / 0.0000 |
| recovery | LC4 | 45 / 47 / 45 | 0.7143 / 0.7460 / 0.7143 | 118.7148 / 118.0795 / 118.7149 |
| recovery | LPLC2 | 70 / 68 / 70 | 0.7568 / 0.7351 / 0.7568 | 119.6555 / 119.4925 / 119.6555 |
| recovery | GF | 8 / 8 / 8 | 8.0000 / 8.0000 / 8.0000 | 23.5382 / 23.1445 / 23.5382 |
| recovery | DNp09 | 0 / 0 / 0 | 0.0000 / 0.0000 / 0.0000 | 0.0000 / 0.0000 / 0.0000 |

B0 PASS=True. Population 전 구간 90–110%, dead(network/active <50%) 없음, recovery >200% runaway 없음, simultaneous spikes ≥25% 없음, NaN/Inf 없음. LC4/LPLC2 입력·GF downstream·정상 recovery 보존, DNp09 0Hz. 정확한 판단 값과 그룹 active fraction/mean EMA는 b0-equivalence.json.

## B0 — 실제 native noise 성능

| 조건 | Neural s | Internal compute wall s | Neural/wall | Population spikes |
|---|---:|---:|---:|---:|
| baseline | 10 | 69.207681 | 0.1445× | 902419 |
| stimulus | 10 | 69.408585 | 0.1441× | 1302038 |

Gate A noise-off baseline 1.9103× / looming 1.3716× 대비 큰 성능 하락. Noise RNG 생성 비용은 C++ compute 안에 포함했다. SciPy profile 23.3%로 Brian2 비용을 추정하지 않았다. Shared tape 실행 성능은 noise-on realtime 성능으로 사용하지 않는다.
10초 조건별 wall은 200개 internal window timer 합이며 boundary maintenance를 제외한다. 20.5초 전체 Network.run wall과 overhead는 b0-performance.json에 별도 보관.

## B1 — Actual lockstep quantum stress

한 persistent generated Network.run 내부의 50개 실제 1ms step 단위. 각 window의 시작·종료 neural time, compute ms, slack, realtime factor, spike count, 활동을 JSON 및 raw C++ txt에 저장. Python launcher/startup은 quantum timer 밖이다. 별도의 async/backlog 의미나 world prediction 없음.
개별 window timer는 경계의 통계 수집·입력 갱신·로그 기록을 제외한다. 표의 compute wall은 그 maintenance까지 포함한 전체 Network.run이다. Baseline window timer 합은 404.846739s, 전체 Network.run은 425.421806s이며 어느 범위로도 realtime FAIL이다.
Baseline 실제 60s / 1200 windows, 나머지 각 20s / 400 consecutive windows. Real predator는 기존 Godot/ecology 실제 60-frame 전체 sensory current trace를 3s 주기로 반복한 replay. 음식/열/female의 실제 동시 채널도 유지한다. Compound는 실제 최고 visual snapshot + 실제 최고 hot current를 지속 재생 (다른 채널 zero). 새로운 biology/current gain 없음.

| 부하 | Neural s / windows | Compute wall s | Mean / p50 / p95 / p99 / max ms | Miss count / rate | Longest misses | Realtime / clean quality |
|---|---:|---:|---:|---:|---:|---|
| baseline | 60 / 1200 | 425.4218 | 337.372 / 335.795 / 347.342 / 368.089 / 420.166 | 1200 / 100.000% | 1200 | False / False |
| looming | 20 / 400 | 136.2678 | 338.395 / 337.683 / 344.506 / 350.437 / 365.367 | 400 / 100.000% | 400 | False / False |
| real_predator | 20 / 400 | 134.6003 | 335.662 / 333.408 / 346.597 / 356.538 / 360.639 | 400 / 100.000% | 400 | False / False |
| compound | 20 / 400 | 137.7029 | 342.951 / 342.432 / 346.791 / 351.771 / 356.443 | 400 / 100.000% | 400 | False / False |

COMPUTE_REALTIME PASS=False; worst p99 workload=baseline. 판정은 실제 compute total ≤ neural duration AND p99≤50ms. Stress 20s를 60s로 외삽하지 않으며 p99 fail만으로도 realtime을 거부한다. Quality target: miss<1% & longest≤2.

## B2 — 60s deterministic drift

동일 initial state/baseline/weights/signs/dt/refractory/reset, noise OFF. 20s baseline + 20s looming current 3 + 20s recovery. SciPy와 Brian2를 각각 실제 60s 연속 실행했다. 매 1s의 실제 trajectory는 b2-drift.json.

분류: BOUNDED / NUMERICALLY STABLE CANDIDATE; max normalized population error=8.7828071e-06. Absolute mismatch 선형 fit slope=0.265101 spike/s, R²=0.324092; signed slope=0.165796, signed R²=0.084519.

| Neural s | Ref cumulative | Brian cumulative | Difference / absolute / relative | LC4 / LPLC2 / GF difference |
|---|---:|---:|---:|---:|
| 1 | 72421 | 72421 | 0 / 0 / 0 | 0 / 0 / 0 |
| 2 | 147057 | 147057 | 0 / 0 / 0 | 0 / 0 / 0 |
| 3 | 221558 | 221558 | 0 / 0 / 0 | 0 / 0 / 0 |
| 4 | 296186 | 296186 | 0 / 0 / 0 | 0 / 0 / 0 |
| 5 | 370765 | 370765 | 0 / 0 / 0 | 0 / 0 / 0 |
| 6 | 445287 | 445287 | 0 / 0 / 0 | 0 / 0 / 0 |
| 7 | 519676 | 519676 | 0 / 0 / 0 | 0 / 0 / 0 |
| 8 | 594327 | 594327 | 0 / 0 / 0 | 0 / 0 / 0 |
| 9 | 668823 | 668823 | 0 / 0 / 0 | 0 / 0 / 0 |
| 10 | 743421 | 743421 | 0 / 0 / 0 | 0 / 0 / 0 |
| 11 | 817947 | 817947 | 0 / 0 / 0 | 0 / 0 / 0 |
| 12 | 892465 | 892465 | 0 / 0 / 0 | 0 / 0 / 0 |
| 13 | 967171 | 967171 | 0 / 0 / 0 | 0 / 0 / 0 |
| 14 | 1041537 | 1041537 | 0 / 0 / 0 | 0 / 0 / 0 |
| 15 | 1116037 | 1116037 | 0 / 0 / 0 | 0 / 0 / 0 |
| 16 | 1190634 | 1190633 | -1 / 1 / -8.3988866e-07 | 0 / 0 / 0 |
| 17 | 1265082 | 1265081 | -1 / 1 / -7.9046259e-07 | 0 / 0 / 0 |
| 18 | 1339828 | 1339827 | -1 / 1 / -7.4636446e-07 | 0 / 0 / 0 |
| 19 | 1414136 | 1414135 | -1 / 1 / -7.0714556e-07 | 0 / 0 / 0 |
| 20 | 1488790 | 1488789 | -1 / 1 / -6.716864e-07 | 0 / 0 / 0 |
| 21 | 1603285 | 1603284 | -1 / 1 / -6.2371943e-07 | 0 / 0 / 0 |
| 22 | 1717771 | 1717770 | -1 / 1 / -5.8214977e-07 | 0 / 0 / 0 |
| 23 | 1832249 | 1832249 | 0 / 0 / 0 | 0 / 0 / 0 |
| 24 | 1946606 | 1946606 | 0 / 0 / 0 | 0 / 0 / 0 |
| 25 | 2061028 | 2061026 | -2 / 2 / -9.7038953e-07 | 0 / -1 / 0 |
| 26 | 2175647 | 2175651 | 4 / 4 / 1.8385335e-06 | 0 / -1 / 0 |
| 27 | 2290096 | 2290100 | 4 / 4 / 1.7466517e-06 | 0 / -1 / 0 |
| 28 | 2404443 | 2404447 | 4 / 4 / 1.663587e-06 | 0 / 0 / 0 |
| 29 | 2518988 | 2518983 | -5 / 5 / -1.9849241e-06 | -1 / -1 / -1 |
| 30 | 2633316 | 2633306 | -10 / 10 / -3.7974934e-06 | -1 / -4 / -2 |
| 31 | 2747584 | 2747574 | -10 / 10 / -3.6395612e-06 | -2 / -6 / -4 |
| 32 | 2862190 | 2862170 | -20 / 20 / -6.9876563e-06 | -4 / -7 / -3 |
| 33 | 2976878 | 2976870 | -8 / 8 / -2.6873792e-06 | -5 / -5 / -2 |
| 34 | 3091167 | 3091146 | -21 / 21 / -6.7935508e-06 | -6 / -8 / -3 |
| 35 | 3205756 | 3205760 | 4 / 4 / 1.2477556e-06 | -5 / -8 / -5 |
| 36 | 3320236 | 3320219 | -17 / 17 / -5.120118e-06 | -5 / -12 / -6 |
| 37 | 3434586 | 3434566 | -20 / 20 / -5.8231181e-06 | -6 / -13 / -6 |
| 38 | 3548803 | 3548801 | -2 / 2 / -5.6357031e-07 | -4 / -11 / -5 |
| 39 | 3663561 | 3663560 | -1 / 1 / -2.7295847e-07 | -4 / -12 / -5 |
| 40 | 3777822 | 3777821 | -1 / 1 / -2.6470278e-07 | -4 / -9 / -4 |
| 41 | 3852317 | 3852309 | -8 / 8 / -2.0766723e-06 | -4 / -8 / -4 |
| 42 | 3926917 | 3926919 | 2 / 2 / 5.0930539e-07 | -4 / -7 / -5 |
| 43 | 4001208 | 4001221 | 13 / 13 / 3.2490188e-06 | -4 / -7 / -5 |
| 44 | 4075931 | 4075928 | -3 / 3 / -7.3602816e-07 | -4 / -7 / -5 |
| 45 | 4150475 | 4150474 | -1 / 1 / -2.4093628e-07 | -4 / -8 / -5 |
| 46 | 4225044 | 4225045 | 1 / 1 / 2.3668393e-07 | -3 / -8 / -4 |
| 47 | 4299715 | 4299704 | -11 / 11 / -2.5583091e-06 | -4 / -9 / -4 |
| 48 | 4374071 | 4374075 | 4 / 4 / 9.144799e-07 | -4 / -9 / -4 |
| 49 | 4448565 | 4448563 | -2 / 2 / -4.4958318e-07 | -4 / -9 / -4 |
| 50 | 4523219 | 4523226 | 7 / 7 / 1.5475704e-06 | -4 / -9 / -4 |
| 51 | 4597852 | 4597864 | 12 / 12 / 2.6099144e-06 | -4 / -8 / -4 |
| 52 | 4672336 | 4672346 | 10 / 10 / 2.140257e-06 | -3 / -8 / -5 |
| 53 | 4746828 | 4746847 | 19 / 19 / 4.0026729e-06 | -4 / -8 / -5 |
| 54 | 4821460 | 4821455 | -5 / 5 / -1.0370303e-06 | -4 / -7 / -5 |
| 55 | 4895929 | 4895972 | 43 / 43 / 8.7828071e-06 | -4 / -7 / -5 |
| 56 | 4970396 | 4970407 | 11 / 11 / 2.2131033e-06 | -3 / -8 / -4 |
| 57 | 5044925 | 5044947 | 22 / 22 / 4.360818e-06 | -4 / -8 / -4 |
| 58 | 5119516 | 5119511 | -5 / 5 / -9.7665482e-07 | -3 / -9 / -4 |
| 59 | 5194007 | 5194027 | 20 / 20 / 3.8505917e-06 | -4 / -8 / -4 |
| 60 | 5268573 | 5268577 | 4 / 4 / 7.5921886e-07 | -5 / -8 / -4 |

Final population mismatch 4; selected group EMA error도 같은 trajectory에 저장했다. 결과 확보 전 선언한 trend rule은 각 trend의 criterion에 기록했다. 유한한 60s 실행과 안정적인 phase statistics를 확인하는 검사이며, 영구적인 수학적 상한이나 exact spike identity를 증명했다고 주장하지 않는다.

## Resources / performance integrity

Peak executable RSS 0.3036GiB; preparation/compile/executable tree sampled peak 1.6348GiB. GPU/OpenMP 없음.

| Run | Python load / model setup / codegen / compile-link s | C++ init / compute / output s | Python launch + unassigned s |
|---|---:|---:|---:|
| baseline | 0.585 / 0.445 / 0.811 / 5.872 | 0.490 / 425.422 / 0.198 | 0.282 |
| looming | 0.493 / 0.366 / 14.814 / 6.291 | 0.476 / 136.268 / 3.824 | 0.938 |
| real_predator | 0.487 / 0.322 / 0.495 / 5.187 | 0.460 / 134.600 / 0.196 | 0.263 |
| compound | 0.477 / 0.307 / 0.448 / 5.088 | 0.501 / 137.703 / 3.461 | 0.285 |
| b0-native | 0.513 / 0.387 / 0.491 / 5.745 | 0.460 / 13.314 / 0.142 | 0.299 |
| b0-frozen | 0.491 / 0.315 / 0.465 / 5.742 | 0.451 / 1.900 / 0.147 | 0.296 |
| b0-performance | 0.635 / 0.506 / 0.941 / 7.142 | 0.764 / 142.384 / 0.267 | 0.448 |
| b2 | 0.521 / 0.321 / 0.537 / 5.214 | 0.495 / 36.106 / 0.155 | 0.309 |

Baseline SHA 비교: 196 files, changed=[], existing tests=13 PASS. Gate A/body/ecology/core artifacts 보존. 새 파일은 realtime/gate-b/, reports/realtime/gate-b/뿐이며 intermediate binaries/input/noise tape는 workspace work/에 있다.

## Debt / scope stop

기존 body remainder 약 8.5%, ecology 약 19.4%는 startup/socket/logging/ACK/wait 등을 포함한 composite wall remainder다. 이번에는 최적화하지 않았으며 persistent Brian2 integration이나 전체 end-to-end realtime을 구현·인증하지 않았다.
Native noise-on에서 큰 성능 하락을 실제 측정했다. 다만 RNG만의 격리 profile은 수행하지 않았으므로 하락 전체를 RNG 생성 비용으로 단정하지 않는다. 모델/noise amplitude/dt/weights/pruning/motor decoder를 조정하지 않았다. 새로운 backend/GPU/IPC 최적화/Godot 이식으로 확장하지 않고 B0~B2 판정으로 종료한다.
불확실성: native MT seed stream과 reference PCG64 stream은 동일하지 않다 (shared B0는 동일). 단일 seed/제한된 회로/유한한 60s 검사다. B1 stress는 각 20s이며 baseline만 60s이다.

[Brian2 Gaussian/seed documentation](https://brian2.readthedocs.io/en/2.9.0/advanced/random.html) — RNG source of truth is actual generated objects.h (std::mt19937/polar Box-Muller).
[Brian2 standalone/custom injection documentation](https://brian2.readthedocs.io/en/2.9.0/user/computation.html) — steady Network.run compute separated from init/build/output.
