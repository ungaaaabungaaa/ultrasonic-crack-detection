# Acquisition interface and pending hardware work

This release accepts exported receiver traces. It does not control an oscilloscope, digitizer, ultrasonic pulser, Arduino, or other instrument. No physical build or measured scan has been verified.

## Equipment roles

A future measured workflow needs a suitable ultrasonic transducer and commercial pulser/receiver, a digitizer or oscilloscope with sufficient analog bandwidth and sample rate, appropriate couplant/fixture, and reference specimens with independently known dimensions and features. This is a list of equipment roles, not a tested parts list or purchasing recommendation. Probe frequency, sound velocity, and useful penetration depend on the actual material and geometry.

Use the instrument maker's procedures and rated receiver/ADC interfaces. Ultrasonic excitation outputs can be high voltage; they must not be connected directly to a general-purpose ADC or microcontroller. This repository provides no pulser wiring or electrical-safety design. The numeric input bounds and ADC full-scale setting describe file processing; they are not safe input ratings.

## Before export

1. Record material, print process, thickness, probe, couplant, instrument, gain, analog filtering, ADC range, trigger, date, and operator notes outside any public demo. Use a stable sample fixture.
2. Independently establish time zero and velocity with suitable reference measurements. Establish the reference echo and the region where transmit ringing prevents useful inspection. The manufacturer's [calibration concepts](https://ims.evidentscientific.com/en/learn/ndt-tutorials/flaw-detection/calibration-concepts) describe the purpose of these calibrations. The software does not perform or verify them.
3. Set sample rate and analog bandwidth to avoid aliasing. The parser's four-samples-per-highest-passband-cycle requirement is a processing bound, not proof that the original analog signal was sampled correctly.
4. Export a complete uniformly sampled receiver trace. Convert instrument-specific units explicitly to seconds and volts. Do not interpolate missing samples or silently discard clipping to make a capture pass.

## File interface

The exact CSV header is `time_s,amplitude_v`. Include one time/receiver-voltage pair per row. A minimal metadata file follows this form; replace values with actual capture notes:

```json
{
  "schema_version": 1,
  "capture_id": "specimen_01_capture_01",
  "source_kind": "measured_unverified",
  "notes": "Receiver trace exported by the operator; calibration and source not verified by this software."
}
```

Do not supply velocity when it is unknown. Optional `velocity_m_s` requires a `velocity_basis` note describing its calibration or assumption. Supplying a number does not make it verified. Set all gates, band edges, time zero, ADC range, and quality threshold in a complete settings JSON that follows [contract.md](contract.md).

```sh
ultrasonic-lab analyze --trace capture.csv --metadata capture.json --settings settings.json --output artifacts/capture-01
```

The output records hashes of the exact parsed input bytes, the settings, signal figures, quality status, dimensionless score, and optional apparent peak depth. It makes no measured crack decision. Preserve the original instrument export and calibration record separately. Public examples in this repository are generated, not measured acquisitions.

## Physical acceptance still needed

Verify electrical interfaces, reference calibration, correct gate selection, repeated coupling/position sensitivity, known-good and known-defect specimens, independent labels, and a held-out specimen split. Include rejected scans and their reasons. Use qualified inspection procedures for any real integrity or safety assessment; this research prototype does not establish standards compliance.
