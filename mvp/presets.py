"""Controlled initial conditions; never a focal-fly movement policy."""
import copy
import math
from pathlib import Path
from ecology.model import load_config

ROOT = Path(__file__).resolve().parents[1]
PRESETS = ('CONTROL', 'PREDATOR', 'FOOD', 'FEMALE', 'HEAT', 'PREDATOR + HEAT')
# Previous wall centres +/-4, wall thickness .2: actual interior was 7.8 square.
OLD_HALF = 4.0
WALL_THICKNESS = .2
NEW_HALF = .1 + (OLD_HALF - .1) * math.sqrt(2)


def configure(name='CONTROL', world_seed=20260914, duration=0):
    if name not in PRESETS:
        raise ValueError('Unknown experiment preset')
    cfg = load_config(ROOT / 'ecology/config.json', 'certification')
    cfg.update(mode=name, certification=False, world_seed=int(world_seed),
               initial_gut=0., duration_s=float(duration), horizon_s=0.)
    # Fixed 0.5s baseline, finite stimulus, then recovery. No random background events.
    events = {
        'PREDATOR': dict(kind='predator', at_s=.5, position=[.8,.3,-2.5]),
        'FOOD': dict(kind='food', at_s=.5, position=[0.,.22,0.]),
        'FEMALE': dict(kind='female', at_s=.5, position=[.3,.22,0.], wander=[[0.,1.],[.5,-1.]]),
        'HEAT': dict(kind='heat', at_s=.5),
    }
    selected = [] if name == 'CONTROL' else (['PREDATOR','HEAT'] if name == 'PREDATOR + HEAT' else [name])
    cfg['initial_events'] = [copy.deepcopy(events[x]) for x in selected]
    cfg['arena_half_width'] = NEW_HALF
    return cfg


def area_evidence():
    old = 2 * OLD_HALF - WALL_THICKNESS
    new = 2 * NEW_HALF - WALL_THICKNESS
    return dict(definition='horizontal floor inside wall collision faces, before fly-radius clearance',
                old_wall_center_width=8., new_wall_center_width=2*NEW_HALF,
                wall_thickness=WALL_THICKNESS, old_width=old, old_depth=old, old_area=old**2,
                new_width=new, new_depth=new, new_area=new**2, ratio=(new/old)**2,
                fly_radius=.19, old_center_accessible_width=old-.38,
                new_center_accessible_width=new-.38)
