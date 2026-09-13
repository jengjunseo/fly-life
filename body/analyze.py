"""Certify continuous evidence from real Godot and MaleCNS logs, not screenshots alone."""
import hashlib
import json
import math
import subprocess
from pathlib import Path

from decoder import decode

ROOT=Path(__file__).parent
DIR=ROOT/'reports/integration'


def rows(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
g=rows(DIR/'godot.jsonl'); b=rows(DIR/'brain.jsonl')
resources=json.loads((DIR/'resources.json').read_text())
mapping=json.loads((DIR/'baseline_mapping.json').read_text())
cfg=mapping['body_config']
states={(x['generation'],x['seq']):x for x in b if x.get('kind')=='state'}
commits=[x for x in g if x['event']=='body_commit']
markers={x['event']:x for x in g if x['event'].startswith('test_')}
checks={}
checks['actual_real_dataset_loaded']=mapping['dataset']=='male-cns:v1.0' and mapping['brain_config']['dataset']=='male-cns:v1.0'
checks['one_neural_movement_path']= (ROOT/'main.gd').read_text(encoding='utf-8').count('fly.move_and_collide(')==1
keycode=(ROOT/'main.gd').read_text(encoding='utf-8').split('func _unhandled_key_input')[1].split('func _process')[0]
checks['keyboard_contains_no_body_mutation']=all(x not in keycode for x in ['fly.','velocity =','rotation =','position ='])
checks['every_body_commit_has_real_brain_source']=all((x['generation'],x['source_seq']) in states for x in commits)
checks['decoder_reads_only_real_neural_activity']=all(
    abs(x['decoder_turn']-decode(states[(x['generation'],x['source_seq'])]['activity_hz'],cfg['decoder'])['turn'])<1e-7 and
    abs(x['decoder_forward']-decode(states[(x['generation'],x['source_seq'])]['activity_hz'],cfg['decoder'])['forward'])<1e-7 for x in commits)
checks['world_equals_completed_neural_motor_time']=all(abs(x['world_time_s']-states[(x['generation'],x['source_seq'])]['motor_time_s'])<1e-6 for x in commits)
checks['heading_integrates_only_neural_turn']=True
previous={}
for x in commits:
    old=previous.get(x['generation'],0.)
    expected=old-x['decoder_turn']*cfg['body']['max_turn_radians_per_neural_second']*x['neural_dt_s']
    if abs(expected-x['heading_yaw_radians'])>2e-6: checks['heading_integrates_only_neural_turn']=False
    previous[x['generation']]=x['heading_yaw_radians']

metrics={}
for name,start,end in [('left','test_left_start','test_right_start'),('right','test_right_start','test_forward_start'),('forward','test_forward_start','test_reset_one')]:
    a,z=markers[start],markers[end]
    subset=[x for x in commits if x['generation']==a['generation'] and a['world_time_s']<x['world_time_s']<=z['world_time_s']+1e-6]
    metrics[name]=dict(start_world_s=a['world_time_s'],end_world_s=z['world_time_s'],
        heading_delta_radians=z['heading_yaw_radians']-a['heading_yaw_radians'],
        position_distance=math.dist(a['position'],z['position']),
        max_abs_decoder_turn=max(abs(x['decoder_turn']) for x in subset),
        max_decoder_forward=max(x['decoder_forward'] for x in subset),
        max_left_hz=max(x['source_activity_hz']['left'] for x in subset),
        max_right_hz=max(x['source_activity_hz']['right'] for x in subset),
        max_forward_hz=max(x['source_activity_hz']['forward'] for x in subset))
checks['left_turn_body_positive_yaw']=metrics['left']['heading_delta_radians']>0.2
checks['right_turn_body_negative_yaw']=metrics['right']['heading_delta_radians']<-.2
checks['forward_body_translation']=metrics['forward']['position_distance']>.2

disabled=markers['test_disabled_key']; after=markers['test_reset_two']
keys=[x for x in g if x['event']=='key' and x['generation']==disabled['generation'] and not x['stimulus_path_enabled']]
injects=[x for x in b if x.get('event')=='current_injection' and x['generation']==disabled['generation']]
disabled_commits=[x for x in commits if x['generation']==disabled['generation'] and x['world_time_s']>=disabled['world_time_s']]
checks['disabled_same_key_no_current_injection']=bool(keys) and not injects
checks['disabled_same_key_no_direct_body_motion']=all(abs(x['heading_yaw_radians'])<1e-8 and math.dist(x['position'],disabled['position'])<1e-8 for x in disabled_commits)

reset_states={gen:[states[(x['generation'],x['source_seq'])] for x in commits if x['generation']==gen and x['world_time_s']<=.4+1e-6] for gen in [2,3]}
checks['reset_same_seed_readouts_reproduced']=len(reset_states[2])==8 and len(reset_states[3])==8 and all(
    a['activity_hz']==z['activity_hz'] and a['forward']==z['forward'] and a['turn']==z['turn'] and a['population_hz']==z['population_hz'] for a,z in zip(reset_states[2],reset_states[3]))
checks['reset_body_initial_conditions_reproduced']=markers['test_suite_ready_for_disconnect']['position']==after['position'] and markers['test_suite_ready_for_disconnect']['heading_yaw_radians']==0
disconnected=[x for x in g if x['event']=='sample' and 'disconnected' in x['connection']]
checks['real_brain_kill_observed']=resources['real_brain_terminated_for_failure_test'] and bool(disconnected)
checks['disconnect_body_and_world_frozen']=len(disconnected)>=3 and all(x['position']==disconnected[0]['position'] and x['heading_yaw_radians']==disconnected[0]['heading_yaw_radians'] and x['world_time_s']==disconnected[0]['world_time_s'] for x in disconnected)
checks['no_owned_orphan_processes']=not resources['children_remaining']
clean=json.loads((ROOT/'reports/clean-exit/resources.json').read_text())
checks['normal_godot_window_shutdown_without_orphans']=clean['brain_exit_code']==0 and clean['godot_exit_code']==0 and not clean['children_remaining']
checks['ram_under_target_16gb']=resources['peak_combined_sampled_rss']<mapping['machine']['total_ram_bytes']
baseline_changes=subprocess.check_output(['git','diff','--name-only','4cd038f','--','.',':!body'],cwd=ROOT.parent,text=True).strip()
checks['baseline_tracked_core_and_reports_unchanged']=not baseline_changes
checks['baseline_source_sha_matches_commit']=all(hashlib.sha256(subprocess.check_output(['git','show','4cd038f:'+name],cwd=ROOT.parent)).hexdigest()==value for name,value in mapping['baseline_files_sha256'].items() if name in ['braincore/core.py','config.json','data/runtime/metadata.json'])
gen1=[x for x in commits if x['generation']==1]
first,last=gen1[0],gen1[-1]
motor_duration=last['world_time_s']-first['world_time_s']
wall_duration=last['wall_time_s']-first['wall_time_s']
fps=[x['fps'] for x in g if x['event']=='sample' and x['connection']=='ready' and x['fps']>0]
throughput=dict(neural_wall_ratio_excluding_warmup=motor_duration/wall_duration,
    control_updates_per_wall_second=(len(gen1)-1)/wall_duration,
    godot_ready_fps_min=min(fps),godot_ready_fps_max=max(fps),
    peak_python_process_tree_rss_bytes=resources['peak_python_sampled_rss'],
    peak_godot_process_tree_rss_bytes=resources['peak_godot_sampled_rss'],
    peak_combined_process_tree_rss_bytes=resources['peak_combined_sampled_rss'],
    minimum_available_system_ram_bytes=resources['minimum_available_ram'])
report=dict(checks=checks,all_checks_passed=all(checks.values()),phase_metrics=metrics,throughput=throughput,
    body_commit_count=len(commits),actual_mapping=mapping['actual_groups'],
    evidence=dict(brain_log='integration/brain.jsonl',godot_log='integration/godot.jsonl',resources='integration/resources.json'),
    limitations=['Engine-generated InputEventKey events via Input.parse_input_event; physical OS keyboard injection not certified because computer-use approval timed out.',
        'Decoder is experimental, not proof of biological motor behaviour. FPS is actual rendered Godot, not headless.',
        'RSS sums process trees including Windows venv redirectors; GPU VRAM and unrelated apps are not counted as process RSS.'])
(ROOT/'reports/certification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
if not report['all_checks_passed']: raise SystemExit('Integration certification incomplete')
