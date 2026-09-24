import json
import numpy as np
from env import ROOT, WORK, REPORT, OLD, Brain, save

def compare(reference, candidate, exact=False):
    a=json.loads((REPORT/(reference+'.json')).read_text());b=json.loads((REPORT/(candidate+'.json')).read_text())
    x=np.loadtxt(REPORT/(reference+'-windows.txt'));y=np.loadtxt(REPORT/(candidate+'-windows.txt'))
    assert x.shape==y.shape
    initial=np.load(OLD/'initial.npz')
    selected=np.unique(np.concatenate([initial['group_'+k] for k in ['LC4','LPLC2','GF','DNp09']]+[np.linspace(0,165121,32,dtype=int)]))
    obs={};checks=[]
    for name,col in [('population',5),('LC4',9),('LPLC2',14),('GF',19),('DNp09',24)]:
        ref=x[:,col];can=y[:,col]
        max_delta=float(np.max(np.abs(can-ref)));scale=max(float(np.max(np.abs(ref))),1)
        equal=bool(np.array_equal(ref,can));passes=equal if exact else max_delta/scale<=.10
        obs[name]=dict(reference_final=int(ref[-1]),candidate_final=int(can[-1]),max_abs_delta=max_delta,
                       max_delta_over_reference_peak=max_delta/scale,exact=equal,guardrail_pass=passes)
        checks.append(passes)
    states={}
    for name,dtype in [('v',np.float32),('syn',np.float32),('activity',np.float32),('noise_sample',np.float32),('ref_steps',np.int32),('eligible',np.int32)]:
        r=list((WORK/reference).glob('_array_neurons_'+name+'_*'));c=list((WORK/candidate).glob('_array_neurons_'+name+'_*'))
        assert len(r)==len(c)==1
        rv=np.fromfile(r[0],dtype=dtype);cv=np.fromfile(c[0],dtype=dtype)
        equal=bool(np.array_equal(rv,cv))
        passes=equal if exact or dtype==np.int32 else bool(np.allclose(rv[selected],cv[selected],rtol=1e-4,atol=1e-5))
        states[name]=dict(full_array_exact=equal,selected_max_abs_delta=float(np.max(np.abs(rv[selected]-cv[selected]))),selected_close=passes)
        checks.append(passes)
    # Circuit activity/EMA/peak and quantum spike counts are preserved too.
    cols=[4,7]+list(range(9,29))
    activity_equal=bool(np.array_equal(x[:,cols],y[:,cols]))
    if exact:checks.append(activity_equal)
    else:
        for col in [10,12,13,15,17,18,20,22,23,25,27,28]:
            checks.append(bool(np.allclose(x[:,col],y[:,col],rtol=.10,atol=1e-5)))
    finite=b['finite'];runaway=b['max_spiking_fraction']<=max(a['max_spiking_fraction']*2,.01)
    checks += [finite,runaway]
    # Check effective connectivity against the immutable original CSR.
    cfg=json.loads((ROOT/'config.json').read_text());brain=Brain.load(ROOT/'data/runtime',cfg)
    graph={}
    for name,prefix,expected in [('source','_dynamic_array_connections__synaptic_pre_',brain.w.indices),
        ('target','_dynamic_array_connections__synaptic_post_',np.repeat(np.arange(brain.n,dtype=np.int32),np.diff(brain.w.indptr))),
        ('weight','_dynamic_array_connections_w_',brain.w.data)]:
        p=list((WORK/candidate).glob(prefix+'*'));assert len(p)==1
        graph[name]=bool(np.array_equal(np.fromfile(p[0],dtype=expected.dtype),expected))
    checks += list(graph.values())
    result=dict(reference=reference,candidate=candidate,exact_required=exact,success=all(checks),counts=obs,states=states,
        all_quantum_circuit_observations_exact=activity_equal,finite=finite,no_runaway=runaway,graph=graph,
        selected_state_indices=selected.tolist(),qualification='Shared deterministic noise and input. OpenMP: engineering circuit/count10% and selected float state rtol1e-4 atol1e-5 guardrails; not 3-seed natural variability certification. Monitor/noise-only same1T variants require exact full dynamics state and observable identity.')
    save(REPORT/(candidate+'-correctness.json'),result)
    print('CORRECTNESS',candidate,result['success'],flush=True)
    assert result['success'], 'Do not adopt failed variant'
    return result
