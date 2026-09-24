import os, runpy, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT.parents[1] / 'work/brian2-gate-a/deps'))
task_e_cache = ROOT.parents[1] / 'work/brian2-gate-e/cache-home'
task_e_cache.mkdir(parents=True, exist_ok=True)
os.environ['USERPROFILE'] = str(task_e_cache)
runpy.run_path(str(Path(__file__).with_name(sys.argv.pop(1) + '.py')), run_name='__main__')
