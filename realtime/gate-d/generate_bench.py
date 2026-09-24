import json,sys,time
import numpy as np
from env import ROOT,REPORT,OLD,WORK,save,sha,machine
from producer import Producer,statistics,N
if __name__=='__main__':
    mode=sys.argv[1];cfg=json.loads((ROOT/'config.json').read_text());seed=cfg['experiment']['seed'];workers=int(sys.argv[2]) if len(sys.argv)>2 else 1
    if mode=='direct':
        rng=np.random.default_rng(seed);rng.standard_normal(N,dtype=np.float32);out=np.empty((50,N),np.float32)
        def fill():
            start=time.perf_counter();rng.standard_normal(out.shape,dtype=np.float32,out=out);return (time.perf_counter()-start)*1000
        meta=dict(root_seed=seed,dtype=str(out.dtype),shape=list(out.shape),contiguous=bool(out.flags.c_contiguous),out_reused=True,float64_to_float32_cast=False,allocation_inside_fill=False,gate_c_source_sha256=sha(ROOT/'realtime/gate-c/generation.py'))
    else:
        assert json.loads((REPORT/'d-minus1.json').read_text())['statistics']['p99_ms']>35
        p=Producer(seed,workers);fill=p.fill;meta=p.metadata()
    warm=[fill() for _ in range(10)];times=[fill() for _ in range(200)]
    if mode!='direct':p.close()
    name='d-minus1' if mode=='direct' else f'd0-{workers}w'
    d=dict(statistics=statistics(times),wall_ms=times,warmup_blocks=10,warmup_ms=warm,metadata=meta,machine=machine(),samples_per_block=50*N,bytes_per_block=50*N*4)
    save(REPORT/(name+'.json'),d);print(json.dumps(d['statistics'],indent=2))
