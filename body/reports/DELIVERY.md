# MaleCNS brain gets a body — target 실측 완료

## 사용자가 체감하는 결과

Godot의 작은 사각 arena에 primitive 초파리 한 마리가 실제 표시됩니다. 초기 warm-up 뒤 `1`/`2`/`3` 키는 실제 MaleCNS 뉴런에 current를 넣으며, 그 결과의 activity만을 읽어 몸이 좌/우로 회전하거나 전진합니다. Keyboard가 velocity/position을 직접 조절하지 않습니다. 약 0.088× slow-motion이며 렌더링은 60–61FPS입니다. 먹이/천적/암컷/온도/HP/게임 AI 등은 없습니다.

실제 화면: `integration/arena.png`. 화면은 Godot viewport가 저장한 실제 RX 570 렌더 결과입니다. mock, headless image, 생성 이미지가 아닙니다.

## Neural groups / decoder

모든 뉴런의 실제 `type`, `instance`, `somaSide`, `superclass`, NT를 기존 `neurons.parquet`에서 확인했습니다.

| group | bodyIds / annotation |
| --- | --- |
| left | `10442` DNa01(VES006)_L; `523769` DNa02_L |
| right | `10760` DNa01(VES006)_R; `10360` DNa02_R |
| experimental forward | `10783` DNp09_L; `11177` DNp09_R |

