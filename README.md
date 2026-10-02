# MaleCNS 파리 신경망 실험실

실제 MaleCNS의 **165,122개 뉴런**과 시냅스 연결을 LIF 모형으로 계산해 Godot 몸체에 전달합니다. **먹이 접근·그늘 선택·성공적인 포식자 회피가 완성된 자율 동물 모형은 아닙니다.** 현재 검증에서 이 세 행동은 실패했습니다. 신경 신호의 전달과 생물학적 행동의 성공을 구분해 실험하는 도구입니다.

## 실행

준비된 개발 PC에서 저장소 폴더를 열고 실행합니다.

```powershell
.\run_mvp.ps1
```

한글 전체 화면의 **시냅스 수 기반 행동 가설 모델**과 기본 환경으로 시작합니다. 전뇌 기저 전류 1.5라는 **각성 가정**에 의해 운동 뉴런이 발화하고 보행합니다. 이 조건은 실제 각성 회로나 자연스러운 자발 활동을 규명한 결과가 아닙니다. 기본 실행에 시간표에 따른 운동 뉴런 자극은 없습니다.

왼쪽 **신경 모델과 대조 조건**에서 기저 전류, 기존 v0.1 모델, 감각 입력 차단, GF 뉴런 차단을 선택할 수 있습니다. **모델 조건 적용**은 초기화합니다. **감각 입력**과 **GF 차단**은 선택한 실험·초기화 뒤에도 유지됩니다. 조건을 바꾸고 초기화한 뒤 같은 시드로 비교하세요.

**포식자 접근**, **왼쪽/오른쪽 먹이**, **왼쪽/오른쪽 그늘**을 선택하고 **선택한 실험 시작**을 누릅니다. 가설 모델은 환경시간 2초 후 자극을 제시하며 먹이·열 자극을 오래 유지합니다. 먹이를 파리 위치에 바로 놓는 과거 접촉 시험과 구분합니다. 중앙에 거리·국소 온도·그늘 체류·누적 경로를 표시합니다. 포식자 접근 시 GF 신호로 원시 도약이 발생하지만, 현재 실험에서는 생존에 성공하지 못했습니다.

```powershell
.\run_mvp.ps1 --preset PREDATOR
.\run_mvp.ps1 --preset "FOOD RIGHT" --windowed
.\run_mvp.ps1 --preset HEAT --no-sensory
.\run_mvp.ps1 --preset PREDATOR --no-gf
.\run_mvp.ps1 --tonic-current 0
.\run_mvp.ps1 --model frozen
.\run_mvp.ps1 --model frozen --backend reference
.\run_mvp.ps1 --model frozen --preset "MOTOR TEST"
.\run_mvp.ps1 --legacy
```

기존 v0.1 모델은 자연 감각만으로 운동 출력이 거의 없거나 0일 수 있습니다. **운동 뉴런 자극 · 경로 검사**와 수동 전진/좌우 검사 버튼은 실제 운동 뉴런에 전류를 넣는 **인위적 신경 자극**입니다. 자연 행동의 증거가 아닙니다.

진행/정지: 스페이스 · 한 뇌 프레임: N · 초기화: R · 전체 화면: F11. 기본 뇌 프레임 20밀리초는 **1밀리초 적분 20회**이며 `--brain-frame-ms 10/20/50`을 지원합니다. 실제시간 1:1은 아직 달성하지 못했습니다. 완료된 신경 프레임만 몸체에 적용하고, 실제 위치 응답으로 다음 감각을 계산합니다.

실행마다 새 로그 폴더와 통신 포트를 만듭니다. **종료**는 해당 실행의 뇌·몸체를 함께 닫습니다. `--duration`은 환경시간, `--quit-after`는 실제시간 초입니다. `--logdir`에는 아직 없는 폴더를 지정합니다.

## 설치와 연결 복원

새 Windows PC에서 Python 3.11 x64를 설치하고 다음을 실행합니다.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe mvp/setup_godot.py
.\run_mvp.ps1
```

기존 검증 연결망이 저장소에 포함되어 있어 기본 실행에 대용량 원본 다운로드가 필요하지 않습니다. 작은 시냅스까지 복원한 그래프는 별도로 생성합니다. 개발 PC에서는 이미 준비되어 있습니다.

```powershell
# 원본 파일이 없는 PC에서만 다운로드 (약 1.1 GB)
.venv/Scripts/python.exe acquire.py
.venv/Scripts/python.exe -m behavior.prepare
.\run_mvp.ps1 --restore-weak
```

복원은 `data/behavior/`에 약 2,556만 개 연결을 저장하며 기존 `data/runtime/`를 덮어쓰지 않습니다. 생성된 대용량 파일은 Git에서 제외합니다. 복원·재정규화만으로 원하는 자율 행동이 해결되지는 않았습니다.

## 모델과 검증 범위

기존 [LIF 코드](braincore/core.py), [고정 모델 설정](config.json), 연결 데이터, [운동 디코더](body/decoder.py), 인증 자료와 `male-cns-mvp-v0.1` 태그는 보존했습니다. `--model frozen`의 고속 경로는 이전에 원본과 1,000회 적분의 전체 상태 및 난수 상태 일치를 검증했습니다. **이 동일성은 새 행동 가설 모델에 적용되지 않습니다.**

가설 모델은 같은 뉴런 정체성·연결 방향·전달물질 부호를 사용하지만, 입력 합 정규화 대신 시냅스 수, 별도 전달 강도, 균일한 기저 구동, 발화 시 시냅스 상태 초기화를 사용합니다. 좌우 감각 입력과 그늘 주변 공기 냉각은 명시적인 모형 가정입니다. 정확한 망막 수용장, 배고픔 조절, 학습된 냄새/열 가치, 수용체별 동역학, 완전한 비행·다리 운동은 구현하지 않았습니다. 먹이 입력은 냄새이며 먹이 시각 인식은 구현하지 않았습니다.

```powershell
.venv/Scripts/python.exe -m behavior.test_all
.venv/Scripts/python.exe -m behavior.run_assays
```

새 결과는 `reports/behavior/`에 저장합니다. 원본 회귀와 신규 검사 **49개 통과**, 실제 Godot의 **13개 대조 실험**에서 통신·시간·프로세스 정리가 통과했습니다. GF 도약의 감각/GF 의존성은 확인했으나 먹이 접근·그늘 선택·포식자 피해 감소는 실패했습니다. 소프트웨어 검사 통과를 생물학 인증으로 해석하지 않습니다.

[현재 행동 검증 결과](BEHAVIOR_STATUS.md) · [실험 원자료](reports/behavior/assays/results.json) · [이전 리마스터 검증](reports/remaster/RESULTS.md) · [기존 과학적 상태](SCIENTIFIC_STATUS.md).

먹이 섭취·구애·신경 통증은 미검증/비활성입니다. 장·배설·체력은 단순 환경/생리 모형입니다. 바닥 내부 면적 121.68 단위²를 유지합니다. 데이터: FlyEM / HHMI Janelia, Cambridge, MRC LMB, Google Research, CC-BY-4.0.
