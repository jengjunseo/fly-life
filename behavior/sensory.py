"""Experimental hemispheric encoding with explicit anatomical laterality."""
import copy
import math
import numpy as np
from ecology.sensory import Encoder, MAPPINGS, LEVELS, amplitudes

class BilateralEncoder(Encoder):
    def __init__(self,brain,params):
        super().__init__(brain,params)
        self.indices['food_odor']=brain.resolve(dict(types=['ORN_DM1','ORN_VA2']))
        self.selectors['food_odor']=dict(types=['ORN_DM1','ORN_VA2'])
        self.sides={};self.members={}
        for name,idx in self.indices.items():
            rows=brain.neurons.iloc[idx]
            sides=rows.somaSide.fillna(rows.rootSide)
            self.sides[name]={s:idx[sides.eq(s).to_numpy()] for s in ['L','R']}
            self.sides[name]['U']=idx[~sides.isin(['L','R']).to_numpy()]
            self.members[name]={s:brain.neurons.iloc[j].bodyId.tolist() for s,j in self.sides[name].items()}

    def encode(self,raw):
        current=np.zeros(self.brain.n,np.float32);terms=[]
        common=amplitudes(raw,self.params)
        directional={}
        for side,sign in [('L',-1.),('R',1.)]:
            local=dict(raw,**raw.get('bilateral',{}).get(side,{}))
            # Coarse hemispheric projection. Not measured LC receptive fields.
            # A frontal object stimulates both; side fields overlap smoothly.
            local['figures']=[dict(f,contrast=f['contrast']*
                (.5+.5*sign*math.sin(f['bearing_radians']))) for f in raw['figures']]
            directional[side]=amplitudes(local,self.params)
        for name,common_amp in common.items():
            for side,idx in self.sides[name].items():
                if not len(idx):continue
                amp=directional[side][name] if side!='U' else common_amp
                current[idx]+=np.float32(amp)
                terms.append(dict(modality=name,side=side,amplitude=amp,
                    bodyIds=self.members[name][side],level=LEVELS[name],
                    encoding='EXPERIMENTAL_HEMISPHERIC_VISUAL' if name in ['lc4','lplc2','figure'] else 'LOCAL_ANTENNAL_SAMPLE'))
        return current,terms

    def evidence(self):
        evidence=super().evidence()
        evidence['food_odor']['selector']=dict(types=['ORN_DM1','ORN_VA2'])
        for name,item in evidence.items():
            item['bilateral_bodyIds']=copy.deepcopy(self.members[name])
            item['laterality']='somaSide, otherwise rootSide; unassigned members get common feature'
        return evidence
