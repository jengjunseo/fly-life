# SHOT 4 — final full-application evidence

Actual 3840×2160 fullscreen Godot + original SciPy/PCG64 brain + console; six matched-seed 3.5 s world runs. 0.5 s neural warmup is additional. No old backend timings used below.

## Gates

Closed-loop integrity: **FAIL**. Each condition has 70 completed 50 ms quanta and matching real body commits.

## Performance (milliseconds unless stated)

| Condition | Compute p50 / p95 / p99 | Lockstep mean | Remainder mean | JSON/log/send mean | ACK wait mean | FPS p50 | Active neural/wall | World/wall incl. startup |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| CONTROL | 513.30 / 521.37 / 534.41 | 636.38 | 122.53 | 0.52 | 24.68 | 60 | 0.0786× | 0.0679× |
| PREDATOR | 507.14 / 513.43 / 523.15 | 631.20 | 123.36 | 0.59 | 27.43 | 60 | 0.0792× | 0.0691× |
| FOOD | 961.19 / 1021.68 / 1039.60 | 1095.80 | 127.31 | 0.54 | 24.49 | 60 | 0.0456× | 0.0398× |
| FEMALE | 1094.02 / 1122.48 / 1225.52 | 1226.88 | 125.01 | 0.56 | 25.63 | 60 | 0.0408× | 0.0356× |
| HEAT | 528.74 / 550.10 / 585.96 | 655.31 | 122.49 | 0.52 | 26.14 | 60 | 0.0763× | 0.0666× |
| PREDATOR + HEAT | 1162.84 / 1264.13 / 1339.26 | 1303.16 | 127.69 | 0.57 | 26.41 | 60 | 0.0384× | 0.0335× |

Remainder = end-to-end quantum (encode → actual completed body ACK/world update) minus pure brain.step time. JSON/log/send includes group reduction, serialization, synchronous log and socket send. ACK wait includes Godot scheduling/physics and return processing; it is not a pure network latency measurement. Component timers overlap those aggregate categories and must not be added again.

Performance is measured, not realtime-certified. 70 windows per condition support a short application health check, not a sustained tail guarantee. No 35 ms gate is imposed.

## Console cost

| Condition | 10 Hz refresh mean / max ms | World viewport | Fullscreen |
|---|---:|---|---|
| CONTROL | 0.179 / 0.901 | [2794, 1517] | [3840, 2160], mode 3 |
| PREDATOR | 0.224 / 0.486 | [2794, 1517] | [3840, 2160], mode 3 |
| FOOD | 0.194 / 0.389 | [2794, 1517] | [3840, 2160], mode 3 |
| FEMALE | 0.201 / 0.425 | [2794, 1517] | [3840, 2160], mode 3 |
| HEAT | 0.194 / 0.359 | [2794, 1517] | [3840, 2160], mode 3 |
| PREDATOR + HEAT | 0.229 / 0.513 | [2794, 1517] | [3840, 2160], mode 3 |

Direct callback timings cover text/control/event updates; neural-sample sparkline draw and GPU rendering are included in observed full-app FPS, not misrepresented as isolated zero-cost work.

## Circuit autopsy

Numbers below are mean selected-group spike rate Hz (total spikes / members / sampled neural seconds). Baseline is world [0,0.5), stimulus [0.5,2.5), recovery [3,3.5). Finite stimuli have distinct lifetimes within the stimulus window. EMA values and exact counts are in summary.json.

### CONTROL

| Group | Baseline Hz | Stimulus Hz | Recovery Hz |
|---|---:|---:|---:|
| GF | 8.000 | 8.500 | 8.000 |
| DNa01 | 0.000 | 0.000 | 0.000 |
| DNa02 | 0.000 | 0.000 | 0.000 |
| DNp09 | 0.000 | 0.000 | 0.000 |
| lc4 | 0.794 | 0.794 | 0.841 |
| lplc2 | 0.778 | 0.770 | 0.768 |
| figure | 0.447 | 0.452 | 0.438 |
| food_odor | 0.811 | 0.885 | 0.892 |
| taste | 0.000 | 0.000 | 0.000 |
| fly_odor | 0.672 | 0.674 | 0.664 |
| hot | 0.000 | 0.000 | 0.000 |
| cold | 0.000 | 0.000 | 0.000 |
| feeding_observation | 0.000 | 0.000 | 0.000 |
| courtship_observation | 0.897 | 0.856 | 0.846 |

