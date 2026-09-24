import os
import runpy
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT.parents[1]/'work/brian2-gate-a/deps'))
task_cache_home=ROOT.parents[1]/'work/brian2-gate-b/cache-home'
task_cache_home.mkdir(parents=True,exist_ok=True);os.environ['USERPROFILE']=str(task_cache_home)
runpy.run_path(str(Path(__file__).with_name(sys.argv.pop(1)+'.py')),run_name='__main__')
