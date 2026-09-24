"""Gate A only: no changes to the reference model or integration."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from braincore.core import Brain
from braincore.evidence import save, machine

REPORT = ROOT / 'reports/realtime'
WORK = ROOT.parents[1] / 'work/brian2-gate-a'
COMPILER = Path('C:/Program Files (x86)/Embarcadero/Dev-Cpp/TDM-GCC-64/bin')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def load():
    config = json.loads((ROOT/'config.json').read_text())
    brain = Brain.load(ROOT/'data/runtime', config)
    # Only the in-memory experimental copy disables noise. Baseline config stays intact.
    brain.p['noise_std'] = 0.0
    groups = {name: brain.resolve({'types': [typ]}) for name, typ in
              [('LC4', 'LC4'), ('LPLC2', 'LPLC2'), ('GF', 'DNp01'), ('DNp09', 'DNp09')]}
    return brain, config, groups


def summarize(spike_i, spike_steps, activity, record_indices, groups, phases):
    """activity is [recorded neuron, step], sampled AFTER reset/activity update."""
    result = {}
    for phase, start, end in phases:
        mask = (spike_steps >= start) & (spike_steps < end)
        ids = spike_i[mask]
        value = {'population_spikes': int(mask.sum()),
                 'population_rate_hz': float(mask.sum()/165122/((end-start)*.001)), 'groups': {}}
        for name, idx in groups.items():
            rows = np.flatnonzero(np.isin(record_indices, idx))
            a = activity[rows, start:end].mean(axis=0)
            count = int(np.isin(ids, idx).sum())
            value['groups'][name] = dict(neurons=len(idx), spike_count=count,
                rate_hz=count/len(idx)/((end-start)*.001), mean_activity_hz=float(a.mean()),
                peak_mean_activity_hz=float(a.max()), final_mean_activity_hz=float(a[-1]))
        result[phase] = value
    for name in groups:
        result['stimulus']['groups'][name]['rate_minus_baseline_hz'] = (
            result['stimulus']['groups'][name]['rate_hz']-result['baseline']['groups'][name]['rate_hz'])
    return result
