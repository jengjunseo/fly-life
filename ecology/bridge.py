"""Ecology transport extension; imports the unchanged brain and motor decoder.

Lockstep: sensory at world t -> 50 real neural steps -> original Godot body
commit -> actual pose ACK -> world advances 50ms -> next sensory. No prediction.
"""
import argparse
import copy
import json
import socket
import sys
import time
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parent;CORE=ROOT.parent;BODY=CORE/'body'
sys.path.insert(0,str(CORE));sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(BODY))
from body import bridge as baseline
from braincore.evidence import save
from model import World,load_config
from sensory import Encoder


class EcologyRuntime(baseline.Runtime):
    def __init__(self,config,eco_config,logdir):
        self.eco_config=eco_config;self.world=None;self.encoder=None;self.encoder_brain=None
        self.awaiting_seq=None;self.awaiting_dt=0.;self.last_pose=None;self.terms=[];self.sensor_source_seq=None
        super().__init__(config,logdir)
        self.world_log=(self.logdir/'world.jsonl').open('w',encoding='utf-8',newline='\n')
        self.event_log=(self.logdir/'events.jsonl').open('w',encoding='utf-8',newline='\n')
        save(self.logdir/'ecology_config.json',eco_config)

    def reset(self):
        self.world=self.create_world();self.encoder=None;self.encoder_brain=None
        self.awaiting_seq=None;self.last_pose=None;self.terms=[];self.sensor_source_seq=None
        save(self.logdir/f'schedule-generation-{self.generation+1}.json',dict(world_seed=self.eco_config['world_seed'],schedule=self.world.initial_schedule))
        super().reset()
        save(self.logdir/'sensory_mapping.json',dict(dataset=self.coreconfig['dataset'],actual=self.encoder.evidence(),
            disabled=dict(pain='No verified adult nociceptive identity/circuit mapping',female_contact='putative_ppk23 annotation is not female-specific proof',
                          ingestion='Fdg alias verified, upstream->functional feeding gate unresolved',hunger_modulation='No implemented verified modulatory circuit'),
            bilateral_visual_pool=self.sensory_assumptions()))

    def emit(self,status,dt=0.,extra=None):
        if self.brain is not None and self.encoder_brain is not self.brain:
            self.encoder=self.create_encoder();self.encoder_brain=self.brain
        ext=dict(extra or {})
        if self.world is not None:
            ext['ecology']=dict(world=self.world.snapshot(),sensory_terms=self.terms,readouts_hz=self.encoder.readouts() if self.encoder else {},
                sensor_source_body_seq=self.sensor_source_seq,sensory_time_s=self.world.time,world_seed=self.eco_config['world_seed'])
        if status=='ready':
            self.awaiting_seq=self.sequence;self.awaiting_dt=dt
        super().emit(status,dt,ext)

    def create_world(self):
        return World(self.eco_config)

    def sensory_assumptions(self):
        return 'somaSide L/R verified; no retinotopic receptive-field positions available. Both pools get same feature, no invented steering direction.'

    def create_encoder(self):
        return Encoder(self.brain,self.eco_config['sensory'])

    def flush_world(self,ack):
        neural=self.brain.step_count*self.brain.p['dt_ms']/1000
        snap=self.world.snapshot()
        self.world_log.write(json.dumps(dict(generation=self.generation,source_seq=ack['source_seq'],neural_time_s=neural,**snap),allow_nan=False)+'\n');self.world_log.flush()
        for event in self.world.events:
            self.event_log.write(json.dumps(dict(generation=self.generation,source_seq=ack['source_seq'],neural_time_s=neural,**event),allow_nan=False)+'\n')
        self.event_log.flush();self.world.events.clear()

    def handle(self,m):
        if m.get('v')!=1:raise ValueError('Protocol mismatch')
        self.last_client=time.perf_counter();kind=m.get('kind')
        if kind=='heartbeat':return
        if not isinstance(m.get('id'),str):raise ValueError('Command ID required')
        if m['id'] in self.command_ids:raise ValueError('Duplicate command ID')
        self.command_ids.add(m['id']);self.commands.append(m['id'])
        if kind=='body_snapshot':
            if m.get('generation')!=self.generation or m.get('source_seq')!=self.awaiting_seq:raise ValueError('Wrong causal body ACK')
            if not np.isclose(m['motor_time_s'],self.motor_steps*self.brain.p['dt_ms']/1000):raise ValueError('Body/neural time mismatch')
            # Accept actual pose only as sensor geometry input. It cannot inject motor current.
            self.last_pose=list(m['position']);self.sensor_source_seq=m['source_seq']
            feed=self.encoder.readouts()['feeding_observation']
            self.world.advance(self.awaiting_dt,self.last_pose,float(m['yaw']),feed)
            if not np.isclose(self.world.time,m['motor_time_s']):raise ValueError('World advanced without completed neural body time')
            self.flush_world(m);self.awaiting_seq=None
        elif kind=='reset':self.pending_reset=True
        elif kind=='shutdown':self.running=False
        elif kind=='world_event':
            if m.get('event') not in ['food','predator','female','heat','defecation']:raise ValueError('Unknown world event')
            self.world.manual_event(m['event'])
        elif kind=='clear':self.stimulus=None
        elif kind=='stimulus':
            group=m.get('group')
            if group not in self.groups:raise ValueError('Unknown debug neural group')
            if self.config['debug']['enabled'] and self.status=='ready':
                self.stimulus=dict(group=group,id=m['id'],remaining=self.brain.steps_for(self.config['debug']['duration_ms']),
                    current=self.brain.current(self.groups[group],self.config['debug']['current']))
                self.log.write(json.dumps(dict(event='debug_current_injection',group=group,command_id=m['id']))+'\n')
        else:raise ValueError('Unknown command')
        self.log.write(json.dumps(dict(event='command',generation=self.generation,world_time_s=self.world.time,message=m))+'\n');self.log.flush()

    def receive(self):
        try:data=self.conn.recv(8192)
        except BlockingIOError:data=None
        if data==b'':self.running=False;return
        if data:
            self.buffer+=data
            if len(self.buffer)>65536:raise ValueError('Oversized command buffer')
            while b'\n' in self.buffer:
                line,self.buffer=self.buffer.split(b'\n',1);self.handle(json.loads(line))
        if time.perf_counter()-self.last_client>self.config['disconnect_seconds']:raise TimeoutError('Godot heartbeat lost')

    def wait_ack(self):
        import select
        started=time.perf_counter()
        while self.running and not self.pending_reset and self.awaiting_seq is not None:
            self.receive()
            if time.perf_counter()-started>self.config['disconnect_seconds']:raise TimeoutError('Completed-body ACK lost')
            if self.awaiting_seq is not None:select.select([self.conn],[],[],.02)

    def run(self):
        self.groups={}
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);listener.bind((self.config['host'],self.config['port']))
            listener.listen(1);listener.settimeout(15.);conn,addr=listener.accept()
            if addr[0]!='127.0.0.1':raise ValueError('Localhost only')
            self.conn=conn;conn.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);conn.setblocking(False)
            try:
                self.reset();quantum=self.brain.steps_for(self.config['packet_neural_ms'])
                while self.running:
                    self.wait_ack()
                    if self.pending_reset:self.reset();continue
                    if not self.running:break
                    external,self.terms=self.encoder.encode(self.world.sensor)
                    # Each quantum uses the last completed world snapshot; no neural steps omitted.
                    for _ in range(quantum):
                        self.receive()
                        if not self.running or self.pending_reset:break
                        current=external+self.stimulus['current'] if self.stimulus else external
                        begin=time.perf_counter();spikes=self.brain.step(current);self.core_seconds+=time.perf_counter()-begin
                        self.motor_steps+=1;self.batch_spikes+=int(spikes.sum())
                        if self.stimulus:
                            self.stimulus['remaining']-=1
                            if self.stimulus['remaining']<=0:self.stimulus=None
                    if self.pending_reset:continue
                    if not self.running:break
                    self.emit('ready',quantum*self.brain.p['dt_ms']/1000)
                    self.last_frame_steps=self.motor_steps;self.batch_spikes=0
            except Exception as e:
                try:self.emit('error',extra=dict(error=str(e)))
                except OSError:pass
                raise
            finally:
                conn.close();self.conn=None
                save(self.logdir/'brain_exit.json',dict(wall_seconds=time.perf_counter()-self.start,pure_core_wall_seconds=self.core_seconds,
                    normal_shutdown=not self.running,last_generation=self.generation,last_sequence=self.sequence,world_time_s=self.world.time))
                self.log.close();self.world_log.close();self.event_log.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--body-config',default=str(BODY/'body_config.json'));p.add_argument('--ecology-config',default=str(ROOT/'config.json'))
    p.add_argument('--mode');p.add_argument('--logdir',default=str(ROOT/'logs/latest'));a=p.parse_args()
    eco=load_config(a.ecology_config,a.mode);cfg=json.loads(Path(a.body_config).read_text());cfg['debug']['enabled']=eco['debug_neural_keys'];cfg['port']=18762
    EcologyRuntime(cfg,eco,a.logdir).run()
