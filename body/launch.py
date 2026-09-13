"""Own both child processes and clean them up when Godot exits (no orphan brain)."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT=Path(__file__).resolve().parent


def stop(process):
    if process.poll() is None:
        # Windows venv python.exe may be a small redirector with a real interpreter child.
        try: descendants=psutil.Process(process.pid).children(recursive=True)
        except psutil.NoSuchProcess: descendants=[]
        for child in reversed(descendants):
            try: child.terminate()
            except psutil.NoSuchProcess: pass
        process.terminate()
        _,alive=psutil.wait_procs(descendants,timeout=3)
        for child in alive:
            try: child.kill()
            except psutil.NoSuchProcess: pass
        try: process.wait(timeout=3)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--godot',default=str(ROOT/'tools/Godot_v4.6.1-stable_win64.exe'))
    parser.add_argument('--config',default=str(ROOT/'body_config.json'))
    parser.add_argument('--logdir',default=str(ROOT/'logs/latest'))
    parser.add_argument('--integration-test',action='store_true')
    parser.add_argument('--quit-after',type=float,default=0)
    args=parser.parse_args()
    logdir=Path(args.logdir).resolve(); logdir.mkdir(parents=True,exist_ok=True)
    config=Path(args.config).resolve()
    if not Path(args.godot).exists(): raise SystemExit('Godot executable missing; run setup_godot.py or pass --godot')
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    brainlog=(logdir/'brain_console.txt').open('w')
    godotlog=(logdir/'godot_console.txt').open('w')
    brain=subprocess.Popen([sys.executable,str(ROOT/'bridge.py'),'--config',str(config),'--logdir',str(logdir)],
        stdout=brainlog,stderr=subprocess.STDOUT,creationflags=flags)
    # Runtime window is intentionally visible: it is the requested 3D arena.
    godot_args=[args.godot,'--path',str(ROOT),'--','--config='+str(config),'--logdir='+str(logdir)]
    if args.integration_test: godot_args.append('--integration-test')
    if args.quit_after: godot_args.append('--quit-after='+str(args.quit_after))
    godot=subprocess.Popen(godot_args,stdout=godotlog,stderr=subprocess.STDOUT)
    started=time.perf_counter(); samples=[]; brain_killed=False; disconnected_at=None
    owned={}
    try:
        while godot.poll() is None:
            def rss(p):
                if p.poll() is not None: return 0
                try:
                    root=psutil.Process(p.pid)
                    total=0
                    for actual in [root]+root.children(recursive=True):
                        try:
                            owned[actual.pid]=actual.create_time()
                            total+=actual.memory_info().rss
                        except psutil.NoSuchProcess: pass
                    return total
                except psutil.NoSuchProcess: return 0
            samples.append(dict(wall_s=time.perf_counter()-started,python_rss=rss(brain),godot_rss=rss(godot),
                available_ram=psutil.virtual_memory().available))
            if args.integration_test and not brain_killed:
                path=logdir/'godot.jsonl'
                if path.exists() and 'test_suite_ready_for_disconnect' in path.read_text(encoding='utf-8'):
                    # Genuine process termination, not a mocked disconnect packet.
                    stop(brain); brain_killed=True; disconnected_at=time.perf_counter()
            if brain_killed and time.perf_counter()-disconnected_at>4:
                break
            time.sleep(.1)
    finally:
        stop(godot); stop(brain)
        brainlog.close(); godotlog.close()
        remaining=[]
        for pid,birth in owned.items():
            try:
                if psutil.Process(pid).create_time()==birth: remaining.append(pid)
            except psutil.NoSuchProcess: pass
        report=dict(brain_pid=brain.pid,godot_pid=godot.pid,brain_exit_code=brain.returncode,
            godot_exit_code=godot.returncode,children_remaining=bool(remaining),remaining_owned_pids=remaining,
            process_tree_rss_includes_windows_venv_redirector_children=True,
            real_brain_terminated_for_failure_test=brain_killed,total_wall_seconds=time.perf_counter()-started,
            samples=samples,peak_combined_sampled_rss=max(x['python_rss']+x['godot_rss'] for x in samples) if samples else 0,
            peak_python_sampled_rss=max(x['python_rss'] for x in samples) if samples else 0,
            peak_godot_sampled_rss=max(x['godot_rss'] for x in samples) if samples else 0,
            minimum_available_ram=min(x['available_ram'] for x in samples) if samples else 0)
        (logdir/'resources.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
