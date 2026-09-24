"""User-facing Korean result from actual certification values, no invented metrics."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports/ecology'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__=='__main__':
    c=read(R/'certification.json');m=c['measurements'];machine=read(R/'live/baseline_mapping.json')['machine'];mapping=read(R/'live/sensory_mapping.json')['actual']
    if not c['success']:raise SystemExit('Cannot deliver a failed certification as success')
    loop=c['closed_loop_feedback_examples'][0];thermal=read(R/'thermal-integration.json');baseline=read(R/'baseline.json')
    proof=[('BASELINE','UNIT + INTEGRATION','baseline.json','기존 13개 테스트 통과. 원래 파일/보고서 보존'),
        ('WORLD','LIVE / EXPERIMENTAL','live/events.jsonl','food·predator·female·heat·feces 실제 primitive 및 수명/접촉'),
        ('SENSORYMAPPING','INTEGRATION / VERIFIED IDENTITY','live/sensory_mapping.json','실제 MaleCNS IDs/alias; encoding 자체는 실험적'),
        ('NOSHORTCUT','STATIC + LIVE + INTEGRATION','certification.json','current target·encoder·기존 decoder·body packet·ACK 연결 검사'),
        ('PREDATORCLOSEDLOOP','LIVE / EXPERIMENTAL','live/brain.jsonl','LC4/LPLC2 입력 + LC9 figure 감각→DNp09→몸체→다음 geometry'),
        ('FOOD','LIVE / EXPERIMENTAL BYPASS / DISABLED','live/world.jsonl','ORN_DM1 및 CNS Sugar-SEL PN 입력. 섭식 gate 미해결/비활성'),
        ('THERMAL','LIVE HEAT + INTEGRATION SHADE','thermal-integration.json','local heat current; shade 비교는 테스트 초기 위치, 이동 행동 아님'),
        ('FEMALE','LIVE ORN / CONTACT DISABLED','live/brain.jsonl','비성별특이적 fly odor→ORN_VA1v/d. pC1 관찰만'),
        ('DAMAGE','LIVE HP + UNIT DEATH / PAIN DISABLED','live/events.jsonl','sphere-overlap 기반 3 hit. 신경성 pain 미해결'),
        ('DEFECATION','LIVE / PHYSIOLOGY_PLACEHOLDER','live/events.jsonl','초기 gut load→seed latency→gut 감소/갈색 primitive'),
        ('TIME','LIVE','live/godot.jsonl','50ms 완료 neural packet만 몸체 진행; ACK만 world 진행'),
        ('DETERMINISM','LIVE REPLAY + UNIT RANDOM SCHEDULE','replay/brain.jsonl','세 세대 60 packet씩 감각/current/readout/motor/pose 완전 동일'),
        ('FAILURE_FREEZE','LIVE ACTUAL PROCESS FAILURE','replay/godot.jsonl','실제 brain tree 종료 후 몸체/world clock 동결'),
        ('RESOURCE','LIVE PROCESS TREE RSS','live/resources.json','모든 검증 run의 combined RSS<16GiB, 종료 후 소유 PID 없음'),
        ('CLEAN_EXIT','LIVE','live/brain_exit.json','정상 세 run 양쪽 exit code 0')]
    text=f'''# 3단계 — MaleCNS seeded 3D 생태계 결과

화면에는 기존 작은 초파리, 녹색 food, 빨간 predator, 다른 색의 female, shade 영역과 갈색 feces primitive가 나타난다. 키 입력 없이 예정된 사건이 발생하고, predator 접근 중 **실제 neural output으로 몸체가 {m['body_distance_units']:.6f} world unit 전진**했다. 회전 readout은 0이었으며, 회피/추격/먹이 탐색 성공을 주장하지 않는다. Predator가 접근해 HP를 감소시킨다. Heat 입력은 34C까지 올라간다. 배설은 명확한 physiology placeholder다.

## 감각→neural→몸체→다음 감각의 실제 증거

LC4/LPLC2-only scout의 3/6/10 current는 GF에는 반응을 만들었지만 기존 locomotor groups는 발화하지 않았다. 이를 GF escape body 동작으로 대체하지 않았다. 실제 topology 조사에서 LC9 figure group→DNp09의 **1,904 retained contacts**를 확인했다. Figure motion은 별도의 실험적 sensory 입력이며 도망 rule이나 DNp09 직접 stimulus가 아니다.

Live peak bilateral DNp09 readout **{m['peak_forward_group_hz']:.6f}Hz**, decoder forward **{m['peak_forward']:.6f}**. Existing DNa left/right readout은 **0/0Hz**, yaw change도 0이었다. All-sensory-off 및 predator 제거 대조는 각 3 world seconds/60 packets에서 motor와 displacement가 0이었다. 따라서 이 조건의 작은 이동은 predator를 포함한 감각 경로에 의존하지만 생물학적 escape reconstruction으로 해석하지 않는다.

대표 연결: source packet `{loop['source_seq']}`→Godot 몸체 위치 `{loop['actual_body_position']}`→ACK world t={loop['world_time_s']:.2f}s→다음 packet `{loop['next_seq']}` 감각 source `{loop['next_sensor_source_seq']}`. 같은 다음 predator 위치에서 실제 이동한 몸체로 계산한 angular size는 {loop['actual_angular_size_deg']:.8f}deg, 이전 몸체 위치를 고정한 counterfactual은 {loop['frozen_body_counterfactual_size_deg']:.8f}deg로 다르다. 자세한 current/geometry 변화는 [certification.json](certification.json)의 `closed_loop_feedback_examples`에 연결되어 있다. 이는 형상 feedback의 실제 증거이지 행동 성공 증거가 아니다.

## 실제 mappings / 미해결 항목

| 입력/관찰 | 실제 MaleCNS group | 수 | 수준 |
|---|---|---:|---|
| expansion / expanding size | LC4 / LPLC2 | 126 / 185 | identity VERIFIED, encoding EXPERIMENTAL |
| figure edge motion | LC9 | 219 | EXPERIMENTAL, escape reconstruction 아님 |
| food odor | ORN_DM1 | 74 | 실제 upstream ORN, generic odor 모델 |
| contact sugar | GNG540, Sugar SEL PN alias | 2 | EXPERIMENTAL CNS BYPASS, peripheral GRN 아님 |
| fly odor | ORN_VA1v / ORN_VA1d | 262 | 실제 ORN, female-specific cue 아님 |
| hot / cold | TRN_VP2 / TRN_VP3a+b | 7 / 7 | 실제 thermosensory afferents, 전달식 EXPERIMENTAL |
| feeding 관찰 | GNG588 / Fdg alias | 2 | 관찰만; functional gate DISABLED_UNRESOLVED |
| courtship 관찰 | ^pC1 family | 156 | 관찰만, central 직접 입력 없음 |

모든 IDs·측면·annotation·NT는 [mapping](live/sensory_mapping.json), 후보/negative topology는 [research](research/mapping-research.json), 원문 근거와 encoder 가정은 [README](../../ecology/README.md)에 있다. Bilateral visual pooling은 실제 somaSide만 확인했으며 receptive-field retinotopy는 확인되지 않아 방향성 steering mapping을 만들지 않았다. GNG540 alias의 serotonergic literature와 실제 preserved acetylcholine consensus_nt 차이도 기록하고 **sign policy는 변경하지 않았다**.

실제 food-odor/contact current는 들어갔지만 Fdg 최대 activity는 **{m['max_Fdg_hz']:.2f}Hz**였다. 기능적 feeding gate가 인증되지 않아 ingestion은 **DISABLED_UNRESOLVED**다. Food collision로 자동 섭식하지 않는다. Hunger는 {35:.2f}→{m['final_hunger']:.2f}, gut는 test initial 75→{m['final_gut']:.2f}로 변했다. Hunger neural modulation/food targeting은 없다.

Local temperature는 live 최대 **{m['max_temperature_c']:.1f}C**. 실제 같은 brain mapping의 테스트 초기조건 비교에서 hot {thermal['hot_c']:.1f}C/current {thermal['hot_current']:.2f}, shade {thermal['shade_c']:.1f}C/current {thermal['shade_current']:.2f}였다. Shade 방향을 입력하거나 몸체를 shade로 움직이지 않았다. 이 비교는 **INTEGRATION_INITIAL_CONDITIONS_NOT_BEHAVIOR**이며 shade seeking은 미인증이다.

Female spawn/contact 및 ORN 입력은 실제 로그에 있으며 pC1-family peak {m['max_pC1_family_hz']:.4f}Hz는 관찰값이다. Female 추격/courtship을 주장하지 않는다. `putative_ppk23` annotation만으로 특정 female-responsive afferents를 정하지 않았으므로 contact neural mapping은 비활성이다.

실제 geometric hit {m['damage_events']}회 ×12로 **HP 100→{m['final_hp']:.0f}**. Hit가 escape command를 만들지 않는다. Neural pain은 adult mapping 미해결로 비활성이다. Death stop은 UNIT 수준으로만 검증했다. Defecation은 gut threshold→seeded latency→gut drop/feces sphere의 **LIVE PHYSIOLOGY_PLACEHOLDER**이며 adult 신경성 배설 circuit으로 인증하지 않는다. Ingestion-disabled 상태를 숨기지 않고 test initial gut=75를 사용했다. Interactive initial gut=0이다.

## 자동 실행 / 시간 / 자원

Live 자동 cert run은 키보드 없이 **{m['world_s']:.2f}s world**, **{m['neural_s']:.2f}s neural**(500ms warm-up 포함)을 수행했다. World seed=20260914, brain seed=20260913. 세 generation의 60개 완료 packet씩 **총 180개** 감각/current/neural readout/motor/pose trajectory와 초기 schedule이 정확히 같다. Irregular interactive scheduler는 별도로 UNIT 수준에서 seed·선샘플링을 검증했다; fast live cert는 설정된 강제 initial events와 seeded defecation latency다. Random interactive life 전체를 장시간 live-certified했다고 쓰지 않는다.

50ms neural quantum당 50개의 실제 1ms step을 모두 계산하며, 기존 motor decoder→원래 Godot movement commit→실제 pose ACK 순으로만 다음 world가 진행된다. `_delta`/wall clock은 rendering·heartbeat·timeout·종료용이고 ecology time을 증가시키지 않는다. NPC/물체 시각 state는 input snapshot 기준 한 quantum 지연이며 prediction/extrapolation은 없다. 실제 brain process 종료 뒤 body/world freeze와 owned-tree 정리가 검증됐다.

실제 장비 **{machine['cpu']}**, {machine['physical_cores']}C/{machine['logical_cores']}T, RAM {machine['total_ram_bytes']/1024**3:.2f}GiB. Brain은 CPU이고 Radeon RX570은 Godot rendering에만 사용했다. Steady post-warm-up throughput **{m['post_warmup_neural_wall_ratio']:.5f}×**, motor packet rate **{m['motor_packet_hz']:.3f}Hz**, Godot median **{m['godot_fps_median']:.0f}FPS**. 이는 realtime brain이 아니라 느린 neural-time world다. Peak sampled Python tree RSS **{m['peak_python_rss']/1024**3:.3f}GiB**, Godot **{m['peak_godot_rss']/1024**3:.3f}GiB**, combined **{m['peak_combined_rss']/1024**3:.3f}GiB**. 정상 세 run은 both exit code=0, failure test는 의도적인 process termination이며 모든 run의 remaining owned PID=[]다. Process-tree 측정은 Windows venv redirector의 실제 interpreter child를 포함한다. CPU percent는 별도로 측정하지 않았으며 core step wall time은 `brain_exit.json`에 있다.

## Baseline / Claim certification

기존 LIF·signed/pruned matrix·decoder·body movement·configs·원래 launcher/project와 scientific/body reports를 편집하지 않았다. {baseline['preexisting_files_checked']}개 기존 Git baseline 파일의 content가 보존됐고 기존 **13개 UNIT/INTEGRATION**, 새 **12개 UNIT/INTEGRATION** 테스트가 통과했다. 두 기존 console log의 inherited CRLF working-tree/LF Git-object 차이는 [baseline](baseline.json)에 분리 기록했으며 원래 보고서를 다시 쓰지 않았다. 새 ecology transport의 lockstep ACK와 종료 grace만 별도 extension에 있다.

| Claim | 인증 수준 | 실제 evidence | 해석 |
|---|---|---|---|
'''
    for name,level,path,note in proof:
        text+=f"| {name} — {'PASS' if c['checks'][name] else 'FAIL'} | {level} | [{path}]({path}) | {note} |\n"
    text+='''
## Certification Debt / 종료 범위

실제 추가 기능은 food, predator, damage/HP/death, female, heat/shade, hunger/gut와 명시적 placeholder defecation뿐이다. 실제 환경 입력→MaleCNS→기존 decoder→Godot 몸체→다음 geometry의 최소 loop가 확인되어 이 범위에서 종료한다. 회피·먹이 찾기·섭식·그늘 찾기·courtship·adult neural defecation·peripheral taste transduction·근육/비행 mechanics는 인증하지 않았다. NT ambiguity 및 bilaterally pooled visual receptive fields도 부채로 남긴다. 실제 OS keyboard 조작/스크린 capture를 했다고 주장하지 않으며 screenshots는 live Godot viewport다. 그래픽 polish, gain을 원하는 행동 방향에 맞춘 탐색, backend rewrite, 추가 생태계 기능은 하지 않았다.

실행: brain-core에서 `.venv/Scripts/python.exe ecology/launch.py --life-run`.
'''
    (R/'DELIVERY.md').write_text(text,encoding='utf-8')
    files=list((ROOT/'ecology').glob('*.py'))+[ROOT/'ecology/config.json',ROOT/'ecology/README.md']+list((ROOT/'body/ecology').glob('*'))
    (R/'source_sha256.json').write_text(json.dumps({str(p.relative_to(ROOT)):digest(p) for p in files if p.is_file()},indent=2))
    print('DELIVERY.md and final source hashes written from certified evidence')
