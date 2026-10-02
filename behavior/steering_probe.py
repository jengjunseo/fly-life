"""Audit unstimulated steering variation, without using target coordinates."""
import json
from pathlib import Path
import numpy as np
from behavior.run_assays import rows

ROOT=Path(__file__).resolve().parents[1]/'reports/behavior-retry'

def main():
    result={}
    for name in ['assays','seed-42']:
        values=rows(ROOT/name/'control/brain.jsonl')
        phases={}
        for label,start,end in [('initial',.5,2.5),('late',2.5,8.5)]:
            packets=[r for r in values if r.get('kind')=='state' and r['status']=='ready' and start<r['neural_time_s']<=end]
            diff=np.array([r['steering_difference_hz'] for r in packets])
            phases[label]=dict(mean_hz=float(diff.mean()),std_hz=float(diff.std()),minimum_hz=float(diff.min()),maximum_hz=float(diff.max()),
                absolute_p95_hz=float(np.percentile(np.abs(diff),95)),warmup_bias_hz=packets[0]['steering_warmup_bias_hz'])
        result[name]=phases
    (ROOT/'steering-baseline-audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
