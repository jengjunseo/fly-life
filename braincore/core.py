import json
import math
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse


def select(neurons, selector):
    """Union of exact types, explicit bodyIds, and optional type regex."""
    mask = np.zeros(len(neurons), dtype=bool)
    if selector.get('types'):
        mask |= neurons['type'].isin(selector['types']).to_numpy()
    if selector.get('bodyIds'):
        mask |= neurons['bodyId'].isin(selector['bodyIds']).to_numpy()
    if selector.get('type_regex'):
        mask |= neurons['type'].fillna('').str.contains(selector['type_regex'], regex=True).to_numpy()
    return np.flatnonzero(mask)


def signed_normalized_matrix(counts, signs):
    """Counts[target, source]; presynaptic signs; absolute incoming normalization."""
    w = counts.astype(np.float32).multiply(signs[None, :]).tocsr()
    w.eliminate_zeros()
    denom = np.maximum(np.asarray(abs(w).sum(axis=1)).ravel(), 1.0)
    w.data /= np.repeat(denom, np.diff(w.indptr))
    return w


class Brain:
    def __init__(self, weights, parameters, seed=0, neurons=None):
        if weights.shape[0] != weights.shape[1]:
            raise ValueError('Connectivity must be square')
        self.p = dict(parameters)
        p = self.p
        for key in ['dt_ms', 'tau_m_ms', 'tau_syn_ms', 'activity_tau_ms']:
            if not math.isfinite(p[key]) or p[key] <= 0:
                raise ValueError(f'{key} must be finite and positive')
        if p['dt_ms'] > p['tau_m_ms'] or p['reset'] >= p['threshold'] or p['refractory_ms'] < 0:
            raise ValueError('Invalid timestep, reset, or refractory period')
        if not all(math.isfinite(v) for v in p.values()):
            raise ValueError('Model parameters must be finite')
        self.w = weights.astype(np.float32).tocsr()
        if not np.isfinite(self.w.data).all():
            raise ValueError('Nonfinite weights')
        self.n = self.w.shape[0]
        self.neurons = neurons
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.v = np.full(self.n, p['rest'], np.float32)
        self.syn = np.zeros(self.n, np.float32)
        self.spikes = np.zeros(self.n, np.float32)
        self.refractory = np.zeros(self.n, np.int32)
        self.activity = np.zeros(self.n, np.float32)
        self.baseline = (p['baseline_current'] + p['baseline_heterogeneity'] *
                         self.rng.standard_normal(self.n, dtype=np.float32))
        self.syn_decay = np.float32(np.exp(-p['dt_ms'] / p['tau_syn_ms']))
        self.activity_decay = np.float32(np.exp(-p['dt_ms'] / p['activity_tau_ms']))
        self.refractory_steps = math.ceil(p['refractory_ms'] / p['dt_ms'])
        self.step_count = 0

    @classmethod
    def load(cls, runtime, config, seed=None):
        runtime = Path(runtime)
        metadata = json.loads((runtime / 'metadata.json').read_text())
        if metadata['dataset'] != config['dataset']:
            raise ValueError('Dataset mismatch')
        if metadata['preprocessing'] != config['preprocessing'] or metadata['groups'] != config['groups']:
            raise ValueError('Config mapping/pruning changed: regenerate artifact')
        if metadata['sign_policy'] != config['sign_policy']:
            raise ValueError('Sign policy changed: regenerate artifact')
        if metadata['matrix_orientation'] != 'W[target, source]; input = W @ previous_step_spikes':
            raise ValueError('Matrix orientation mismatch')
        for name in ['weights.npz', 'neurons.parquet']:
            h = hashlib.sha256()
            with (runtime / name).open('rb') as f:
                for block in iter(lambda:f.read(8*1024*1024),b''):
                    h.update(block)
            if h.hexdigest() != metadata['artifact_sha256'][name]:
                raise ValueError(f'Artifact integrity mismatch: {name}')
        neurons = pd.read_parquet(runtime / 'neurons.parquet')
        weights = sparse.load_npz(runtime / 'weights.npz')
        if len(neurons) != weights.shape[0] or not np.array_equal(neurons.runtime_index, np.arange(len(neurons))):
            raise ValueError('Identity/matrix alignment mismatch')
        return cls(weights, config['model'], seed if seed is not None else config['experiment']['seed'], neurons)

    def resolve(self, selector):
        if self.neurons is None:
            raise ValueError('No neuron identity table attached')
        return select(self.neurons, selector)

    def current(self, indices, amplitude):
        """Return current vector affecting only these runtime indices."""
        indices = np.asarray(indices, dtype=np.int64)
        if (indices < 0).any() or (indices >= self.n).any() or not np.isfinite(amplitude):
            raise ValueError('Invalid stimulus')
        external = np.zeros(self.n, np.float32)
        external[indices] = amplitude
        return external

    def steps_for(self, duration_ms):
        count = round(duration_ms / self.p['dt_ms'])
        if duration_ms < 0 or not np.isclose(count * self.p['dt_ms'], duration_ms):
            raise ValueError('Duration must be a nonnegative integer number of timesteps')
        return count

    def step(self, external=None):
        """One timestep; W @ preceding spikes gives a one-step transmission delay.

        Returns a reused float32 spike vector. Copy it if retaining across steps.
        Two refractory steps hold reset for the next two complete timesteps.
        """
        p = self.p
        if external is not None:
            external = np.asarray(external, dtype=np.float32)
            if external.shape != (self.n,) or not np.isfinite(external).all():
                raise ValueError('External current must be a finite N-vector')
        self.syn *= self.syn_decay
        self.syn += np.float32(p['recurrent_gain']) * (self.w @ self.spikes)
        active = self.refractory == 0
        self.refractory[~active] -= 1
        drive = self.baseline + self.syn
        if p['noise_std']:
            drive += np.float32(p['noise_std']) * self.rng.standard_normal(self.n, dtype=np.float32)
        if external is not None:
            drive += external
        self.v[active] += np.float32(p['dt_ms'] / p['tau_m_ms']) * (
            p['rest'] - self.v[active] + drive[active])
        self.v[~active] = p['reset']
        fired = active & (self.v >= p['threshold'])
        self.spikes[:] = fired
        self.v[fired] = p['reset']
        self.refractory[fired] = self.refractory_steps
        self.activity *= self.activity_decay
        self.activity += (1 - self.activity_decay) * self.spikes * np.float32(1000 / p['dt_ms'])
        self.step_count += 1
        if self.step_count % 100 == 0 and not (np.isfinite(self.v).all() and np.isfinite(self.syn).all()):
            raise FloatingPointError('LIF state became nonfinite')
        return self.spikes

    def warmup(self, duration_ms):
        for _ in range(self.steps_for(duration_ms)):
            self.step()

    def read_activity(self, indices):
        """EMA activity in Hz and current-step spikes for a selected group."""
        return dict(activity_hz=self.activity[indices].copy(), spikes=self.spikes[indices].copy())

    def spike_body_ids(self):
        if self.neurons is None:
            raise ValueError('No identity table')
        return self.neurons.bodyId.to_numpy()[self.spikes.astype(bool)]
