"""Experimental conductance LIF. Distinct scientific model, not v0.1 equivalence.

Measured connectivity and presynaptic signs are unchanged. Conductance reversal
potentials bound inhibition rather than permitting arbitrary negative voltages.
All intrinsic/reversal/tonic parameters are assumptions, not MaleCNS measurements.
"""
import numpy as np
from numba import njit
from remaster.fastbrain import FastBrain

@njit(cache=True, nogil=True)
def step_cells(v, ge, gi, spikes, refractory, activity, baseline, exc, inh, noise,
               external, decay, gain, noise_std, alpha, threshold, reset, rest,
               refractory_steps, ema, e_exc, e_inh, dt):
    for i in range(len(v)):
        ge[i] = ge[i]*decay + gain*exc[i]
        gi[i] = gi[i]*decay + gain*inh[i]
        if refractory[i] != 0:
            refractory[i] -= 1
            v[i] = reset
            fired = False
        else:
            total = 1. + ge[i] + gi[i]
            steady = (rest + baseline[i] + external[i] + noise_std*noise[i]
                      + ge[i]*e_exc + gi[i]*e_inh)/total
            v[i] = steady + (v[i]-steady)*np.exp(-alpha*total)
            fired = v[i] >= threshold
            if fired:
                v[i] = reset
                refractory[i] = refractory_steps
        spikes[i] = 1. if fired else 0.
        activity[i] = activity[i]*ema + (1.-ema)*spikes[i]*1000./dt

@njit(cache=True, nogil=True)
def delivery(ptr, target, weight, spikes, exc, inh):
    exc[:] = 0.; inh[:] = 0.
    for source in range(len(spikes)):
        if spikes[source] != 0:
            for edge in range(ptr[source], ptr[source+1]):
                w = weight[edge]
                if w > 0: exc[target[edge]] += w
                else: inh[target[edge]] -= w

class ConductanceBrain(FastBrain):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ge = np.zeros(self.n, np.float32)
        self.gi = np.zeros(self.n, np.float32)
        self.exc = np.zeros(self.n, np.float32)
        self.inh = np.zeros(self.n, np.float32)

    def step(self, external=None):
        if external is not None:
            external=np.asarray(external,dtype=np.float32)
            if external.shape!=(self.n,) or not np.isfinite(external).all():
                raise ValueError('External current must be a finite N-vector')
        p=self.p; c=self.outgoing
        if p['noise_std']:self.rng.standard_normal(dtype=np.float32,out=self.noise)
        delivery(c.indptr,c.indices,c.data,self.spikes,self.exc,self.inh)
        step_cells(self.v,self.ge,self.gi,self.spikes,self.refractory,self.activity,
                   self.baseline,self.exc,self.inh,self.noise,
                   self.zero if external is None else external,self.syn_decay,
                   p['recurrent_gain'],p['noise_std'],p['dt_ms']/p['tau_m_ms'],
                   p['threshold'],p['reset'],p['rest'],self.refractory_steps,
                   self.activity_decay,p.get('e_exc',52./7.),p.get('e_inh',-18./7.),p['dt_ms'])
        self.syn[:] = self.ge-self.gi
        self.step_count+=1
        if self.step_count%100==0 and not (np.isfinite(self.v).all() and np.isfinite(self.ge).all() and np.isfinite(self.gi).all()):
            raise FloatingPointError('Conductance state became nonfinite')
        return self.spikes
