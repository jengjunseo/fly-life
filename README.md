# MaleCNS Virtual Fly — MVP v0.1

A real **165,122-neuron MaleCNS-connectome-derived LIF brain** drives one virtual
fruit fly in a small interactive 3D ecology. A native Godot experiment console
makes the sensory inputs, selected circuits, body consequences and scientific
uncertainty visible on a 4K desktop.

This is an experimental connectome-driven animal model, not biologically complete
Drosophila. The original SciPy brain, signed/pruned graph, PCG64 noise, 1 ms neural
timestep and motor decoder remain unchanged. No scripted focal-fly steering,
hidden behavior policy or substitute network is used.

## Run

On the prepared development machine, from this repository root:

```powershell
.\run_mvp.ps1
```

It launches both owned processes, opens 3840×2160 fullscreen, warms the actual
brain, and creates a fresh session directory. Exit shuts down the brain and its
process tree. No five-terminal setup is required.

Fresh checkout (Windows, Python 3.11 x64):

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe mvp/setup_godot.py
.\run_mvp.ps1
```

The freeze includes the checksummed runtime weights, annotation table and count
matrix (about 60 MB total), so running does not require re-downloading the raw
1.03 GiB dataset. To regenerate from official pinned data, use `acquire.py` and
`preprocess.py`; the preserved [brain-core guide](docs/BRAIN_CORE.md) explains
preprocessing, sign assumptions and the older core-only commands. Do not run old
report-writing certification scripts over archived evidence; use the new suite.

Useful launch options:

```powershell
.\run_mvp.ps1 --preset PREDATOR
.\run_mvp.ps1 --preset "PREDATOR + HEAT" --world-seed 20260914 --brain-seed 20260913
.\run_mvp.ps1 --preset FOOD --duration 3.5 --logdir mvp/logs/my-new-food-run
```

`--windowed`, `--godot <path>`, and a wall-time safety `--quit-after <seconds>` are
available. Log destinations must be new, protecting prior experiments.

## Use the console

Select CONTROL, PREDATOR, FOOD, FEMALE, HEAT or PREDATOR + HEAT and apply/reset.
The common 0.5 s baseline is followed by finite stimuli and recovery. Run, pause,
single 50 ms step, reset, seeded world-object creation, temperature and shade
controls work without editing code. Only initial conditions and world objects
change; locomotion remains neural-driven. Camera overview/follow and F11 affect
viewing only. Escape exits fullscreen before closing a windowed session.

LC4, LPLC2, GF/DNp01, DNa01, DNa02 and DNp09 remain visible; secondary tabs expose
LC9, food/fly-odor/thermal groups, Fdg and the actual pC1 family. Bounded neural
sparklines, explicit status badges, physiology, performance health and a causal
timeline make both positive and negative observations readable.

[Practical experiment guide](EXPERIMENTS.md) · [Scientific status](SCIENTIFIC_STATUS.md)
· [Known limitations](KNOWN_LIMITATIONS.md)

## What is real and what remains unresolved

**VERIFIED:** MaleCNS identities, actual connectome-derived matrix and tested
sensory-current → neural computation → original decoder → collision-aware body →
next-sensory chain. **EXPERIMENTAL:** receptor transfer functions, pooled visual
features, motor interpretation and simplified physiology. **UNRESOLVED:** feeding,
courtship, directional retinotopy and biological avoidance. **DISABLED:** neural
pain and female-specific contact mappings. **PLACEHOLDER:** gut/defecation model.
Food contact never automatically feeds the fly; no pC1/P1 injection creates courtship.

Arena interior expands from 7.8×7.8 = 60.84 to 11.0308658×11.0308658 = 121.68
world units², exactly 2× inside the wall collision faces. Object counts and sensory
gains are not doubled. Floor/outer dimensions and fly-radius clearance are
reported separately so the area claim is unambiguous.

## Hardware and performance

Tested on Ryzen 3 4100 (4C/8T), 16 GB RAM, Radeon RX 570, Windows, Godot 4.6.1
OpenGL. Neural computation is CPU-only. The screen can render near 60 FPS while
the original full-population SciPy simulation advances well below realtime.
The console displays actual compute p50/p95/p99 and neural/wall time; it does not
hide slow biological time or change scientific semantics to meet a deadline.

See [final full-app measurements](reports/mvp/RESULTS.md). The separate
[Performance v1 freeze](PERFORMANCE_V1_FREEZE.md) preserves Gate A–E findings;
Brian2 experimental numbers are not claimed as final-app performance.

## Verify and reproduce

```powershell
.venv/Scripts/python.exe mvp/test_all.py
.venv/Scripts/python.exe mvp/integrity.py after
.venv/Scripts/python.exe mvp/run_suite.py --out mvp/logs/my-new-suite
.venv/Scripts/python.exe mvp/analyze.py --runs mvp/logs/my-new-suite --out mvp/logs/my-new-analysis
```

The test runner redirects outputs from legacy tests into new MVP evidence and
preserves their old certificates. The final freeze manifest, hashes, screenshots
and classified gates are in [MVP_FREEZE.md](MVP_FREEZE.md). Future work belongs in
[v0.2 / research backlog](DEFERRED_WORK.md), not another unfinished v0.1 round.

Data credit: FlyEM / HHMI Janelia, Cambridge, MRC LMB and Google Research;
MaleCNS v1.0, CC-BY-4.0. Official pinned source URLs and SHA-256 are retained in
`data/raw/manifest.json`; exact processing/sign policies are in `config.json`
and `data/runtime/metadata.json`. See [data attribution](DATA_ATTRIBUTION.md).

