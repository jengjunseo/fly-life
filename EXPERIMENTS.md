# Experiment guide — at the 4K console

Launch from the repository root in PowerShell:

```powershell
.\run_mvp.ps1
```

The full real brain loads and warms for 500 neural milliseconds. This takes wall
time; controls remain disabled during startup. The world then progresses in
completed 50 ms neural quanta, often visibly slower than realtime on the Ryzen 3.

1. Choose a preset and world/brain seeds, then **Apply preset + reset**. The selected
   draft is not active until applied. The top bar and body panel show active values.
2. Watch the first 0.5 s of world time as the common baseline. The finite stimulus
   starts at world 0.50 s. Observe through at least 3.5 s for stimulus and recovery.
3. **Pause** waits for the in-flight quantum to finish. **Step** completes exactly
   one additional 0.05 s, then remains paused. **Run** resumes. World edits queued
   during compute are applied only after the actual body ACK.
4. Reset repeats the current initial conditions and both RNG seeds. Manual edits
   are logged but reset discards them. To repeat an intervention exactly, use the
   prescribed preset or replay the same commands at the same completed world times.

| Preset | Stimulus | Watch | What is not claimed |
|---|---|---|---|
| CONTROL | No scheduled objects/heat | Baseline GF, LC4/LPLC2, silent motor readouts | Spontaneous biological locomotion |
| PREDATOR | One sphere at (0.8,0.3,-2.5), speed 3, lifetime 1.8 s | LC4/LPLC2 and LC9, then GF/DNp09; actual displacement, contact and HP | Faithful escape, flight or avoidance |
| FOOD | Food at the starting fly position, lifetime 2.5 s | ORN DM1, Sugar SEL PN bypass, Fdg, gut | Feeding is unresolved and ingestion stays disabled |
| FEMALE | Nearby generic fly-odor source and moving figure, lifetime 1.5 s | VA1v/VA1d, LC9, pC1 family | Sex recognition, courtship or exact P1 identity |
| HEAT | 25→34°C, 0.4 s ramp / 0.6 s hold / 0.4 s recovery | VP2 hot / VP3 cooling, local temperature | Shade seeking or thermotaxis |
| PREDATOR + HEAT | Same two stimuli together | Visual and thermal circuit responses separately | A validated behavioral priority policy |

Manual buttons add food, predator, female or a heat pulse without moving the fly.
Spawn positions are seeded world-model positions. **Set temperature** applies a
15–40°C ambient setting at the boundary; it changes temperature offset without
inventing an instantaneous derivative. **Shade** toggles the existing 6°C local
cooling rectangle. **Clear objects + pending stimuli** removes entities, scheduled
stimuli and the active heat pulse; it does not reset the brain or body.

Primary cards show mean selected-group EMA in Hz. Each chart is at most 120 actual
neural samples (6 neural seconds), independently autoscaled; equal heights do not
mean equal rates. The lower circuit tab exposes food, fly-odor, thermal, Fdg and
pC1 groups. Timeline activity-rise markers use EMA above the pre-stimulus maximum
plus 10 Hz, with 5 Hz hysteresis. They are observations, not proof of pathway
causality. Raw per-quantum group spike counts are also in the evidence logs.

**Overview / follow** changes the camera only. F11 enters/exits fullscreen. Escape
exits fullscreen first, then closes when windowed; **Exit** always closes cleanly.
Keys: Space pause/run, N step, R reset, F food, P predator, M female, H heat.

Every launch gets a new `mvp/logs/<timestamp>` directory. Save that directory to
reproduce/inspect a session: configs, mappings, seeds, commands, sensory features,
neural outputs, actual body commits, events, timing and screenshots are together.
The scene shows the input world snapshot, at most one neural quantum behind the
completed body. The clocks explicitly distinguish world, neural (includes warmup)
and wall time for the current generation.

For the finite six-condition suite (run sequentially, never concurrently):

```powershell
.venv/Scripts/python.exe mvp/run_suite.py --out mvp/logs/my-new-suite
.venv/Scripts/python.exe mvp/analyze.py --runs mvp/logs/my-new-suite --out mvp/logs/my-analysis
```

Output paths must be new. Do not rerun over `reports/` certificates. The six runs
are matched initial-condition interventions on a fixed seed, not a multi-seed
statistical behavioral study.
