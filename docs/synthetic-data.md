# Synthetic inputs and split

All bundled inputs are generated in this repository. There is no downloaded or measured inspection dataset, and no claim that any trace represents an actual printed specimen. The input generator and generated examples/results use the repository's MIT license.

The frozen seed is 20261027. A SHA256-derived stream for each specimen ID controls all specimen parameters and three repeated captures. Generation order is calibration, evaluation, high-noise stress, then low-coupling stress. IDs never cross groups. Changing the seed, model, group counts, gates, quality rule, or threshold procedure is a new experiment requiring a new recorded run.

| Group | Specimens | Normal / extra reflector | Captures |
| --- | ---: | ---: | ---: |
| Calibration | 64 | 64 / 0 | 192 |
| Evaluation | 80 | 40 / 40 | 240 |
| High-noise stress | 20 | 10 / 10 | 60 |
| Low-coupling stress | 20 | 10 / 10 | 60 |

Each trace has 1,024 samples at 20 MHz. Model assumptions are recorded in `metrics.json`: 0.95–1.05 MHz carriers, Gaussian pulse width 0.55 µs, time zero 2 µs, assumed 20 mm thickness, assumed velocity 2,120–2,280 m/s, white-noise standard deviation 0.015–0.05 V, coupling multiplier 0.4–1.1, small background echo, and an optional extra reflector delayed 6–12 µs after time zero. These are illustrative ranges, not measured properties of PLA or a specific instrument. Stress noise is 0.18 V; stress coupling is 0.04. No acoustic finite-element simulation is present.

`synthetic-traces.npz` contains numeric `time_s` and `amplitude_v` arrays, with no object arrays or pickle. Row `array_row` in `captures.json` identifies the corresponding voltage row. That capture record also stores specimen ID, split, label, repeat, quality result, score, and the actual generator parameters. `specimens.json` stores aggregate scores, valid-repeat counts, and synthetic decisions. Labels mean only normal model versus added-reflector model.

Example CSV/JSON pairs include one normal, one extra-reflector, one noisy, and one weak-coupling capture. Their metadata explicitly says synthetic. The CSV adapter can process them in exactly the same format as a future operator export.

The calibration threshold uses normal calibration specimen medians only, with at least two accepted repeats per specimen and at least 20 usable calibration specimens. Its 95th percentile is a fitting convention. Held-out and stress outcomes do not change it. Rejected traces/specimens remain in the saved results and in coverage denominators. All physical validation remains pending.
