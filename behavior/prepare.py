"""Restore weak synapses into a separate artifact; never overwrite v0.1."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    cfg = json.loads((ROOT/'config.json').read_text())
    cfg['preprocessing']['weight_threshold'] = 1
    path = ROOT/'behavior/unpruned.json'
    path.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
    subprocess.run([sys.executable, str(ROOT/'preprocess.py'), '--config', str(path),
                    '--runtime', str(ROOT/'data/behavior')], check=True)

if __name__ == '__main__':
    main()
