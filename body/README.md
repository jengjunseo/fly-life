# Brain gets a body — Godot + verified MaleCNS core

이 폴더만 새 integration layer입니다. 부모 brain-core의 LIF/preprocessing/sign/pruning/config 및 기존 scientific reports는 수정하지 않습니다. Godot arena 안에 primitive 초파리 하나가 있으며 body 이동 입력은 오직 실제 MaleCNS activity에서 나온 decoder 값입니다. 먹이/천적/암컷/온도/HP/보행 physics/비행/AI는 없습니다.

## 실행

아래 명령은 부모 `brain-core` 폴더에서 실행합니다. 기존 `.venv`, `data/runtime`이 필요합니다. 새 checkout의 core 준비는 부모 README를 따르십시오.

```powershell
.venv/Scripts/python.exe body/setup_godot.py
.venv/Scripts/python.exe body/launch.py
```

Godot 4.6.1 stable Windows portable을 공식 GitHub에서 받습니다. 이미 Godot 4.6이 있으면 다운로드 없이 `--godot C:/path/to/Godot.exe`를 전달할 수 있습니다. 실제 사용 버전/다운로드 SHA-256은 `reports/godot_acquisition.json`, runtime console logs에 있습니다. OpenGL Compatibility renderer로 RX 570을 사용하며 GPU는 **graphics only**, brain은 기존 CPU core입니다.

Godot 창이 실제로 열립니다. 처음에 starting/warming-up을 보여주고 약 수 초 후 ready가 됩니다. Godot 정상 닫기/Esc 또는 CLI Ctrl+C의 정상 cleanup에서 그 실행이 만든 Python/Godot process tree만 종료합니다. 기존 타인의 Python/Godot process는 건드리지 않습니다. Godot 창의 Esc/닫기 및 `--quit-after`는 shutdown 메시지를 보내고 launcher가 remaining child를 정리합니다. Brain 오류/종료 시 몸은 정지하며 HUD는 disconnected/error가 됩니다. fallback AI가 없습니다. Supervisor 자체를 OS에서 강제 kill하는 경우의 cleanup은 별도 인증하지 않았습니다.

키는 몸을 직접 조절하지 않습니다.

- `1`: 왼쪽 DNa01/DNa02 뉴런 current
- `2`: 오른쪽 DNa01/DNa02 뉴런 current
- `3`: DNp09 양측 뉴런 current
- `4`: current 제거
- `R`: 동일 seed brain 재초기화 및 body/world 초기조건 reset
- `Esc`: 종료

`body_config.json`의 debug current/duration, group type/somaSide selector, decoder scale/gain, body units 및 arena size를 바꿀 수 있습니다. 기본 current 3.0, duration 400ms **neural time**이므로 wall time에서는 약 4초가 걸릴 수 있습니다. World 입력 경계는 `stimulus` JSON→검증된 neural group→`brain.current`뿐입니다. 추후 감각 그룹을 이 layer의 config에 추가할 수 있지만 이번 단계에는 환경 행동 규칙이 없습니다.

## 실제 mapping / decoder 가정

`neurons.parquet`에서 `type`, `instance`, `somaSide`, `superclass`를 확인합니다. `instance`의 L/R suffix와 somaSide가 서로 일치해야 실행됩니다.

| group | 실제 type / bodyId / side |
| --- | --- |
| left | DNa01 `10442` L; DNa02 `523769` L |
| right | DNa01 `10760` R; DNa02 `10360` R |
| experimental forward | DNp09 `10783` L, `11177` R |

