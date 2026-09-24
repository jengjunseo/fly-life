# MaleCNS v1.0 — minimal seeded 3D ecology

This layer uses the **existing 165,122-neuron MaleCNS runtime**, existing signed/pruned matrix, LIF parameters and existing DNa01/DNa02/DNp09 decoder. It does not substitute a toy brain or a behavioral policy. The original body application remains independently runnable.

## Run

From the brain-core directory, in PowerShell:

```powershell
.venv/Scripts/python.exe ecology/launch.py --life-run
```

The interactive seed creates pre-sampled, irregular food/predator/female/heat events. No keyboard is needed. Because the actual CPU brain is slower than real time, the environment is also slower than real time. The HUD distinguishes wall, neural (including 500ms warm-up), and completed world time. `Esc` closes and cleans up owned processes. `R` reinitializes brain and world seeds. `F/P/M/H` spawn only world entities/heat; `D` explicitly loads gut to demonstrate a **non-neural physiology placeholder**. Neural debug keys are off by default; enable `debug_neural_keys` in a separate ecology config only if wanted. They are not used in the ecology certificates.

Fast, deterministic certification schedules, still computing every neural step:

```powershell
.venv/Scripts/python.exe ecology/launch.py --certification --life-run --logdir ecology/logs/cert
.venv/Scripts/python.exe ecology/launch.py --certification --replay-test --logdir ecology/logs/replay
.venv/Scripts/python.exe ecology/launch.py --certification --life-run --sensory-off --logdir ecology/logs/off
.venv/Scripts/python.exe ecology/launch.py --certification --life-run --without-predator --logdir ecology/logs/no-predator
.venv/Scripts/python.exe ecology/test_ecology.py
.venv/Scripts/python.exe ecology/baseline_check.py
```

`--headless` is available for development but is **not** used to claim live rendering FPS or screenshots. `--quit-after` is a wall-time safety shutdown only; it does not advance ecology time. Godot binary selection is `--godot`; the previous `body/setup_godot.py` acquisition remains the installation path. Logs default to ignored `ecology/logs/latest`; do not run new experiments over the delivered `reports/ecology/*` evidence directories.

## Control and clock boundary

```text
Python seeded world, sampled at t (sensor geometry only)
  -> sensory Encoder -> Brain.current(actual resolved upstream indices)
  -> 50 unchanged LIF steps, each 1ms, on the full real matrix
  -> unchanged body.decoder.decode(selected neural activity only)
  -> original Godot apply_neural_frame: 50ms movement/physics commit
  -> ACK actual Godot fly position/yaw + source sequence
  -> Python world advances that same 50ms, NPCs/physiology/events update
  -> next sensory geometry at t+50ms
```

Python owns seeded NPC/physiology state; Godot mirrors those actual primitive entity positions and owns the focal CharacterBody3D collision/movement in the original arena. Predator damage is geometric sphere overlap against the actual ACKed Godot body pose, not an animated escape or locomotor impulse. Only NPCs pursue/wander by script. World state in each motor packet is the **input snapshot** for that quantum, so visual ecology state lags the newest ACK by one 50ms quantum; no forward prediction is made. `world.jsonl` records the completed post-ACK world. Body packets retain global sequence numbers and generation-specific clocks. The bridge waits for each completed body ACK before computing the next quantum. It rejects incorrect sequence/time, and an engine/brain/transport failure freezes rather than invents movement.

There is **no** food-distance-to-DNp09, female-to-pC1, heat-to-shade-direction, hunger-to-food-target, predator-to-escape policy, direct locomotor stimulus from world events, or render/wall-time simulation advancement. Sensor input includes only angular size, positive angular expansion, relative bearing, angular figure motion/contrast, odor/contact concentration, and local temperature/change. The decoder never receives these quantities. Anatomical L/R memberships are verified, but detailed receptive-field positions are unavailable: visual features are pooled bilaterally instead of inventing retinotopic steering.

HP=0 is the single explicitly allowed physiology override: the inherited body movement receives zero forward/turn for death, with a separate `death_stop` log row. A living fly always receives the original decoder output. Death is unit-tested; the delivered live run remains alive. Reset is an initial-condition operation, not a movement controller. Life events and all NPC velocities, durations, cooldowns, hunger/gut processing and defecation latency use completed world dt only. RNG is `random.Random(world_seed)`, separate from the brain NumPy RNG; event schedules and NPC wander intervals are pre-sampled, not Bernoulli probabilities per render frame.

