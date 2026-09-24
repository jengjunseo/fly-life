# Known limitations — canonical v0.1 scope

- **EXPERIMENTAL neural dynamics:** full actual MaleCNS-derived identities and
  signed/pruned graph are real; homogeneous LIF parameters, current encoders,
  incoming normalization and scalar motor readout are engineering models.
- **EXPERIMENTAL locomotion:** DNa01/DNa02 determine the inherited left/right
  signal; DNp09 determines forward output. GF is observed but has no validated
  escape/flight/freezing body decoder. A displacement is not proof of avoidance.
- **UNRESOLVED directional vision:** bilateral visual pools have verified
  anatomical laterality but no calibrated receptive-field retinotopy. No desired
  heading or target position is sent to the decoder.
- **UNRESOLVED feeding:** odor/contact currents may activate upstream cells;
  ingestion remains disabled. Sugar SEL PN (GNG540) is an experimental CNS bypass,
  not a certified peripheral sugar GRN. The preserved annotation NT differs from
  a literature interpretation; no convenient NT override was applied. Fdg alias
  is verified, functional gate is not. Hunger does not make the fly seek food.
- **UNRESOLVED courtship:** generic VA1v/VA1d fly-odor input is not female-specific.
  pC1-family observation is not an exact P1 alias. Putative contact receptors are
  insufficient proof; the female-contact pathway is DISABLED.
- **DISABLED neural pain:** predator contact changes HP through an explicit world
  model; no unverified nociceptive injection. HP zero has the disclosed death stop.
- **PLACEHOLDER physiology:** gut processing, seeded-latency defecation, damage and
  hunger progression are simple world rules, not validated adult neural circuits.
  Normal presets start gut at zero, so no fabricated food fills it.
- **EXPERIMENTAL temperature:** actual thermosensory annotation groups receive
  bounded local temperature/change currents. Shade is a geometric cooling region;
  thermotaxis or shade-seeking is not demonstrated.
- **Slow neural-time runtime:** SciPy/PCG64 remains the certified production core.
  The Brian2 optimization line is closed and was not deployed. UI rendering can be
  smooth while biological time advances much more slowly than wall time. Pausing
  waits for a quantum; it is not an instantaneous cancellation of brain compute.
- **Short single-seed autopsy:** six 3.5 s runs include baseline, finite stimuli
  and recovery. This is reproducible product verification, not population-level
  behavioral validation, multi-seed statistics, or a proof of causal mediation.
- **Snapshot display:** the ecology shown with a packet is that quantum's input
  snapshot, so it lags the completed body by up to 50 neural ms. Group curves show
  EMA sampled at neural boundaries, not interpolated per-neuron activity.
- **4K first:** the primary console targets 3840×2160. Smaller windows retain
  scrollable side panels; 1080p is not an equally dense or fully validated target.
- **Simple finite ecology:** fixed presets contain one object per selected type,
  no background spawns. Manual controls add conditions; NPC motion is scripted
  world behavior, while the focal fly is exclusively neural-driven. Primitive
  spheres are intentionally not anatomical reconstructions.

Future research and optimization belong in [DEFERRED_WORK.md](DEFERRED_WORK.md).
Historical certificates in `reports/` retain their original, narrower scope.
