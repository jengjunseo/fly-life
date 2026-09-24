# MaleCNS MVP v0.1 — freeze record

**Decision: PASS — frozen 2026-09-24.** The releasable product is the unchanged
MaleCNS-derived full connectome and SciPy/PCG64 LIF core, driven through the
original neural decoder and body controller by a finite, controlled ecology,
with a native 3840×2160 Godot console. The evidence below supports an MVP
software freeze. It does not certify biological behavior or realtime speed.

## Included product

- One launch command starts the certified Python brain, original Godot body, and
  the four-panel console: `./run_mvp.ps1` on Windows PowerShell.
- Six reproducible worlds are available: CONTROL, PREDATOR, FOOD, FEMALE, HEAT,
  and PREDATOR + HEAT. Seeds, finite stimulus schedules, pause/step/reset,
  camera, temperature, shade, and world-object controls are exposed.
- The fly's movement continues through the original neural decoder and body
  path. There is no target-direction command or scripted steering for the focal
  fly. Ecology objects can follow simple world schedules.
- The arena's clear inner floor is 11.0308658 × 11.0308658 units (121.68²).
  The previous 7.8 × 7.8 floor (60.84²) is exactly half that area, within
  floating-point geometry precision. Wall ray and sphere-collision checks pass.
- The original MaleCNS sources, model inputs, prior certificates, and evidence
  are byte-identical to the pre-MVP snapshot: 820 files, zero differences.
  New artifacts have a SHA-256 manifest at `reports/mvp/freeze-hashes.json`.

## Acceptance evidence

- **Software regression:** 29 tests passed, zero skipped, including original
  core/data/decoder tests, real MaleCNS stimulus integration, ecology rules,
  preset replay, geometry, and action-boundary checks. Full report:
  `reports/mvp/tests.json`.
- **Live experiments:** all six matched-seed, full-application runs completed
  3.5 world-seconds and 70 neural quanta apiece, with the 0.5-second baseline
  warmup, actual Godot body commits, replay checks, and clean process exits.
  Circuit counts, body traces, performance, and interpretation boundaries are
  recorded in `reports/mvp/RESULTS.md` and `reports/mvp/summary.json`.
- **Desktop QA:** actual full-screen 4K interaction passed pause, one-quantum
  step, reset, camera follow, interpretation view, full-screen/windowed return,
  paused-world edits, temperature and shade, clear, UI preset selection, and
  heat response. The final app exited cleanly. Machine-readable checks and
  screenshot references: `reports/mvp/visual-qa.json`.
- **Replay:** paused and reset predator traces, plus a HEAT run selected from
  the UI, reproduce the first 70 observable neural/body outputs exactly against
  the corresponding fixed-seed run. Timing fields are deliberately excluded.
- **Historical integrity:** `reports/mvp/historical-before.json` and
  `reports/mvp/historical-after.json` retain the complete 820-file comparison.
  The final manifest covers all indexed deliverables except itself and its
  verification-result file; its verifier checks exact file bytes.

## Scientific status

Anatomical identities, retained signed connections, selected sensory mappings,
and the software path from the preceding body acknowledgment through the real
network, original decoder, and resulting body commit are verified within the
scope documented in `SCIENTIFIC_STATUS.md`. The six interventions establish
observed responses at the recorded seeds. They do not establish population
statistics, neural mediation, or validated fly behavior.

Predator input raises the measured visual groups and GF, produces a small
forward displacement, and the world records contact damage. DNp09 has only a
small response, while DNa01/DNa02 remain silent; avoidance is unresolved. Food
odor and contact strongly activate upstream groups, while Fdg, movement,
ingestion, and gut change remain absent. Generic fly odor activates sensory
and pC1-family observations, but sex recognition and courtship remain
unresolved. Heating and cooling activate the mapped hot/cold groups; the world
temperature changes, while thermotaxis is unresolved. Neural pain is disabled;
damage, gut, and defecation behavior remain explicit world-model rules or
placeholders.

The verified full graph contains 165,122 neurons and 6,327,564 effective
signed connections (6,474,533 retained anatomical connections). LIF parameters,
sensory currents, normalization, and scalar motor readout remain experimental
engineering choices. No new behavior was invented to make an experiment appear
successful.

## Runtime finding and limits

On the recorded Ryzen 3 4100 / 16 GB RAM system, full-app rendering held a
60 FPS median in the six short runs. The measured neural-time rate was about
0.038–0.079 active neural seconds per wall second; including launch and warmup,
  the 3.5-second worlds took about 50.6–104.5 seconds. The pure brain-step p50
was about 0.51–1.09 seconds per 50 ms quantum, depending on condition. This is
measured performance, not a realtime claim or a sustained-tail guarantee.
Previously closed Gate A–E profiling remains closed. No custom backend, GPU
rewrite, timestep change, or model simplification is part of this release.

## Reproduce and inspect

From the repository root on Windows, run `./run_mvp.ps1`. `README.md` documents
first-time dependencies and data acquisition. `EXPERIMENTS.md` describes the
six fixed-seed conditions and evidence; `PERFORMANCE_V1_FREEZE.md` records the
closed performance investigation; `KNOWN_LIMITATIONS.md` and
`DEFERRED_WORK.md` define the scientific and v0.2 boundaries. Complete result
logs and desktop captures are retained under `reports/mvp/`.

Freeze checks are retained in `reports/mvp/tests.json`,
`reports/mvp/geometry.json`, `reports/mvp/visual-qa.json`,
`reports/mvp/historical-after.json`, and `reports/mvp/freeze-hashes.json`.
