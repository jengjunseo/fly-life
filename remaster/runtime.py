"""Remaster adapter: certified equivalent compute, explicit neural actuator test."""
import argparse
import json
import sys
import time
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
        self.cached_data=None;self.cached_key=None;self.model_evidence={};self.escape=None;self.gf_ablated=False;self.gf_brain=None;self.gf_indices=None
        self.test_until=0;self.test_group=None;self.test_current=None;self.active_test=None
        super().__init__(*args)
        self.gf_ablated=bool(self.config.get('gf_ablated',False))

    def load_brain(self):
        key=(self.config.get('scientific_model','frozen'),self.config.get('restore_weak',False),self.config.get('backend'))
        if key[0]=='counts':
            if self.cached_key!=key:
                w,n,self.model_evidence=load_connectivity(self.coreconfig,key[1]);self.cached_data=(w,n);self.cached_key=key
            w,n=self.cached_data
            brain=CountBrain(w,parameters(self.coreconfig,self.config.get('tonic_current',1.5)),seed=self.config['seed'],neurons=n)
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
        self.escape=None
        self.test_until=0;self.test_group=None;self.test_current=None;self.active_test=None
        super().reset()
        (self.logdir/f'model-generation-{self.generation}.json').write_text(json.dumps(dict(
            scientific_model=self.config.get('scientific_model','frozen'),parameters=self.brain.p,
            evidence=self.model_evidence,assumptions=['Uniform tonic drive is an assumed arousal condition, not natural spontaneous activity',
            'Count-weighted spike-reset LIF is not equivalent to v0.1 or an exact Shiu replication',
            'No world stimulus label, target position or desired action enters the motor decoder',
            'Hemispheric vision and local air cooling are explicit experimental approximations',
            'GF readout drives a primitive jump, not a complete flight controller'])),encoding='utf-8')

    def create_world(self):
        return ExperimentWorld(self.eco_config) if self.config.get('scientific_model')=='counts' else super().create_world()

    def create_encoder(self):
        cls=BilateralEncoder if self.config.get('scientific_model')=='counts' else EfficientEncoder
        return cls(self.brain,self.eco_config['sensory'])

    def sensory_assumptions(self):
        if self.config.get('scientific_model')=='counts':
            return 'Experimental overlapping hemispheric visual projection, not measured retinotopy; separate antenna-local chemical and thermal samples; somaSide otherwise rootSide.'
        return super().sensory_assumptions()

    def decode_motor(self,activities):
        motor=super().decode_motor(activities)
        if self.config.get('scientific_model')=='counts':
            if self.escape is None:self.escape=EscapeReadout(self.brain)
            self.escape.enabled=not self.gf_ablated
            motor.update(self.escape.decode(self.brain))
        return motor

    def advance_neurons(self,external=None):
        spikes=self.brain.step(external)
        if self.gf_ablated and not isinstance(self.brain,CountBrain):
            if self.gf_brain is not self.brain:
                self.gf_indices=self.brain.resolve(dict(types=['DNp01']));self.gf_brain=self.brain
            idx=self.gf_indices
            spikes[idx]=0.;self.brain.activity[idx]=0.;self.brain.v[idx]=self.brain.p['reset'];self.brain.syn[idx]=0.;self.brain.refractory[idx]=0
        return spikes

    def configure_preset(self,name,seed,duration):
        cfg=configure(name,seed,duration,behavior=self.config.get('scientific_model')=='counts')
        cfg['sensory']['enabled']=self.eco_config['sensory']['enabled']
        return cfg

    def apply_actions(self):
        conditions=[m for m in self.pending_actions if m['kind'] in ('model_condition','sensory_condition','gf_condition')]
        self.pending_actions=[m for m in self.pending_actions if m['kind'] not in ('model_condition','sensory_condition','gf_condition')]
        for m in conditions:
            if m['id'] in self.command_ids:raise ValueError('Duplicate command')
            self.command_ids.add(m['id']);self.commands.append(m['id'])
            if m['kind']=='model_condition':
                if m['model'] not in ('counts','frozen'):raise ValueError('Unknown scientific model')
                parameters(self.coreconfig,float(m['tonic_current']))
                self.config.update(scientific_model=m['model'],tonic_current=float(m['tonic_current']),restore_weak=bool(m['restore_weak']))
                if m['model']=='frozen' and self.eco_config['mode'] in ('FOOD RIGHT','HEAT RIGHT'):self.eco_config['mode']='CONTROL'
                self.eco_config=self.configure_preset(self.eco_config['mode'],self.eco_config['world_seed'],self.eco_config['duration_s'])
                self.pending_reset=True
            elif m['kind']=='sensory_condition':self.eco_config['sensory']['enabled']=bool(m['enabled'])
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
        return dict(backend='fast' if self.config.get('scientific_model')=='counts' else self.config.get('backend','reference'),brain_frame_ms=self.config['packet_neural_ms'],
                    scientific_model=self.config.get('scientific_model','frozen'),tonic_current=float(self.brain.p['baseline_current']) if self.brain else 0.,
                    count_tonic_setting=self.config.get('tonic_current',1.5),
                    restored_weak_connections=self.config.get('scientific_model')=='counts' and self.config.get('restore_weak',False),
                    restored_available=(ROOT/'data/behavior/counts.npz').exists(),
                    sensory_enabled=self.eco_config['sensory']['enabled'],gf_enabled=not self.gf_ablated,
                    shade_center=self.world.cfg['shade']['center'],shade_half_size=self.world.cfg['shade']['half_size'],
                    neural_test=dict(active=self.active_test is not None,group=self.active_test,
                                     amplitude=3. if self.active_test else 0.,
                                     automatic=self.eco_config['mode']=='MOTOR TEST'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--body-config');p.add_argument('--ecology-config');p.add_argument('--logdir');a=p.parse_args()
    RemasterRuntime(json.loads(Path(a.body_config).read_text()),json.loads(Path(a.ecology_config).read_text()),a.logdir).run()
