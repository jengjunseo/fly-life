from mvp.presets import PRESETS as ECO_PRESETS,configure as ecology_preset
from behavior.presets import EXTRA_PRESETS,configure as behavior_preset
PRESETS=('MOTOR TEST',)+ECO_PRESETS+EXTRA_PRESETS

def configure(name='MOTOR TEST',world_seed=20260914,duration=0,behavior=False):
    if behavior:return behavior_preset(name,world_seed,duration)
    config=ecology_preset('CONTROL' if name=='MOTOR TEST' else name,world_seed,duration)
    config['mode']=name
    return config
