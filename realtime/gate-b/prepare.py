"""Reuse ACTUAL delivered sensory terms; no new biological mapping or world simulation."""
import json
import numpy as np
from env import ROOT,REPORT,WORK,Brain,save,sha

if __name__=='__main__':
    cfg=json.loads((ROOT/'config.json').read_text());brain=Brain.load(ROOT/'data/runtime',cfg)
    WORK.mkdir(parents=True,exist_ok=True)
    groups={k:brain.resolve(dict(types=[v])) for k,v in [('LC4','LC4'),('LPLC2','LPLC2'),('GF','DNp01'),('DNp09','DNp09')]}
    initial=dict(baseline=brain.baseline,**{'group_'+k:idx.astype(np.int32) for k,idx in groups.items()})
    np.savez(WORK/'initial.npz',**initial)
    source=ROOT/'reports/ecology/live/brain.jsonl'
    frames=[json.loads(line) for line in source.read_text().splitlines()]
    frames=[x for x in frames if x.get('kind')=='state' and x.get('status')=='ready' and x.get('dt_s')==.05]
    assert len(frames)==60
    modalities=[x['modality'] for x in frames[0]['ecology']['sensory_terms']]
    mapping={x['modality']:brain.resolve(dict(bodyIds=x['bodyIds'])).astype(np.int32) for x in frames[0]['ecology']['sensory_terms']}
    assert all(len(v)>0 for v in mapping.values())
    pool=np.unique(np.concatenate(list(mapping.values()))).astype(np.int32)
    matrix=np.zeros((len(modalities),len(pool)),np.float32)
    for j,name in enumerate(modalities):matrix[j,np.isin(pool,mapping[name])]=1.
    amps=np.array([[x['amplitude'] for x in f['ecology']['sensory_terms']] for f in frames],np.float32)
    for f in frames:
        assert [x['modality'] for x in f['ecology']['sensory_terms']]==modalities
        assert all(np.array_equal(brain.resolve(dict(bodyIds=x['bodyIds'])),mapping[x['modality']]) for x in f['ecology']['sensory_terms'])
    looming=np.zeros((1200,len(modalities)),np.float32)
    for name in ['lc4','lplc2']:looming[:,modalities.index(name)]=cfg['experiment']['stimulus_current']
    visual=[modalities.index(x) for x in ['lc4','lplc2','figure']]
    maxvisual=int(np.argmax(amps[:,visual].sum(axis=1)));maxhot=int(np.argmax(amps[:,modalities.index('hot')]))
    compound=np.zeros_like(looming);compound[:,visual]=amps[maxvisual,visual];compound[:,modalities.index('hot')]=amps[maxhot,modalities.index('hot')]
    schedules=dict(baseline=np.zeros_like(looming),looming=looming,real_predator=np.tile(amps,(20,1)),compound=compound)
    b0=np.zeros((40,len(modalities)),np.float32)
    b0[20:30]=looming[:10]
    schedules['b0']=b0
    perf=np.zeros((410,len(modalities)),np.float32);perf[210:]=looming[:200];schedules['b0_performance']=perf
    b2=np.zeros_like(looming);b2[400:800]=looming[:400];schedules['b2']=b2
    np.savez(WORK/'inputs.npz',pool=pool,matrix=matrix,**schedules)
    save(REPORT/'input-artifact.json',dict(dataset=cfg['dataset'],neurons=brain.n,effective_connections=brain.w.nnz,
        dt_ms=cfg['model']['dt_ms'],seed=cfg['experiment']['seed'],noise_std=cfg['model']['noise_std'],
        modalities=modalities,resolved_indices={k:v.tolist() for k,v in mapping.items()},
        observed_groups={k:dict(indices=v.tolist(),body_ids=brain.neurons.iloc[v].bodyId.tolist()) for k,v in groups.items()},
        source_path=str(source.relative_to(ROOT)),source_sha256=sha(source),actual_trace_frames=60,
        real_predator_policy='Exact entire delivered 3s sensory-current sequence, repeated 20x to obtain 60s; includes actual concurrent food/heat/female channels. NOT a new world run or square pulse substitute.',
        compound_policy='Sustained strongest actual recorded visual snapshot + strongest actual recorded heat current; other channels zero; no amplitude tuning.',
        compound_visual_source_seq=frames[maxvisual]['seq'],compound_hot_source_seq=frames[maxhot]['seq'],
        original_trace=[dict(seq=f['seq'],sensory_time_s=f['ecology']['sensory_time_s'],raw=f['ecology']['world']['raw_sensors'],
             terms=f['ecology']['sensory_terms']) for f in frames],
        schedules={k:v.tolist() for k,v in schedules.items()},initial_sha256=sha(WORK/'initial.npz'),inputs_sha256=sha(WORK/'inputs.npz'),
        b2_policy='60s continuous: 20s baseline, 20s existing looming current 3, 20s recovery; noise OFF'))
    print('Prepared actual 60-frame replay, compound and deterministic schedules')
