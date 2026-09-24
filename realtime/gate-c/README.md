# Gate C — Gaussian RNG rescue, isolated from verified Gate A/B

All experimental sources and reports are dedicated Gate C paths. Existing model,
runtime weights, Gate A/B sources/reports, body/ecology and JSON bridge are read-only.
This is Brian2 2.9 C++ standalone, not a custom SNN backend.

From the repository root, baseline Python is `.venv/Scripts/python.exe` (NumPy2.4.6).
Brian2 entry uses the already isolated Gate A NumPy1.26.4 compatibility directory.
No baseline package is downgraded. Only the experimental child USERPROFILE is
redirected to workspace `work/brian2-gate-c/cache-home` to avoid Brian home writes.

## Ordered execution

1. `.venv/Scripts/python.exe realtime/gate-c/preserve.py before`
2. `.venv/Scripts/python.exe realtime/gate-c/audit.py`
3. `.venv/Scripts/python.exe realtime/gate-c/rng_bench.py 1`
4. `.venv/Scripts/python.exe realtime/gate-c/run_c2.py`

C0 audits actual frozen generated C++, model parameters, full graph, input/baseline
and tape SHA. It extracts the **actual unmodified generated RandomGenerator class**
into an intermediate header for C1. Frozen 2s consumption evidence does not include
noise pre-generation and is not a sustained realtime claim.

C1/C2 RNG-only uses 165122 samples per ms, float32 output stores, independent
per-thread MT states, static OpenMP neuron loop. Warmup 50ms is separate from two
actual 1-second measured runs. Compile/startup and checksum are outside timing.
The compiler DLL directory must be in the child PATH. The first launch found a
missing DLL (0xC0000135); adding the existing compiler bin to child PATH fixed the
launch, without touching RNG/neural parameters. That failed launch is not a sample.

C2 runs RNG-only 2/4/8T followed by full Brian native-noise 1/2/4/8T until an actual
full p99<=50ms is found. No concurrent producer is active. Full measurements use
400 consecutive nonoverlapping 50ms windows (20 neural seconds) per tested setup.
`full.py` imports the **unchanged** Gate B translation and replaces only its
experimental setup callable to set Brian's OpenMP preference. Weight i/j/w arrays
are checked against the whole actual runtime graph after every run.

Each quantum timer is inside one persistent generated `Network.run`, excludes
boundary input/stat/log maintenance, and includes Gaussian draws within the neural
loop. The entire Network.run wall includes maintenance and is reported separately.
Python launcher, code generation, compiler/linker, C++ initialization and output are
separate fields. Completed neural time is the authority; there is no world run here.

Native seeded MT stream is not NumPy PCG64-identical. Parallel configurations also
change stream assignment. Exact stream claims apply only to shared-noise runs;
native candidates must pass stochastic statistics/circuit checks over three seeds.

## Conditional stages, not automatically built

If C2 full native p99<=50ms: C3/C4 are forbidden; validate that candidate with three
distinct reference/candidate seeds, then stop. If C2 fails: only then perform C3
NumPy PCG64 float32 block generation (50/100/500/1000ms) and full network consumption.
If either side lacks long-term realtime throughput, C4 is forbidden and no final
candidate exists for multi-seed validation. Do not create a producer to conceal that
shortfall. Only if both sides pass independently but sequential combined execution
fails is minimal bounded double-buffer C4 allowed, with concurrent CPU contention
and noise-wait evidence. No Godot/ecology, persistent bridge or behavior work.

After the required terminal classification, run `preserve.py after` and deliver
Gate C results. Existing core/body decoder tests and old artifact SHA must pass.

## C3 reproduction (only after actual C2 failure)

`.venv/Scripts/python.exe realtime/gate-c/generation.py` measures NumPy2.4 PCG64
float32 blocks for 50/100/500/1000ms, two warmups then five measured trials each,
both allocation+fill and ordinary preallocated `out=` fill. It first verifies that
the flattened block equals the original per-ms float32 sequence after baseline.
Throughput excludes disk I/O and sanity statistics; allocation is explicitly
included/excluded per method. A measured mean >=165122000 normals/s is required.

`.venv/Scripts/python.exe realtime/gate-c/entry.py full c3-consumption 1 40 b0 frozen`
uses the existing Gate B tape READ-ONLY. A Gate C generated reader preloads the
bounded exact 2s (1,320,976,000 bytes) before Network.run, then memcpy-consumes one
N-row per ms into the same Brian noise array. Preload is initialization; row-copy
is quantum compute. This is 40 nonperiodic windows, not a 60s performance claim.
`.venv/Scripts/python.exe realtime/gate-c/check_consumption.py` compares actual
phase population/LC4/LPLC2/GF/DNp09 counts and active fractions against prior shared
SciPy B0. No scientific parameter or neural equation is changed.

If generation fails, stop without C4 or a final realtime candidate; do not run
multi-seed on a failed performance method. Finally run `preserve.py after`, then
`analyze.py`; SHA source/evidence manifests cover the new delivery only.

[Brian2 OpenMP/standalone preferences](https://brian2.readthedocs.io/en/2.9.0/user/computation.html)
