import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'realtime'))
from common import sha,save,machine
from braincore.core import Brain
REPORT=ROOT/'reports/realtime/gate-b'
WORK=ROOT.parents[1]/'work/brian2-gate-b'