## Actual mappings, encoding levels and debts

Every member and selector is saved in `reports/ecology/live/sensory_mapping.json`. No bodyIds from FlyWire/hemibrain are substituted. The selectors resolve against the existing MaleCNS annotations and retain that artifact's NT/sign policy.

| Primitive | Actual runtime group | Members | Evidence / limitations |
|---|---|---:|---|
| Angular expansion | LC4 | 126 | Verified type/laterality, experimental bounded expansion current |
| Angular size, gated by expansion | LPLC2 | 185 | Verified looming class; not a simple distance/presence switch |
| Figure-edge angular motion on static ground | LC9 | 219 | Experimental population feature encoder; **not an escape circuit reconstruction** |
| Generic food-associated odor concentration | ORN_DM1 | 74 | Verified ORN identities; Or42b/DM1 correspondence and food-odor relevance from literature |
| Contact sugar cue | GNG540: 11740 L, 15214 R | 2 | Actual `Sugar SEL PN` alias, **experimental CNS bypass**, not reconstructed peripheral sweet GRNs or verified second-order cells |
| Fly-produced odor concentration | ORN_VA1v / ORN_VA1d | 262 | Or47b/Or88a corresponding glomeruli; fly odor is **not female-specific** and does not identify sex |
| Local heating / cooling | TRN_VP2 / TRN_VP3a+b | 7 / 7 | Actual thermosensory afferents; experimental local temperature/change transfer function, no shade direction |
| Feeding observation only | GNG588 / Fdg: 12617 L, 14321 R | 2 | Alias verified; no input current to Fdg. Functional feeding gate not certified; ingestion off |
| Courtship observation only | ^pC1 family | 156 | No direct input or required increase; not an exact P1 selector |

LC4/LPLC2 encode positive expansion/size with finite caps of 6 model-current units; LC9 encodes angular motion of visible figure edges, including expansion and bearing changes, with a cap of 6. Chemicals cap at 3. Thermal current is a bounded experimental combination of local temperature offset and change, capped at 3. These are dimensionless model currents, not amperes or measured biophysical receptor transfer functions. They are not optimized for behavioral success. The fixed sensory-range scout at 0/3/6/10 records finite population response and recovery. At 6, sensory firing is approximately 177Hz, below the model's refractory maximum; 10 is a scout, not the configured encoder cap. LIF, recurrent gain, pruning, sign mapping and decoder gains are untouched.

Important negative evidence: LC4/LPLC2-only current scouts at 3, 6 and 10 did **not** elicit spikes in the original locomotor groups, though giant-fiber response increased. GF readout alone is not accepted as a body loop. LC9 has 1,904 retained actual contacts to the bilateral DNp09 group and enables the small experimental figure-motion loop. The live displacement is **not** proof of fleeing: this decoder only represents forward walking/steering and does not model GF escape, freezing, flight or muscle mechanics.

Food contact generates a sensory cue, **never automatic ingestion**. There are actual gustatory LB/PhG/leg classes, but a specific adult peripheral sugar-GRN identity is unresolved here. GNG540's annotation alias provides a clearly marked CNS bypass; it is not claimed to be a direct peripheral sensor. Literature describes serotonergic sugar-SEL cells whereas the preserved MaleCNS `consensus_nt` for these two members is acetylcholine. This discrepancy is recorded; **no NT override or serotonin dynamics were added**. No direct retained GNG540-to-Fdg contact was found and no Fdg activity was observed in the live run. This is not proof that no indirect biological feeding pathway exists. The prospective contact AND neural-Fdg threshold rule is unit-tested counterfactually, but `ingestion_enabled=false` remains mandatory for the delivered scientific configuration. Hunger therefore grows; it does not modulate any neural group or target food. Gut processing is a bounded simple world model.

Female contact cuticle cue is logged but its neural mapping is **DISABLED_UNRESOLVED**. The dataset contains `putative_ppk23` leg/wing afferent annotations; putative receptor labels do not prove female-specific responsive subgroups. No central pC1 injection is used. Predator hit neural pain is **DISABLED_UNRESOLVED**: mechanosensory class labels alone are not a verified adult nociceptive circuit. HP damage is a world physiology model, not claimed neural pain. The config loader rejects attempts to enable these unresolved mappings or ingestion through a flag; the counterfactual feeding rule unit test is not an enabling certificate.

