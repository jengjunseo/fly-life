# Gate E: consumer profiling and cheapest semantics-preserving experiments

Experimental only; report `reports/realtime/gate-e/DELIVERY.md`. Do not mutate
prior Gate A/B/C/D sources, reports, runtime data or body/ecology integration.

Run from brain-core with `.venv/Scripts/python.exe`. `entry.py` enables the
existing isolated experimental NumPy1.26.4 used by Brian2 2.9; baseline stays2.4.6.

Completed ordering:

1. `realtime/gate-e/preserve.py before` (never recapture/overwrite).
2. `realtime/gate-e/audit.py` inspects actual old generated rules, preload,
   monitor and delay path, records power plan. No global power/priority changes.
3. `entry.py build 1 baseline 1`, then
   `entry.py measure current-1t-baseline-p1-2s-q50 0 6`.
   `entry.py stages profile` produces the strongest input built-in profile.
4. `entry.py stages scale` serially builds, measures3 repeats, verifies shared
   input output equivalence, and profiles1/2/4T. Stops if stable35ms achieved;
   no8T unless measured4T scaling justifies it (not justified in delivered run).
5. `entry.py stages cheap` tests only one change at a time: clear-fused,
   then existing row-pointer zero-copy consumer. Each requires full exact neural
   state/circuit identity versus same-input1T control, not just a speed result.
6. `entry.py stages timeline`:20s persistent diagnostic with resident2s frozen
   noise replay;400 consecutive windows, first0.5s excluded. Replays are explicitly
   diagnostic, not production independent20s Gaussian noise/pipeline certification.
7. `entry.py stages planz`: only after cheap35ms failure and typical40–50ms
   consumer cost. Same20s input/initial state,100ms boundary, dt1ms unchanged;
   verify full final state SHA exact. Diagnostic only, not control architecture.
8. `preserve.py after`: prior artifacts SHA and regression tests.
9. `entry.py analyze`: evidence-only JSON/report/timeline/histogram/SHA generation.
   Static charts use `plot.py` with Pillow in the bundled desktop runtime.
   Set `GATE_E_PLOT_PYTHON` to a Pillow-enabled Python executable if its location
   differs; no plotting dependencies are installed in the verified brain venv.

Build and timing processes never overlap. Each completed result directory uses
`mkdir(exist_ok=False)`; never overwrite existing delivered trials. Benchmarks
set HIGH_PRIORITY_CLASS only on owned disposable consumer/controller processes,
not REALTIME and not other user processes. All actual affinity/priority evidence
and aggregate PDH Processor Performance readings are stored per trial.

No producer optimization, generic buffer, double-buffer production integration,
IPC/Godot/ecology rewrite, fourth shot, Console UI, resize, GPU/backend/Rust,
dt/weights/pruning/connectivity/neural equation/delay/noise amplitude work.

`clear-fused` only moves zeroing of the incoming scratch accumulator after its
single LIF use, instead of the next timestep's start pass. Final scratch itself
is zero rather than pending-clear; all full neural dynamics states, counts,
readout and circuit observations must be identical. It was rejected, not adopted.
`zero` points to the frozen row and restores the owned allocation before end.

Final classification does not extrapolate Gate D contention or claim an E5
concurrent/pipeline certification without actual measurements. When no cheap
consumer headroom candidate survives, E5 is conditional NOT RUN and stop4 applies.
