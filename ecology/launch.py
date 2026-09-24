"""Visible Godot ecosystem launcher with the original process-tree cleanup."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT=Path(__file__).resolve().parent;BODY=ROOT.parent/'body'
sys.path.insert(0,str(ROOT.parent));sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(BODY))
from body.launch import stop
from model import load_config

def main():
    p=argparse.ArgumentParser();p.add_argument('--godot',default=str(BODY/'tools/Godot_v4.6.1-stable_win64.exe'))
    p.add_argument('--ecology-config',default=str(ROOT/'config.json'));p.add_argument('--logdir',default=str(ROOT/'logs/latest'))
    p.add_argument('--life-run',action='store_true');p.add_argument('--certification',action='store_true');p.add_argument('--replay-test',action='store_true')
    p.add_argument('--quit-after',type=float,default=0.);p.add_argument('--headless',action='store_true')
    p.add_argument('--sensory-off',action='store_true');p.add_argument('--without-predator',action='store_true');a=p.parse_args()
    eco=load_config(a.ecology_config,'certification' if a.certification else None)
    if a.sensory_off:eco['sensory']['enabled']=False
    if a.without_predator:
        if not a.certification:raise ValueError('Predator ablation is a certification-only initial condition')
        eco['initial_events']=[e for e in eco['initial_events'] if e['kind']!='predator']
    logdir=Path(a.logdir).resolve();logdir.mkdir(parents=True,exist_ok=True)
    ep=logdir/'ecology_runtime_config.json';ep.write_text(json.dumps(eco,indent=2),encoding='utf-8')
    cfg=json.loads((BODY/'body_config.json').read_text());cfg['port']=18762;cfg['debug']['enabled']=eco['debug_neural_keys']
    bp=logdir/'body_runtime_config.json';bp.write_text(json.dumps(cfg,indent=2))
    logs=[(logdir/name).open('w') for name in ['brain_console.txt','godot_console.txt']]
    hidden=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    brain=subprocess.Popen([sys.executable,str(ROOT/'bridge.py'),'--body-config',str(bp),'--ecology-config',str(ep),'--logdir',str(logdir)],stdout=logs[0],stderr=subprocess.STDOUT,creationflags=hidden)
    args=[a.godot,'--path',str(BODY),'res://ecology/main.tscn']
    if a.headless:args.append('--headless')
    args+=['--','--config='+str(bp),'--ecology-config='+str(ep),'--logdir='+str(logdir),'--duration='+str(eco['duration_s'])]
    if a.life_run:args.append('--life-run')
    if a.replay_test:args.append('--replay-test')
    if a.quit_after:args.append('--quit-after='+str(a.quit_after))
    godot=subprocess.Popen(args,stdout=logs[1],stderr=subprocess.STDOUT)
    start=time.perf_counter();samples=[];owned={};killed=False;killed_at=0.
    def rss(p):
        if p.poll() is not None:return 0
        try:
            root=psutil.Process(p.pid);total=0
            for actual in [root]+root.children(recursive=True):
                try:owned[actual.pid]=actual.create_time();total+=actual.memory_info().rss
                except psutil.NoSuchProcess:pass
            return total
        except psutil.NoSuchProcess:return 0
    try:
        while godot.poll() is None:
            samples.append(dict(wall_s=time.perf_counter()-start,python_rss=rss(brain),godot_rss=rss(godot),available_ram=psutil.virtual_memory().available))
            path=logdir/'godot.jsonl'
            if a.replay_test and not killed and path.exists() and 'ecology_ready_for_failure' in path.read_text(encoding='utf-8'):
                stop(brain);killed=True;killed_at=time.perf_counter()
            if killed and time.perf_counter()-killed_at>4.:break
            if a.quit_after and time.perf_counter()-start>a.quit_after+10:break
            if brain.poll() is not None and not killed and time.perf_counter()-start>15:break
            time.sleep(.1)
    finally:
        stop(godot)
        # Give an ordinary shutdown message time to exit cleanly before tree cleanup.
        if not killed:
            try:brain.wait(timeout=3.)
            except subprocess.TimeoutExpired:pass
        stop(brain)
        for log in logs:log.close()
        active=[]
        for pid,birth in owned.items():
            try:
                proc=psutil.Process(pid)
                if proc.create_time()==birth:active.append(proc)
            except psutil.NoSuchProcess:pass
        # The venv redirector can return before its real interpreter finishes teardown.
        _,alive=psutil.wait_procs(active,timeout=3.)
        for proc in alive:
            try:proc.terminate()
            except psutil.NoSuchProcess:pass
        _,alive=psutil.wait_procs(alive,timeout=3.)
        for proc in alive:
            try:proc.kill()
            except psutil.NoSuchProcess:pass
        psutil.wait_procs(alive,timeout=3.)
        remain=[]
        for pid,birth in owned.items():
            try:
                if psutil.Process(pid).create_time()==birth:remain.append(pid)
            except psutil.NoSuchProcess:pass
        report=dict(total_wall_s=time.perf_counter()-start,brain_exit_code=brain.returncode,godot_exit_code=godot.returncode,
            real_brain_terminated_for_failure_test=killed,remaining_owned_pids=remain,process_tree_rss=True,samples=samples)
        for name in ['python','godot']:report[f'peak_{name}_rss']=max((s[f'{name}_rss'] for s in samples),default=0)
        report['peak_combined_rss']=max((s['python_rss']+s['godot_rss'] for s in samples),default=0)
        (logdir/'resources.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()
