"""No keys, stimuli, world state or body state enter this decoder."""
import math


def decode(activity_hz, parameters):
    values={k:float(activity_hz[k]) for k in ['left','right','forward']}
    if not all(math.isfinite(v) and v>=0 for v in values.values()):
        raise ValueError('Activity must be finite nonnegative Hz')
    scale=float(parameters['activity_scale_hz'])
    if not math.isfinite(scale) or scale<=0:
        raise ValueError('Activity scale must be positive')
    forward=min(1.,max(0.,parameters['forward_gain']*values['forward']/scale))
    turn=min(1.,max(-1.,parameters['turn_gain']*(values['right']-values['left'])/scale))
    return dict(forward=forward,turn=turn)
