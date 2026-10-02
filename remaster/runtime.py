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
        self.cached_data=None;self.test_until=0;self.test_group=None;self.test_current=None;self.active_test=None
        super().__init__(*args)

    def load_brain(self):
        cls=FastBrain if self.config.get('backend')=='fast' else Brain
        if self.cached_data is None:
            brain=cls.load(ROOT/'data/runtime',self.coreconfig,seed=self.config['seed'])
            self.cached_data=(brain.w,brain.neurons)
            return brain
        weights,neurons=self.cached_data
        return cls(weights,self.coreconfig['model'],seed=self.config['seed'],neurons=neurons)

    def reset(self):
        self.test_until=0;self.test_group=None;self.test_current=None;self.active_test=None
        super().reset()
        self.encoder=EfficientEncoder(self.brain,self.eco_config['sensory']);self.encoder_brain=self.brain

    def configure_preset(self,name,seed,duration):
        return configure(name,seed,duration)

    def apply_actions(self):
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
            begin=time.perf_counter();spikes=self.brain.step(current)
            self.core_seconds+=time.perf_counter()-begin
            self.motor_steps+=1;self.batch_spikes+=int(spikes.sum())
            for name,idx in watched.items():self.counts[name]+=int(spikes[idx].sum())
        self.stimulus=None

    def console_metadata(self):
        return dict(backend=self.config.get('backend','reference'),brain_frame_ms=self.config['packet_neural_ms'],
                    neural_test=dict(active=self.active_test is not None,group=self.active_test,
                                     amplitude=3. if self.active_test else 0.,
                                     automatic=self.eco_config['mode']=='MOTOR TEST'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--body-config');p.add_argument('--ecology-config');p.add_argument('--logdir');a=p.parse_args()
    RemasterRuntime(json.loads(Path(a.body_config).read_text()),json.loads(Path(a.ecology_config).read_text()),a.logdir).run()
