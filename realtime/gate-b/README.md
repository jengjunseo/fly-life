# Brian2 Gate B0 / B1 / B2 — verification only

The verified core, body, ecology, Gate A sources, matrices, configs and reports remain
unchanged. New source/evidence is confined to `realtime/gate-b/` and
`reports/realtime/gate-b/`; generated binaries and intermediate inputs live under
workspace `work/brian2-gate-b/`. Do not overwrite this delivered evidence when rerunning.

## Environment

Actual Ryzen 3 4100 / 4C8T / 16GB Windows; GPU compute and OpenMP disabled.
Original Python3.11.9 / NumPy2.4.6 / SciPy1.17.1 runs the reference. `entry.py` uses
Gate A's separate NumPy1.26.4 directory ONLY for Brian2 2.9.0 compatibility, never
downgrading original NumPy. Brian cache is redirected to work. Existing TDM-GCC9.2
is used with ordinary release flags `-O3 -march=native -std=c++17`, no fast-math.
C++17 inline variables share the measurement hooks across generated translation units;
this is instrumentation compatibility, not a new neural backend or altered model.

## Noise policy

Reference truth: NumPy default_rng PCG64, seed from config (20260913); float32
baseline heterogeneity is drawn first. Each 1ms update draws N independent float32
standard normals, multiplies by unchanged noise amplitude 0.1, and adds them to
baseline+syn before external current. Draws occur even for refractory neurons.
This is discrete CURRENT noise; not continuous voltage diffusion (`xi`).

B0 has TWO comparisons, both against the original actual noise-on SciPy run:

1. A bounded 2s tape reproduces the exact PCG64 float32 stream after baseline draw.
   Shape `[2000,165122]`, C order, little endian float32, index `[step,runtime_index]`.
   C++ reads one vector each step; amplitude is applied in the same float32 position.
   The tape is ~1.32GB on disk but only a small vector is resident in the C++ process.
   `noise-tape.json` records SHA/dimensions/mean/variance/seed. This proves exact current
   injection semantics, but its throughput is NOT used to claim live RNG realtime.
2. Native Brian2 noise uses its ACTUAL generated `objects.h`: std::mt19937 + polar
   Box-Muller. Same numeric seed, same independent Gaussian per-neuron/per-step law,
   float32 cast and scaling. Its stream differs from PCG64. B0 quantitative equivalence
   is applied separately, and B0 performance/B1 generate this noise INSIDE C++.

The native stream is seeded/reproducible but not reference-seed-identity equivalent.
Noisy exact spike-train identity is therefore not claimed; the shared tape demonstrates
the stronger same-input check. No noise amplitude, gain, timestep or connectivity tuning.

## B0/B1/B2 setup

B0 comparison: 0.5s warmup + 0.5s baseline + 0.5s existing LC4/LPLC2 current 3 +
0.5s recovery; LC4/LPLC2/GF/DNp09/population only. Population rate PASS range90–110%,
dead rate/active <50%, recovery runaway >200%, simultaneous spike fraction>=25%,
finite/input/GF/recovery/DNp09 criteria are recorded by `b0_check.py`.

B0 performance: one generated persistent 20.5s Network.run, with 0.5s warmup,
10s baseline, 10s sustained looming. RNG cost is included. Each condition's actual
compute time is the sum of its 200 internal 50ms timers; full Network.run including
boundary overhead is also reported. Shared noise file playback is NOT a live performance result.

B1: baseline60s/1200 windows, looming20s/400 windows, real trace20s/400 windows,
compound20s/400 windows. Every workload runs one persistent C++ binary; no restart/build
per quantum, no Python neural loop. Actual compute timers span50 real1ms Brian steps.
Raw C++ windows plus structured JSON retain neural start/end, compute ms, factor/slack,
population count and selected activity. Boundary stats/input replay/file writes are
outside individual compute timers, but INCLUDED in the full Network.run wall timer.
Realtime requires actual60s total<=60s AND p99<=50ms. Stress runs are NOT extrapolated to
60s; failing their p99 alone already rejects realtime. Miss<1%, longest<=2 are quality targets.

