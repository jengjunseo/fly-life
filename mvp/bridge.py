"""MVP console adapter. Original brain, decoder and ecology sources stay immutable."""
import argparse
import collections
import copy
import json
import select
import socket
import sys
import time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'body'));sys.path.insert(0,str(ROOT/'ecology'))
from ecology.bridge import EcologyRuntime
from mvp.presets import configure

class ConsoleRuntime(EcologyRuntime):
    def __init__(self,*args):
        self.paused=False;self.step_once=False;self.pending_actions=[]
        self.observer={};self.observer_brain=None;self.counts={}
        self.metrics={};self.windows=collections.deque(maxlen=200)
        self.recent_events=collections.deque(maxlen=40)
        self.emitted_at=None;self.last_emit_ms=0.;self.ack_ms=0.;self.response_baseline={};self.response_high=set()
        super().__init__(*args)
        self.perf_log=(self.logdir/'performance.jsonl').open('w',encoding='utf-8')

    def reset(self):
        self.observer={};self.observer_brain=None;self.counts={};self.metrics={};self.windows.clear()
        self.recent_events.clear();self.emitted_at=None;self.response_baseline={};self.response_high.clear()
        super().reset()
        self.recent_events.append(dict(event='RESET',world_time_s=0.,preset=self.eco_config['mode']))

    def emit(self,status,dt=0.,extra=None):
        if self.brain is not None and self.observer_brain is not self.brain:
            self.observer={name:self.brain.resolve(dict(types=[typ])) for name,typ in
                           [('GF','DNp01'),('DNa01','DNa01'),('DNa02','DNa02'),('DNp09','DNp09')]}
            if any(not len(idx) for idx in self.observer.values()):raise ValueError('Missing observer identity')
            self.observer_brain=self.brain
        groups={name:float(self.brain.activity[idx].mean()) for name,idx in self.observer.items()} if self.brain else {}
        if self.encoder is not None and self.encoder.brain is self.brain:
            groups.update(self.encoder.readouts())
        if status=='ready' and dt>0:
            for name,value in groups.items():
                if self.world.time<.5:
                    self.response_baseline[name]=max(self.response_baseline.get(name,0.),value)
                threshold=self.response_baseline.get(name,0.)+10.
                if self.world.time>=.5 and value>threshold and name not in self.response_high:
                    event=dict(event=name+' ACTIVITY RISE',world_time_s=self.world.time+dt,
                               activity_hz=value,criterion='EMA > pre-stimulus maximum + 10 Hz; observation, not causality proof')
                    self.recent_events.append(event)
                    if hasattr(self,'event_log'):
                        self.event_log.write(json.dumps(dict(generation=self.generation,source_seq=self.sequence,**event))+'\n')
                    self.response_high.add(name)
                elif value<threshold-5 and name in self.response_high:self.response_high.remove(name)
        ext=dict(extra or {})
        ext['console']=dict(preset=self.eco_config['mode'],paused=self.paused,brain_seed=self.config['seed'],
            groups_hz=groups,group_spikes=self.counts,performance=self.metrics,
            events=list(self.recent_events),shade_enabled=self.world.cfg['shade']['cooling_c']>0,
            ambient_setting=self.world.cfg['ambient_c'],backend='SciPy reference / PCG64 / dt 1ms')
        ext['console'].update(self.console_metadata())
        terms=self.terms
        self.terms=[{k:v for k,v in t.items() if k!='bodyIds'} for t in terms]
        before=time.perf_counter()
        try:super().emit(status,dt,ext)
        finally:self.terms=terms
        self.last_emit_ms=(time.perf_counter()-before)*1000
        if status=='ready':self.emitted_at=time.perf_counter()

    def console_metadata(self):
        return {}

    def flush_world(self,ack):
        self.recent_events.extend(copy.deepcopy(self.world.events))
        super().flush_world(ack)

    def handle(self,m):
        kind=m.get('kind')
        if kind=='body_snapshot':
            super().handle(m)
            if self.emitted_at:self.ack_ms=(time.perf_counter()-self.emitted_at)*1000
            return
        if kind in ('heartbeat','shutdown'):
            super().handle(m);return
        # World edits and pause take effect only at a completed neural frame boundary.
        if m.get('v')!=1 or not isinstance(m.get('id'),str):raise ValueError('Invalid command')
        self.pending_actions.append(m)
        self.last_client=time.perf_counter()

    def apply_actions(self):
        actions,self.pending_actions=self.pending_actions,[]
        for m in actions:
            kind=m['kind']
            if kind in ('world_event','reset'):
                super().handle(m)
            else:
                if m['id'] in self.command_ids:raise ValueError('Duplicate command')
                self.command_ids.add(m['id']);self.commands.append(m['id'])
                if kind=='pause':self.paused=True
                elif kind=='resume':self.paused=False
                elif kind=='step':self.paused=True;self.step_once=True
                elif kind=='preset':
                    self.eco_config=self.configure_preset(m['preset'],int(m['world_seed']),self.eco_config['duration_s'])
                    seed=int(m['brain_seed'])
                    if not 0<=seed<=2147483647:raise ValueError('Invalid brain seed')
                    self.config['seed']=seed;self.pending_reset=True
                elif kind=='temperature':
                    temp=float(m['celsius'])
                    if not np.isfinite(temp) or not 15<=temp<=40:raise ValueError('Temperature outside 15-40C')
                    self.world.cfg['ambient_c']=temp;self.world.heat_start=None
                    self.world.event('TEMPERATURE_SET',celsius=temp)
                elif kind=='shade':
                    self.world.cfg['shade']['cooling_c']=6. if m['enabled'] else 0.
                    self.world.event('SHADE_CONDITION',enabled=bool(m['enabled']))
                elif kind=='clear_objects':
                    for e in self.world.entities.values():self.world.event(e['kind'].upper()+'_DESPAWN',entity_id=e['id'])
                    self.world.entities.clear();self.world.schedule.clear();self.world.heat_start=None
                    self.world.event('EXPERIMENT_CLEARED')
                else:raise ValueError('Unsupported console command')
                self.log.write(json.dumps(dict(event='command',generation=self.generation,world_time_s=self.world.time,message=m))+'\n')
            if kind in ('world_event','temperature','shade','clear_objects'):
                # Refresh geometry at the SAME world time. Do not invent a thermal derivative.
                self.world.sensor=self.world.sense(0.)
                self.recent_events.extend(copy.deepcopy(self.world.events))
                for e in self.world.events:self.event_log.write(json.dumps(dict(generation=self.generation,**e))+'\n')
                self.world.events.clear();self.event_log.flush()
        if actions:self.log.flush()

    def configure_preset(self,name,seed,duration):
        return configure(name,seed,duration)

    def compute_quantum(self,external,quantum,watched):
        for _ in range(quantum):
            self.receive()
            if not self.running:break
            begin=time.perf_counter();spikes=self.brain.step(external)
            self.core_seconds+=time.perf_counter()-begin
            self.motor_steps+=1;self.batch_spikes+=int(spikes.sum())
            for name,idx in watched.items():self.counts[name]+=int(spikes[idx].sum())

    def run(self):
        self.groups={}
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET,getattr(socket,'SO_EXCLUSIVEADDRUSE',socket.SO_REUSEADDR),1)
            listener.bind((self.config['host'],self.config['port']));listener.listen(1);listener.settimeout(30)
            conn,addr=listener.accept()
            if addr[0]!='127.0.0.1':raise ValueError('Localhost only')
            self.conn=conn;conn.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);conn.setblocking(False)
            try:
                self.reset();quantum=self.brain.steps_for(self.config['packet_neural_ms'])
                while self.running:
                    self.wait_ack();self.receive();self.apply_actions()
                    if not self.running:break
                    if self.pending_reset:self.reset();continue
                    if self.paused and not self.step_once:
                        if time.perf_counter()-self.last_status>.5:self.emit('paused')
                        select.select([conn],[],[],.02);continue
                    self.step_once=False
                    start=time.perf_counter();core_before=self.core_seconds
                    external,self.terms=self.encoder.encode(self.world.sensor)
                    watched={**self.encoder.indices,**self.observer}
                    self.counts={name:0 for name in watched}
                    self.compute_quantum(external,quantum,watched)
                    if not self.running:break
                    core_ms=(self.core_seconds-core_before)*1000
                    self.windows.append(core_ms)
                    neural_dt=quantum*self.brain.p['dt_ms']/1000
                    self.metrics=dict(neural_quantum_ms=neural_dt*1000,compute_ms=core_ms,
                        p50_ms=float(np.percentile(self.windows,50)),p95_ms=float(np.percentile(self.windows,95)),p99_ms=float(np.percentile(self.windows,99)),
                        integration_before_emit_ms=(time.perf_counter()-start)*1000-core_ms,
                        previous_serialization_log_send_ms=self.last_emit_ms,previous_body_ack_ms=self.ack_ms,
                        rolling_windows=len(self.windows))
                    self.emit('ready',neural_dt)
                    self.wait_ack()
                    self.perf_log.write(json.dumps(dict(generation=self.generation,seq=self.sequence-1,world_time_s=self.world.time,
                        compute_ms=core_ms,total_lockstep_ms=(time.perf_counter()-start)*1000,
                        serialization_log_send_ms=self.last_emit_ms,body_ack_ms=self.ack_ms,**{k:v for k,v in self.metrics.items() if k!='compute_ms'}))+'\n')
                    self.perf_log.flush();self.last_frame_steps=self.motor_steps;self.batch_spikes=0
            except Exception as e:
                try:self.emit('error',extra=dict(error=str(e)))
                except OSError:pass
                raise
            finally:
                conn.close();self.conn=None
                (self.logdir/'brain_exit.json').write_text(json.dumps(dict(normal_shutdown=not self.running,world_time_s=self.world.time,
                    wall_seconds=time.perf_counter()-self.start,pure_core_wall_seconds=self.core_seconds)))
                self.log.close();self.world_log.close();self.event_log.close();self.perf_log.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--body-config');p.add_argument('--ecology-config');p.add_argument('--logdir');a=p.parse_args()
    ConsoleRuntime(json.loads(Path(a.body_config).read_text()),json.loads(Path(a.ecology_config).read_text()),a.logdir).run()
