# MaleCNS v1.0 offline brain core

실제 Janelia MaleCNS v1.0의 sparse connectivity를 실행하는 독립형 Python LIF 코어입니다. 행동 규칙, 게임, 서버, GPU backend는 없습니다. 이 모델은 **connectome 기반의 신호 전달 실험 도구**이며 실제 수컷 초파리의 신경 동역학/행동을 검증한 모델은 아닙니다.

## 새 환경에서 실행

Python 3.11 x64 권장. 아래 명령은 이 README가 있는 `brain-core` 폴더에서 실행합니다. 첫 설치/다운로드만 인터넷이 필요합니다. token이 필요하지 않습니다.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt --index-url https://pypi.org/simple
.venv/Scripts/python.exe acquire.py
.venv/Scripts/python.exe preprocess.py
.venv/Scripts/python.exe inspect_annotations.py
.venv/Scripts/python.exe verify.py
.venv/Scripts/python.exe run.py simulate
.venv/Scripts/python.exe run.py sanity
.venv/Scripts/python.exe run.py benchmark --duration-ms 10000
.venv/Scripts/python.exe offline_check.py
```

현재 이 폴더에는 다운로드된 원본, runtime artifact, 실행한 결과가 있습니다. 따라서 simulation/sanity/benchmark/offline check는 **오프라인**에서도 가능합니다. `verify.py`는 실제 데이터가 없으면 integration test를 skip으로 기록하고 비정상 종료합니다. synthetic 대체 완료는 허용하지 않습니다.

원본 약 1.03GiB와 runtime 파일을 위한 공간을 확보하십시오. Git에는 거대한 재생성 가능 데이터 파일/가상환경을 넣지 않지만, 실제 로컬 파일은 유지합니다. 깨끗한 checkout에서는 `acquire.py`와 `preprocess.py`로 재생성합니다. 원본 URL, 용량, SHA-256은 `data/raw/manifest.json` 및 runtime metadata에 기록됩니다. acquisition은 이번 공식 원본의 SHA-256으로 pin되며 파일이 교체/손상되면 중단합니다. 원인 조사 없이 checksum을 바꾸지 마십시오. 별도 빈 runtime 폴더로 재생성한 네 파일의 SHA-256 동일성은 `reports/regeneration.json`에 기록했습니다.

## 데이터와 전처리

[공식 다운로드](https://male-cns.janelia.org/download/)의 세 파일만 사용합니다. dataset identifier는 `male-cns:v1.0`, synapse confidence cutoff는 배포 파일명의 `minconf-0.5`입니다. 개별 synapse 좌표/mesh/skeleton은 받지 않습니다. 데이터 제공: FlyEM/HHMI Janelia, Cambridge, MRC LMB, Google Research; [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).

Annotation 211,577행 중 `status=Traced` 165,122개를 선택합니다. `Glia`, `Orphan`, unassigned 및 annotation 없는 segment endpoint는 제외합니다. 따라서 원본의 모든 segment graph를 그대로 실행하는 것은 아닙니다. neuron degree 때문에 뉴런을 삭제하지 않으며 연결이 없는 1,217개도 identity table에 유지합니다.

원본 connectivity 151,856,684행/311,833,243 synaptic contacts에서 두 endpoint가 Traced인 25,563,197개 연결/124,025,046 contacts를 얻습니다. count ≥5를 유지하되 config 보호 집단 477개 뉴런에 incident한 모든 양수 연결을 유지합니다. 보호로 추가 유지되는 약한 연결은 238,851개입니다. 최종 6,474,533개 연결/90,177,929 contacts입니다. threshold 1/3/5/10의 **보호 전** 규모 비교도 metadata에 남습니다.

`data/runtime/neurons.parquet`는 모든 원본 annotation column과 모든 해당 neuron-level NT column을 보존합니다. `runtime_index`가 matrix index이며 `bodyId`로 원본을 역추적합니다. `counts.npz`는 실제 unsigned synapse counts, `weights.npz`는 sign/normalization 적용 float32 CSR입니다. 모두 **[target, source]**이고 `W @ previous_spikes`로 신호를 전달합니다. `resolved_groups.json`은 type/instance/IDs/NT 선택 결과입니다. `metadata.json`은 source/schema/pruning/sign/model/defaults/checksums/resource evidence입니다.

## 모델 가정

뉴런별 `consensus_nt`를 사용합니다. ACh +1, GABA/glutamate/histamine -1, dopamine/octopamine/serotonin/unclear/결측값 0. 원본 predicted NT, confidence, ground truth와 celltype consensus 정보는 제거하지 않습니다. 0-sign 연결은 topology 파일에 남지만 fast-current dynamics에는 기여하지 않습니다. effective 연결은 6,327,564개입니다.

ACh/GABA/glutamate의 단순화는 기존 [connectome 연구의 sign 가정](https://www.nature.com/articles/s41586-024-07558-y)을 참고했습니다. **전달물질은 항상 고정된 효과를 의미하지 않습니다.** 특히 VNC/motor/NMJ에서 glutamate는 excitatory일 수 있습니다. receptor별 효과와 co-transmission을 이 데이터만으로 추론하지 않으며 motor 기능 재현을 주장하지 않습니다. Histamine의 inhibitory 취급도 단순한 model assumption입니다. 불확실한 modulatory 전달물질은 임의로 강하게 만들지 않습니다.

target별 incoming effective absolute synapse count로 정규화하며 row absolute sum ≤1입니다. 전체 strength는 `recurrent_gain`으로 설정합니다. 가중치/시간상수/전압/current는 생물물리학을 fitting한 값이 아닙니다. membrane Euler update 및 지수 decay synaptic current를 사용합니다.

```text
syn[t] = exp(-dt/tau_syn) * syn[t-1] + gain * W @ spikes[t-1]
v[t] += dt/tau_m * (rest - v[t] + baseline + seeded_noise + syn[t] + external)
```

임계치를 넘으면 spike/reset, 다음 refractory 전체 timesteps 동안 reset을 유지합니다. state는 배열, float32, refractory는 int32입니다. baseline은 seed로 생성한 고정 heterogeneous drive와 매 timestep seeded Gaussian noise입니다. 초기 warm-up은 configurable합니다. refractory 외에 firing-rate 강제 clipping, 행동 command, 임의 feedback controller는 없습니다. uniform 1-step delay, gap junction/plasticity/몸체 feedback 없음. 다수 뉴런의 침묵은 관찰되며 baseline은 외부 모델 가정입니다.

## Config와 body 연결 인터페이스

`config.json`에서 threshold/보호 집단, 정확한 `types`, `bodyIds`, `type_regex`, sign 정책, model, seed, warm-up, input/observe 집단을 바꿉니다. 선택은 union입니다. 관측/자극 그룹을 바꾸려면 config를 바꾸고 전처리를 재실행하십시오. model/seed/time만 변경하면 runtime artifact 재생성이 필요 없습니다. runtime loader는 mapping/pruning/sign/identity checksum 불일치를 거부합니다.

LC4/LPLC2, MDN, DNa01/DNa02, DNp01(Giant Fiber), pC1 계열은 **실제 annotation에서 확인**했습니다. `P1`이라는 exact type을 임의로 pC1 bodyId에 대응시키지 않습니다. food/temperature/pain 집단은 안전하게 비어 있으며 실제 확인된 type/ID를 사용자가 나중에 추가할 수 있습니다.

```python
import json
from braincore import Brain
config = json.load(open('config.json'))
brain = Brain.load('data/runtime', config)
brain.warmup(config['experiment']['warmup_ms'])
sensory = brain.resolve(config['groups']['looming'])
motor = brain.resolve(config['groups']['steering'])
external = brain.current(sensory, 3.0)  # selected runtime indices only
spikes = brain.step(external)           # reused array; copy if retaining
motor_readout = brain.read_activity(motor)  # EMA Hz + current spikes
all_fired_body_ids = brain.spike_body_ids()
```

향후 body/world는 neural time과 독립적으로 필요한 횟수만큼 `step`을 호출합니다. real-time 보장은 없습니다. 선택 집단의 spike/activity를 출력할 뿐 행동을 결정하지 않습니다.

## Sanity / certification

`verify.py`: deterministic graph 방향, presynaptic sign, refractory/reset, seed/warm-up, selector/current 대상 및 **실제 MaleCNS** identity, named topology, signed matrix, 첫 자극으로 선택 대상에만 생기는 전압 차이, isolated neuron 유지까지 검증합니다. 결과는 `reports/tests.json`에 저장됩니다.

`run.py sanity`: LC4+LPLC2를 자극하고 DNp01/Giant Fiber 등을 관측합니다. 실제 retained anatomy에서 input→GF 311 edges/11,224 contacts가 존재합니다. MDN/steering/courtship으로의 **직접** 연결은 이 입력 집합에서는 0입니다. 이를 숨기거나 기대하는 도주 행동을 강제하지 않습니다. 직접 downstream 전체도 관측합니다.

동일 seed의 무자극 control, 자극, 입력의 outgoing effective weights만 0으로 만든 diagnostic ablation, 자극 replay를 각 2초 실행합니다(warm-up/baseline/stimulus/recovery 각각 500ms). ablation은 대조 실험에만 사용하고 일반 core에는 적용하지 않습니다. baseline drive는 변경하지 않습니다. Control과 자극의 baseline 일치, 자극 replay의 전체 spike sequence hash 일치를 검증합니다. 각 phase의 모든 뉴런 spike counts, 전뇌/선택 집단 rate, synaptic current, voltage, 50ms bin statistics, current target IDs를 저장합니다.

Engineering guardrails는 finite state, post-warmup 각 bin에서 nonzero activity, population mean <100Hz, 동시 spike fraction <25%입니다. **생리학적 타당성의 증명은 아닙니다.** 자극에 따른 rate 차이와 ablation 대비 downstream current 차이도 필수입니다. 실패하면 summary를 저장하고 비정상 종료하며 성공으로 보고하지 않습니다.

`run.py benchmark`: warm-up 후 연속 CPU sparse simulation의 neural/wall-clock 비율, loading 시간, 20ms 간격 RSS/system available RAM 및 Windows process lifetime peak working set을 기록합니다. 16GB는 모든 앱이 함께 사용하므로 다른 앱의 이용량은 코어가 제어할 수 없습니다. 전처리와 runtime 모두의 실측 메모리를 참고하십시오.

`offline_check.py`는 Python socket connect/DNS audit event를 차단한 상태에서 실제 데이터 sanity 전체를 실행합니다. 네트워크 호출이 시도되면 실패합니다. 이는 머신 전체의 물리적 인터넷 단절이 아니라 Python runtime의 연결 금지 검증입니다.

이번 실측 결과와 claim별 evidence는 `reports/DELIVERY.md`를 참고하십시오. 다른 머신/GPU의 수치를 사용하지 않습니다.