Defecation is explicitly **PHYSIOLOGY_PLACEHOLDER**: gut threshold -> seeded world-time latency -> gut drop and brown primitive with lifetime. The certification initial gut is 75 to verify this feature while ingestion is disabled. It is not a claimed adult-connectome defecation pathway and no larval circuit is repurposed. Interactive initial gut is 0, so no fabricated ingestion fills it. Food, predator, female and feces all have completed-world-time lifetimes. Heat ramps from 25 to 34C and recovers; the shade rectangle lowers local temperature by 6C only. Shade/current comparison uses test initial positions; the live fly is not forced into shade.

## Primary references and interpretation

- [Ache et al. 2019, LC4/LPLC2 angular velocity/size into GF](https://www.sciencedirect.com/science/article/pii/S0960982219301381). Supports the feature classes, not the population current formula.
- [Aptekar et al. 2015, LC9 figure-ground discriminations](https://pubmed.ncbi.nlm.nih.gov/25972183/). Supports figure-selective visual input, not this simplified spherical figure-edge encoder or an escape claim.
- [Semmelhack & Wang 2009, DM1 and food-odor attraction](https://pubmed.ncbi.nlm.nih.gov/19396157/), [Root et al. 2011, Or42b food search](https://pmc.ncbi.nlm.nih.gov/articles/PMC3073827/). Generic modeled concentration is not a chemically calibrated odor plume.
- [Lin et al. 2016, Or47b/Or88a fly-odor sensing](https://pmc.ncbi.nlm.nih.gov/articles/PMC4911275/), [Schlegel et al., full olfactory connectome receptor/glomerular nomenclature](https://elifesciences.org/articles/66018). Both-sex fly odors do not imply a female classifier.
- [Marin et al. 2020, adult thermo/hygrosensory connectomics](https://www.sciencedirect.com/science/article/pii/S0960982220308447). Supports VP2 heating and VP3 cooling identities; current transfer remains experimental.
- [Yao & Scott 2022, sugar-SEL neurons](https://www.sciencedirect.com/science/article/pii/S089662732101045X), [MaleCNS cell type explorer GNG540](https://reiserlab.github.io/celltype-explorer-drosophila-male-cns/types/GNG540_L.html). CNS taste bypass is an inference from annotation aliases and sugar responsiveness, not validated peripheral reconstruction.
- [Shiu et al. 2022, adult feeding initiation circuit and Fdg](https://elifesciences.org/articles/79887). Supports observation of Fdg; it does not certify this layer's disabled feeding gate.
- [Zacarias et al. 2018, DNp09 defensive state dependence](https://www.nature.com/articles/s41467-018-05875-1). Reinforces why this inherited forward decoder must not be called a faithful escape/freeze decoder.

## Evidence and preservation

See `reports/ecology/DELIVERY.md`, `certification.json`, real mapping/topology, separate live/control/replay JSONL logs and `live/ecology.png`. The delivered certificate checks actual packet->decoder->body commits, source ACK->next sensory, predator ablation, all-sensory ablation, actual reset replay, actual process failure/freeze, completed time and process-tree RSS. `ecology/analyze.py` regenerates the certificate from those directories and fails on failed checks; it does not synthesize missing logs.

All pre-existing files, including scientific and body certificates, are preserved. The baseline comparison records two **inherited** console-log CRLF working-tree versus LF Git-object differences rather than rewriting old evidence. The original suites are rerun into new `reports/ecology/baseline.json`. New ecology files are under `ecology/`, the small Godot subclass/scene under `body/ecology/`, and all new reports under `reports/ecology/`. The original body `main.gd`, bridge, launcher, decoder, body config and Godot project are not edited. New transport synchronization and process-teardown grace exist only in the ecology extension.

This is the smallest demonstrated sensory-neural-body feedback environment, not a validated animal simulation. No guaranteed food finding, predator avoidance, shade seeking, courtship, peripheral transduction, neural defecation, reproductive cycle, learning or metabolic realism is claimed.