이 집합은 모두 실제 descending_neuron 및 acetylcholine consensus입니다. Soma side와 instance suffix가 일치하지 않으면 실행을 거부합니다. [DNa02의 turning 관련 근거](https://www.nature.com/articles/s41586-025-08925-z), [DNp09의 walking 관련 근거](https://www.nature.com/articles/s41586-024-07523-9)는 후보 선정 근거이지 아래 decoder의 biological validation이 아닙니다.

기존 core의 EMA Hz를 각 집단 평균으로 읽고 `forward=clip(DNp09/100,0,1)`, `turn=clip((right-left)/100,-1,1)`로 변환합니다. Movement scale은 config의 2 world-units/neural-second, 2 radians/neural-second입니다. `turn>0`은 right이며 Godot yaw 부호를 반전해 적용합니다. Anatomical side→ipsilateral body turn과 DNp09 activity→forward scalar는 명시적인 **experimental motor decoding assumptions**입니다.

## Bridge / time / lifecycle

기존 core는 별도 Python process에서 전체 165,122개 뉴런 / 6,327,564 signed nonzero 연결 artifact를 로드합니다. 원본 retained anatomy 6,474,533개 연결은 변경하지 않았습니다. `W[target,source]`, LIF, seed/noise, pruning, NT sign, core config 및 scientific reports를 모두 보존했습니다. Baseline commit `4cd038f`에 대한 tracked files 비교와 core/config/metadata SHA가 일치합니다. 변경 surface는 새 `body/`뿐입니다.

Python socket↔Godot StreamPeerTCP로 **127.0.0.1:18761 / v=1 / UTF-8 JSONL**을 사용합니다. UDP loss/ACK의 추가 복잡성 없이 완료 구간을 보존하기 위한 작은 reliable local IPC입니다. Godot→brain은 heartbeat/current group/clear/reset/shutdown, 반대 방향은 상태·gen/seq·neural time·completed dt·activity·motor 값·population summary입니다. 부적합 packet/time 불연속/timeout은 stop/error이며 fallback AI는 없습니다.

Neural 50ms 완료마다 packet 하나를 보내므로 이론상 최대 control 20Hz, 현재 PC에서는 **1.754Hz**입니다. Core는 모든 1ms neural step을 실제 계산합니다. Godot body/world는 packet의 completed neural dt만 적분합니다. Render/physics wall delta로 cached movement를 진행하지 않습니다. Warm-up 500ms는 neural HUD에 포함하고 world는 0입니다. Reset 후 neural/world는 초기화하고 앱 wall time은 계속 표시합니다.

## Actual runtime tests

Godot `Input.parse_input_event(InputEventKey)`로 실제 debug key 처리 경로를 실행했고 실제 full MaleCNS backend와 통신했습니다. OS physical key injection을 했다고 주장하지 않습니다.

| 실제 neural stimulus | 집단 peak EMA | body 결과 |
| --- | ---: | ---: |
| left current 3.0, 400ms neural | left 121.317Hz | yaw **+0.844239rad** |
| right current 3.0, 400ms neural | right 104.959Hz | yaw **−0.801011rad** |
| DNp09 current 3.0, 400ms neural | forward 113.768Hz | 전진 거리 **0.834916 units** |

각 phase는 stimulus 400ms와 decay 관측을 포함하는 700ms world/neural 시간창입니다. Log에는 key command id→실제 current bodyIds/count/strength→neural activity packet gen/seq→decoder→body position/yaw가 시간순으로 남습니다. wall-clock command 수신 경계에 따라 반복 실험의 current 시작 step이 조금 달라질 수 있습니다. reset 초기 state의 동일성은 별도로 검증했습니다.

자극 path를 끈 같은 KEY_1 event는 current injection을 만들지 않았고 baseline body rotation/translation은 0이었습니다. 두 동일-seed reset 뒤 첫 8개의 50ms packet에서 activity/forward/turn/population readout이 정확히 일치했습니다. 실제 brain process tree를 강제 종료한 뒤 HUD connection은 disconnected/error, 최소 3개의 연속 sample에서 body position/yaw/world time이 고정됐습니다. 정상 창 종료에서는 Python/Godot exit code 0, 잔여 own process PID 0이었습니다.

`analyze.py`는 62개 body commits의 real source gen/seq, activity→decoder 식, yaw 적분 및 world==completed motor time을 모두 검사합니다. Decoder UNIT 3개 및 integration certification 21개 모두 통과합니다.

## CPU / RAM / FPS / brain speed

Target Ryzen 3 4100 4-core/8-thread, Windows build 26200, Python 3.11.9, 16,957,935,616 bytes RAM, RX 570 graphics. Godot **4.6.1.stable.official.14d19694e**, OpenGL 3.3 Compatibility. Brain은 기존 CPU backend입니다.

| 측정 | 실측 |
| --- | ---: |
| steady neural/wall ratio | **0.087719×** |
| motor control packets / wall second | **1.754386Hz** |
| rendered Godot ready FPS | **60–61** |
| Python process-tree peak sampled RSS | **375,324,672 bytes / 0.350GiB** |
| Godot process-tree peak sampled RSS | **221,593,600 bytes / 0.206GiB** |
| 동시 combined peak sampled RSS | **591,233,024 bytes / 0.551GiB** |
| 최소 available system RAM (integration) | **4,546,478,080 bytes** |

Windows venv redirector뿐 아니라 실제 Python interpreter 자식까지 포함한 process-tree 측정입니다. 100ms sampler를 사용했고 VRAM/OS/다른 앱/작은 supervisor 자체의 RSS는 위 두 process-tree 합계와 구분합니다. 정상 종료 run도 combined 583,401,472 bytes였고 최소 available system RAM은 3,202,314,240 bytes였습니다. 16GB 내에서 실제 동시 실행했습니다.

기존 core-only benchmark 약 0.100573×보다 이번 동시 integration에서 throughput은 약 13% 낮았습니다. 이는 다른 시간의 측정이므로 차이를 전부 network overhead로 단정하지 않습니다. 정상 종료 run에서 bridge runtime wall 11.58305초 중 `Brain.step` 자체 10.59409초(91.46%)였고 나머지에는 loading/waiting/mapping/logging/IPC가 포함됩니다. 심각한 IPC 병목은 관찰하지 않았으며 최적화/backend 교체를 하지 않았습니다.

## Claims / certification / evidence

| Claim | 수준 | 실제 evidence |
| --- | --- | --- |
| BASELINE | STATIC + INTEGRATION | `integration/baseline_mapping.json`: original artifact hashes, actual groups, real PID; unchanged Git baseline check |
| BRIDGE | LIVE | `integration/brain.jsonl`, `integration/godot.jsonl`: commands/acks/state gen/seq |
| NEURAL CONTROL | INTEGRATION/LIVE | current_injection rows→source_activity_hz→body_commit yaw/position |
| NO DIRECT MOVEMENT | STATIC + UNIT + INTEGRATION | one movement path scan, decoder tests, disabled same key test |
| LEFT/RIGHT/FORWARD | INTEGRATION/LIVE | certification phase metrics and continuous body commits |
| TIME | INTEGRATION/LIVE | every body world time matches actual source motor time; dt-only integration |
| FAILURE MODE | INTEGRATION/LIVE | actual process-tree kill→disconnected samples→frozen body/world; clean-exit codes/PIDs |
| RESOURCE | LIVE target | integration/resources.json and renderer console/FPS telemetry |

주요 artifact는 `body_config.json`, `decoder.py`, `bridge.py`, `main.gd`, `main.tscn`, `project.godot`, `launch.py`, `setup_godot.py`, `test_decoder.py`, `analyze.py`, `reports/`입니다. 실행법은 `body/README.md`를 참고하십시오. 기존 certification은 core를 변경하지 않았으므로 재실행/덮어쓰기하지 않았습니다.

## Uncertainty / debt

Physical OS keyboard injection / native screenshot은 Computer-use app approval timeout 때문에 인증하지 못했습니다. 실제 engine-generated key input handling과 전체 live neural/body path 및 viewport rendering은 인증했습니다. Experimental scalar decoding은 fly biology의 motor reconstruction이 아니며 forward group의 선택도 확정된 생물학적 locomotion decoder를 뜻하지 않습니다. Baseline에서 steering/DNp09가 침묵하므로 debug current 없는 몸의 정지는 정상입니다. 활동은 sampled 50ms frame의 endpoint EMA이며 몸체는 primitive kinematic proxy, neural/world/render 단위는 생물학적으로 fitting하지 않았습니다. 장시간 안정성·모든 config의 동작을 보증하지 않습니다.

요구된 brain→최소 3D body 연결 상태에서 종료합니다.
