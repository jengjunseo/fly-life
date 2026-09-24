"""Small asymmetric signed graph, but actual compiled Brian2 (not the full-data proof)."""
import json
import numpy as np
from scipy import sparse
from common import Brain, ROOT, REPORT, WORK, save
from prototype import b, translate, build


if __name__ == '__main__':
    p=json.loads((ROOT/'config.json').read_text())['model'];p['noise_std']=0.;p['baseline_current']=0.;p['baseline_heterogeneity']=0.
    # Source 0 -> target 1 excitatory, source 0 -> target 2 inhibitory; no reverse path.
    w=sparse.csr_matrix((np.array([12., -12.],np.float32),([1,2],[0,0])),shape=(4,4))
    ref=Brain(w,p,seed=7); external=ref.current([0],30.)
    directory=WORK/'semantic-cpp'
    g,s,net,spikes,states=translate(ref, external, np.arange(4),directory)
    net.run(12*b.ms, namespace={})
    construction=build(directory); b.device.run(directory=str(directory))
    vv=[];ss=[];rr=[];aa=[];fired=[]
    for step in range(12):
        fired.append(np.flatnonzero(ref.step(external)).tolist());vv.append(ref.v.copy());ss.append(ref.syn.copy());rr.append(ref.refractory.copy());aa.append(ref.activity.copy())
    steps=np.rint(spikes.t[:]/b.ms).astype(int);ids=np.asarray(spikes.i[:])
    candidate=[ids[steps==k].tolist() for k in range(12)]
    errors={name:float(np.max(np.abs(np.asarray(getattr(states,name)[:]).T-np.asarray(expected))))
            for name,expected in [('v',vv),('syn',ss),('ref_steps',rr),('activity',aa)]}
    report=dict(success=candidate==fired and max(errors.values())<.001,
        reference_spikes_by_step=fired,brian2_spikes_by_step=candidate,max_absolute_errors=errors,
        checks=dict(direction=ss[1][1]>0 and ss[1][0]==0 and ss[1][3]==0,
            sign=ss[1][2]<0,one_step_delay=ss[0][1]==0 and ss[1][1]>0,
            refractory=fired[0]==[0] and 0 not in fired[1] and 0 not in fired[2] and 0 in fired[3],
            external_only_source=external.tolist()==[30.,0.,0.,0.]),build=construction,
        noise_policy='OFF; seeded NumPy baseline exported without Brian RNG',scheduler=str(net.scheduling_summary()))
    report['checks']={k:bool(v) for k,v in report['checks'].items()}
    save(REPORT/'semantics.json',report);print(json.dumps(report,indent=2));raise SystemExit(not report['success'])
