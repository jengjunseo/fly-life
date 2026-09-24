"""Isolated NumPy compatibility; the verified .venv NumPy is NOT downgraded."""
import runpy
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1]/'work/brian2-gate-a/deps'))
# Brian2 imports create ~/.brian CPU flags/preferences; keep that transient cache in work.
task_cache_home = ROOT.parents[1]/'work/brian2-gate-a/cache-home'
task_cache_home.mkdir(parents=True, exist_ok=True)
os.environ['USERPROFILE'] = str(task_cache_home)
script = Path(__file__).with_name(sys.argv.pop(1)+'.py')
runpy.run_path(str(script), run_name='__main__')
