"""Apply user quantitative B0 gates before B1; no tuned scientific parameters."""
import json
from env import REPORT,save

def read(name):return json.loads((REPORT/name).read_text())

if __name__=='__main__':
    reference=read('reference-b0.json');reports={name:read(name+'.json') for name in ['b0-native','b0-frozen']}
    comparisons={};checks={}
    for name,candidate in reports.items():
        rows=[];local={}
        for phase in ['baseline','stimulus','recovery']:
            r=reference['phases'][phase];c=candidate['phases'][phase]
            ratio=c['population_rate_hz']/r['population_rate_hz'];active=c['active_fraction']/r['active_fraction']
            rows.append(dict(phase=phase,reference=r,brian2=c,population_ratio=ratio,active_fraction_ratio=active))
            local[phase+'_population_90_110']=.9<=ratio<=1.1
            local[phase+'_not_dead']=ratio>=.5 and active>=.5
        p=candidate['phases'];r=reference['phases']
        local['input_response']=all(p['stimulus']['groups'][g]['mean_hz']>10*p['baseline']['groups'][g]['mean_hz'] for g in ['LC4','LPLC2'])
        local['gf_downstream_response']=p['stimulus']['groups']['GF']['mean_hz']>p['baseline']['groups']['GF']['mean_hz']
        local['gf_recovery']=abs(p['recovery']['groups']['GF']['mean_hz']-p['baseline']['groups']['GF']['mean_hz'])<abs(p['stimulus']['groups']['GF']['mean_hz']-p['baseline']['groups']['GF']['mean_hz'])
        local['population_recovery']=p['recovery']['population_rate_hz']<=1.1*r['baseline']['population_rate_hz']
        local['no_sustained_runaway']=p['recovery']['population_rate_hz']<=2*r['recovery']['population_rate_hz']
        local['no_simultaneous_runaway']=max(x['max_simultaneous_spiking_fraction'] for x in candidate['windows'])<.25
        local['finite']=candidate['finite'];local['same_full_connectivity']=candidate['full_connection_arrays_verified']
        local['dnp09_no_new_activity']=all(p[phase]['groups']['DNp09']['mean_hz']<=r[phase]['groups']['DNp09']['mean_hz']+1 for phase in ['baseline','stimulus','recovery'])
        comparisons[name]=rows;checks[name]=local
    result=dict(success=all(all(v.values()) for v in checks.values()),checks=checks,comparison=comparisons,
        noise_policy='Exact same PCG64 float32 tape for B0 injection correctness PLUS native C++ MT19937 statistical equivalence; native noise cost measured separately. Stream identity not claimed for native Brian2 seed.')
    save(REPORT/'b0-equivalence.json',result);print(json.dumps({'success':result['success'],'checks':checks},indent=2));raise SystemExit(not result['success'])
