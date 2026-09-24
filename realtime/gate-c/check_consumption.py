"""Bounded C3 shared-noise correctness against actual prior SciPy B0."""
import json
from env import ROOT,REPORT,save
if __name__=='__main__':
    ref=json.loads((ROOT/'reports/realtime/gate-b/reference-b0.json').read_text())
    candidate=json.loads((REPORT/'c3-consumption.json').read_text());checks={};comparisons={}
    for phase in ['baseline','stimulus','recovery']:
        r=ref['phases'][phase];c=candidate['phases'][phase]
        checks[phase+'_population']=r['population_spikes']==c['population_spikes']
        checks[phase+'_active_fraction']=r['active_fraction']==c['active_fraction']
        comparisons[phase]=dict(reference=r,candidate=c)
        for g in ['LC4','LPLC2','GF','DNp09']:
            checks[phase+'_'+g+'_counts']=r['groups'][g]['spike_count']==c['groups'][g]['spike_count']
            checks[phase+'_'+g+'_active']=r['groups'][g]['active_fraction']==c['groups'][g]['active_fraction']
    checks['finite']=candidate['finite'];checks['full_graph']=candidate['full_connection_arrays_verified']
    checks['no_synchronous_runaway']=max(w['max_simultaneous_spiking_fraction'] for w in candidate['windows'])<.25
    result=dict(success=all(checks.values()),checks=checks,comparisons=comparisons,
        qualification='Exact shared 2s input; population/group counts and phase-active fractions agree, not exact spike train or native multi-seed evidence.')
    save(REPORT/'c3-correctness.json',result);print(json.dumps(dict(success=result['success'],checks=checks),indent=2));raise SystemExit(not result['success'])
