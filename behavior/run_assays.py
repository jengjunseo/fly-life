"""Paired body-world trials. Failed behavior criteria remain failed in the report."""
import argparse
import gzip
import json
import hashlib
import subprocess
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def rows(path):
    if path.exists():return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    with gzip.open(str(path)+'.gz','rt',encoding='utf-8') as f:return [json.loads(line) for line in f]

def measure(folder):
    brain=rows(folder/'brain.jsonl');body=rows(folder/'godot.jsonl');world=rows(folder/'world.jsonl')
    states=[r for r in brain if r.get('kind')=='state' and r['status']=='ready' and r['dt_s']>0]
    commits=[r for r in body if r['event']=='body_commit']
    events=rows(folder/'events.jsonl');resources=json.loads((folder/'resources.json').read_text())
    byseq={r['source_seq']:r for r in commits}
    warmup_s=json.loads((folder/'body_runtime_config.json').read_text())['warmup_ms']/1000
    clock=all(abs(w['world_time_s']-w['neural_time_s']+warmup_s)<1e-8 for w in world)
    links=all(p['seq'] in byseq and
              abs((0. if p['ecology']['world']['hp']<=0 else p['forward'])-byseq[p['seq']]['decoder_forward'])<1e-12 and
              abs((0. if p['ecology']['world']['hp']<=0 else p['turn'])-byseq[p['seq']]['decoder_turn'])<1e-12 for p in states)
    feeding=[r for r in world if r['world_time_s']>=2. and r['distances']['food'] is not None]
    heat=[r for r in world if r['world_time_s']>=4.]
    last=world[-1]
    return dict(transport_passed=clock and links and len(states)==len(commits) and len(world)==len(states)+1,
        cleanup_passed=resources['brain_exit']==0 and resources['godot_exit']==0 and not resources['remaining_owned_pids'],
        no_manual_motor_injection=not any(r.get('event') in ['explicit_neural_test','debug_current_injection'] for r in brain),
        neural_time_s=states[-1]['neural_time_s'],world_time_s=last['world_time_s'],
        jumps=sum(r['event']=='gf_jump' for r in body),
        jump_seq=[r['source_seq'] for r in body if r['event']=='gf_jump'],
        predator_hits=sum(r['event']=='PREDATOR_HIT' for r in events),hp=last['hp'],
        maximum_height=max(r['fly_position'][1] for r in world),
        path_length=last.get('experiment_measurements',{}).get('path_length',0.),
        first_food_distance=feeding[0]['distances']['food'] if feeding else None,
        final_food_distance=feeding[-1]['distances']['food'] if feeding else None,
        minimum_food_distance=min(r['distances']['food'] for r in feeding) if feeding else None,
        food_contacts=sum(r['event']=='FOOD_CONTACT' for r in events),
        shade_seconds=last.get('experiment_measurements',{}).get('shade_seconds',0.),
        heat_exposure_c_s=last.get('experiment_measurements',{}).get('heat_exposure_c_s',0.),
        average_hot_temperature=float(np.mean([r['local_temperature_c'] for r in heat])) if heat else None)