이 뉴런들은 실제 annotation에서 모두 descending_neuron, cholinergic입니다. [DNa02 turning 연구](https://www.nature.com/articles/s41586-025-08925-z)와 [DNp09 forward walking 연구](https://www.nature.com/articles/s41586-024-07523-9)를 후보 선정 근거로 삼았으나 아래 식 자체는 **motor decoding assumption**입니다. Anatomy의 L/R 확인은 physiological ipsilateral effect의 검증과 다릅니다. 실제 초파리 보행 decoder라고 주장하지 않습니다.

기존 core의 50ms EMA activity Hz를 집단 평균으로 읽습니다. 새 noise, 행동 rule, core parameter tuning은 없습니다.

```text
forward = clamp(DNp09_mean_Hz / 100, 0, 1)
turn    = clamp((right_mean_Hz - left_mean_Hz) / 100, -1, 1)
body_speed = forward * 2 units / neural second
body_yaw_rate = -turn * 2 radians / neural second
```

`turn>0`은 right이며 Godot의 +Y yaw는 left이므로 마지막 부호가 반대입니다. Decoder 입력은 activity와 scale/gain뿐이며 키, stimulus 상태, 세계/body 상태는 입력이 아닙니다. 기본 baseline에서는 steering/DNp09가 침묵해 몸이 정지할 수 있습니다. Debug current를 통한 이동은 실제 core step/EMA readout을 거칩니다.

## 시간 / bridge contract

UDP는 작은 packet에 적합하지만 이번 단계에서는 packet 손실 처리/ACK를 추가하지 않는 가장 단순한 reliable **TCP JSONL**을 선택했습니다. `127.0.0.1:18761` 한 쌍만 사용하며 외부 interface에 bind하지 않습니다. standalone localhost IPC이며 서버 infrastructure가 아닙니다. JSON protocol `v=1`, UTF-8 한 줄당 한 메시지, 최대 receive buffer 64KiB. 통신 자체는 복잡한 dependency 없이 Godot StreamPeerTCP / Python socket을 사용합니다.

Godot→brain: `heartbeat`, `stimulus(group)`, `clear`, `reset`, `shutdown`와 command id. 반복 command id는 중복 적용하지 않습니다. Debug amplitude/duration은 Python config가 결정하므로 message가 임의 parameter를 주입하지 않습니다.

Brain→Godot: status, generation, seq, wall/neural/motor time, completed dt, forward/turn, group EMA Hz, population Hz, stimulus state, command acknowledgments, Python RSS. Sequence/모델 time의 불연속, 잘못된 motor 값, timeout은 움직임 정지/error를 만듭니다. 누락 packet을 extrapolate하지 않습니다. 50ms neural 구간당 하나의 motor frame입니다. 이론적 최대 20Hz, 이 PC에서는 대략 2Hz입니다. 작은 start/warm-up/ready 상태 메시지는 dt=0으로 body를 움직이지 않습니다.

Render는 60FPS wall time으로 실행합니다. core warm-up 500ms는 HUD neural time에 포함하고 world는 0입니다. ready 후 world는 **완료된 neural motor frame의 dt만** 더합니다. body도 이 dt만 적분합니다. Godot physics `_delta`나 render `_delta`로 cached velocity를 계속 적분하지 않습니다. 따라서 약 0.1×의 정직한 slow-motion world입니다. interpolation/미래 추측/신경 step 생략은 없습니다. 충돌은 벽과의 기계적 제약일 뿐 AI가 아닙니다.

Reset은 neural/world 초기조건을 재설정하되 앱 wall clock은 유지합니다. 따라서 reset 이후 HUD의 `neural / app-wall` 값은 reset 이후 throughput 측정값이 아닙니다. steady-run throughput은 telemetry의 같은 generation 구간에서 시간 차이로 측정합니다.

## 검증 / 로그

```powershell
.venv/Scripts/python.exe body/test_decoder.py
.venv/Scripts/python.exe body/launch.py --integration-test --logdir body/reports/integration --quit-after 110
.venv/Scripts/python.exe body/launch.py --logdir body/reports/clean-exit --quit-after 12
.venv/Scripts/python.exe body/analyze.py
```

integration-test는 **실제로 렌더되는 Godot**에서 `Input.parse_input_event(InputEventKey)`로 같은 debug keyboard 경로를 실행합니다. 실제 MaleCNS backend에 left/right/forward current를 넣고, 두 reset, disabled-stimulus key, launcher가 실제 brain process tree를 종료하는 failure test를 수행합니다. Mock brain이 아닙니다. Engine viewport 이미지 `arena.png`도 저장합니다. OS-level physical key injection은 Computer-use app approval timeout 때문에 별도 인증하지 못했으며 엔진의 키 이벤트 처리/IPC/neural/body 경로는 실측했습니다.

`analyze.py`는 brain packet과 body commit의 gen/seq를 연결하고 activity→decoder→yaw 및 completed neural time→world time 적분을 검사합니다. 좌우 반대 yaw, forward translation, disabled key의 current 미주입/직접 움직임 없음, 동일 seed reset readout 일치, real brain kill 후 body/world freeze, process cleanup, target RAM을 검사하고 하나라도 실패하면 비정상 종료합니다.

`brain.jsonl`은 current injection IDs/strength/duration 및 packet readout을, `godot.jsonl`은 key·packet·position·heading·world/neural/wall·FPS를 기록합니다. `resources.json`은 Python/Godot **process tree** RSS(Windows venv redirector의 실제 interpreter 자식 포함), available RAM, 종료된 PID 증거입니다. 기본 interactive logs는 `logs/latest`, 인증 실행은 `reports/integration`에 있습니다. 새 통합 reports는 부모의 scientific reports와 분리됩니다.

기본 config 성능 및 실제 결과는 `reports/certification.json` 및 `reports/DELIVERY.md`를 참고하십시오. VRAM/다른 앱 RAM은 process RSS 합계에 포함하지 않으며 16GB는 모든 앱이 공유합니다. Realtime/GPU brain 최적화는 하지 않았습니다.
