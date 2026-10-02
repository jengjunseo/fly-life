"""Local bilateral sensory measurements. Never emits a movement command."""
import math
from ecology.model import World, distance

class ExperimentWorld(World):
    def __init__(self,cfg):
        self.path_length=0.;self.shade_seconds=0.;self.heat_exposure=0.
        super().__init__(cfg)

    def advance(self,dt,pose,yaw,feeding_hz=0.):
        previous=list(self.fly)
        super().advance(dt,pose,yaw,feeding_hz)
        self.path_length+=distance(previous,pose)
        self.shade_seconds+=dt if self.in_shade else 0.
        self.heat_exposure+=max(0.,self.sensor['temperature_c']-28.)*dt

    def snapshot(self):
        return dict(super().snapshot(),experiment_measurements=dict(path_length=self.path_length,
            shade_seconds=self.shade_seconds,heat_exposure_c_s=self.heat_exposure,
            interpretation='OBSERVATION_ONLY; compare mirrored trials and neural ablations before claiming behavior'))

    def local_temperature(self, pose):
        shade=self.cfg['shade']
        offsets=[abs(pose[k]-shade['center'][k])-shade['half_size'][k] for k in [0,2]]
        inside=max(offsets)<=0
        outside=math.hypot(max(0.,offsets[0]),max(0.,offsets[1]))
        # Assumed surrounding air mixing field, explicitly part of world physics.
        cooling=shade['cooling_c']*math.exp(-outside/.6)
        return self.ambient()-cooling,inside

    def antennae(self):
        # Body geometry units: two sensors near the front, separated by 0.28 units.
        forward=[-math.sin(self.yaw),0.,-math.cos(self.yaw)]
        right=[math.cos(self.yaw),0.,-math.sin(self.yaw)]
        return {side:[self.fly[k]+.28*forward[k]+sign*.14*right[k] for k in range(3)]
                for side,sign in [('L',-1),('R',1)]}

    def sense(self, dt):
        raw=super().sense(dt)
        previous=getattr(self,'antenna_temperatures',None)
        bilateral={}
        for side,pose in self.antennae().items():
            food=fly=0.
            for e in self.entities.values():
                if e['kind']=='food':food+=math.exp(-distance(pose,e['position'])/self.cfg['food']['odor_scale'])
                elif e['kind']=='female':fly+=math.exp(-distance(pose,e['position'])/self.cfg['female']['pheromone_scale'])
            temp,_=self.local_temperature(pose)
            bilateral[side]=dict(food_odor=min(food,1.),fly_odor=min(fly,1.),temperature_c=temp,
                temperature_change_c_s=(temp-previous[side])/dt if previous is not None and dt else 0.)
        self.antenna_temperatures={s:r['temperature_c'] for s,r in bilateral.items()}
        raw['bilateral']=bilateral
        return raw
