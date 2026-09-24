"""Bounded 2s shared PCG64 float32 noise tape for B0 ONLY, not a performance shortcut."""
import json
import time
import numpy as np
from env import ROOT,WORK,REPORT,save,sha

if __name__=='__main__':
    cfg=json.loads((ROOT/'config.json').read_text());p=cfg['model'];initial=np.load(WORK/'initial.npz')
    rng=np.random.default_rng(cfg['experiment']['seed']);n=len(initial['baseline'])
    baseline=p['baseline_current']+p['baseline_heterogeneity']*rng.standard_normal(n,dtype=np.float32)
    assert np.array_equal(baseline,initial['baseline'])
    path=WORK/'noise-b0-float32.bin';s=ss=0.;count=0;start=time.perf_counter()
    with path.open('wb') as f:
        for _ in range(40):
            # Same number/order of PCG64 float32 draws as 50 Brain.step calls.
            values=np.stack([rng.standard_normal(n,dtype=np.float32) for _ in range(50)])
            f.write(values.tobytes());s+=float(values.sum(dtype=np.float64));ss+=float(np.square(values,dtype=np.float64).sum());count+=values.size
    save(REPORT/'noise-tape.json',dict(seed=cfg['experiment']['seed'],rng='NumPy2.4 default_rng PCG64 float32 standard_normal',
        initial_baseline_matches=True,shape=[2000,n],dtype='little endian float32',index_rule='[neural_step, runtime_index], C order; step0 is first update after initial state',
        noise_std=p['noise_std'],tape_stores='UNSCALED standard normals; amplitude applied float32 in model, before external current, even during refractory',
        sha256=sha(path),bytes=path.stat().st_size,standard_normal_mean=s/count,standard_normal_variance=ss/count-(s/count)**2,
        generation_wall_seconds=time.perf_counter()-start,scope='B0 2s shared noise injection verification ONLY; NOT B0 performance/B1 input; those generate Gaussian noise in C++ and include its cost'))
    print('Shared B0 PCG64 noise tape generated',flush=True)
