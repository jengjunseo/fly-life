"""C3-A only after failed C2: actual baseline NumPy PCG64 float32 blocks."""
import json,time
import numpy as np
from env import ROOT,REPORT,WORK,Brain,save,machine
from braincore.evidence import Resources
if __name__=='__main__':
    assert json.loads((REPORT/'c2-decision.json').read_text())['c3_allowed']
    cfg=json.loads((ROOT/'config.json').read_text());n=165122;seed=cfg['experiment']['seed']
    rng=np.random.default_rng(seed);baseline=cfg['model']['baseline_current']+cfg['model']['baseline_heterogeneity']*rng.standard_normal(n,dtype=np.float32)
    assert np.array_equal(baseline,np.load(WORK/'initial.npz')['baseline'])
    # Flattened block and reference per-ms calls must preserve the shared sequence.
    a=np.random.default_rng(seed);z=np.random.default_rng(seed)
    a.standard_normal(n,dtype=np.float32);z.standard_normal(n,dtype=np.float32)
    one=a.standard_normal((50,n),dtype=np.float32)
    exact=all(np.array_equal(one[i],z.standard_normal(n,dtype=np.float32)) for i in range(50));assert exact
    del one
    records=[]
    with Resources() as resources:
        for ms in [50,100,500,1000]:
            shape=(ms,n);methods={};samples=ms*n
            for method in ['allocate','reuse_out']:
                block=np.empty(shape,dtype=np.float32) if method=='reuse_out' else None
                warm_start=time.perf_counter()
                for _ in range(2):
                    if method=='reuse_out':rng.standard_normal(shape,dtype=np.float32,out=block)
                    else:block=rng.standard_normal(shape,dtype=np.float32)
                warm=time.perf_counter()-warm_start;trials=[]
                for _ in range(5):
                    if method=='allocate':block=None
                    started=time.perf_counter()
                    if method=='reuse_out':rng.standard_normal(shape,dtype=np.float32,out=block)
                    else:block=rng.standard_normal(shape,dtype=np.float32)
                    trials.append((time.perf_counter()-started)*1000)
                methods[method]=dict(wall_ms=trials,mean_ms=float(np.mean(trials)),p50_ms=float(np.median(trials)),p95_ms=float(np.percentile(trials,95)),max_ms=max(trials),warmup_seconds=warm,
                    samples_per_second=samples/(np.mean(trials)*.001),neural_wall_ratio=ms/float(np.mean(trials)),sanity_mean=float(block.ravel()[:1000000].mean()),sanity_variance=float(block.ravel()[:1000000].var()))
                del block
            chosen=min(methods,key=lambda k:methods[k]['mean_ms']);best=methods[chosen]
            records.append(dict(neural_ms=ms,bytes=samples*4,samples=samples,chosen_method=chosen,methods=methods,**{k:best[k] for k in ['mean_ms','p50_ms','p95_ms','max_ms','samples_per_second','neural_wall_ratio']}))
            print(json.dumps(records[-1]),flush=True)
    best=max(records,key=lambda q:q['neural_wall_ratio']);feasible=best['neural_wall_ratio']>=1
    report=dict(blocks=records,realtime_feasible=feasible,best_block_neural_ms=best['neural_ms'],best_mean_neural_wall_ratio=best['neural_wall_ratio'],seed=seed,neurons=n,
        rng='NumPy2.4 default_rng PCG64 float32 standard_normal; state after actual baseline draw',block_matches_reference_per_ms_sequence=exact,
        criterion='At least one measured block strategy mean generation throughput >=165122000 samples/s. Allocation included for allocate, existing output buffer for reuse_out. No disk write/statistics in generation timing; two warmups then five trials per method.',
        memory='50ms=33024400 bytes; 1s=660488000 bytes. Reuse_out preallocated and touched by warmup. Allocate includes allocation + fill; page faults belong to generation. At most one block retained between trials.',
        machine=machine(),resources=resources.report(),c4_allowed_by_generation=feasible)
    save(REPORT/'c3-generation.json',report)
