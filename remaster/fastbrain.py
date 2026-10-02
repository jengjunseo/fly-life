"""Exact-order sparse spike delivery and fused float32 reference equations."""
import numpy as np
from numba import njit
from braincore.core import Brain


@njit(cache=True, nogil=True, fastmath=False)
def deliver(ptr, target, weight, spikes, incoming):
    incoming[:] = np.float32(0.)
    # CSR rows are source-sorted. Visit firing sources in that same order.
    for source in range(len(spikes)):
        if spikes[source] != 0:
            for edge in range(ptr[source], ptr[source + 1]):
                row = target[edge]
                incoming[row] = np.float32(incoming[row] + np.float32(weight[edge] * spikes[source]))


@njit(cache=True, nogil=True, fastmath=False)
def integrate(v, syn, spikes, refractory, activity, baseline, incoming, noise,
              external, has_external, decay, activity_decay, gain, noise_std,
              alpha, rest, reset, threshold, refractory_steps, activity_gain, rate):
    for i in range(len(v)):
        syn[i] = np.float32(np.float32(syn[i] * decay) + np.float32(gain * incoming[i]))
        active = refractory[i] == 0
        if not active:
            refractory[i] -= 1
        drive = np.float32(baseline[i] + syn[i])
        if noise_std != 0:
            drive = np.float32(drive + np.float32(noise_std * noise[i]))
        if has_external:
            drive = np.float32(drive + external[i])
        if active:
            delta = np.float32(np.float32(rest - v[i]) + drive)
            v[i] = np.float32(v[i] + np.float32(alpha * delta))
        else:
            v[i] = reset
        fired = active and v[i] >= threshold
        spikes[i] = np.float32(1.) if fired else np.float32(0.)
        if fired:
            v[i] = reset
            refractory[i] = refractory_steps
        activity[i] = np.float32(np.float32(activity[i] * activity_decay) +
                                 np.float32(np.float32(activity_gain * spikes[i]) * rate))


class FastBrain(Brain):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.w.has_sorted_indices:
            raise ValueError('Exact spike delivery requires source-sorted reference CSR rows')
        self.outgoing = self.w.tocsc()
        self.incoming = np.zeros(self.n, np.float32)
        self.noise = np.zeros(self.n, np.float32)
        self.zero = np.zeros(self.n, np.float32)

    def step(self, external=None):
        if external is not None:
            external = np.asarray(external, dtype=np.float32)
            if external.shape != (self.n,) or not np.isfinite(external).all():
                raise ValueError('External current must be a finite N-vector')
        p = self.p
        if p['noise_std']:
            self.rng.standard_normal(dtype=np.float32, out=self.noise)
        c = self.outgoing
        deliver(c.indptr, c.indices, c.data, self.spikes, self.incoming)
        integrate(self.v, self.syn, self.spikes, self.refractory, self.activity,
                  self.baseline, self.incoming, self.noise,
                  self.zero if external is None else external, external is not None,
                  self.syn_decay, self.activity_decay, np.float32(p['recurrent_gain']),
                  np.float32(p['noise_std']), np.float32(p['dt_ms'] / p['tau_m_ms']),
                  np.float32(p['rest']), np.float32(p['reset']), np.float32(p['threshold']),
                  self.refractory_steps, np.float32(1 - self.activity_decay),
                  np.float32(1000 / p['dt_ms']))
        self.step_count += 1
        if self.step_count % 100 == 0 and not (np.isfinite(self.v).all() and np.isfinite(self.syn).all()):
            raise FloatingPointError('LIF state became nonfinite')
        return self.spikes
