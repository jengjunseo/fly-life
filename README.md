# MaleCNS 파리 신경망 실험실 · 한글 리마스터

실제 MaleCNS 연결망의 **165,122개 뉴런**을 LIF 모형으로 계산하고, 운동 뉴런의 발화율을 기존 디코더로 해석해 Godot 파리 몸체에 전달합니다.

## 실행

준비된 개발 PC에서 이 저장소 폴더를 열고 실행합니다.

```powershell
.\run_mvp.ps1
```

한글 전체 화면, 고속 계산, **운동 뉴런 자극 · 경로 검사**가 기본입니다. 신경망 초기 안정화가 끝나면 환경시간 0.5–2.5초 동안 DNp09 뉴런에 전류 3.0을 넣습니다. 실제 발화 → 원본 디코더 → 몸체 이동을 확인하는 **인위적 신경 검사**이며, 자연 감각에서 생긴 자발적 보행의 증거가 아닙니다. 검사는 한 번 끝나고 회복을 관찰합니다. 다시 보려면 **현재 실험 초기화** 또는 **전진 뉴런 자극**을 누르세요.

자연 감각만 관찰하려면 **기본 상태 · 무자극**, **포식자 접근**, **먹이 냄새와 접촉** 등을 선택하고 **선택한 실험 시작**을 누릅니다. 현재 자연 감각만으로는 운동 출력이 거의 없거나 0일 수 있습니다. 중앙 진단에서 운동 출력 0과 계산 대기를 구분합니다.

```powershell
.\run_mvp.ps1 --preset CONTROL
.\run_mvp.ps1 --preset PREDATOR --windowed
.\run_mvp.ps1 --brain-frame-ms 10
.\run_mvp.ps1 --backend reference
.\run_mvp.ps1 --legacy
```

`--brain-frame-ms`는 10, 20, 50을 지원합니다. 기본 20밀리초는 **원본 1밀리초 적분 20회**입니다. 화면 렌더링과 신경 계산의 빈도는 별개이며, 이 PC에서 실제시간 1:1은 아직 달성하지 못했습니다. 완료된 신경 프레임만 몸체에 적용하고 실제 위치 응답을 다음 감각 입력에 사용합니다. 화면은 실제 처리율과 목표 미달을 표시합니다.

진행/정지: 스페이스 · 한 뇌 프레임: N · 초기화: R · 전체 화면: F11. 왼쪽 운동 검사 버튼은 몸체를 직접 조종하지 않고 실제 운동 뉴런을 자극합니다.

실행마다 새 로그 폴더와 별도 통신 포트를 만듭니다. **종료** 버튼은 해당 실행의 뇌·몸체 프로세스를 함께 닫습니다. `--duration`은 환경시간, `--quit-after`는 실제시간 초 단위입니다. `--logdir`에는 아직 없는 폴더를 지정합니다.

새 Windows PC에서는 Python 3.11 x64를 설치하고 다음을 실행합니다.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe mvp/setup_godot.py
.\run_mvp.ps1
```

검증된 연결망·주석 데이터가 저장소에 포함되어 있어 실행 시 원본 대용량 데이터의 재다운로드가 필요하지 않습니다. 최초 고속 실행에는 JIT 준비 시간이 추가될 수 있습니다.

## 과학적 범위와 변경

원본 [LIF 코드](braincore/core.py), 연결망 데이터, 뉴런 정체성, 부호, 가중치, PCG64 난수, 1밀리초 적분, [운동 디코더](body/decoder.py)는 보존했습니다. 고속 경로는 발화한 뉴런의 연결만 동일한 순서로 합산하고 float32 계산을 결합합니다. 감각 부호화는 반복 배열 할당을 줄였으며 원본과 동일한 입력을 생성합니다. 같은 시드·입력에서 1,000회 적분의 전체 신경 상태와 난수 상태가 원본과 정확히 같았습니다.

먹이 섭취, 구애, 자발적 도피·회피는 미검증입니다. 신경 통증과 암컷 특이 접촉 입력은 비활성입니다. 장·배설·체력은 단순 환경/생리 모형입니다. 인위적 운동 검사는 이러한 생물학적 행동의 재현을 뜻하지 않습니다. 바닥 내부 면적은 기존의 정확히 2배, 121.68 단위²를 유지합니다.

[리마스터 검증 결과](reports/remaster/RESULTS.md) · [원본 과학적 상태](SCIENTIFIC_STATUS.md) · [모델 안내](docs/BRAIN_CORE.md).

## 검증과 이전 동결판

```powershell
.venv/Scripts/python.exe -m remaster.test_all
.venv/Scripts/python.exe -m remaster.validate
.venv/Scripts/python.exe -m remaster.analyze
```

리마스터 결과는 `reports/remaster/`에 따로 저장합니다. 기존 `reports/mvp/`, 과거 인증 자료와 `male-cns-mvp-v0.1` 태그는 보존합니다. v0.1 동결 해시의 대상은 그 태그의 소스이며 현재 리마스터 소스에 같은 동결 해시를 적용하지 않습니다. 이전 실행 화면·계산 경로는 `--legacy`로 선택할 수 있습니다.

데이터: FlyEM / HHMI Janelia, Cambridge, MRC LMB, Google Research. 이 프로젝트는 실험적 연결망 기반 동물 모형이며 생물학적으로 완전한 초파리 모형은 아닙니다.