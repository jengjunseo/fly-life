BRIAN2 GATE A: SURVIVES

실제 target: AMD Ryzen 3 4100 (4C/8T), 16GB RAM, Windows. GPU compute 없음.

## 최소 current-backend profile

Noise-on 원본 의미의 0.5 neural s / 5.240596 wall s. 타이머 복사본은 원본과 상태 bit-exact.

| 구간 | Wall s | 비중 |
|---|---:|---:|
| propagation | 3.895293 | 74.33% |
| neuron_noise_refractory_reset | 1.221870 | 23.32% |
| misc | 0.117480 | 2.24% |
| readout | 0.001695 | 0.03% |

## 구현과 연결망

Brian2 2.9.0 generated/compiled C++ standalone, CPU 1 thread. 165,122 neurons / 6,327,564 effective signed synapses (6,474,533 anatomical retained).
1ms, 기존 float32 weights와 membrane/synapse/reset 파라미터 유지. 전파는 presynaptic spike-triggered. 전체 C++ i/source, j/target, w 배열을 실제 runtime CSR와 정확 비교했다.
Reference의 seeded baseline drive를 그대로 export. Gaussian noise는 실험용 in-memory copy에서만 OFF. 외부 전류는 기존 LC4/LPLC2 311개에 3.0. Core config는 수정하지 않았다.
작은 asymmetric signed compiled 테스트: spike 스텝 일치, direction/sign/one-step-delay/external/refactory 확인. 최대 v 오차 9.54e-7, syn 오차 3.81e-6, refractory 및 activity 오차 0.

## Noise-off 최소 회로 비교

각 비교 구간 0.5s; 그 앞 warmup 0.5s. 표의 활동은 해당 그룹 평균 EMA(Hz)의 구간 평균/최대.

| 구간 | 그룹 | Spike count Ref / Brian | Rate Hz Ref / Brian | Mean activity Ref / Brian | Peak activity Ref / Brian |
|---|---|---:|---:|---:|---:|
| baseline | LC4 | 42 / 42 | 0.6667 / 0.6667 | 0.6630 / 0.6630 | 0.9961 / 0.9961 |
| baseline | LPLC2 | 57 / 57 | 0.6162 / 0.6162 | 0.6128 / 0.6128 | 0.8498 / 0.8498 |
| baseline | GF | 8 / 8 | 8.0000 / 8.0000 | 8.3309 / 8.3309 | 14.3540 / 14.3540 |
| baseline | DNp09 | 0 / 0 | 0.0000 / 0.0000 | 0.0000 / 0.0000 | 0.0000 / 0.0000 |
| stimulus | LC4 | 7503 / 7503 | 119.0952 / 119.0952 | 107.0621 / 107.0621 | 123.8339 / 123.8339 |
| stimulus | LPLC2 | 11153 / 11153 | 120.5730 / 120.5730 | 108.4305 / 108.4305 | 124.3308 / 124.3308 |
| stimulus | GF | 22 / 22 | 22.0000 / 22.0000 | 20.2282 / 20.2282 | 33.3326 / 33.3326 |
| stimulus | DNp09 | 0 / 0 | 0.0000 / 0.0000 | 0.0000 / 0.0000 | 0.0000 / 0.0000 |
| recovery | LC4 | 41 / 41 | 0.6508 / 0.6508 | 12.6721 / 12.6719 | 119.7361 / 119.7361 |
| recovery | LPLC2 | 55 / 55 | 0.5946 / 0.5946 | 12.7427 / 12.7425 | 120.9484 / 120.9484 |
| recovery | GF | 8 / 8 | 8.0000 / 8.0000 | 9.6301 / 9.6183 | 21.9397 / 21.9397 |
| recovery | DNp09 | 0 / 0 | 0.0000 / 0.0000 | 0.0000 / 0.0000 | 0.0000 / 0.0000 |

