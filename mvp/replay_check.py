"""Compare observable neural/body sequences across real seeded application runs."""
import argparse
import json
from pathlib import Path

def packets(path,generation):
    return [p for p in map(json.loads,(path/'brain.jsonl').read_text().splitlines())
            if p.get('kind')=='state' and p['status']=='ready' and p['dt_s']>0 and p['generation']==generation]

def signature(p):
    return dict(motor_time_s=p['motor_time_s'],activity=p['activity_hz'],forward=p['forward'],turn=p['turn'],
                population=p['population_hz'],circuits=p['console']['groups_hz'],counts=p['console']['group_spikes'],
                sensor=p['ecology']['world']['raw_sensors'],world=p['ecology']['world'],terms=p['ecology']['sensory_terms'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--replay',required=True)
    p.add_argument('--generation',type=int,default=1);p.add_argument('--frames',type=int,default=70);p.add_argument('--out',required=True);a=p.parse_args()
    x=packets(Path(a.reference),1);y=packets(Path(a.replay),a.generation)
    mismatch=[i for i,(left,right) in enumerate(zip(x[:a.frames],y[:a.frames])) if signature(left)!=signature(right)]
    result=dict(passed=len(x)>=a.frames and len(y)>=a.frames and not mismatch,reference=a.reference,replay=a.replay,
                replay_generation=a.generation,frames=a.frames,available=[len(x),len(y)],mismatching_frames=mismatch,
                scope='Exact observable population/group counts, EMA, motor, sensory/world snapshots. Not a full internal membrane-state hash claim.')
    Path(a.out).write_text(json.dumps(result,indent=2));print(json.dumps(result));raise SystemExit(not result['passed'])
