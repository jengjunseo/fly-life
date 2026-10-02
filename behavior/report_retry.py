"""Summarize final paired assays, preserving failed and exploratory evidence."""
import hashlib
import gzip
import json
from pathlib import Path
from behavior.run_assays import rows

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/behavior-retry'

def main():
    final=json.loads((OUT/'final-assays/results.json').read_text())
    repeat=json.loads((OUT/'final-seed-42/results.json').read_text())
    if len(final['results'])!=17 or len(repeat['results'])!=8:raise ValueError('Final trials not finished')
    qa=rows(OUT/'ui-buttons/godot.jsonl')
    qa_rows=[r for r in qa if r['event'].startswith('qa_')]
    resources=json.loads((OUT/'ui-buttons/resources.json').read_text())
    console_path=OUT/'ui-buttons/godot_console.txt'
    if console_path.exists():console=console_path.read_text(encoding='utf-8')
    else:
        with gzip.open(str(console_path)+'.gz','rt',encoding='utf-8') as stream:console=stream.read()
    software=all(x['criteria']['software_passed'] for x in [final,repeat])
    qa_passed=len(qa_rows)==4 and all(r['passed'] for r in qa_rows) and resources['brain_exit']==resources['godot_exit']==0 and not resources['remaining_owned_pids'] and 'ERROR:' not in console
    visual=all(final['results']['food-'+side+'-no-vision']['food_contacts']==0 and final['results']['food-'+side+'-no-chemical']['food_contacts']>0 for side in ['left','right'])
    same_baseline=all(x['warmup_ms']==2000 for x in [final,repeat])
    frozen_now=rows(OUT/'frozen-path/world.jsonl')[-1]['fly_position']
    frozen_before=rows(ROOT/'reports/behavior/frozen-path/world.jsonl')[-1]['fly_position']
    preserved_position=frozen_now==frozen_before
    result=dict(software_passed=software,ui_conditions_and_cleanup_passed=qa_passed,same_warmup=same_baseline,
        paired_food_both_seeds_passed=all(x['criteria']['mirrored_food_approach_passed'] for x in [final,repeat]),
        paired_predator_both_seeds_passed=all(x['criteria']['predator_avoidance_passed'] for x in [final,repeat]),
        initial_seed_visual_dependency_passed=visual,thermal_avoidance_passed=final['criteria']['mirrored_thermal_avoidance_passed'],
        frozen_motor_position_unchanged=preserved_position,frozen_motor_position=frozen_now,
        tests=json.loads((OUT/'tests.json').read_text()),biological_certification=False,
        limitations=['Two seeds and 8 seconds are engineering evidence, not population statistics or biological certification.',
            'Object pursuit and primitive GF takeoff do not establish food recognition, ingestion or complete flight.',
            'Steering slope and body impulses were selected during engineering trials.',
            'Prior 500ms calibration failed a second-seed food criterion; see preserved seed-42 results.',
            'Thermal avoidance remains unresolved; exploratory negative evidence is retained.'],
        final=final,repeat=repeat,qa=qa_rows)
    result['tests']={k:v for k,v in result['tests'].items() if k!='output'}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    paths=['behavior/sensorimotor.py','behavior/model.py','behavior/sensory.py','behavior/readout.py',
        'behavior/world.py','behavior/presets.py','behavior/run_assays.py','behavior/report_retry.py','behavior/tests.py',
        'remaster/runtime.py','remaster/fastbrain.py','remaster/presets.py','braincore/core.py','mvp/launch.py',
        'mvp/bridge.py','mvp/presets.py','ecology/bridge.py','ecology/model.py','ecology/sensory.py','ecology/config.json',
        'body/main.gd','body/mvp/main.gd','body/ecology/main.gd','body/remaster/main.gd','body/decoder.py',
        'config.json','body/body_config.json','data/runtime/metadata.json']
    (OUT/'final-source-sha256.json').write_text(json.dumps({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ['final','repeat','qa','limitations']},indent=2))

if __name__=='__main__':main()
