"""Sequential visible final runs; never overlap neural benchmarks."""
import datetime
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mvp.presets import PRESETS
from body.launch import stop
if __name__=='__main__':
    p=__import__('argparse').ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    dest=Path(a.out);dest.mkdir(parents=True,exist_ok=False)
    results=[]
    for name in PRESETS:
        label=name.lower().replace(' + ','-').replace(' ','-')
        cmd=[sys.executable,str(ROOT/'mvp/launch.py'),'--legacy','--preset',name,'--duration','3.5','--quit-after','160','--logdir',str(dest/label)]
        print('RUN '+name,flush=True)
        r=subprocess.Popen(cmd,cwd=ROOT)
        try:r.wait()
        except BaseException:
            stop(r)
            raise
        results.append(dict(preset=name,returncode=r.returncode))
        (dest/'runs.json').write_text(json.dumps(results,indent=2))
        if r.returncode:raise SystemExit(r.returncode)