`prepare.py` reuses the EXACT delivered ecology `live/brain.jsonl` 60 actual frames:
resolved body IDs and all actual sensory amplitudes, plus raw geometry and source SHA.
Real-predator replay repeats that3s actual current sequence, including original concurrent
food/heat/female channels. It is not substituted by a guessed square pulse or a new world.
Compound stress sustains the strongest actual recorded visual snapshot combined with the
strongest actual recorded hot current, others zero; original resolved groups/policy/gains.
No new biology/mappings/behavior/decoder, and NO Godot/ecology migration.

B2: both implementations run the SAME60s initial state/deterministic drive/input schedule:
20s baseline +20s LC4/LPLC2 current3 +20s recovery, noise OFF. Every1s records cumulative
population and LC4/LPLC2/GF/DNp09 counts and group EMA. All60 samples are saved.
Simple absolute/signed mismatch slopes/R2, late20s trend, normalized error and phase
statistics support bounded/growing classification; exact spike identity is not required.
The conservative trend rule is predeclared in `analyze.py` before B2 results are obtained.
It is not an indefinite mathematical-bound proof or multi-seed statistical certification.

## Reproduction sequence

Run from workspace containing `outputs/brain-core`. First use NEW report/build paths or
archive only this experiment's own delivered evidence. Never rewrite earlier report suites.

```powershell
outputs/brain-core/.venv/Scripts/python.exe outputs/brain-core/realtime/gate-b/preserve.py before
outputs/brain-core/.venv/Scripts/python.exe outputs/brain-core/realtime/gate-b/prepare.py
outputs/brain-core/.venv/Scripts/python.exe outputs/brain-core/realtime/gate-b/reference.py b0
outputs/brain-core/.venv/Scripts/python.exe outputs/brain-core/realtime/gate-b/noise_tape.py
outputs/brain-core/.venv/Scripts/python.exe outputs/brain-core/realtime/gate-b/entry.py candidate b0-native
outputs/brain-core/.venv/Scripts/python.exe outputs/brain-core/realtime/gate-b/entry.py candidate b0-frozen
outputs/brain-core/.venv/Scripts/python.exe outputs/brain-core/realtime/gate-b/b0_check.py
outputs/brain-core/.venv/Scripts/python.exe outputs/brain-core/realtime/gate-b/entry.py candidate b0-performance
# Only after B0 quantitative equivalence passes:
outputs/brain-core/.venv/Scripts/python.exe outputs/brain-core/realtime/gate-b/run_remaining.py
outputs/brain-core/.venv/Scripts/python.exe outputs/brain-core/realtime/gate-b/preserve.py after
outputs/brain-core/.venv/Scripts/python.exe outputs/brain-core/realtime/gate-b/analyze.py
```

Runs are SEQUENTIAL to prevent CPU benchmark contention. `run_remaining.py` executes
four B1 loads followed by SciPy60s B2 and Brian260s B2; exit/completion history is saved.
Generated code, full i/j/w array checks and executable SHA prove actual full-size C++ execution.
Per-run codegen/compile-link/init/Network.run/quantum sums/result-output/Python orchestration
and executable-vs-preparation tree RSS are distinct, not conflated.

Existing body/ecology aggregate remainder ~8.5%/~19.4% is recorded debt only; it includes
startup/socket/log/ACK/waits and is not a steady-state prediction under a fast backend.
Stop after B0/B1/B2 classification. No alternative backend, Gaussian RNG retuning,
IPC optimization, graphics, persistent integration, or additional circuits.

Primary references (actual generated source takes priority over generic docs):

- https://brian2.readthedocs.io/en/2.9.0/advanced/random.html
- https://brian2.readthedocs.io/en/2.9.0/user/computation.html
- https://brian2.readthedocs.io/en/2.9.0/user/running.html#scheduling
