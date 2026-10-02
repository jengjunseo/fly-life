"""An explicitly separate count-weighted LIF hypothesis for behavioral assays.

No target positions, stimulus labels, rewards or desired actions enter this model.
Uniform tonic drive is an assumed arousal condition, not measured spontaneous
activity. The v0.1 model and its certificates remain available through --model frozen.
"""
import json
import hashlib
from pathlib import Path
import numpy as np
from scipy import sparse
from remaster.fastbrain import FastBrain

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = dict(recurrent_gain=.002, baseline_current=1.5,
                  baseline_heterogeneity=0., noise_std=.1)

def load_connectivity(coreconfig, unpruned=False):
    # Use Brain.load for verified identity alignment and source artifact integrity.
    reference = FastBrain.load(ROOT/'data/runtime', coreconfig)
    directory = ROOT/('data/behavior' if unpruned else 'data/runtime')
    metadata=json.loads((directory/'metadata.json').read_text())
    if metadata['dataset']!=coreconfig['dataset'] or metadata['matrix_orientation']!='W[target, source]; input = W @ previous_step_spikes':
        raise ValueError('Count artifact dataset/orientation mismatch')
    path=directory/'counts.npz'
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024), b''):h.update(block)
    if h.hexdigest()!=metadata['artifact_sha256']['counts.npz']:
        raise ValueError('Synapse-count artifact integrity mismatch')
    if unpruned:
        original=json.loads((ROOT/'data/runtime/metadata.json').read_text())
        if metadata['artifact_sha256']['neurons.parquet']!=original['artifact_sha256']['neurons.parquet']:
            raise ValueError('Restored connectivity identity order differs from v0.1')
    counts=sparse.load_npz(path)
    if counts.shape!=(reference.n,reference.n) or not np.isfinite(counts.data).all() or np.any(counts.data<=0):
        raise ValueError('Count artifact has invalid dimensions or synapse counts')
    signs=reference.neurons.consensus_nt.map(coreconfig['sign_policy']['signs']).fillna(0).to_numpy(np.float32)
    weights=counts.astype(np.float32).multiply(signs[None,:]).tocsr()
    weights.eliminate_zeros();weights.sort_indices()
    return weights, reference.neurons, dict(counts_sha256=h.hexdigest(),
        neurons_sha256=metadata['artifact_sha256']['neurons.parquet'],
        restored_weak_connections=unpruned, retained_connections=int(counts.nnz),
        effective_connections=int(weights.nnz), synapses=int(counts.sum()))

class CountBrain(FastBrain):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.silenced=np.empty(0,dtype=np.int64)

    def step(self, external=None):
        spikes=super().step(external)
        # A documented alternative to v0.1, inspired by Shiu's spike-reset model.
        # Other timing/integration/stimulation assumptions differ from that paper.
        self.syn[spikes!=0]=0.
        if len(self.silenced):
            spikes[self.silenced]=0.;self.activity[self.silenced]=0.
            self.v[self.silenced]=self.p['reset'];self.syn[self.silenced]=0.
        return spikes

def parameters(coreconfig, tonic=1.5):
    if not np.isfinite(tonic) or not 0<=tonic<=2:
        raise ValueError('Tonic drive must be finite and between 0 and 2')
    return dict(coreconfig['model'],**dict(PARAMETERS,baseline_current=float(tonic)))
