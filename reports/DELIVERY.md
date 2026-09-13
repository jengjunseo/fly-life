# 검증 완료: MaleCNS v1.0 Python brain core

## 작동 범위

실제 connectome을 로컬에서 재생성하고 오프라인에서 로드하는 float32 NumPy/SciPy CSR LIF core를 완성했습니다. 배열 기반 membrane/synaptic/refractory/activity 상태, seeded baseline, warm-up, 선택 뉴런 current 주입, spike bodyId 및 선택 집단 activity readout을 제공합니다. 게임/3D/GPU/행동 규칙은 없습니다.

작업 폴더는 처음에 빈 비-Git 공간이었습니다. 사용자 선택 workspace의 `outputs/brain-core`에 독립 저장소를 생성했습니다. Python 3.11.9와 전용 신규 venv를 사용했습니다. neuPrint 환경 token은 발견되지 않아 인증이 필요 없는 [공식 bulk 배포](https://male-cns.janelia.org/download/)를 사용했습니다. WMI 조회는 접근 거부였지만 CPU/GPU는 Windows registry, RAM/코어는 psutil로 확인했습니다.

## 데이터 규모 / 단순화

`male-cns:v1.0` 공식 annotation 211,577행, neuron-level NT 1,835,518행, segment connectivity 151,856,684행/311,833,243 contacts를 실제 다운로드하고 SHA-256 pin을 기록했습니다. source files 총 1,109,008,094 bytes. synapse 위치 파일은 받지 않았습니다.

`Traced` 165,122개 뉴런을 모두 유지하며 두 endpoint가 이 집합에 속하는 25,563,197개 연결에서 count ≥5를 적용합니다. 관심 집단 477개에 incident한 양수 연결은 보호합니다. 최종 6,474,533개 연결/90,177,929 contacts입니다. 정도가 낮거나 고립된 뉴런 1,217개도 identity를 유지합니다. 원본의 orphan/glia/unassigned/unannotated segment connectivity는 제외됩니다.

모든 annotation 및 해당 neuron-level NT fields를 Parquet에 보존했습니다. `counts.npz`는 원본 synapse count, `weights.npz`는 presynaptic consensus NT sign 및 incoming absolute normalization을 적용한 float32 CSR입니다. ACh +1, GABA/glutamate/histamine -1, modulatory/unclear/결측값 0입니다. 0-sign edge를 anatomy에서 삭제하지 않으며 effective dynamics 연결은 6,327,564개입니다. 방향은 `W[target, source]`입니다.

근거: [전처리 metadata](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/data/runtime/metadata.json), [원본 manifest](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/data/raw/manifest.json).

## Sanity 결과

LC4 126개 + LPLC2 185개를 current 3.0으로 500ms 자극했습니다. warm-up/baseline/stimulus/recovery 각각 500ms입니다. Control, 자극, input outgoing effective edge ablation, 자극 replay를 동일 seed `20260913`으로 실행했습니다. Control과 자극의 baseline 및 자극/replay의 전체 spike sequence hash가 일치합니다. initial current injection의 전압 차이가 선택 집단에만 생기는 real-data integration test도 통과합니다.

실제 named anatomy에서 LC4/LPLC2→DNp01(Giant Fiber) 311개 연결/11,224 contacts가 확인됐습니다. GF bodyIds는 `10001`(R), `10010`(L)입니다. 두 뉴런의 평균 rate는 같은 stimulus 시간창에서 **control 9Hz → 자극 25Hz**, ablation은 **9Hz**였습니다. 자극-minus-control GF rate는 +16Hz이며 synaptic current의 자극-minus-ablation 차이는 +0.40609 arbitrary units입니다. 직접 downstream 10,620개(입력 집합 제외)의 평균은 0.58418→0.87797Hz, ablation 0.58399Hz입니다.

| 자극 trial phase | 전체 spikes | 평균 Hz/neuron | active neurons |
| --- | ---: | ---: | ---: |
| warm-up | 42,160 | 0.51065 | 7,170 |
| baseline | 45,181 | 0.54724 | 7,281 |
| stimulus | 65,209 | 0.78983 | 7,741 |
| recovery | 45,148 | 0.54684 | 7,273 |

자극 중 최대 동시 spike 비율은 0.13566%, maximum single-neuron rate는 134Hz입니다. 모든 post-warmup 50ms bin에 activity가 있고 finite state이며 회복합니다. MDN/steering/courtship으로의 **직접 input 연결은 0**이며 MDN과 steering은 spike가 발생하지 않았고 pC1 집단의 평균 spike rate도 control 대비 변하지 않았습니다. 해당 결과를 숨기거나 행동이 발생했다고 해석하지 않습니다.

실제 annotation의 MDN IDs는 `10763,11288,11332,12348`, DNa01 type IDs는 `10442,10760`, DNa02는 `10360,523769`입니다. Courtship 후보는 156개 `pC1_*`/`pC1x_*` family로 선택했습니다. `P1` exact field match는 없으며 P1과의 일대일 biological alias를 주장하지 않습니다. Cross-dataset alias 검색 결과와 현재 type selection은 구분해서 기록했습니다.

근거: [sanity summary](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/sanity/summary.json), [stimulated statistics](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/sanity/stimulated.json), [실제 directed named edges](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/sanity/circuit_topology.json), [resolved identity](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/data/runtime/resolved_groups.json), [annotation investigation](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/annotation_investigation.json).

## Target benchmark / RAM

실제 target: AMD Ryzen 3 4100(4 physical/8 logical cores), Windows build 26200, Python 3.11.9, RAM 16,957,935,616 bytes(15.79GiB), Radeon RX 570 Series 확인. GPU compute는 사용하지 않았습니다. NumPy 2.4.6, SciPy 1.17.1, pandas 3.0.5, pyarrow 25.0.1, psutil 7.2.2입니다.

200ms warm-up 후 **neural time 10.0초를 wall time 99.43054초**에 실행했습니다. neural/wall 비율은 **0.100573**, neural 1초당 wall **9.94305초**입니다. loading 0.40085초. 실제 902,590 spikes, 평균 0.54662Hz/neuron, 모든 100ms bin 8,861–9,120 spikes, 종료 state finite입니다. 이 benchmark는 10초 연속 실행에 대한 증거이며 무한 시간 안정성을 보장하지 않습니다.

Windows process lifetime peak working set **374,579,200 bytes(0.348854GiB)**; 20ms sampled peak RSS 325,464,064 bytes; representative RSS 321,191,936 bytes. benchmark 중 최소 system available RAM 4,396,216,320 bytes. effective CSR 자체는 51,281,004 bytes입니다.

첫 preprocessing wall 36.60409초(checksum 포함), process peak **1,723,334,656 bytes(1.60503GiB)**. 16GB 한계 내입니다. 다른 앱의 RAM 사용은 제어하지 않습니다. Sparse CPU 구현으로 완료 기준을 달성했으므로 Numba/GPU/Rust 최적화를 추가하지 않았습니다. wall-clock realtime은 달성하지 않았고 요구조건도 아닙니다.

근거: [benchmark LIVE 결과](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/benchmark.json), [hardware evidence](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/reports/hardware.json), 전처리 metadata의 `resources`.

## Claim certification

| Claim | 검증 수준 | Evidence artifact |
| --- | --- | --- |
| DATA | LIVE download + INTEGRATION | `data/raw/manifest.json`, `data/runtime/metadata.json` |
| CONNECTIVITY | UNIT + INTEGRATION | `reports/tests.json`: deterministic 11→22→33 및 실제 signed matrix/known direction |
| SIMULATION | INTEGRATION, target execution | `reports/simulate/stimulated.json`, `reports/benchmark.json` |
| STABILITY | INTEGRATION | `reports/sanity/stimulated.json`, 10초 benchmark bin/rate/finite state |
| BIOLOGICAL-MAPPING | INTEGRATION | `reports/annotation_investigation.json`, `resolved_groups.json`, `circuit_topology.json` |
| STIMULUS | UNIT + INTEGRATION | `reports/tests.json` 실제 선택-target 전압 차이, trial current evidence, control/ablation statistics |
| RESOURCE | LIVE on target | `reports/benchmark.json`, preprocessing `metadata.json`, `reports/hardware.json` |
| REPRODUCIBILITY / OFFLINE | INTEGRATION | `reports/regeneration.json`, sanity replay hash, `reports/offline.json`, `requirements.txt`, `config.json` |

10개 tests(6 UNIT/4 real-data INTEGRATION)가 모두 통과하며 skip은 없습니다. 전처리를 별도 빈 runtime 폴더에 재실행한 counts/weights/neurons/resolved_groups의 SHA-256이 원본 artifact와 모두 동일합니다. 전체 sanity를 Python socket connect/DNS 차단 audit guard에서 다시 실행하고 network attempt 0을 확인했습니다. 물리적인 머신 전체 air-gap을 주장하지 않습니다.

## 주요 artifact / 재실행

`acquire.py`, `preprocess.py`, `inspect_annotations.py`, `braincore/core.py`, `config.json`, `run.py`, `verify.py`, `offline_check.py`, `tests/`, `data/raw/manifest.json`, `data/runtime/`, `reports/`, `README.md`, pinned `requirements.txt`입니다. 소스와 evidence를 Git에 보존하고 다운로드한 대용량 데이터는 로컬 유지/재생성하도록 ignore합니다.

현재 `outputs/brain-core`에서 다음을 실행하면 됩니다.

```powershell
.venv/Scripts/python.exe verify.py
.venv/Scripts/python.exe run.py simulate
.venv/Scripts/python.exe run.py sanity
.venv/Scripts/python.exe run.py benchmark --duration-ms 10000
.venv/Scripts/python.exe offline_check.py
```

새 checkout의 venv 설치/다운로드/전처리 순서는 [README](C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/outputs/brain-core/README.md)를 따릅니다.

## Certification debt / 한계

이번 brain-only Done의 미확인 필수 evidence는 없습니다. 다만 검증된 것은 특정 config/seed에서의 simplified operating regime이며 생물학적 정확성이나 모든 파라미터 조합의 안정성이 아닙니다. 뉴런 대부분은 baseline에서 침묵합니다. Baseline drive/noise, sign, normalization/gain, 시간상수, uniform delay는 model assumptions입니다. Glutamate의 VNC/motor excitatory 효과, receptor별 부호, co-transmission, modulatory dynamics, plasticity, gap junctions를 재현하지 않습니다. 실제 looming receptive field 또는 escape/courtship/steering/몸체 행동을 검증하지 않았습니다. food/temperature/pain의 미확인 mapping은 비어 있습니다. 다른 OS/라이브러리 버전의 bit-identical 결과와 수시간 실행 안정성도 보증하지 않습니다.

요구된 가장 단순한 brain core 상태에서 종료합니다.