def criteria(results):
    complete=all(k in results for k in ['control','control-no-sensory','predator','predator-no-sensory','predator-no-gf',
        'food-left','food-left-no-sensory','food-right','food-right-no-sensory','heat-left','heat-left-no-sensory','heat-right','heat-right-no-sensory'])
    gf=None;avoid=None;food=None;heat=None
    if all(k in results for k in ['control','predator','predator-no-sensory','predator-no-gf']):
        gf=(results['control']['jumps']==0 and results['predator']['jumps']>0 and
            results['predator-no-sensory']['jumps']==0 and results['predator-no-gf']['jumps']==0)
        avoid=gf and results['predator']['predator_hits']<results['predator-no-gf']['predator_hits'] and results['predator']['hp']>results['predator-no-gf']['hp']
    if all(k in results for k in ['food-left','food-left-no-sensory','food-right','food-right-no-sensory']):
        food=all(results['food-'+side]['minimum_food_distance']+.2<results['food-'+side+'-no-sensory']['minimum_food_distance']
                 and results['food-'+side]['food_contacts']>0 for side in ['left','right'])
    if all(k in results for k in ['heat-left','heat-left-no-sensory','heat-right','heat-right-no-sensory']):
        heat=all(results['heat-'+side]['shade_seconds']>results['heat-'+side+'-no-sensory']['shade_seconds']+.5 and
                 results['heat-'+side]['heat_exposure_c_s']<results['heat-'+side+'-no-sensory']['heat_exposure_c_s']-.5
                 for side in ['left','right'])
    return dict(complete=complete,software_passed=all(v['transport_passed'] and v['cleanup_passed'] and v['no_manual_motor_injection'] for v in results.values()),
                gf_sensory_dependency_passed=gf,predator_avoidance_passed=avoid,mirrored_food_approach_passed=food,mirrored_thermal_avoidance_passed=heat,
                biological_certification=False,limitations='One-seed paired assays. A primitive GF jump is not certified directional escape or full flight; innate odor/thermal valence is not inferred from anatomical connectivity alone.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='reports/behavior/assays');p.add_argument('--restore-weak',action='store_true');p.add_argument('--quick',action='store_true')
    p.add_argument('--model',choices=['counts','sensorimotor'],default='counts');p.add_argument('--duration',type=float,default=8.)
    p.add_argument('--brain-seed',type=int,default=20260913);p.add_argument('--world-seed',type=int,default=20260914)
    p.add_argument('--warmup-ms',type=int,choices=[500,2000],default=2000)
    p.add_argument('--modalities',action='store_true');p.add_argument('--cases',nargs='+');a=p.parse_args()
    if a.modalities and a.model!='sensorimotor':p.error('Modality assays require sensorimotor')
    root=ROOT/a.out;root.mkdir(parents=True,exist_ok=True)
    cases=[('control','CONTROL',[]),('control-no-sensory','CONTROL',['--no-sensory']),
           ('predator','PREDATOR',[]),('predator-no-sensory','PREDATOR',['--no-sensory']),('predator-no-gf','PREDATOR',['--no-gf']),
           ('food-left','FOOD',[]),('food-left-no-sensory','FOOD',['--no-sensory']),
           ('food-right','FOOD RIGHT',[]),('food-right-no-sensory','FOOD RIGHT',['--no-sensory']),
           ('heat-left','HEAT',[]),('heat-left-no-sensory','HEAT',['--no-sensory']),
           ('heat-right','HEAT RIGHT',[]),('heat-right-no-sensory','HEAT RIGHT',['--no-sensory'])]
    if a.quick:cases=cases[:5]
    if a.modalities:
        cases += [(f'food-{side}-no-{modality}',preset,['--no-'+modality])
                  for side,preset in [('left','FOOD'),('right','FOOD RIGHT')] for modality in ['vision','chemical']]
    if a.cases:
        unknown=set(a.cases)-{c[0] for c in cases}
        if unknown:p.error('Unknown cases: '+', '.join(sorted(unknown)))
        cases=[c for c in cases if c[0] in a.cases]
    results={}
    for name,preset,flags in cases:
        folder=root/name
        if (folder/'resources.json').exists():
            saved=json.loads((folder/'body_runtime_config.json').read_text())
            eco=json.loads((folder/'ecology_runtime_config.json').read_text())
            expected=dict(scientific_model=a.model,seed=a.brain_seed,restore_weak=a.restore_weak,gf_ablated='--no-gf' in flags,warmup_ms=a.warmup_ms if a.model=='sensorimotor' else 500)
            expected_sensory={k:'--no-'+flag not in flags for k,flag in [('enabled','sensory'),('vision_enabled','vision'),('chemical_enabled','chemical'),('thermal_enabled','thermal')]}
            if any(saved.get(k)!=v for k,v in expected.items()) or eco['mode']!=preset or eco['world_seed']!=a.world_seed or eco['duration_s']!=a.duration or any(eco['sensory'].get(k,True)!=v for k,v in expected_sensory.items()):
                raise ValueError(f'Refusing to reuse mismatched trial {folder}; choose a new output directory')
            generation=json.loads((folder/'model-generation-1.json').read_text())
            hashes=generation.get('source_sha256',{})
            if not hashes or any(not (ROOT/path).is_file() or hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest for path,digest in hashes.items()):
                raise ValueError(f'Refusing to reuse a trial with different or unavailable source hashes: {folder}; choose a new output directory')
        if not (folder/'resources.json').exists():
            cmd=[sys.executable,'-m','mvp.launch','--headless','--model',a.model,'--preset',preset,'--duration',str(a.duration),'--brain-seed',str(a.brain_seed),'--world-seed',str(a.world_seed),'--logdir',str(folder)]+flags
            if a.restore_weak:cmd+=['--restore-weak']
            if a.model=='sensorimotor':cmd+=['--warmup-ms',str(a.warmup_ms)]
            subprocess.run(cmd,cwd=ROOT,check=True)
        results[name]=measure(folder)
        report=dict(results=results,criteria=criteria(results),model=a.model,warmup_ms=a.warmup_ms if a.model=='sensorimotor' else 500,duration_s=a.duration,restore_weak=a.restore_weak,brain_seed=a.brain_seed,world_seed=a.world_seed)
        (root/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(dict(case=name,**results[name])),flush=True)

if __name__=='__main__':main()
