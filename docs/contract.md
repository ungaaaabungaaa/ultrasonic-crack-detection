# Commands and files — version 0.1

No command uses a network service or controls hardware. Exit codes are 0 success, 2 invalid command syntax, and 1 controlled file/validation/runtime failure. Output directories must not already exist.

- `ultrasonic-lab benchmark --output NEW_DIR`: run the frozen synthetic experiment (seed 20261027), calibration-only threshold fit, held-out and stress evaluation, figures, raw synthetic arrays, CSV examples, JSON results, and a static HTML report. There is no seed sweep or test-driven parameter selection.
- `ultrasonic-lab analyze --trace TRACE.csv --metadata META.json --output NEW_DIR [--settings SETTINGS.json]`: process one bounded local capture. It returns waveform/quality/indication-score results and figures. It does not apply the synthetic benchmark threshold to measured data or decide that a real crack exists. Without settings use the explicit defaults below.
- `ultrasonic-lab --help` and `--version`: show the interface and package version.

## Trace and metadata

CSV header is exactly `time_s,amplitude_v`. Values are finite ASCII decimal numbers in seconds and volts; optional signs, decimal points, and scientific exponents are supported. Underscores, Unicode digits, hexadecimal notation, surrounding whitespace, and non-finite spellings are rejected before numeric conversion; absolute amplitude must not exceed 1,000 V (a parser bound, not a safe electrical input rating). Require 256–100,000 samples, regular file without symlinks <=8,000,000 bytes, strictly increasing uniform times (relative interval tolerance 0.0001), nonnegative start time, duration <=0.01 seconds, and sample rate between 100 kHz and 100 MHz. Duplicate, missing, extra, non-finite, or irregular fields fail. CSV is data, never an expression. All configured gates must fit inside the trace and contain at least eight samples.

Metadata is a JSON object <=32,000 bytes with only these keys: `schema_version` (1), `capture_id` (1–80 safe letters/digits/underscore/hyphen), `source_kind` (`synthetic` or `measured_unverified`), `notes` (string <=2,000 characters), optional `velocity_m_s` (100–20,000) and `velocity_basis` (nonempty string <=500 characters when velocity is supplied). No default material sound velocity is assumed for measured input. The optional depth is only an apparent pulse-echo depth from declared velocity and time zero, not validated crack size or location. Input source labels and calibration notes are user declarations, not independently verified measurements.

JSON metadata and settings reject duplicate object keys, non-finite constants, and decoder nesting failures. Ambiguous repeated declarations are never silently replaced. Invalid input returns a controlled error before any output directory is created.

## Settings

JSON settings must specify the exact complete default schema: `band_hz: [600000,1400000]`, `indication_gate_s: [0.000005,0.000015]`, `backwall_gate_s: [0.000017,0.000024]`, `noise_gate_s: [0.000032,0.000045]`, `time_zero_s: 0.000002`, `min_backwall_snr: 8`, `adc_full_scale_v: 2`. Unknown, missing, malformed, non-finite, or unsupported values fail. Gates are ordered and nonoverlapping, with the indication gate after time zero. Upper passband edge must be below half the sampling frequency; at least four samples per highest passband cycle are required. Bounds and dead-zone/gate choices are a research convention, not an instrument calibration.

Use a fourth-order Butterworth band-pass in second-order-section form, forward/backward offline filtering, and magnitude of the Hilbert analytic signal. The indication score is the indication-gate envelope maximum divided by the backwall-gate envelope maximum. Estimate noise as RMS of the filtered quiet gate. Mark a trace indeterminate if >=0.1% of raw samples reach 99.9% of declared ADC full scale, or the backwall peak is less than 8 times quiet-gate RMS. Scores from indeterminate traces are null; they are not negative results. Spectral filtering/Hilbert processing uses future samples and is not real-time.

## Synthetic evaluation

Generate 64 normal calibration specimens, 80 held-out evaluation specimens (40 normal, 40 with an added synthetic reflector), and separate stress sets. Each specimen has three repeated captures and a deterministic ID-based random stream. All repeated captures stay with their specimen; no specimen can occur in two groups. The simulator is a sum of Gaussian-windowed carriers plus white noise, background echoes, trigger jitter, and coupling changes. It is not a finite-element acoustic model of PLA or a real crack.

Fit a 95th-percentile (`method='higher'`) threshold from the median accepted score of each calibration-normal specimen only. At least two of three repeats must be valid for a specimen score; otherwise it is indeterminate. Freeze the threshold before scoring held-out labels. Use strict `score > threshold` for a synthetic indication. Save every specimen ID, split, label, valid-repeat count, score, and decision. Report confusion counts and denominators only for determinate specimens, plus indeterminate counts by class and total coverage. Sensitivity and false-positive rates describe the synthetic generator only; no probability, physical accuracy, or validation guarantee is produced.

## Outputs

Save settings, metrics, input/code hashes and dependency versions, explicit simulation assumptions, individual specimen results, genuine Matplotlib figures, and self-contained static HTML with relative figures. Benchmark also saves bounded numeric `.npz` arrays (no object arrays/pickle), a manifest, and trace CSV examples. Input-file analysis records both input byte hashes, source declaration, quality reasons, score and optional apparent depth. Never overwrite an existing directory or claim generated data are measured scans.