GF: bodyId 10001/10010, baseline 8 → stimulus 22 → recovery 8Hz 양쪽 동일. Δ +14Hz. DNp09: 10783/11177, 전 구간 0Hz 양쪽 동일 (pass 조건 아님).
LC4 Δ +118.4286Hz, LPLC2 Δ +119.9568Hz 양쪽 동일. EMA recovery 구간 평균에는 정상적인 잔류 decay가 포함된다. 모든 관측량의 상세 delta/final 값은 gate-a.json에 있다.
Population spikes: baseline 37310 / 37310, stimulus 57393 / 57393, recovery 37333 / 37332. 유한 상태/정상 회복 확인.

## 실제 성능

2s smoke: C++ neural/wall 1.7406× (계산 wall 1.149059s).

| Backend / 부하 | Neural s | Simulation wall s | Neural/wall | Population spikes |
|---|---:|---:|---:|---:|
| SciPy noise-off baseline | 10 | 85.437567 | 0.1170× | 745696 |
| Brian2 baseline | 10 | 5.234802 | 1.9103× | 745685 |
| Brian2 LC4_LPLC2_stimulus | 10 | 7.290787 | 1.3716× | 1144427 |

Baseline 비교 16.32배 개선. 자극 firing load 0.4516 → 0.6931Hz/neuron. 자극은 baseline 10s의 상태에서 연속 실행했다.
Cold build total 8.631933s, 실제 make/compile+link 8.140002s. Python load 0.493460s; model generation 0.367148s; C++ load/init 0.456976s.
전체 executable 실행(0.5s warmup + 10s baseline + 10s stimulus, init/output 포함)은 14.567011s. Simulation timer는 std::chrono wall timer이며 Network.run만 포함한다. 남은 launch/output/구간 준비 등 1.312797s은 계산 성능에 섞지 않았다. Spike/selected-activity monitor 비용은 simulation에 포함.
RAM: executable peak 0.3482GiB, representative 0.3243GiB. Python preparation peak 0.6153GiB, Python+compiler/executable tree sampled peak 1.4591GiB. System available minimum 3.9863GiB. Sampling 20ms + OS child peak working set.

## Integration overhead debt

body: 기존 동일 run 내부 total 11.583051s = Brain.step 10.594094s + remainder 0.988957s (8.54%). Source: body\reports\clean-exit\brain_exit.json.
ecology: 기존 동일 run 내부 total 43.183288s = Brain.step 34.820171s + remainder 8.363118s (19.37%). Source: reports\ecology\live\brain_exit.json.
이 remainder는 serialization/socket/logging/ecology/Godot ACK/initialization/shutdown을 합친 실제 wall 잔여이며 개별 CPU 비용 분해는 아니다. 기존 core 0.1006×, body 0.0877×, ecology 0.0805×는 서로 다른 workload의 참고치다.
Brain은 10배 이상 빨라졌으므로 이 unchanged integration 비용이 다음 병목이 될 수 있다. 특히 standalone cold-start/결과 쓰기를 50ms packet마다 반복하는 설계는 안 된다. 이번 결과는 Brian2+Godot 전체 realtime 성능을 보증하지 않는다. IPC/JSON/세계 구조는 전혀 최적화·이식하지 않았다.

## 보존과 판정

기존 source/runtime/body/ecology/report 173개 SHA-256 byte snapshot: 변경 0. 기존 13 core/real-data/decoder tests 통과. 새 파일은 realtime/ 및 reports/realtime/뿐이며 build/compatibility 중간물은 workspace work/에 있다.
Generated source와 executable SHA 및 실제 C++ timer evidence는 brian-benchmark.json / generated-proof/에 보관. 후보는 SURVIVES. Gate B, noisy equivalence, compound burst, ecology migration은 실행하지 않고 종료한다.

## 기술 참고

[Brian2 standalone 및 timing injection 공식 문서](https://brian2.readthedocs.io/en/2.9.0/user/computation.html) — build/run 분리와 Network.run 전후 C++ hook 사용.
[Brian2 scheduling 공식 문서](https://brian2.readthedocs.io/en/2.9.0/user/running.html#scheduling) — before_groups 순서와 explicit integer refractory 구현.
