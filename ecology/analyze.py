"""Evidence-backed certification: fail loudly, never promote absence to success."""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1];REPORT=ROOT/'reports/ecology';sys.path.insert(0,str(ROOT/'body'));sys.path.insert(0,str(ROOT/'ecology'))
from decoder import decode
from sensory import amplitudes
from model import distance

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def rows(path):return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s]
def ready(folder):return [r for r in rows(folder/'brain.jsonl') if r.get('kind')=='state' and r['status']=='ready' and r['dt_s']>0]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def check(condition):return bool(condition)

def canonical_frames(frames):
    return [dict(neural_time_s=f['neural_time_s'],motor_time_s=f['motor_time_s'],dt_s=f['dt_s'],activity_hz=f['activity_hz'],
        forward=f['forward'],turn=f['turn'],population_hz=f['population_hz'],world=f['ecology']['world'],sensory_terms=f['ecology']['sensory_terms'],readouts_hz=f['ecology']['readouts_hz']) for f in frames]

def certify():
    live=REPORT/'live';replay=REPORT/'replay';off=REPORT/'sensory-off';no_pred=REPORT/'without-predator'
    frames=ready(live);logs=rows(live/'godot.jsonl');world=rows(live/'world.jsonl');events=rows(live/'events.jsonl')
    cfg=read(live/'ecology_config.json');bodycfg=read(live/'body_runtime_config.json');mapping=read(live/'sensory_mapping.json')
    source={f['seq']:f for f in frames};snapshots={r['source_seq']:r for r in world};commits=[r for r in logs if r['event']=='body_commit']
    checks={};checks['BASELINE']=read(REPORT/'baseline.json')['success']
    checks['WORLD']=set(e['event'] for e in events)>={'FOOD_SPAWN','FOOD_CONTACT','FOOD_DESPAWN','PREDATOR_SPAWN','PREDATOR_HIT','PREDATOR_DESPAWN','FEMALE_SPAWN','FEMALE_CONTACT','FEMALE_DESPAWN','HEAT_START','HEAT_END','DEFECATE'}
    checks['SENSORYMAPPING']=mapping['dataset']=='male-cns:v1.0' and all(v['members'] for v in mapping['actual'].values()) and read(REPORT/'tests.json')['success']
    forbidden=set()
    for name in ['feeding_observation','courtship_observation']:forbidden.update(m['bodyId'] for m in mapping['actual'][name]['members'])
    for members in read(live/'baseline_mapping.json')['actual_groups'].values():forbidden.update(m['bodyId'] for m in members)
    sensory_targets_ok=all(not forbidden.intersection(term['bodyIds']) for f in frames for term in f['ecology']['sensory_terms'])
    encoder_ok=all(all(np.isclose(term['amplitude'],amplitudes(f['ecology']['world']['raw_sensors'],cfg['sensory'])[term['modality']]) for term in f['ecology']['sensory_terms']) for f in frames)
    decoder_ok=all(all(np.isclose(f[k],decode(f['activity_hz'],bodycfg['decoder'])[k]) for k in ['forward','turn']) for f in frames)
    body_link_ok=len(commits)==len(frames) and all(c['source_seq'] in source and np.isclose(c['world_time_s'],source[c['source_seq']]['motor_time_s']) and
        np.isclose(c['decoder_forward'],source[c['source_seq']]['forward']) and np.isclose(c['decoder_turn'],source[c['source_seq']]['turn']) and
        np.allclose(c['position'],snapshots[c['source_seq']]['fly_position']) for c in commits)
    python_source=(ROOT/'ecology/sensory.py').read_text();godot_source=(ROOT/'body/ecology/main.gd').read_text();world_source=(ROOT/'ecology/model.py').read_text()
    static_ok=all(token not in python_source+world_source for token in ['forward_gain','max_forward_units','max_turn_radians','move_and_collide']) and 'fly.position =' not in godot_source and 'move_and_collide' not in godot_source
    no_debug=not any(r['event'] in ['key','world_event_key'] for r in logs) and not any(r.get('event')=='debug_current_injection' for r in rows(live/'brain.jsonl'))
    checks['NOSHORTCUT']=sensory_targets_ok and encoder_ok and decoder_ok and body_link_ok and static_ok and no_debug
    feedback=[]
    for i,f in enumerate(frames[:-1]):
        if f['forward']<=0:continue
        before=f['ecology']['world'];after=snapshots[f['seq']]
        for entity in after['entities']:
            if entity['kind']!='predator':continue
            moving=math.degrees(2*math.atan2(entity['radius'],max(distance(after['fly_position'],entity['position']),1e-6)))
            frozen=math.degrees(2*math.atan2(entity['radius'],max(distance(before['fly_position'],entity['position']),1e-6)))
            if abs(moving-frozen)>1e-6:
                nxt=frames[i+1]
                feedback.append(dict(source_seq=f['seq'],next_seq=nxt['seq'],world_time_s=after['world_time_s'],prior_position=before['fly_position'],
                    actual_body_position=after['fly_position'],predator_position=entity['position'],actual_angular_size_deg=moving,
                    frozen_body_counterfactual_size_deg=frozen,difference_deg=moving-frozen,next_sensor_source_seq=nxt['ecology']['sensor_source_body_seq'],
                    next_figures=nxt['ecology']['world']['raw_sensors']['figures'],next_sensory_currents={t['modality']:t['amplitude'] for t in nxt['ecology']['sensory_terms']}))
    off_frames=ready(off);np_frames=ready(no_pred)
    motion=distance(world[0]['fly_position'],world[-1]['fly_position'])
    checks['PREDATORCLOSEDLOOP']=(motion>1e-5 and bool(feedback) and max(f['forward'] for f in frames)>0 and
        all(f['forward']==0 and f['turn']==0 for f in off_frames+np_frames) and len(off_frames)==60 and len(np_frames)==60 and
        all(r['next_sensor_source_seq']==r['source_seq'] for r in feedback) and
        any(t['modality']=='lc4' and t['amplitude']>0 for f in frames for t in f['ecology']['sensory_terms']) and any(t['modality']=='lplc2' and t['amplitude']>0 for f in frames for t in f['ecology']['sensory_terms']))
    checks['FOOD']=not cfg['food']['ingestion_enabled'] and not any(e['event']=='FOOD_INGEST' for e in events) and all(
        any(t['modality']==name and t['amplitude']>0 for f in frames for t in f['ecology']['sensory_terms']) for name in ['food_odor','taste'])
    checks['THERMAL']=read(REPORT/'thermal-integration.json')['hot_current']>read(REPORT/'thermal-integration.json')['shade_current'] and any(t['modality']=='hot' and t['amplitude']>0 for f in frames for t in f['ecology']['sensory_terms']) and not any('shade' in k for k in frames[0]['ecology']['world']['raw_sensors'])
    checks['FEMALE']=any(t['modality']=='fly_odor' and t['amplitude']>0 for f in frames for t in f['ecology']['sensory_terms']) and not cfg['sensory']['female_contact_enabled']
    damage=[e for e in events if e['event']=='DAMAGE'];checks['DAMAGE']=bool(damage) and world[-1]['hp']==cfg['initial_hp']-sum(e['amount'] for e in damage) and not cfg['sensory']['pain_enabled']
    checks['DEFECATION']=all(e['classification']=='PHYSIOLOGY_PLACEHOLDER' for e in events if e['event']=='DEFECATE') and any(e['event']=='DEFECATE' for e in events)
    checks['TIME']=len(commits)==60 and all(np.isclose(f['dt_s'],.05) and np.isclose(f['motor_time_s']-.05,f['ecology']['sensory_time_s']) for f in frames) and all(np.isclose(r['neural_time_s']-.5,r['world_time_s']) for r in world)
    rp=ready(replay);groups=[[f for f in rp if f['generation']==g] for g in [1,2,3]]
    schedules=[read(replay/f'schedule-generation-{g}.json') for g in [1,2,3]]
    checks['DETERMINISM']=all(len(g)==60 for g in groups) and canonical_frames(groups[0])==canonical_frames(groups[1])==canonical_frames(groups[2]) and schedules[0]==schedules[1]==schedules[2]
    rp_logs=rows(replay/'godot.jsonl');marker=next(i for i,r in enumerate(rp_logs) if r['event']=='ecology_ready_for_failure')
    tail=[r for r in rp_logs[marker+1:] if r['event']=='sample'];anchor=rp_logs[marker]
    resources=read(replay/'resources.json')
    checks['FAILURE_FREEZE']=resources['real_brain_terminated_for_failure_test'] and len(tail)>=3 and all(r['position']==anchor['position'] and r['world_time_s']==anchor['world_time_s'] for r in tail) and any(r['connection']!='ready' for r in tail)
    runs=[live,replay,off,no_pred];rs=[read(p/'resources.json') for p in runs]
    checks['RESOURCE']=all(r['peak_combined_rss']<16*1024**3 and not r['remaining_owned_pids'] and r['process_tree_rss'] for r in rs)
    checks['CLEAN_EXIT']=all(read(p/'resources.json')['brain_exit_code']==0 and read(p/'resources.json')['godot_exit_code']==0 for p in [live,off,no_pred])
    wall=frames[-1]['wall_time_s']-frames[0]['wall_time_s'];neural=frames[-1]['motor_time_s']-frames[0]['motor_time_s']
    data=dict(success=all(checks.values()),checks={k:check(v) for k,v in checks.items()},levels=dict(BASELINE='13 UNIT/INTEGRATION + original certificates preserved',WORLD='LIVE_EXPERIMENTAL_WORLD',SENSORYMAPPING='INTEGRATION_VERIFIED_IDENTITIES_EXPERIMENTAL_ENCODING',NOSHORTCUT='STATIC_AND_LIVE',PREDATORCLOSEDLOOP='LIVE_EXPERIMENTAL_LC9_FIGURE_PATH_PLUS_LC4_LPLC2',FOOD='LIVE_ORN_AND_EXPERIMENTAL_CNS_TASTE_BYPASS; INGESTION_DISABLED',THERMAL='LIVE_HEAT_AND_REAL_MAPPING_INTEGRATION_SHADE_NOT_BEHAVIOR',FEMALE='LIVE_NON_SEX_SPECIFIC_ORN; CONTACT_DISABLED',DAMAGE='LIVE_HP; PAIN_DISABLED; DEATH_UNIT',DEFECATION='LIVE_PHYSIOLOGY_PLACEHOLDER',TIME='LIVE_50MS_LOCKSTEP',DETERMINISM='LIVE_3_GENERATION_EXACT_REPLAY',RESOURCE='LIVE_PROCESS_TREES'),
        measurements=dict(world_s=world[-1]['world_time_s'],neural_s=frames[-1]['neural_time_s'],body_distance_units=motion,peak_forward=max(f['forward'] for f in frames),
            peak_forward_group_hz=max(f['activity_hz']['forward'] for f in frames),peak_left_hz=max(f['activity_hz']['left'] for f in frames),peak_right_hz=max(f['activity_hz']['right'] for f in frames),
            post_warmup_neural_wall_ratio=neural/wall,motor_packet_hz=(len(frames)-1)/wall,godot_fps_median=float(np.median([r['fps'] for r in logs if r['event']=='sample' and r['world_time_s']>.3])),
            peak_python_rss=rs[0]['peak_python_rss'],peak_godot_rss=rs[0]['peak_godot_rss'],peak_combined_rss=rs[0]['peak_combined_rss'],final_hp=world[-1]['hp'],damage_events=len(damage),
            final_hunger=world[-1]['hunger'],final_gut=world[-1]['gut'],max_temperature_c=max(r['local_temperature_c'] for r in world),
            max_Fdg_hz=max(f['ecology']['readouts_hz']['feeding_observation'] for f in frames),max_pC1_family_hz=max(f['ecology']['readouts_hz']['courtship_observation'] for f in frames),
            sensory_off_peak_motor=max(f['forward'] for f in off_frames),without_predator_peak_motor=max(f['forward'] for f in np_frames)),
        closed_loop_feedback_examples=feedback[:8],all_run_resources={p.name:{k:v for k,v in r.items() if k!='samples'} for p,r in zip(runs,rs)},
        limitations=['LC4/LPLC2 alone did not recruit original locomotor readouts in bounded scouts; GF activity is not body escape.',
            'Motion in life run uses experimental LC9 figure-motion encoding through real LC9->DNp09 contacts; not calibrated escape.',
            'Food finding, escape, shade seeking and courtship behavior are not claimed.', 'Sugar-SEL PN bypass is not a reconstructed peripheral sweet-GRN transducer.',
            'Fdg observed but no certified functional feeding gate: ingestion disabled.', 'Defecation is non-neural physiology placeholder with initial gut load, not evidence of adult defecation connectomics.',
            'Local temperature encoding is experimental; shade comparison relocates only test initial conditions.', 'No physical OS keyboard injection was needed or claimed.'],
        evidence_files={str(p.relative_to(REPORT)):digest(p) for p in (
            [REPORT/'tests.json',REPORT/'baseline.json',REPORT/'thermal-integration.json',REPORT/'topology.json']+
            [p/name for p in runs for name in ['brain.jsonl','godot.jsonl','world.jsonl','events.jsonl','resources.json','ecology_config.json','body_runtime_config.json']]+
            [live/'sensory_mapping.json',live/'baseline_mapping.json']+[replay/f'schedule-generation-{g}.json' for g in [1,2,3]])})
    (REPORT/'certification.json').write_text(json.dumps(data,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in data.items() if k in ['success','checks','measurements']},indent=2));return data

if __name__=='__main__':raise SystemExit(0 if certify()['success'] else 1)
