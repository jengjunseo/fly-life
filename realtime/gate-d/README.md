# Gate D — noise supply headroom experiment

Experimental only. Final measured decision: D1 concurrent feasibility failed;
no D2 pipeline, D3 sustained certification, D4 stochastic certification or adoption.
Full report and per-repeat evidence: `reports/realtime/gate-d/DELIVERY.md`.

All commands below are run from brain-core with `.venv/Scripts/python.exe`.
`entry.py` uses the existing isolated experimental NumPy 1.26.4 dependencies;
baseline NumPy 2.4.6 and prior verified artifacts are not changed.

## Completed experiment ordering

1. `realtime/gate-d/preserve.py before` (already captured; do not recapture).
2. `realtime/gate-d/entry.py generate_bench direct`.
3. `realtime/gate-d/entry.py run_d0` (worker counts stop at first p99 <=35ms).
4. Build both baseline and looming consumers before measurement, using
   `entry.py build_consumer <threads> <scenario> [zero]`.
5. `entry.py contention <label> <threads> <comma-separated-brain-cpus> <comma-separated-producer-cpus> [zero]`;
   see actual argument syntax in contention.py. Each label has private result
   directories and refuses to overwrite completed experiment directories.
   `run_remaining_d1.py` and `run_zero.py` orchestrate clean sequential trials.
6. `entry.py measure_off` records matched producer-OFF and producer-only checks.
7. `realtime/gate-d/preserve.py after` performs baseline SHA and regression tests.
8. `realtime/gate-d/analyze.py` generates the report, summary and SHA manifests
   from existing evidence only. This command does not simulate or benchmark.

Do not rerun wrappers over completed private result directories. Reproduction
requires new explicit experiment labels and corresponding report paths; preserve
the delivered evidence. Never compile during a concurrent timing trial.

## Scientific and timing scope

Full unchanged Gate B Brian2 model: 165122 neurons, 6327564 effective signed
synapses, float32, dt1ms, original weights and currents. Consumer D1 noise is
the frozen exact nonperiodic 2s PCG64 tape, preloaded outside compute clocks.
Producer runs concurrently but discards its output: D1 is not a streaming
pipeline. Brain first 0.5 neural second is excluded, leaving 30 measured 50ms
windows per repeat; three repeats for each baseline/strong workload.

Producer workers are persistent, each with an independent spawned PCG64 child
stream and fixed runtime-index slice. Output is worker-major float32. The
row-pointer variant includes C-order packing cost in its producer timing.
Thread-level actual Windows masks and IDs are recorded, not inferred from
process affinity. No claim of exact single-reference sequence or network-level
parallel RNG equivalence is made. Shared-input 1T copy/zero exact state proof
is recorded separately.

Sources, generated proofs, reports and intermediates are Gate D-only. No Godot,
ecology migration, IPC rewrite, fourth-shot, Console UI, resize, GPU, new model,
weight/dt/noise-amplitude tuning, generic ring buffer or future world-state work.
