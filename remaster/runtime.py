"""Remaster adapter: certified equivalent compute, explicit neural actuator test."""
import argparse
import json
import sys
import time
import hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mvp.bridge import ConsoleRuntime
from braincore.core import Brain
from remaster.fastbrain import FastBrain
from remaster.presets import configure
from ecology.sensory import Encoder,amplitudes,LEVELS
from behavior.model import CountBrain,load_connectivity,parameters
from behavior.world import ExperimentWorld
from behavior.sensory import BilateralEncoder
from behavior.readout import EscapeReadout
from behavior.sensorimotor import SensorimotorWorld,SensorimotorEncoder,SteeringReadout

class EfficientEncoder(Encoder):
    def __init__(self,*args):
        super().__init__(*args)
        self.members={name:self.brain.neurons.iloc[idx].bodyId.tolist() for name,idx in self.indices.items()}

    def encode(self,raw):
        amps=amplitudes(raw,self.params);current=np.zeros(self.brain.n,np.float32);terms=[]
        for name,amp in amps.items():
            current[self.indices[name]]+=np.float32(amp)
            terms.append(dict(modality=name,amplitude=amp,bodyIds=self.members[name],level=LEVELS[name]))
        return current,terms

class RemasterRuntime(ConsoleRuntime):
    def __init__(self,*args):
        self.cached_data=None;self.cached_key=None;self.model_evidence={};self.escape=None;self.steering=None;self.steering_brain=None;self.gf_ablated=False;self.gf_brain=None;self.gf_indices=None
        self.test_until=0;self.test_group=None;self.test_current=None;self.active_test=None
        super().__init__(*args)
        self.gf_ablated=bool(self.config.get('gf_ablated',False))

    def load_brain(self):
        key=(self.config.get('scientific_model','frozen'),self.config.get('restore_weak',False),self.config.get('backend'))
        if key[0] in ('counts','sensorimotor'):
            if self.cached_key!=key:
                w,n,self.model_evidence=load_connectivity(self.coreconfig,key[1],psi_literature=key[0]=='sensorimotor');self.cached_data=(w,n);self.cached_key=key
            w,n=self.cached_data
            brain=CountBrain(w,parameters(self.coreconfig,self.config.get('tonic_current',1.5)),seed=self.config['seed'],neurons=n)
            if key[0]=='sensorimotor':
                kc_tonic=min(.85,float(self.config.get('tonic_current',1.5)))
                brain.baseline[n['class'].eq('Kenyon_Cell').to_numpy()]=kc_tonic
                self.model_evidence['excitability_profile']=dict(kenyon_cell_tonic=kc_tonic,
                    other_cells_tonic=self.config.get('tonic_current',1.5),
                    limitation='Sparse KC baseline hypothesis; cell dynamics are not experimentally fitted')
            if self.gf_ablated:brain.silenced=brain.resolve(dict(types=['DNp01']))
            return brain
        if self.cached_key!=key:self.cached_data=None;self.cached_key=key;self.model_evidence={}
        cls=FastBrain if self.config.get('backend')=='fast' else Brain
        if self.cached_data is None:
            brain=cls.load(ROOT/'data/runtime',self.coreconfig,seed=self.config['seed'])
            self.cached_data=(brain.w,brain.neurons)
            return brain
        weights,neurons=self.cached_data
        return cls(weights,self.coreconfig['model'],seed=self.config['seed'],neurons=neurons)

    def reset(self):
        self.escape=None;self.steering=None;self.steering_brain=None
        self.test_until=0;self.test_group=None;self.test_current=None;self.active_test=None
        super().reset()
        model=self.config.get('scientific_model','frozen')
        assumptions=['No world stimulus label, target position or desired action enters the motor decoder']
        if model!='frozen':assumptions += ['Tonic drive is an assumed arousal condition, not natural spontaneous activity',
            'Count-weighted spike-reset LIF is not equivalent to v0.1 or an exact Shiu replication',
            'Hemispheric vision and local air cooling are explicit experimental approximations',
            'GF readout drives a primitive jump, not a complete flight controller']
        if model=='sensorimotor':assumptions += [
            'KC tonic capped at 0.85; other cells use the selected tonic setting',
            'LC10a input is generic object motion, not food identity or reconstructed retinotopy',
            'Looming uses geometric self-motion compensation; LC10a retains retinal motion',
            'Signed thermal current approximates response polarity; ionic scales are assumed',
            'DNa02-only readout: 0.3 rad/s/Hz, 150 ms filter, unstimulated warmup bias',
            'GF takeoff: 4.2 vertical and 3 forward units/s, 9.8 gravity, 0.8/s drag; actuator assumptions',
            'PSI acetylcholine assignment is literature-supported, not changed dataset annotation']
        paths=['remaster/runtime.py','remaster/fastbrain.py','remaster/presets.py',
               'behavior/model.py','behavior/sensorimotor.py','behavior/sensory.py','behavior/readout.py',
               'behavior/world.py','behavior/presets.py','braincore/core.py','mvp/bridge.py','mvp/presets.py',
               'ecology/bridge.py','ecology/model.py','ecology/sensory.py','ecology/config.json',
               'body/main.gd','body/mvp/main.gd','body/ecology/main.gd','body/remaster/main.gd',
               'body/decoder.py','config.json','body/body_config.json']
        (self.logdir/f'model-generation-{self.generation}.json').write_text(json.dumps(dict(
            scientific_model=model,warmup_ms=self.config['warmup_ms'],parameters=self.brain.p,evidence=self.model_evidence,assumptions=assumptions,
            source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}),indent=2),encoding='utf-8')

    def create_world(self):
        if self.config.get('scientific_model')=='sensorimotor':return SensorimotorWorld(self.eco_config)
        return ExperimentWorld(self.eco_config) if self.config.get('scientific_model')=='counts' else super().create_world()

    def create_encoder(self):
        if self.config.get('scientific_model')=='sensorimotor':return SensorimotorEncoder(self.brain,self.eco_config['sensory'])
        cls=BilateralEncoder if self.config.get('scientific_model')=='counts' else EfficientEncoder
        return cls(self.brain,self.eco_config['sensory'])

    def sensory_assumptions(self):
        if self.config.get('scientific_model') in ('counts','sensorimotor'):
            return 'Experimental overlapping hemispheric visual projection, not measured retinotopy; separate antenna-local chemical and thermal samples; somaSide otherwise rootSide.'
        return super().sensory_assumptions()

    def decode_motor(self,activities):
        motor=super().decode_motor(activities)
        if self.config.get('scientific_model') in ('counts','sensorimotor'):
            if self.escape is None:self.escape=EscapeReadout(self.brain)
            self.escape.enabled=not self.gf_ablated
            motor.update(self.escape.decode(self.brain))
            if self.config.get('scientific_model')=='sensorimotor':
                motor.update(self.steering.decode(6.))
                motor['steering_activity_hz']={s:float(self.brain.activity[idx].mean()) for s,idx in self.steering.sides.items()}
                motor['max_turn_radians_per_neural_second']=6.
                motor['takeoff_forward_impulse']=3.
        return motor

    def advance_neurons(self,external=None):
        spikes=self.brain.step(external)
        if self.gf_ablated and not isinstance(self.brain,CountBrain):
            if self.gf_brain is not self.brain:
                self.gf_indices=self.brain.resolve(dict(types=['DNp01']));self.gf_brain=self.brain
            idx=self.gf_indices
            spikes[idx]=0.;self.brain.activity[idx]=0.;self.brain.v[idx]=self.brain.p['reset'];self.brain.syn[idx]=0.;self.brain.refractory[idx]=0
        if self.config.get('scientific_model')=='sensorimotor':
            if self.steering_brain is not self.brain:
                self.steering=SteeringReadout(self.brain,warmup_ms=self.config['warmup_ms']);self.steering_brain=self.brain
            self.steering.observe(self.brain,warmup=self.brain.step_count<=self.brain.steps_for(self.config['warmup_ms']))
        return spikes

    def configure_preset(self,name,seed,duration):
        cfg=configure(name,seed,duration,behavior=self.config.get('scientific_model') in ('counts','sensorimotor'))
        cfg['sensory']['enabled']=self.eco_config['sensory']['enabled']
        for key in ['vision_enabled','chemical_enabled','thermal_enabled']:cfg['sensory'][key]=self.eco_config['sensory'].get(key,True)
        return cfg

    def apply_actions(self):
        conditions=[m for m in self.pending_actions if m['kind'] in ('model_condition','sensory_condition','gf_condition','modality_condition')]
        self.pending_actions=[m for m in self.pending_actions if m['kind'] not in ('model_condition','sensory_condition','gf_condition','modality_condition')]
        for m in conditions:
            if m['id'] in self.command_ids:raise ValueError('Duplicate command')
            self.command_ids.add(m['id']);self.commands.append(m['id'])
            if m['kind']=='model_condition':
                if m['model'] not in ('counts','frozen','sensorimotor'):raise ValueError('Unknown scientific model')
                parameters(self.coreconfig,float(m['tonic_current']))
                self.config.update(scientific_model=m['model'],tonic_current=float(m['tonic_current']),restore_weak=bool(m['restore_weak']))
                self.config['warmup_ms']=self.config.get('sensorimotor_warmup_ms',2000) if m['model']=='sensorimotor' else 500
                if m['model']=='frozen' and self.eco_config['mode'] in ('FOOD RIGHT','HEAT RIGHT'):self.eco_config['mode']='CONTROL'
                self.eco_config=self.configure_preset(self.eco_config['mode'],self.eco_config['world_seed'],self.eco_config['duration_s'])
                self.pending_reset=True
            elif m['kind']=='sensory_condition':self.eco_config['sensory']['enabled']=bool(m['enabled'])
            elif m['kind']=='modality_condition':
                if m['modality'] not in ('vision','chemical','thermal') or self.config.get('scientific_model')!='sensorimotor':
                    raise ValueError('Individual modality ablation requires sensorimotor model and a known modality')
                self.eco_config['sensory'][m['modality']+'_enabled']=bool(m['enabled'])
            else:
                self.gf_ablated=not bool(m['enabled'])
                if isinstance(self.brain,CountBrain):
                    self.brain.silenced=self.brain.resolve(dict(types=['DNp01'])) if self.gf_ablated else np.empty(0,dtype=np.int64)
            event=dict(event=m['kind'].upper(),world_time_s=self.world.time,condition=m)
            self.recent_events.append(event);self.event_log.write(json.dumps(dict(generation=self.generation,**event))+'\n')
            self.log.write(json.dumps(dict(event='experimental_condition',message=m))+'\n')
        if conditions:self.event_log.flush();self.log.flush()
        neural=[m for m in self.pending_actions if m['kind']=='neural_test']
        self.pending_actions=[m for m in self.pending_actions if m['kind']!='neural_test']
        super().apply_actions()
        for m in neural:
            group=m['group']
            if group not in ('left','right','forward','stop'):raise ValueError('Invalid neural test')
            if m['id'] in self.command_ids:raise ValueError('Duplicate command')
            self.command_ids.add(m['id']);self.commands.append(m['id'])
            self.test_group=None if group=='stop' else group
            self.test_current=None if group=='stop' else self.brain.current(self.groups[group],3.)
            self.test_until=self.motor_steps+self.brain.steps_for(2000.)
            if group=='stop':self.recent_events.append(dict(event='NEURAL_TEST_STOP',world_time_s=self.world.time))
            self.log.write(json.dumps(dict(event='explicit_neural_test',message=m,
                group=group,amplitude=3.,duration_ms=2000.,
                bodyIds=[] if group=='stop' else self.brain.neurons.iloc[self.groups[group]].bodyId.tolist()))+'\n')
        if neural:self.log.flush()

    def compute_quantum(self,external,quantum,watched):
        if self.eco_config['mode']=='MOTOR TEST' and 500<=self.motor_steps<2500:
            auto=self.brain.current(self.groups['forward'],3.)
        else:auto=None
        for _ in range(quantum):
            self.receive()
            if not self.running:break
            test=self.test_current if self.motor_steps<self.test_until else auto
            active=self.test_group if self.motor_steps<self.test_until else ('forward' if auto is not None else None)
            if active!=self.active_test:
                event=dict(event='NEURAL_TEST_'+active.upper() if active else 'NEURAL_TEST_END',
                           world_time_s=self.motor_steps*self.brain.p['dt_ms']/1000,
                           artificial=True,source='manual' if self.motor_steps<self.test_until else 'preset',
                           amplitude=3. if active else 0.)
                self.recent_events.append(event)
                self.event_log.write(json.dumps(dict(generation=self.generation,**event))+'\n');self.event_log.flush()
            self.active_test=active
            current=external if test is None else external+test
            begin=time.perf_counter();spikes=self.advance_neurons(current)
            self.core_seconds+=time.perf_counter()-begin
            self.motor_steps+=1;self.batch_spikes+=int(spikes.sum())
            for name,idx in watched.items():self.counts[name]+=int(spikes[idx].sum())
        self.stimulus=None

    def console_metadata(self):
        return dict(backend='fast' if self.config.get('scientific_model') in ('counts','sensorimotor') else self.config.get('backend','reference'),brain_frame_ms=self.config['packet_neural_ms'],
                    scientific_model=self.config.get('scientific_model','frozen'),tonic_current=float(self.brain.p['baseline_current']) if self.brain else 0.,
                    count_tonic_setting=self.config.get('tonic_current',1.5),
                    restored_weak_connections=self.config.get('scientific_model') in ('counts','sensorimotor') and self.config.get('restore_weak',False),
                    restored_available=(ROOT/'data/behavior/counts.npz').exists(),
                    sensory_enabled=self.eco_config['sensory']['enabled'],gf_enabled=not self.gf_ablated,
                    modality_enabled={k:self.eco_config['sensory'].get(k+'_enabled',True) for k in ['vision','chemical','thermal']},
                    warmup_ms=self.config['warmup_ms'],
                    shade_center=self.world.cfg['shade']['center'],shade_half_size=self.world.cfg['shade']['half_size'],
                    neural_test=dict(active=self.active_test is not None,group=self.active_test,
                                     amplitude=3. if self.active_test else 0.,
                                     automatic=self.eco_config['mode']=='MOTOR TEST'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--body-config');p.add_argument('--ecology-config');p.add_argument('--logdir');a=p.parse_args()
    RemasterRuntime(json.loads(Path(a.body_config).read_text()),json.loads(Path(a.ecology_config).read_text()),a.logdir).run()
