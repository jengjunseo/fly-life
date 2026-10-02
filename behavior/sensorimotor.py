"""Explicit, separately selectable sensory/motor calibration hypotheses.

The brain still uses the actual graph. These are not a validated animal model.
No entity class, target coordinate or desired movement enters either decoder.
"""
import math
import numpy as np
from behavior.world import ExperimentWorld
from ecology.model import distance, bearing
from behavior.sensory import BilateralEncoder

PSI_SOURCE='https://pubmed.ncbi.nlm.nih.gov/21304452/'
THERMAL_SOURCE='https://pmc.ncbi.nlm.nih.gov/articles/PMC6709853/'
STEERING_SOURCE='https://pmc.ncbi.nlm.nih.gov/articles/PMC12279373/'
OBJECT_SOURCE='https://pmc.ncbi.nlm.nih.gov/articles/PMC12212441/'

class SensorimotorWorld(ExperimentWorld):
    def sense(self,dt):
        raw=super().sense(dt)
        old=getattr(self,'object_geometry',{})
        new={};figures=[]
        for ident,e in self.entities.items():
            d=distance(self.fly,e['position'])
            size=math.degrees(2*math.atan2(e['radius'],max(d,1e-6)))
            angle=bearing(self.fly,e['position'],self.yaw)
            prior=old.get(ident)
            expansion=max(0.,(size-prior[0])/dt) if prior and dt else 0.
            motion=abs(math.degrees(math.atan2(math.sin(angle-prior[1]),math.cos(angle-prior[1]))))/dt if prior and dt else 0.
            compensated_expansion=compensated_motion=0.
            if prior and dt:
                # Predicted optic flow from the measured body motion is removed
                # for generic looming/large-figure channels. This approximation
                # models self-motion compensation; all object classes use it.
                prev_d=distance(self.fly,prior[2])
                prev_size=math.degrees(2*math.atan2(e['radius'],max(prev_d,1e-6)))
                prev_angle=bearing(self.fly,prior[2],self.yaw)
                compensated_expansion=max(0.,(size-prev_size)/dt)
                compensated_motion=abs(math.degrees(math.atan2(math.sin(angle-prev_angle),math.cos(angle-prev_angle))))/dt
            # Object material contrast, not a biological identity or value label.
            contrast={'predator':1.,'female':.35,'food':.8,'feces':.4}[e['kind']]
            figures.append(dict(angular_size_deg=size,positive_expansion_deg_s=expansion,
                bearing_radians=angle,angular_motion_deg_s=motion+expansion/2.,contrast=contrast))
            figures[-1].update(compensated_expansion_deg_s=compensated_expansion,
                compensated_motion_deg_s=compensated_motion+compensated_expansion/2.)
            new[ident]=(size,angle,list(e['position']))
        self.object_geometry=new;raw['figures']=figures
        return raw

