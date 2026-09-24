# Performance v1 — FROZEN (Gate A–E closed)

This is a record of completed research, **not a claim about the final app**.
The MVP still runs the certified SciPy reference. None of the Brian2 candidates
became a certified production Godot/ecology backend. Do not restart this sequence
for a 35 ms target; that headroom experiment is closed.

## Target and exact model

Ryzen 3 4100, 4 physical cores / 8 logical threads; 16,957,935,616 bytes RAM
(15.79 GiB); Radeon RX 570 renders Godot, no GPU neural compute. Windows build
26200, Python 3.11.9, NumPy 2.4.6, SciPy 1.17.1. Experimental isolated environment:
Brian2 2.9.0 / NumPy 1.26.4; TDM-GCC 9.2.0. Gate A used C++11 and later generated
proofs use C++17; inspect each archived makefile. `-O3 -march=native`, no fast-math.
Godot 4.6.1 stable, OpenGL compatibility, RX 570 driver observed 25.8.1.250617.

165,122 neurons; 6,327,564 effective signed connections; 6,474,533 retained
anatomical connections. Float32 LIF, dt 1 ms, preserved one-step spike delivery,
Gaussian current noise amplitude 0.1 (including refractory draws). Exact data and
parameter hashes remain in the archived reports and final manifest.

## What was tested

| Gate | Finding | Durable evidence |
|---|---|---|
| A | C++ translation survives; shared deterministic circuit behavior preserved, noise-off can exceed realtime | [Gate A](reports/realtime/DELIVERY.md) |
| B | Noise-on quantitative equivalence passes; same-input PCG64 tape provides stronger comparison than native MT seed. Very small deterministic 60 s drift. Native Gaussian compute is too slow | [Gate B](reports/realtime/gate-b/DELIVERY.md) |
| C | Native 1/2/4/8-thread RNG and full network tested. Best 8T full p99 176.163 ms; single PCG64 generation still insufficient. No pipeline adopted | [Gate C](reports/realtime/gate-c/DELIVERY.md) |
| D | Two persistent PCG64 workers resolve producer-only throughput; simultaneous full consumer suffers CPU contention. Best repeat-stable side p99 57.726 ms, worst tested 163.480 ms. D2 streaming forbidden by feasibility failure | [Gate D](reports/realtime/gate-d/DELIVERY.md) |
| E | Actual LIF update, synaptic delivery and threshold dominate. OpenMP, clear fusion, row-pointer consumption and 100 ms boundary fail stable headroom. Stop 4; no surviving candidate | [Gate E](reports/realtime/gate-e/DELIVERY.md) |

Gate E strong 1T short means 47.144–51.350 ms and p99 49.925–63.161 ms.
Clear-fused one-repeat mean 41.049 ms was attractive, but its other repeat p99
81.529 ms rejects a stable speedup. Persistent 20 s diagnostic means
44.211 / 61.488 / 50.250 ms, p99 61.447 / 90.625 / 81.741 ms, with respective
4.87% / 74.10% / 32.56% deadline misses. These runs replay a resident 2 s noise
tape; they are not independent 20 s Gaussian production or final-app results.

Built-in strong-workload profile: LIF 42.95%, delivery 27.55%, threshold 12.32%
of profiled CodeObject time. Together 82.83%. Generated delivery uses an OpenMP
master loop, so LIF-only scaling does not imply full-network scaling. Gate D
contention is not extrapolated to an unmeasured Gate E pipeline. Outliers remain
in the archive. Clock/power data did not prove a specific scheduler/cache/page-fault
cause; no speculative repair was made.

## Why this is closed

The cheap, scientifically equivalent cards did not create reliable consumer
headroom on this CPU. Reopening requires a concrete new hardware/backend research
hypothesis, its own scientific-equivalence criteria and budget. Read the existing
reports first; do not repeat Gaussian microbenchmarks or quietly alter dt/noise.
See [deferred work](DEFERRED_WORK.md). Final app timing is separate in
[SHOT 4 report](reports/mvp/RESULTS.md).
