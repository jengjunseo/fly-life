from mvp.presets import PRESETS as ECO_PRESETS,configure as ecology_preset
PRESETS=('MOTOR TEST',)+ECO_PRESETS

def configure(name='MOTOR TEST',world_seed=20260914,duration=0):
    config=ecology_preset('CONTROL' if name=='MOTOR TEST' else name,world_seed,duration)
    config['mode']=name
    return config
