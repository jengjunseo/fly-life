# MVP corrections and preservation record

The original `braincore/`, `config.json`, data, decoder, body, ecology and Gate
A–E implementation/report files are kept byte-for-byte. New functionality lives
in `mvp/` and `body/mvp/`; the canonical README is refreshed and its previous
content preserved in `docs/BRAIN_CORE.md`. `.gitignore` excludes scratch packages,
Godot import/cache files, tools and interactive logs. Historical reports are
explicitly included in the freeze commit, even though several were untracked at
handoff.

## Evidence-supported changes

- Queue all world/control edits until a completed body ACK. The old ecology
  bridge serviced world events inside the 1 ms stepping loop; a world mutation
  could therefore precede the matching body quantum completion. The MVP adapter
  applies conditions only at the 50 ms boundary. It refreshes sensory geometry at
  the same world time, without a fabricated instantaneous thermal derivative.
- Add pause/resume/single-quantum execution through the existing loop. Pausing
  completes in-flight work. A step runs all 50 unchanged neural updates and the
  actual Godot collision-aware body commit; no synthetic movement is substituted.
- Remove repeated body-ID lists **from MVP telemetry only**. Actual selectors and
  resolved members remain in the run mapping artifact. The core current builder
  and original evidence are untouched; only selected-group telemetry is streamed.
- Add actual selected-group spike counts and EMA, explicit observation-threshold
  events, and bounded charts. They neither feed back into the model nor determine
  locomotion. UI text is limited to 10 Hz.
- Place Godot engine logs and its APPDATA cache in the workspace. The first
  sandbox smoke failed when Godot could not write user logs; the scoped cache
  eliminated the corresponding startup/cache errors in user-desktop runs.
- Preserve false-timeout evidence: `final-v1/food` records a 15.691 s gap between
  receipt of a neural packet and the Godot body commit. The prior 3 s heartbeat
  rule terminated the bridge. The final MVP uses a 30 s transport grace period,
  retains complete ACK lockstep, and shows a waiting/held-body status after 3 s
  without a brain packet. No neural step or world time is extrapolated. Root
  cause of the desktop scheduling stall is not asserted. A real disconnect still
  freezes and owned-process cleanup terminates the session.
- Session folders are unique and refuse overwrites. The launcher monitors and
  reaps its owned process tree; the suite stops its owned launcher on interruption.
- Add a pinned Godot setup helper that checks the original archived SHA and does
  not overwrite historical acquisition reports.
- Increase inside-wall floor area exactly 2× while retaining wall thickness,
  entity counts, spawn locations, sensory gains and body geometry. The changed
  wall-centre half-width is derived from the original 4.0 value; the separate
  physics fixture checks four actual wall faces and fly-radius collision.

## What was not changed

No new backend, no dt/noise/weight/sign/gain changes, no new behavioral decoder,
no neural pain/contact enablement, no ingestion gate enablement, no P1 aliases,
no scripted focal-fly AI. Gate A–E remains closed. Cosmetic and observability
refinements do not upgrade biological confidence.

Early work/smoke runs and the interrupted initial suite are development evidence,
not final performance claims. `final-v1` retains the failed food run; `final-v2`
is the final six-condition evaluation after transport-grace correction. The
historical-before/after manifests establish preservation independently of Git's
inherited line-ending normalization.
## Exact-byte Git storage

The handoff working tree contains a small inherited CRLF/LF discrepancy versus
old Git blobs in historical text console files. The before/after check uses the
actual handoff bytes and leaves them untouched. The freeze disables Git EOL
conversion (`* -text`) so a fresh checkout reproduces those exact certified bytes.
Any diff from an old blob caused solely by the previously inherited EOL state is
storage normalization, not rerun or alteration of an experiment. Old commits
remain available. Runtime NPZ/Parquet files are intentionally included, and raw
Feather downloads remain excluded. The freeze hashes cover exact indexed files.
## Final manual-QA correction

A paused-world edit originally changed the backend but did not refresh the entity
meshes until the next ready packet. Manual QA reproduced this in `ui-qa`.
`body/mvp/main.gd` now refreshes entity meshes on paused state packets too, without
ACKing or advancing a neural/body step. The input label explicitly says **last
quantum input**, because changing world conditions while paused does not claim
that their neural currents have already been consumed. The final-product-test
checks paused spawn/temperature/shade edits, exact single-step time, resulting
sensory responses, clearing and a UI-selected HEAT reset. This rendering-only
paused branch is separate from the six continuously running final-v2 measurements.

The initial strict Python-vs-Godot log equality check found only Godot decimal
JSON rounding, maximum motor absolute difference 4.85722573273506e-17. Python's
recomputed original decoder is still compared exactly; only the Godot textual
roundtrip allows 1e-12 absolute error. `analysis/` preserves the initial result;
`final-analysis/` and canonical RESULTS.md apply the justified serialization test.
No model value or actual motor output was changed to satisfy that check.
