"""A single local JSONL TCP peer for an unchanged real MaleCNS brain core."""
import argparse
import hashlib
import json
import os
import socket
import sys
import time
from pathlib import Path

import numpy as np
import psutil

ROOT=Path(__file__).resolve().parent
CORE=ROOT.parent
sys.path.insert(0,str(CORE))
from braincore import Brain
from braincore.evidence import machine,save
from decoder import decode


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()


def resolve(brain,selector):
    idx=brain.resolve(selector)
    if selector.get('somaSide'):
        rows=brain.neurons.iloc[idx]
        idx=idx[rows.somaSide.eq(selector['somaSide']).to_numpy()]
        if not rows.iloc[np.flatnonzero(rows.somaSide.eq(selector['somaSide']))].instance.fillna('').str.endswith('_'+selector['somaSide']).all():
            raise ValueError('Instance/somaSide laterality conflict')
    if not len(idx): raise ValueError('Neural group has no verified members')
    return idx


class Runtime:
    def __init__(self,config,logdir):
        self.config=config
        self.coreconfig=json.loads((CORE/'config.json').read_text())
        self.logdir=Path(logdir); self.logdir.mkdir(parents=True,exist_ok=True)
        self.log=(self.logdir/'brain.jsonl').open('w',encoding='utf-8',newline='\n')
        self.start=time.perf_counter(); self.generation=0; self.sequence=0
        self.running=True; self.buffer=b''; self.conn=None; self.last_client=time.perf_counter()
        self.command_ids=set(); self.commands=[]; self.stimulus=None; self.pending_reset=False
        self.brain=None; self.motor_steps=0; self.last_frame_steps=0; self.batch_spikes=0
        self.core_seconds=0.; self.status='starting'; self.last_status=0.

    def emit(self,status,dt=0.,extra=None):
        now=time.perf_counter()
        activities={g:float(self.brain.read_activity(idx)['activity_hz'].mean()) for g,idx in self.groups.items()} if self.brain else dict(left=0.,right=0.,forward=0.)
        motor=decode(activities,self.config['decoder']) if status=='ready' else dict(forward=0.,turn=0.)
        neural_time=self.brain.step_count*self.brain.p['dt_ms']/1000 if self.brain else 0.
        motor_time=self.motor_steps*self.brain.p['dt_ms']/1000 if self.brain else 0.
        wall=now-self.start
        packet=dict(v=1,kind='state',generation=self.generation,seq=self.sequence,status=status,
            wall_time_s=wall,neural_time_s=neural_time,motor_time_s=motor_time,dt_s=dt,
            neural_wall_ratio=neural_time/wall if wall else 0.,activity_hz=activities,**motor,
            population_hz=self.batch_spikes/self.brain.n/dt if self.brain and dt else 0.,
            stimulus=self.stimulus['group'] if self.stimulus else 'none',
            stimulus_command_id=self.stimulus['id'] if self.stimulus else None,
            acknowledged_commands=self.commands[-8:],python_rss_bytes=psutil.Process().memory_info().rss,
            python_peak_rss_bytes=getattr(psutil.Process().memory_info(),'peak_wset',None))
        if extra: packet.update(extra)
        data=(json.dumps(packet,allow_nan=False,separators=(',',':'))+'\n').encode()
        self.log.write(data.decode()); self.log.flush()
        if self.conn: self.conn.sendall(data)
        self.sequence+=1; self.last_status=now; self.status=status

    def receive(self):
        if not self.conn: return
        try: data=self.conn.recv(8192)
        except BlockingIOError: data=None
        if data==b'': self.running=False; return
        if data:
            self.buffer+=data
            if len(self.buffer)>65536: raise ValueError('Oversized command buffer')
            while b'\n' in self.buffer:
                line,self.buffer=self.buffer.split(b'\n',1)
                message=json.loads(line)
                if message.get('v')!=1: raise ValueError('Protocol mismatch')
                self.last_client=time.perf_counter()
                kind=message.get('kind')
                if kind=='heartbeat': continue
                ident=message.get('id')
                if not isinstance(ident,str): raise ValueError('Command id required')
                if ident in self.command_ids: continue
                self.command_ids.add(ident); self.commands.append(ident)
                self.log.write(json.dumps(dict(event='command',wall_time_s=time.perf_counter()-self.start,
                    neural_time_s=self.brain.step_count*self.brain.p['dt_ms']/1000 if self.brain else 0.,message=message))+'\n'); self.log.flush()
                if kind=='shutdown': self.running=False
                elif kind=='reset': self.pending_reset=True
                elif kind=='clear': self.stimulus=None
                elif kind=='stimulus':
                    group=message.get('group')
                    if group not in self.config['neural_groups']: raise ValueError('Unknown neural stimulus group')
                    if self.config['debug']['enabled'] and self.brain and self.status=='ready':
                        duration=self.brain.steps_for(self.config['debug']['duration_ms'])
                        external=self.brain.current(self.groups[group],self.config['debug']['current'])
                        self.stimulus=dict(group=group,id=ident,remaining=duration,current=external)
                        self.log.write(json.dumps(dict(event='current_injection',command_id=ident,group=group,
                            generation=self.generation,bodyIds=self.brain.neurons.iloc[self.groups[group]].bodyId.tolist(),
                            amplitude=self.config['debug']['current'],duration_ms=self.config['debug']['duration_ms'],
                            nonzero_current_count=int(np.count_nonzero(external)),unselected_current_is_zero=True))+'\n'); self.log.flush()
                else: raise ValueError('Unknown command')
        if time.perf_counter()-self.last_client>self.config['disconnect_seconds']:
            raise TimeoutError('Godot heartbeat lost')

    def load_brain(self):
        return Brain.load(CORE/'data/runtime',self.coreconfig,seed=self.config['seed'])

    def reset(self):
        self.generation+=1; self.stimulus=None; self.brain=None; self.motor_steps=0
        self.last_frame_steps=0; self.batch_spikes=0; self.pending_reset=False
        self.emit('starting')
        self.brain=self.load_brain()
        self.groups={g:resolve(self.brain,s) for g,s in self.config['neural_groups'].items()}
        evidence={g:json.loads(self.brain.neurons.iloc[idx][['bodyId','type','instance','somaSide','superclass','consensus_nt']].to_json(orient='records')) for g,idx in self.groups.items()}
        save(self.logdir/'baseline_mapping.json',dict(dataset=self.coreconfig['dataset'],machine=machine(),
            runtime_pid=os.getpid(),parent_pid=os.getppid(),
            brain_config=self.coreconfig,body_config=self.config,
            baseline_commit='4cd038f',baseline_files_sha256={str(p.relative_to(CORE)):sha(p) for p in
                [CORE/'braincore/core.py',CORE/'config.json',CORE/'data/runtime/metadata.json',CORE/'data/runtime/weights.npz',CORE/'data/runtime/neurons.parquet']},
            actual_groups=evidence))
        self.emit('warming_up')
        for _ in range(self.brain.steps_for(self.config['warmup_ms'])):
            self.receive()
            if not self.running or self.pending_reset: return
            begin=time.perf_counter(); self.brain.step(); self.core_seconds+=time.perf_counter()-begin
            if time.perf_counter()-self.last_status>.25: self.emit('warming_up')
        self.emit('ready')

    def run(self):
        self.groups={}
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind((self.config['host'],self.config['port'])); listener.listen(1); listener.settimeout(15.)
            conn,address=listener.accept()
            if address[0]!='127.0.0.1': raise ValueError('Only localhost peers accepted')
            self.conn=conn
            conn.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1); conn.setblocking(False)
            try:
                self.reset()
                quantum=self.brain.steps_for(self.config['packet_neural_ms'])
                while self.running:
                    self.receive()
                    if self.pending_reset:
                        self.reset(); continue
                    if not self.running: break
                    external=self.stimulus['current'] if self.stimulus else None
                    begin=time.perf_counter(); spikes=self.brain.step(external); self.core_seconds+=time.perf_counter()-begin
                    self.motor_steps+=1; self.batch_spikes+=int(spikes.sum())
                    if self.stimulus:
                        self.stimulus['remaining']-=1
                        if self.stimulus['remaining']<=0: self.stimulus=None
                    if self.motor_steps-self.last_frame_steps==quantum:
                        self.emit('ready',quantum*self.brain.p['dt_ms']/1000)
                        self.last_frame_steps=self.motor_steps; self.batch_spikes=0
            except Exception as e:
                try: self.emit('error',extra=dict(error=str(e)))
                except OSError: pass
                raise
            finally:
                conn.close(); self.conn=None
                save(self.logdir/'brain_exit.json',dict(wall_seconds=time.perf_counter()-self.start,
                    pure_core_wall_seconds=self.core_seconds,normal_shutdown=not self.running,
                    last_generation=self.generation,last_sequence=self.sequence))
                self.log.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--config',default=str(ROOT/'body_config.json')); parser.add_argument('--logdir',default=str(ROOT/'logs/latest'))
    args=parser.parse_args(); Runtime(json.loads(Path(args.config).read_text()),args.logdir).run()
