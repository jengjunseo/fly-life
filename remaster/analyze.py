"""Verify full-app neural packets, body commits, commands and honest timing."""
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/remaster'

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def analyze(folder):
    godot=rows(folder/'godot.jsonl');brain=rows(folder/'brain.jsonl')
    commits=[r for r in godot if r['event']=='body_commit']
    packets={r['seq']:r for r in brain if r.get('kind')=='state'}
    keys={(r['generation'],r['source_seq']) for r in commits}
    perf=[r for r in rows(folder/'performance.jsonl') if (r['generation'],r['seq']) in keys]
    data={}
    for key in ['compute_ms','body_ack_ms','total_lockstep_ms']:
        values=[r[key] for r in perf]
        data[key]={name:float(np.percentile(values,p)) for name,p in [('p50',50),('p95',95)]}
    frame=float(json.loads((folder/'body_runtime_config.json').read_text())['packet_neural_ms'])
    data.update(committed_frames=len(commits),brain_frame_ms=frame,
                observed_world_wall_rate=len(commits)*frame/sum(r['total_lockstep_ms'] for r in perf),
                deadline_misses=sum(r['total_lockstep_ms']>frame for r in perf),
                max_displacement=float(max(np.linalg.norm(r['position']-np.array([0,.22,0])) for r in commits)),
                fps_p50=float(np.median([r['fps'] for r in commits if r['world_time_s']>.3])),
                qa={r['event']:r['passed'] for r in godot if 'passed' in r},
                resource_cleanup=json.loads((folder/'resources.json').read_text())['remaining_owned_pids'],
                normal_shutdown=json.loads((folder/'brain_exit.json').read_text())['normal_shutdown'],
                godot_errors='ERROR:' in (folder/'godot_console.txt').read_text(encoding='utf-8'))
    # Godot's JSON text rounds doubles at about 15 digits. This check allows
    # only that wire-log rounding; Python full-state equivalence is bit-exact.
    close=lambda a,b:bool(np.isclose(a,b,rtol=0,atol=1e-12))
    data['causal_commit_match']=all(
        close(r['decoder_forward'],packets[r['source_seq']]['forward']) and
        close(r['decoder_turn'],packets[r['source_seq']]['turn']) and
        all(close(v,packets[r['source_seq']]['activity_hz'][k]) for k,v in r['source_activity_hz'].items()) and
        r['neural_dt_s']==frame/1000 for r in commits)
    data['continuous_time']=all(abs(r['world_time_s']-packets[r['source_seq']]['motor_time_s'])<1e-5 for r in commits)
    return data,commits,packets

def main():
    fast,fc,fp=analyze(REPORT/'live-fast-final')
    reference,rc,rp=analyze(REPORT/'live-reference-final')
    controls,cc,cp=analyze(REPORT/'live-controls')
    def trajectory(commits,packets):
        return {round(packets[c['source_seq']]['motor_time_s'],5):dict(
            activity=packets[c['source_seq']]['activity_hz'],
            groups=packets[c['source_seq']]['console']['groups_hz'],
            forward=c['decoder_forward'],turn=c['decoder_turn'],position=c['position']) for c in commits}
    ft,rt=trajectory(fc,fp),trajectory(rc,rp)
    exact=set(ft)==set(rt) and all(ft[t]==rt[t] for t in ft)
    controls['left_turn_verified']=any(c['decoder_turn']<-.2 for c in cc if c['generation']==1)
    controls['right_turn_verified']=any(c['decoder_turn']>.2 for c in cc if c['generation']==1)
    controls['forward_verified']=any(c['decoder_forward']>.5 for c in cc if c['generation']==1)
    controls['control_after_reset_motor_zero']=all(c['decoder_forward']==0 and c['decoder_turn']==0 for c in cc if c['generation']==2)
    checks=[exact,fast['max_displacement']>3,fast['qa'].get('qa_pause',False),fast['qa'].get('qa_step',False),controls['qa'].get('qa_reset',False),
            controls['left_turn_verified'],controls['right_turn_verified'],controls['forward_verified'],
            controls['control_after_reset_motor_zero']]
    for run in [fast,reference,controls]:
        checks.extend([run['causal_commit_match'],run['continuous_time'],run['normal_shutdown'],
                       not run['godot_errors'],not run['resource_cleanup']])
    checks.extend([json.loads((REPORT/'equivalence.json').read_text())['passed'],
                   json.loads((REPORT/'tests.json').read_text())['passed']])
    result=dict(passed=all(checks),fast=fast,reference=reference,controls=controls,
                identical_committed_neural_readouts_and_body_trajectory=exact,
                compared_neural_frames=len(ft),equivalence=json.loads((REPORT/'equivalence.json').read_text()),
                regressions=json.loads((REPORT/'tests.json').read_text())['passed'],
                realtime_achieved=fast['deadline_misses']==0)
    (REPORT/'integration.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2));raise SystemExit(not result['passed'])

if __name__=='__main__':main()
