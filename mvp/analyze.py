"""Analyze actual full-app logs. Never substitute old brain-only benchmarks."""
import argparse
import json
import math
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'body'));sys.path.insert(0,str(ROOT/'ecology'))
from body.decoder import decode
from mvp.presets import PRESETS,area_evidence

def rows(path):return [json.loads(x) for x in path.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def stats(values):
    a=np.asarray(values,float)
    return dict(n=len(a),mean=float(a.mean()),p50=float(np.percentile(a,50)),p95=float(np.percentile(a,95)),p99=float(np.percentile(a,99)),max=float(a.max())) if len(a) else None

def analyze(folder):
    packets=[p for p in rows(folder/'brain.jsonl') if p.get('kind')=='state' and p['status']=='ready' and p['dt_s']>0]
    g=rows(folder/'godot.jsonl');world=rows(folder/'world.jsonl');perf=rows(folder/'performance.jsonl');events=rows(folder/'events.jsonl')
    commits=[r for r in g if r['event']=='body_commit'];by_seq={r['source_seq']:r for r in commits}
    world_by_seq={r['source_seq']:r for r in world}
    cfg=json.loads((folder/'body_runtime_config.json').read_text());end=json.loads((folder/'brain_exit.json').read_text())
    resource=json.loads((folder/'resources.json').read_text())
    checks=dict(completed_70_quanta=len(packets)==70 and len(commits)==70 and len(perf)==70,
        duration=math.isclose(end['world_time_s'],3.5),normal_shutdown=end['normal_shutdown'],owned_processes_clean=not resource['remaining_owned_pids'] and resource['brain_exit']==0 and resource['godot_exit']==0,
        no_protocol_errors=not any(r['event']=='error' for r in g),
        source_ack_chain=True,decoder_unchanged=True,contained=True,world_time_lockstep=True,next_sensory_matches_world=True,body_pose_matches_world=True)
    for i,p in enumerate(packets):
        c=by_seq.get(p['seq']);motor=decode(p['activity_hz'],cfg['decoder'])
        checks['decoder_unchanged'] &= c is not None and p['forward']==motor['forward'] and p['turn']==motor['turn']
        source=p['ecology']['sensor_source_body_seq']
        checks['source_ack_chain'] &= source in world_by_seq and (i==0 or source==packets[i-1]['seq'])
        checks['next_sensory_matches_world'] &= source in world_by_seq and p['ecology']['world']['raw_sensors']==world_by_seq[source]['raw_sensors']
        checks['world_time_lockstep'] &= math.isclose(p['motor_time_s'],(i+1)*.05) and math.isclose(p['ecology']['sensory_time_s'],i*.05)
        if c:
            checks['body_pose_matches_world'] &= p['seq'] in world_by_seq and world_by_seq[p['seq']]['fly_position']==c['position']
            checks['contained'] &= all(abs(c['position'][k])<=cfg['arena']['half_width']-.1-.19+1e-5 for k in (0,2))
            checks['decoder_unchanged'] &= math.isclose(c['decoder_forward'],p['forward'],rel_tol=0,abs_tol=1e-12) and math.isclose(c['decoder_turn'],p['turn'],rel_tol=0,abs_tol=1e-12)
    group_sizes={name:len(data['members']) for name,data in json.loads((folder/'sensory_mapping.json').read_text())['actual'].items()}
    import pandas as pd
    identities=pd.read_parquet(ROOT/'data/runtime/neurons.parquet',columns=['bodyId','type','somaSide'])
    for name,typ in [('GF','DNp01'),('DNa01','DNa01'),('DNa02','DNa02'),('DNp09','DNp09')]:
        group_sizes[name]=int(identities.type.eq(typ).sum())
        if not group_sizes[name]:raise ValueError('Missing actual circuit identity: '+name)
    circuit={}
    for key in packets[0]['console']['groups_hz']:
        circuit[key]={}
        for phase,lo,hi in [('baseline',0,.5),('stimulus',.5,2.5),('recovery',3.,3.5)]:
            batch=[p for p in packets if lo-1e-8<=p['ecology']['sensory_time_s']<hi-1e-8]
            total=sum(p['console']['group_spikes'].get(key,0) for p in batch)
            circuit[key][phase]=dict(spikes=total,mean_population_rate_hz=total/(len(batch)*.05*group_sizes[key]),
                mean_ema_hz=float(np.mean([p['console']['groups_hz'][key] for p in batch])),peak_ema_hz=max(p['console']['groups_hz'][key] for p in batch))
    health=[r for r in g if r['event']=='console_health'][-1]
    checks['fullscreen_4k']=health['window_size']==[3840,2160] and health['mode']==3
    checks['world_majority']=math.prod(health['viewport_size'])/(3840*2160)>.5
    fps=[r['fps'] for r in g if r['event']=='sample' and r['world_time_s']>=.05]
    last=world[-1]
    return dict(preset=packets[0]['console']['preset'],checks=checks,passed=all(checks.values()),circuits=circuit,group_sizes=group_sizes,godot_json_motor_max_abs_error=max(abs(p['forward']-by_seq[p['seq']]['decoder_forward']) for p in packets),
        input_peaks={key:max(t['amplitude'] for p in packets for t in p['ecology']['sensory_terms'] if t['modality']==key) for key in group_sizes if key in ['lc4','lplc2','figure','food_odor','taste','fly_odor','hot','cold']},
        final_world=last,displacement=math.dist(last['fly_position'],[0,.22,0]),events=events,
        timing=dict(compute_ms=stats([r['compute_ms'] for r in perf]),lockstep_ms=stats([r['total_lockstep_ms'] for r in perf]),
            serialization_log_send_ms=stats([r['serialization_log_send_ms'] for r in perf]),ack_wait_ms=stats([r['body_ack_ms'] for r in perf]),
            integration_remainder_ms=stats([r['total_lockstep_ms']-r['compute_ms'] for r in perf]),fps=stats(fps),console=health,
            active_neural_wall=3.5/(sum(r['total_lockstep_ms'] for r in perf)/1000),
            completed_world_wall_including_startup=3.5/end['wall_seconds'],neural_wall_including_warmup=4./end['wall_seconds'],
            process_wall_s=end['wall_seconds']))

def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    dest=Path(a.out);dest.mkdir(parents=True,exist_ok=False)
    data={}
    for name in PRESETS:
        slug=name.lower().replace(' + ','-').replace(' ','-');data[name]=analyze(Path(a.runs)/slug)
    output=dict(passed=all(x['passed'] for x in data.values()),world_area=area_evidence(),experiments=data)
    (dest/'summary.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    lines=['# SHOT 4 — final full-application evidence','',
        'Actual 3840×2160 fullscreen Godot + original SciPy/PCG64 brain + console; six matched-seed 3.5 s world runs. 0.5 s neural warmup is additional. No old backend timings used below.','',
        '## Gates','',f"Closed-loop integrity: **{'PASS' if output['passed'] else 'FAIL'}**. Each condition has 70 completed 50 ms quanta and matching real body commits.",'',
        '## Performance (milliseconds unless stated)','',
        '| Condition | Compute p50 / p95 / p99 | Lockstep mean | Remainder mean | JSON/log/send mean | ACK wait mean | FPS p50 | Active neural/wall | World/wall incl. startup |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,r in data.items():
        t=r['timing'];c=t['compute_ms']
        lines.append(f"| {name} | {c['p50']:.2f} / {c['p95']:.2f} / {c['p99']:.2f} | {t['lockstep_ms']['mean']:.2f} | {t['integration_remainder_ms']['mean']:.2f} | {t['serialization_log_send_ms']['mean']:.2f} | {t['ack_wait_ms']['mean']:.2f} | {t['fps']['p50']:.0f} | {t['active_neural_wall']:.4f}× | {t['completed_world_wall_including_startup']:.4f}× |")
    lines+=['','Remainder = end-to-end quantum (encode → actual completed body ACK/world update) minus pure brain.step time. JSON/log/send includes group reduction, serialization, synchronous log and socket send. ACK wait includes Godot scheduling/physics and return processing; it is not a pure network latency measurement. Component timers overlap those aggregate categories and must not be added again.','',
        'Performance is measured, not realtime-certified. 70 windows per condition support a short application health check, not a sustained tail guarantee. No 35 ms gate is imposed.','',
        '## Console cost','', '| Condition | 10 Hz refresh mean / max ms | World viewport | Fullscreen |','|---|---:|---|---|']
    for name,r in data.items():
        h=r['timing']['console'];lines.append(f"| {name} | {h['ui_mean_ms']:.3f} / {h['ui_max_ms']:.3f} | {h['viewport_size']} | {h['window_size']}, mode {h['mode']} |")
    lines+=['','Direct callback timings cover text/control/event updates; neural-sample sparkline draw and GPU rendering are included in observed full-app FPS, not misrepresented as isolated zero-cost work.','',
        '## Circuit autopsy','',
        'Numbers below are mean selected-group spike rate Hz (total spikes / members / sampled neural seconds). Baseline is world [0,0.5), stimulus [0.5,2.5), recovery [3,3.5). Finite stimuli have distinct lifetimes within the stimulus window. EMA values and exact counts are in summary.json.','']
    for name,r in data.items():
        lines += [f'### {name}', '', '| Group | Baseline Hz | Stimulus Hz | Recovery Hz |','|---|---:|---:|---:|']
        for key,v in r['circuits'].items():
            lines.append(f"| {key} | {v['baseline']['mean_population_rate_hz']:.3f} | {v['stimulus']['mean_population_rate_hz']:.3f} | {v['recovery']['mean_population_rate_hz']:.3f} |")
        w=r['final_world'];lines += ['',f"Actual final displacement {r['displacement']:.8f} units; HP {w['hp']:.1f}; gut {w['gut']:.2f}; local temperature {w['local_temperature_c']:.2f}°C.",
            'Input current maxima: '+', '.join(f'{k} {v:.4f}' for k,v in r['input_peaks'].items())+'.','']
    lines+=['## Causal evidence boundary','',
        'Python decoder recomputation is exact. Godot JSON output uses decimal rounding; its motor log comparison allows only 1e-12 absolute error (measured maximum recorded in summary.json). This does not relax neural semantics.','',
        'world.jsonl contains post-ACK geometry and next sensory state. Each brain packet records the preceding source ACK, input raw features/currents, selected sensory and downstream spike counts/EMA, and the original decoder outputs. godot.jsonl records the resulting collision-aware body commit and actual pose. events.jsonl records world consequences and explicitly thresholded activity observations. summary.json classifies sequence, decoder, time and containment checks for every condition.','',
        'The matched CONTROL establishes observed intervention differences at this seed. A rise in a group does not prove that group alone mediates behavior. No lesion-based new causal mediation or biological behavior validation is claimed. Historical sensory-off/predator-off evidence is preserved separately.','',
        'See the canonical [scientific status](../../SCIENTIFIC_STATUS.md), [limitations](../../KNOWN_LIMITATIONS.md), and [experiment guide](../../EXPERIMENTS.md).']
    (dest/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=output['passed'],conditions={k:v['passed'] for k,v in data.items()})))
    raise SystemExit(not output['passed'])
if __name__=='__main__':main()