Actual final displacement 0.00000000 units; HP 100.0; gut 0.00; local temperature 25.00°C.
Input current maxima: lc4 0.0000, lplc2 0.0000, figure 0.0000, food_odor 0.0000, taste 0.0000, fly_odor 0.0000, hot 0.0000, cold 0.0000.

### PREDATOR

| Group | Baseline Hz | Stimulus Hz | Recovery Hz |
|---|---:|---:|---:|
| GF | 8.000 | 18.500 | 8.000 |
| DNa01 | 0.000 | 0.000 | 0.000 |
| DNa02 | 0.000 | 0.000 | 0.000 |
| DNp09 | 0.000 | 0.500 | 0.000 |
| lc4 | 0.794 | 68.571 | 0.841 |
| lplc2 | 0.778 | 57.962 | 0.768 |
| figure | 0.447 | 63.420 | 0.466 |
| food_odor | 0.811 | 0.885 | 0.892 |
| taste | 0.000 | 0.000 | 0.000 |
| fly_odor | 0.672 | 0.674 | 0.664 |
| hot | 0.000 | 0.000 | 0.000 |
| cold | 0.000 | 0.000 | 0.000 |
| feeding_observation | 0.000 | 0.000 | 0.000 |
| courtship_observation | 0.897 | 0.862 | 0.846 |

Actual final displacement 0.02058868 units; HP 64.0; gut 0.00; local temperature 25.00°C.
Input current maxima: lc4 6.0000, lplc2 6.0000, figure 6.0000, food_odor 0.0000, taste 0.0000, fly_odor 0.0000, hot 0.0000, cold 0.0000.

### FOOD

| Group | Baseline Hz | Stimulus Hz | Recovery Hz |
|---|---:|---:|---:|
| GF | 8.000 | 8.500 | 8.000 |
| DNa01 | 0.000 | 0.000 | 0.000 |
| DNa02 | 0.000 | 0.000 | 0.000 |
| DNp09 | 0.000 | 0.000 | 0.000 |
| lc4 | 0.794 | 0.794 | 0.841 |
| lplc2 | 0.778 | 0.770 | 0.768 |
| figure | 0.447 | 0.452 | 0.438 |
| food_odor | 0.811 | 126.000 | 1.027 |
| taste | 0.000 | 112.750 | 0.000 |
| fly_odor | 0.672 | 0.670 | 0.656 |
| hot | 0.000 | 0.000 | 0.000 |
| cold | 0.000 | 0.000 | 0.000 |
| feeding_observation | 0.000 | 0.000 | 0.000 |
| courtship_observation | 0.897 | 0.856 | 0.846 |

Actual final displacement 0.00000000 units; HP 100.0; gut 0.00; local temperature 25.00°C.
Input current maxima: lc4 0.0000, lplc2 0.0000, figure 0.0000, food_odor 3.0000, taste 3.0000, fly_odor 0.0000, hot 0.0000, cold 0.0000.

### FEMALE

| Group | Baseline Hz | Stimulus Hz | Recovery Hz |
|---|---:|---:|---:|
| GF | 8.000 | 10.500 | 9.000 |
| DNa01 | 0.000 | 0.000 | 0.000 |
| DNa02 | 0.000 | 0.000 | 0.000 |
| DNp09 | 0.000 | 0.000 | 0.000 |
| lc4 | 0.794 | 15.929 | 0.857 |
| lplc2 | 0.778 | 15.281 | 0.800 |
| figure | 0.447 | 40.167 | 0.447 |
| food_odor | 0.811 | 0.885 | 0.892 |
| taste | 0.000 | 0.000 | 0.000 |
| fly_odor | 0.672 | 67.823 | 0.664 |
| hot | 0.000 | 0.000 | 0.000 |
| cold | 0.000 | 0.000 | 0.000 |
| feeding_observation | 0.000 | 0.000 | 0.000 |
| courtship_observation | 0.897 | 0.862 | 0.859 |

