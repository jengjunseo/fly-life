"""Gate C paths; existing Gate A/B modules remain read-only."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'realtime'))
from common import Brain,sha,save,machine,COMPILER
WORK=ROOT.parents[1]/'work/brian2-gate-c'
REPORT=ROOT/'reports/realtime/gate-c'
OLD=ROOT.parents[1]/'work/brian2-gate-b'
WORK.mkdir(parents=True,exist_ok=True);REPORT.mkdir(parents=True,exist_ok=True)
