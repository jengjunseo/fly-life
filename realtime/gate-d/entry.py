import os,runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT.parents[1]/'work/brian2-gate-a/deps'))
task_d_cache=ROOT.parents[1]/'work/brian2-gate-d/cache-home'
task_d_cache.mkdir(parents=True,exist_ok=True);os.environ['USERPROFILE']=str(task_d_cache)
runpy.run_path(str(Path(__file__).with_name(sys.argv.pop(1)+'.py')),run_name='__main__')