Actual final displacement 0.00000000 units; HP 100.0; gut 0.00; local temperature 25.00°C.
Input current maxima: lc4 0.5932, lplc2 0.5932, figure 1.6516, food_odor 0.0000, taste 0.0000, fly_odor 2.1507, hot 0.0000, cold 0.0000.

### HEAT

| Group | Baseline Hz | Stimulus Hz | Recovery Hz |
|---|---:|---:|---:|
| GF | 8.000 | 8.500 | 8.000 |
| DNa01 | 0.000 | 0.000 | 0.000 |
| DNa02 | 0.000 | 0.000 | 0.000 |
| DNp09 | 0.000 | 0.000 | 0.000 |
| lc4 | 0.794 | 0.794 | 0.841 |
| lplc2 | 0.778 | 0.770 | 0.768 |
| figure | 0.447 | 0.452 | 0.438 |
| food_odor | 0.811 | 0.885 | 0.892 |
| taste | 0.000 | 0.000 | 0.000 |
| fly_odor | 0.672 | 0.674 | 0.664 |
| hot | 0.000 | 70.714 | 0.000 |
| cold | 0.000 | 25.857 | 0.000 |
| feeding_observation | 0.000 | 0.000 | 0.000 |
| courtship_observation | 0.897 | 0.856 | 0.846 |

Actual final displacement 0.00000000 units; HP 100.0; gut 0.00; local temperature 25.00°C.
Input current maxima: lc4 0.0000, lplc2 0.0000, figure 0.0000, food_odor 0.0000, taste 0.0000, fly_odor 0.0000, hot 3.0000, cold 3.0000.

### PREDATOR + HEAT

| Group | Baseline Hz | Stimulus Hz | Recovery Hz |
|---|---:|---:|---:|
| GF | 8.000 | 18.500 | 8.000 |
| DNa01 | 0.000 | 0.000 | 0.000 |
| DNa02 | 0.000 | 0.000 | 0.000 |
| DNp09 | 0.000 | 0.500 | 0.000 |
| lc4 | 0.794 | 68.571 | 0.841 |
| lplc2 | 0.778 | 57.962 | 0.768 |
| figure | 0.447 | 63.420 | 0.466 |
| food_odor | 0.811 | 0.885 | 0.892 |
| taste | 0.000 | 0.000 | 0.000 |
| fly_odor | 0.672 | 0.674 | 0.664 |
| hot | 0.000 | 70.714 | 0.000 |
| cold | 0.000 | 25.857 | 0.000 |
| feeding_observation | 0.000 | 0.000 | 0.000 |
| courtship_observation | 0.897 | 0.862 | 0.846 |

Actual final displacement 0.02058868 units; HP 64.0; gut 0.00; local temperature 25.00°C.
Input current maxima: lc4 6.0000, lplc2 6.0000, figure 6.0000, food_odor 0.0000, taste 0.0000, fly_odor 0.0000, hot 3.0000, cold 3.0000.

## Causal evidence boundary

world.jsonl contains post-ACK geometry and next sensory state. Each brain packet records the preceding source ACK, input raw features/currents, selected sensory and downstream spike counts/EMA, and the original decoder outputs. godot.jsonl records the resulting collision-aware body commit and actual pose. events.jsonl records world consequences and explicitly thresholded activity observations. summary.json classifies sequence, decoder, time and containment checks for every condition.

The matched CONTROL establishes observed intervention differences at this seed. A rise in a group does not prove that group alone mediates behavior. No lesion-based new causal mediation or biological behavior validation is claimed. Historical sensory-off/predator-off evidence is preserved separately.

See the canonical [scientific status](../../SCIENTIFIC_STATUS.md), [limitations](../../KNOWN_LIMITATIONS.md), and [experiment guide](../../EXPERIMENTS.md).