class SensorimotorEncoder(BilateralEncoder):
    def __init__(self,brain,params):
        super().__init__(brain,params)
        idx=brain.resolve(dict(types=['LC10a']))
        if len(idx)!=275:raise ValueError('Expected 275 identified MaleCNS LC10a cells')
        side=brain.neurons.iloc[idx].somaSide
        self.indices['small_object']=idx
        self.selectors['small_object']=dict(types=['LC10a'])
        self.levels['small_object']='VERIFIED_LC10a_EXPERIMENTAL_OBJECT_ENCODING'
        self.sides['small_object']={s:idx[side.eq(s).to_numpy()] for s in ['L','R']}
        self.members['small_object']={s:brain.neurons.iloc[j].bodyId.tolist() for s,j in self.sides['small_object'].items()}

    def encode(self,raw):
        vision=self.params.get('vision_enabled',True)
        compensated=dict(raw,figures=[dict(f,positive_expansion_deg_s=f.get('compensated_expansion_deg_s',f['positive_expansion_deg_s']),
            angular_motion_deg_s=f.get('compensated_motion_deg_s',f['angular_motion_deg_s'])) for f in raw['figures']] if vision else [])
        current,terms=super().encode(compensated)
        if not self.params['enabled']:return current,terms
        for term in terms:
            if term['modality'] in ['food_odor','fly_odor','taste'] and not self.params.get('chemical_enabled',True):
                current[self.sides[term['modality']][term['side']]]-=np.float32(term['amplitude'])
                term['amplitude']=0.
        # Phasic cooling cells: warming suppresses, cooling excites, steady T
        # does not provide a persistent cool-channel offset. Exact scaling is
        # assumed, with measured response polarity as the constraint.
        for term in terms:
            name,side=term['modality'],term['side']
            if name not in ['hot','cold']:continue
            local=raw.get('bilateral',{}).get(side,raw)
            rate=local['temperature_change_c_s']
            if name=='cold':amp=-3.*math.tanh(rate/.3)
            else:
                delta=np.clip(local['temperature_c']-25.,-15.,15.)
                amp=1.5*(4.4**(delta/10.)-1.)+math.tanh(rate/.3)
            if not self.params.get('thermal_enabled',True):amp=0.
            idx=self.sides[name][side]
            current[idx]+=np.float32(amp-term['amplitude'])
            term.update(amplitude=float(amp),encoding='PHYSIOLOGY_INSPIRED_SIGNED_THERMAL_CURRENT')
        for side,sign in [('L',-1.),('R',1.)]:
            amp=0.
            for f in raw['figures'] if vision else []:
                # Broad small-object size/motion tuning and overlapping fields
                # are approximations, not reconstructed LC10a receptive fields.
                size=f['angular_size_deg']
                tuning=math.exp(-((size-12.)/25.)**2)
                motion=min(1.,f['angular_motion_deg_s']/20.)
                amp+=6.*tuning*motion*f['contrast']*(.5+.5*sign*math.sin(f['bearing_radians']))
            amp=min(6.,amp);idx=self.sides['small_object'][side]
            current[idx]+=np.float32(amp)
            terms.append(dict(modality='small_object',side=side,amplitude=amp,
                bodyIds=self.members['small_object'][side],level='VERIFIED_LC10a_EXPERIMENTAL_OBJECT_ENCODING',
                encoding='EXPERIMENTAL_HEMISPHERIC_SMALL_OBJECT_MOTION'))
        return current,terms

    def evidence(self):
        out=super().evidence()
        out['small_object'].update(source=OBJECT_SOURCE,
            limitation='Object motion input, not certified food recognition or food value')
        for name in ['hot','cold']:out[name]['physiology_source']=THERMAL_SOURCE
        return out

class SteeringReadout:
    """DNa02-only ipsiversive steering; zero offset from unstimulated warmup.

    The slope (0.3 rad/s per Hz), 150 ms smoothing and bias correction are assumed
    actuator calibration. The slope was tuned after an unsuccessful engineering
    food trial; it is not independently measured biology. Target data never
    enters this readout.
"""
    def __init__(self,brain,warmup_ms=500.):
        rows=brain.neurons
        self.sides={s:np.flatnonzero((rows.type.eq('DNa02')&rows.somaSide.eq(s)).to_numpy()) for s in ['L','R']}
        if any(len(v)!=1 for v in self.sides.values()):raise ValueError('Expected one DNa02 per side')
        self.total=0.;self.count=0;self.bias=0.;self.filtered=0.
        self.calibration_start_ms=max(0.,warmup_ms-min(1000.,warmup_ms/2.))

    def difference(self,brain):
        return float(brain.activity[self.sides['R']].mean()-brain.activity[self.sides['L']].mean())

    def observe(self,brain,warmup):
        difference=self.difference(brain)
        if warmup:
            if brain.step_count*brain.p['dt_ms']>=self.calibration_start_ms:
                self.total+=difference;self.count+=1;self.bias=self.total/self.count
            self.filtered=0.
        else:
            alpha=1.-math.exp(-brain.p['dt_ms']/150.)
            self.filtered+=alpha*(difference-self.bias-self.filtered)

    def decode(self,max_turn):
        return dict(turn=float(np.clip(.3*self.filtered/max_turn,-1.,1.)),
            steering_difference_hz=self.filtered,steering_warmup_bias_hz=self.bias,
            steering_model='DNa02_ONLY_WARMUP_CALIBRATED_150MS',steering_slope_rad_s_per_hz=.3)
