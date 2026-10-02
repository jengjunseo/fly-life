"""One-command launch, unique logs, deterministic presets, owned-process cleanup."""
import argparse
import datetime
import json
import os
import subprocess
import socket
import sys
import time
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'body'));sys.path.insert(0,str(ROOT/'ecology'))
from mvp.presets import PRESETS,configure,NEW_HALF,area_evidence
from remaster.presets import PRESETS as REMASTER_PRESETS,configure as configure_remaster
from body.launch import stop

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--preset',choices=REMASTER_PRESETS);p.add_argument('--world-seed',type=int,default=20260914)
    p.add_argument('--legacy',action='store_true',help='Original English v0.1 console and reference backend')
    p.add_argument('--backend',choices=['fast','reference'],default='fast')
    p.add_argument('--model',choices=['counts','sensorimotor','frozen'],default='sensorimotor',help='Explicit behavioral LIF hypotheses, or preserved v0.1 equations')
    p.add_argument('--tonic-current',type=float,default=1.5,help='Assumed arousal current (0..2); sensorimotor KCs capped at 0.85')
    p.add_argument('--restore-weak',action='store_true',help='Use separately restored threshold-1 connectivity; prepare with behavior.prepare')
    p.add_argument('--no-sensory',action='store_true');p.add_argument('--no-gf',action='store_true')
    p.add_argument('--no-vision',action='store_true');p.add_argument('--no-chemical',action='store_true');p.add_argument('--no-thermal',action='store_true')
    p.add_argument('--brain-frame-ms',type=int,choices=[10,20,50],default=20)
    p.add_argument('--warmup-ms',type=int,choices=[500,2000],help='Sensorimotor unstimulated initialization; 500 reproduces the early calibration')
    p.add_argument('--brain-seed',type=int,default=20260913);p.add_argument('--duration',type=float,default=0)
    p.add_argument('--windowed',action='store_true');p.add_argument('--headless',action='store_true');p.add_argument('--qa-controls',action='store_true')
    p.add_argument('--qa-neural',action='store_true',help='Exercise explicit neural-test controls and reset')
    p.add_argument('--qa-model',action='store_true',help='Exercise model switching and sensory/GF ablations across resets')
    p.add_argument('--quit-after',type=float,default=0);p.add_argument('--logdir');p.add_argument('--godot',default=str(ROOT/'body/tools/Godot_v4.6.1-stable_win64.exe'))
    a=p.parse_args()
    a.preset=a.preset or 'CONTROL'
    if not 0<=a.tonic_current<=2:p.error('Tonic current must be 0..2')
    if not a.legacy and a.model!='frozen' and a.backend=='reference':p.error('Count hypothesis uses JIT; reference backend requires --model frozen')
    if (a.no_vision or a.no_chemical or a.no_thermal) and (a.legacy or a.model!='sensorimotor'):p.error('Individual modality ablations require --model sensorimotor')
    if a.warmup_ms is not None and (a.legacy or a.model!='sensorimotor'):p.error('Warmup override requires sensorimotor')
    if a.restore_weak and not (ROOT/'data/behavior/counts.npz').exists():p.error('Restored connectivity missing: python -m behavior.prepare')
    if not Path(a.godot).exists():p.error('Godot missing: run mvp/setup_godot.py or provide --godot')
    if not 0<=a.brain_seed<=2147483647 or not 0<=a.world_seed<=2147483647:p.error('Seeds must be 0..2147483647')
    folder=Path(a.logdir).resolve() if a.logdir else ROOT/'mvp/logs'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True,exist_ok=False)
    eco=configure(a.preset,a.world_seed,a.duration) if a.legacy else configure_remaster(a.preset,a.world_seed,a.duration,behavior=a.model!='frozen')
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0))
        port=reservation.getsockname()[1]
    body=json.loads((ROOT/'body/body_config.json').read_text());body.update(port=port,seed=a.brain_seed,disconnect_seconds=30.)
    body['debug']['enabled']=False;body['arena']['half_width']=NEW_HALF
    body['backend']='reference' if a.legacy else a.backend
    body.update(scientific_model='frozen' if a.legacy else a.model,tonic_current=a.tonic_current,restore_weak=a.restore_weak)
    body['sensorimotor_warmup_ms']=a.warmup_ms if a.warmup_ms is not None else 2000
    if not a.legacy and a.model=='sensorimotor':body['warmup_ms']=body['sensorimotor_warmup_ms']
    body['gf_ablated']=a.no_gf;eco['sensory']['enabled']=not a.no_sensory
    eco['sensory'].update(vision_enabled=not a.no_vision,chemical_enabled=not a.no_chemical,thermal_enabled=not a.no_thermal)
    if not a.legacy:body['packet_neural_ms']=a.brain_frame_ms
    for name,value in [('ecology_runtime_config.json',eco),('body_runtime_config.json',body),('world-area.json',area_evidence())]:
        (folder/name).write_text(json.dumps(value,indent=2))
    print(f'MaleCNS MVP | {a.preset} | logs: {folder}',flush=True)
    logs=[(folder/x).open('w',encoding='utf-8') for x in ('brain_console.txt','godot_console.txt')]
    hidden=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    brain=godot=None;samples=[];owned={};started=time.perf_counter()
    try:
        child_env=os.environ.copy();child_env['PYTHONUTF8']='1'
        brain=subprocess.Popen([sys.executable,str(ROOT/('mvp/bridge.py' if a.legacy else 'remaster/runtime.py')),'--body-config',str(folder/'body_runtime_config.json'),
            '--ecology-config',str(folder/'ecology_runtime_config.json'),'--logdir',str(folder)],stdout=logs[0],stderr=subprocess.STDOUT,creationflags=hidden,env=child_env)
        args=[a.godot,'--path',str(ROOT/'body'),'res://mvp/main.tscn' if a.legacy else 'res://remaster/main.tscn','--resolution','3840x2160','--log-file',str(folder/'engine.log')]
        args+=['--headless'] if a.headless else (['--windowed'] if a.windowed else ['--fullscreen'])
        args+=['--','--config='+str(folder/'body_runtime_config.json'),'--ecology-config='+str(folder/'ecology_runtime_config.json'),
               '--logdir='+str(folder),'--duration='+str(a.duration),'--life-run','--quit-after='+str(a.quit_after)]
        if a.qa_controls:args.append('--qa-controls')
        if a.qa_neural:args.append('--qa-neural')
        if a.qa_model:args.append('--qa-model')
        cache=ROOT/'mvp/cache';cache.mkdir(exist_ok=True)
        env=os.environ.copy();env['APPDATA']=str(cache)
        godot=subprocess.Popen(args,stdout=logs[1],stderr=subprocess.STDOUT,creationflags=hidden,env=env)
        while godot.poll() is None:
            row=dict(wall_s=time.perf_counter()-started)
            for name,proc in [('brain',brain),('godot',godot)]:
                try:
                    root=psutil.Process(proc.pid)
                    tree=[root]+root.children(recursive=True)
                    for x in tree:owned[x.pid]=x.create_time()
                    row[name+'_rss']=sum(x.memory_info().rss for x in tree)
                except psutil.Error:row[name+'_rss']=0
            samples.append(row)
            if brain.poll() is not None:
                time.sleep(1);break
            if a.quit_after and time.perf_counter()-started>a.quit_after+10:break
            time.sleep(.5)
    finally:
        if godot:stop(godot)
        if brain:
            try:brain.wait(timeout=4)
            except subprocess.TimeoutExpired:pass
            stop(brain)
        remaining=[]
        for pid,birth in owned.items():
            try:
                proc=psutil.Process(pid)
                if proc.create_time()==birth:
                    proc.terminate();remaining.append(proc)
            except psutil.Error:pass
        _,alive=psutil.wait_procs(remaining,timeout=3)
        for proc in alive:proc.kill()
        _,alive=psutil.wait_procs(alive,timeout=3)
        for f in logs:f.close()
        result=dict(wall_s=time.perf_counter()-started,brain_exit=brain.returncode if brain else None,
                    godot_exit=godot.returncode if godot else None,remaining_owned_pids=[p.pid for p in alive],samples=samples)
        (folder/'resources.json').write_text(json.dumps(result,indent=2))
    if result['brain_exit']!=0 or result['godot_exit']!=0:raise SystemExit('Application failed; inspect console logs in '+str(folder))
if __name__=='__main__':main()


