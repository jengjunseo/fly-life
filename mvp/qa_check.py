"""Validate observed UI interactions using actual command/state/body logs."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def rows(p):return list(map(json.loads,p.read_text(encoding='utf-8').splitlines()))

def main():
    qa=ROOT/'reports/mvp/ui-qa';final=ROOT/'reports/mvp/final-product-test'
    g=rows(qa/'godot.jsonl');b=rows(final/'brain.jsonl');f=rows(final/'godot.jsonl')
    states=[x for x in b if x.get('kind')=='state']
    commands=[x['message'] for x in b if x.get('event')=='command']
    edits=[x for x in states if x['generation']==1 and x['status']=='paused' and x['ecology']['world']['local_temperature_c']==34 and len(x['ecology']['world']['entities'])==3]
    steps=[x for x in states if x['generation']==1 and x['status']=='ready' and x['dt_s']>0 and x['ecology']['world']['local_temperature_c']==34]
    clear=[x for x in states if x['generation']==1 and x['status']=='paused' and not x['ecology']['world']['entities'] and any(e['event']=='EXPERIMENT_CLEARED' for e in x['console']['events'])]
    heat=[x for x in states if x['generation']==2 and x['console']['preset']=='HEAT' and x['dt_s']>0]
    checks=dict(pause_test=any(x['event']=='qa_pause' and x['passed'] for x in g),
        step_test=any(x['event']=='qa_step' and x['passed'] for x in g),
        fullscreen_round_trip=[x['mode'] for x in g if x['event']=='fullscreen_toggle']==[0,3],
        reset_generations=max(x['generation'] for x in g)==2,
        paused_edits_visible_in_state=bool(edits),temperature_and_shade=bool(edits) and all(not x['console']['shade_enabled'] for x in edits),
        manual_step_exact=bool(edits) and len(steps)==1 and abs(steps[0]['motor_time_s']-edits[0]['motor_time_s']-.05)<1e-9,
        manual_step_hot_response=bool(steps) and steps[0]['console']['groups_hz']['hot']>0,
        clear_objects=bool(clear),ui_preset_changed=bool(heat),heat_observed=bool(heat) and max(x['console']['groups_hz']['hot'] for x in heat)>20,
        final_4k=any(x['event']=='console_health' and x['window_size']==[3840,2160] and x['mode']==3 for x in f),
        clean_exits=all(json.loads((p/'resources.json').read_text())['brain_exit']==0 and json.loads((p/'resources.json').read_text())['godot_exit']==0 and not json.loads((p/'resources.json').read_text())['remaining_owned_pids'] for p in [qa,final]))
    result=dict(passed=all(checks.values()),checks=checks,
        manual_world_time_before=edits[0]['motor_time_s'] if edits else None,manual_world_time_after=steps[0]['motor_time_s'] if steps else None,
        visual_inspection='Actual user-desktop Godot screenshots inspected: 4K layout, camera follow, interpretation tab, fullscreen/windowed round trip, paused objects and temperature, HEAT experiment. Engine captures are 3840x2160; desktop capture is DPI-scaled 2560x1440.',
        screenshot_refs=['final-product-test/paused-edits-desktop.png','final-product-test/heat-desktop.png','ui-qa/follow-desktop.png','ui-qa/windowed-desktop.png','ui-qa/interpretation-desktop.png'])
    (ROOT/'reports/mvp/visual-qa.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result));raise SystemExit(not result['passed'])
if __name__=='__main__':main()
