# Ultrasonic signal lab implementation plan

The approved map reuses `-Cartoonify_Image-_Using_Machine_Learning` as `ultrasonic-crack-detection`. Original main `f4b760cbf654f05f9340a9581eead306998eade9` is saved remotely on `archive/before-ultrasonic-crack-detection-2026-10-27`. The rename retained repository ID `R_kgDOIZVOqQ` and 17 stars. The legacy tree has no license or instructions. Do not reuse the unrelated cartoonifier or notebook code; retain it in the archive. MyPortfolio is read-only. Use the approved project11 v3 line-art cover as a labeled README concept.

## Result and boundary

Build an offline pulse-echo signal-processing lab for 3D-print inspection research. It must generate explicitly synthetic traces, process bounded CSV acquisitions with declared units, compare raw/filtered/envelope views, fit an indication threshold on calibration specimens only, and report held-out synthetic results with exact denominators and quality exclusions. No real scan, material sound velocity, crack size, hardware acquisition, or physical detection accuracy is verified. An extra simulated reflector is not a validated crack model. Do not describe scores as probabilities.

Use NumPy, SciPy second-order-section band-pass filtering and Hilbert envelopes, and Matplotlib for actual scientific figures. Forward/backward filtering and Hilbert processing are offline and use future samples; no real-time claim. Provide CSV/metadata interfaces and an instrument-neutral acquisition guide, not an untested device driver or high-voltage pulser circuit.

## Implementation steps

1. Write the CLI/data contract and physical assumptions before code. Cite official SciPy and ultrasonic-instrument calibration references. Specify input bytes/samples/time bounds, uniform timestamps, units, frequency/Nyquist constraints, ordered nonoverlapping gates, explicit time zero, and optional calibrated velocity. Risk: high.
2. Implement validated local trace/settings input and core processing. Use a quiet-noise gate, an indication gate beyond the transmit dead zone, and a backwall gate. Reject clipped, non-finite, undersampled, short, or weak-backwall traces; return an explicit indeterminate result. Indication score is gated envelope peak divided by backwall envelope peak. Test analytic signals, known delayed echoes, aliasing/gate limits, and quality failures. Risk: high.
3. Generate seeded synthetic specimen groups and repeated captures with documented carrier/pulse/reflector/noise/coupling/jitter assumptions. Keep calibration and held-out specimen IDs disjoint. Fit a fixed 95th-percentile threshold from calibration-normal specimen aggregates only. Freeze it before evaluation. Report accepted/rejected traces, specimen decisions, confusion counts and metric denominators, and separate noise/coupling stress results. Risk: high.
4. Add deterministic exports, code/input/config/data hashes, actual waveform and score figures, a useful static browser report, and a bounded single-trace CSV/metadata analysis command. Mark every default result synthetic. No default network, account, or instrument is needed. Risk: medium.
5. Add README, method/data/acquisition guides, MIT code license, history transparency, contribution/security notes, exact dependencies, tests, CI, source/wheel asset checks, and the approved cover. Risk: medium.
6. Run meaningful behavior tests, source/install checks, the complete frozen synthetic benchmark, and browser QA. Request independent review. Commit/push/PR after checks; root merges after review and green CI. Retain review source/env until root allows cleanup. Risk: high.

## Evidence

Success requires reproducible synthetic inputs with explicit group split and noise/coupling assumptions, honest calibration-only fitting and held-out results, useful invalid-input/quality tests, an actual report and figures, a working measured-file adapter without fabricated measured validation, remote history preservation, and an installed distribution that runs outside the source tree. Physical assembly, electrical safety, specimen-specific velocity/zero/reference calibration, and measured crack validation remain pending user hardware evidence.

## Execution checkpoint

The frozen run has 184 disjoint specimens / 552 captures. Calibration uses 64 normal specimen medians and threshold 0.13058358190783736. Held-out synthetic counts are TP37/FN3/FP2/TN38 on 80 determinate specimens. High-noise stress falsely flags 7/7 accepted normals with only 14/20 determinate; low coupling has only 1/20 determinate. These failures remain prominent; no post-test parameter tuning was performed. There are 77 rejected captures, and score/depth results are explicitly uncalibrated/unverified for physical scans.

Sixteen local tests passed with 95.41% combined line/branch coverage. The measured-declaration adapter was tested using generated voltage fixtures, never presented as physical validation. All 552 saved signals, split/identity records, threshold and quality outcomes were recomputed; source/data/settings hashes matched. An installed wheel outside the source tree ran the full offline benchmark, file adapter, figures/report, and CLI version with external connection creation blocked. Ruff and documentation/distribution checks passed. The browser showed the actual synthetic results and the stress-failure notice. Mobile viewport testing and physical hardware validation remain unverified.

Final recorded source SHA256:87fe8754e1fd8ff36676a6a09a4881b375ca45f2c5090bd7557d2ad7d6caa2e1. Numeric archive SHA256:a6e70ad9612e64ab3f011af2e9cfb6c59b4bf4ba151e4af61a35378236b44fa7. Commit/PR/CI and independent final review remain the next checkpoint; root owns merge and post-backup cleanup.
