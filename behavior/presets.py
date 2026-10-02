"""Longer, mirrored assays. Schedules affect the world, never motors."""
from pathlib import Path
from ecology.model import load_config
from mvp.presets import NEW_HALF

ROOT=Path(__file__).resolve().parents[1]
EXTRA_PRESETS=('FOOD RIGHT','HEAT RIGHT')

def configure(name,seed,duration):
    cfg=load_config(ROOT/'ecology/config.json')
    cfg.update(mode=name,world_seed=int(seed),duration_s=float(duration),horizon_s=0.,
               initial_gut=0.,arena_half_width=NEW_HALF,certification=False)
    cfg['food']['lifetime_s']=60.
    cfg['predator'].update(speed=1.6,lifetime_s=12.)
    cfg['heat'].update(ramp_s=2.,hold_s=30.,recover_s=4.)
    cfg['female']['lifetime_s']=20.
    cfg['shade']['center']=[-2.,0.,-1.5] if name=='HEAT' else [2.,0.,-1.5]
    plans={
        'PREDATOR':dict(kind='predator',at_s=2.,position=[1.,.3,-3.]),
        'FOOD':dict(kind='food',at_s=2.,position=[-1.5,.22,-2.]),
        'FOOD RIGHT':dict(kind='food',at_s=2.,position=[1.5,.22,-2.]),
        'FEMALE':dict(kind='female',at_s=2.,position=[1.,.22,-2.],wander=[[0.,0.],[5.,1.]]),
        'HEAT':dict(kind='heat',at_s=2.),'HEAT RIGHT':dict(kind='heat',at_s=2.)}
    cfg['initial_events']=[plans[p] for p in (['PREDATOR','HEAT'] if name=='PREDATOR + HEAT' else [name]) if p in plans]
    return cfg
