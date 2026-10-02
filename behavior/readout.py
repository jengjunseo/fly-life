"""Motor output depends only on descending-neuron activity and neural time."""
import numpy as np

class EscapeReadout:
    def __init__(self,brain):
        self.indices=brain.resolve(dict(types=['DNp01']))
        if len(self.indices)!=2:raise ValueError('Expected two identified giant fibers')
        self.threshold=float(brain.activity[self.indices].max())+35.
        self.next_ms=0.
        self.enabled=True

    def decode(self,brain):
        rate=float(brain.activity[self.indices].max())
        now=brain.step_count*brain.p['dt_ms']
        pulse=self.enabled and rate>self.threshold and now>=self.next_ms
        if pulse:self.next_ms=now+600.
        return dict(escape_motor=float(pulse),escape_activity_hz=rate,
                    escape_threshold_hz=self.threshold,escape_enabled=self.enabled)
