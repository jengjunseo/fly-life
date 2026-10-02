"""Identity-resolved sensory current only; no motor/body/world-event inputs."""
import math
import numpy as np

MAPPINGS={
 'lc4':dict(types=['LC4']), 'lplc2':dict(types=['LPLC2']), 'figure':dict(types=['LC9']),
 'food_odor':dict(types=['ORN_DM1']), 'taste':dict(types=['GNG540']),
 'fly_odor':dict(types=['ORN_VA1v','ORN_VA1d']),
 'hot':dict(types=['TRN_VP2']), 'cold':dict(types=['TRN_VP3a','TRN_VP3b']),
 'feeding_observation':dict(types=['GNG588']), 'courtship_observation':dict(type_regex='^pC1')}
LEVELS={'lc4':'VERIFIED_IDENTITY_EXPERIMENTAL_ENCODING','lplc2':'VERIFIED_IDENTITY_EXPERIMENTAL_ENCODING',
 'figure':'EXPERIMENTAL_FIGURE_MOTION_NOT_ESCAPE','food_odor':'VERIFIED_ORN_EXPERIMENTAL_ODOR',
 'taste':'EXPERIMENTAL_CNS_SUGAR_SEL_PN_BYPASS','fly_odor':'VERIFIED_ORN_EXPERIMENTAL_NON_SEX_SPECIFIC_CUE',
 'hot':'VERIFIED_TRN_EXPERIMENTAL_ENCODING','cold':'VERIFIED_TRN_EXPERIMENTAL_ENCODING',
 'feeding_observation':'VERIFIED_ALIAS_GATE_DISABLED_UNRESOLVED','courtship_observation':'OBSERVATION_ONLY'}

def amplitudes(raw,p):
    # Every quantity is a sensory primitive, not an entity identifier or desired behavior.
    values=dict(lc4=0.,lplc2=0.,figure=0.,food_odor=0.,taste=0.,fly_odor=0.,hot=0.,cold=0.)
    if not p['enabled']: return values
    for figure in raw['figures']:
        size=figure['angular_size_deg']; expansion=figure['positive_expansion_deg_s']; contrast=figure['contrast']
        values['lc4']+=p['loom_cap']*min(1.,expansion/p['expansion_scale_deg_s'])*contrast
        # A size channel gated by expansion, not mere proximity or predator presence.
        values['lplc2']+=p['loom_cap']*min(1.,size/p['size_scale_deg'])*min(1.,expansion/p['expansion_scale_deg_s'])*contrast
        values['figure']+=p['figure_cap']*min(1.,figure['angular_motion_deg_s']/p['figure_motion_scale_deg_s'])*contrast
    for name in ['lc4','lplc2']:values[name]=min(p['loom_cap'],values[name])
    values['figure']=min(p['figure_cap'],values['figure'])
    values['food_odor']=p['chemical_cap']*raw['food_odor'];values['fly_odor']=p['chemical_cap']*raw['fly_odor']
    values['taste']=p['chemical_cap']*raw['contact_sugar'] if p['taste_enabled'] else 0.
    offset=(raw['temperature_c']-p['thermal_reference_c'])/p['thermal_span_c'];rate=raw['temperature_change_c_s']/p['thermal_rate_scale_c_s']
    values['hot']=p['thermal_cap']*min(1.,max(0.,offset)+max(0.,rate))
    values['cold']=p['thermal_cap']*min(1.,max(0.,-offset)+max(0.,-rate))
    if not all(math.isfinite(v) and v>=0 for v in values.values()): raise ValueError('Invalid sensory current')
    return values

class Encoder:
    def __init__(self,brain,params):
        self.brain=brain;self.params=params
        self.selectors=dict(MAPPINGS);self.levels=dict(LEVELS)
        self.indices={name:brain.resolve(selector) for name,selector in MAPPINGS.items()}
        for name,idx in self.indices.items():
            if not len(idx):raise ValueError(f'Unresolved mapping: {name}')
        if not brain.neurons.iloc[self.indices['taste']].synonyms.str.contains('Sugar SEL PN',na=False).all(): raise ValueError('Sugar PN alias mismatch')
        if not brain.neurons.iloc[self.indices['feeding_observation']].synonyms.str.contains('Fdg',na=False).all(): raise ValueError('Fdg alias mismatch')
        motor=brain.resolve(dict(types=['DNa01','DNa02','DNp09','DNp01']))
        observed=set(self.indices['feeding_observation'])|set(self.indices['courtship_observation'])|set(motor)
        if any(observed.intersection(idx) for name,idx in self.indices.items() if not name.endswith('observation')):raise ValueError('Direct readout/motor stimulus forbidden')

    def encode(self,raw):
        amps=amplitudes(raw,self.params);current=np.zeros(self.brain.n,np.float32);terms=[]
        for name,amp in amps.items():
            idx=self.indices[name];current+=self.brain.current(idx,amp)
            terms.append(dict(modality=name,amplitude=amp,bodyIds=self.brain.neurons.iloc[idx].bodyId.tolist(),level=LEVELS[name]))
        return current,terms

    def readouts(self):
        return {name:float(self.brain.read_activity(idx)['activity_hz'].mean()) for name,idx in self.indices.items()}

    def evidence(self):
        cols=['bodyId','type','instance','somaSide','superclass','class','receptorType','synonyms','consensus_nt']
        import json
        return {name:dict(selector=self.selectors[name],level=self.levels[name],members=json.loads(self.brain.neurons.iloc[idx][cols].to_json(orient='records'))) for name,idx in self.indices.items()}
