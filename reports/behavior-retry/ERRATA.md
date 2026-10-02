# 탐색 보고서 해석과 정정

탐색 중의 실패와 원자료를 지우지 않았습니다. `first-food-left`는 회전 출력이 부족하고 자기 이동을 위협 확대 신호로 잘못 읽었던 **실패 모델**입니다. `calibrated-food-left`와 `assays`는 회전 보정과 자기 이동 보상 후의 모델입니다. 서로 같은 파라미터의 반복 실험으로 합산하면 안 됩니다.

`visual-kc-probe.json`의 `opponent_warm_R` 조건에는 당시 진단 스크립트의 누락으로 오른쪽 냉각 TRN 억제가 적용되지 않았습니다. 따라서 이 조건은 좌우 대칭의 열 자극 대조로 사용할 수 없습니다. 생산 감각 인코더에는 이 진단 오류가 없었습니다. 이후 `strong-transfer-probe`, `thermal-dopamine-probe`, `sparse-background-probe`, `thermal-pathway-probe`, `restored-thermal-pathway-probe`는 좌우 모두 가열 흥분/냉각 억제를 적용했습니다. 원본 탐색 보고서는 보존했습니다.

초기 새 모델의 `model-generation-*.json`에는 KC 기저 전류가 0.85임을 `evidence.excitability_profile`에 기록하면서 공통 설명은 균일한 기저 전류라고 적혀 있었습니다. 새 런타임은 모델별 가정을 구분하고 소스 SHA-256도 기록합니다. 초기 원자료의 잘못된 설명을 자연 자발 활동의 증거로 해석하면 안 됩니다.

`model-controls`에서 모델 전환·감각 차단 유지 검사는 통과했지만 종료 시 Windows TCP 중단 오류로 뇌 프로세스 종료 코드가 1이었습니다. 따라서 이 실행 전체를 소프트웨어 성공으로 집계하지 않습니다. 종료 요청을 보낸 후 뇌가 연결을 닫을 때까지 몸체가 연결을 유지하도록 수정하고 `model-controls-final`에서 다시 검사했습니다.

배경 구동·KC 역치·시냅스 강도·열 수용체 가설·항상성 보정·약한 연결 복원을 탐색했습니다. 최종 모델에 채택하지 않은 탐색 조건도 실패 근거로 보존했습니다. 한쪽 회전이나 배경 발화 증가를 열 회피 성공으로 판정하지 않습니다.

초기 `thermal-pathway-probe`와 `restored-thermal-pathway-probe`의 LHAD1 그룹은 정확히 `LHAD1`인 타입만 선택해 0개였습니다. 이것을 MaleCNS에 경로가 없다는 근거로 사용할 수 없습니다. `pathway-audit.json`은 타입/hemibrainType의 LHAD1 계열을 확인하되 LHAD10/11 등의 숫자 접두사 중복은 제외합니다.
