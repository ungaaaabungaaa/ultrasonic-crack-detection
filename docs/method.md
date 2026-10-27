# Signal method and interpretation

An A-scan is a receiver-voltage trace against acquisition time. This lab processes files after capture. It has no instrument connection, pulser circuit, live acquisition, or verified physical crack detector.

## Processing

Validate sample units, finite values, uniform times, sample count, duration, and frequency support before processing. Use a fourth-order Butterworth band-pass in second-order-section form. SciPy's [`sosfiltfilt`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.sosfiltfilt.html) applies the filter forward and backward. This removes phase delay but uses future samples, squares the one-pass magnitude response, and can introduce edge effects. It is suitable here only for offline analysis. It does not repair aliasing introduced during physical acquisition.

Compute the amplitude envelope as `abs(hilbert(filtered))`, following SciPy's [analytic-signal definition](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.hilbert.html). The quiet gate estimates filtered RMS noise. The backwall gate supplies a reference envelope peak. Score = indication-gate envelope peak / backwall-gate envelope peak. The score is dimensionless, uncalibrated, and is not a failure or crack probability.

The default gates are chosen for the **synthetic** 20 mm / approximately 2200 m/s demonstration. They are not appropriate defaults for an arbitrary printed part. Keep gates outside transmit ringing and away from trace edges. A different material, thickness, probe delay, or instrument requires new calibrated gates and settings.

Reject a trace as indeterminate when at least 0.1% of its samples reach 99.9% of the declared ADC full scale, or its backwall peak / quiet RMS is below 8. A numerical floor prevents division by zero; a zero reference is always rejected. This is a documented heuristic quality rule, not an instrument-performance certificate. A weak backwall can itself relate to material attenuation or a strong discontinuity: excluding it can bias accepted-only results. Coverage and class-specific exclusions must be read with the classification figures.

For a supplied velocity, apparent depth is `(peak time − declared time zero) × velocity / 2`. It describes a gated envelope peak, which can be noise or another interface. Velocity, electronic/probe/couplant delay, geometry, and echo selection need independent calibration. The [instrument manufacturer's calibration guide](https://ims.evidentscientific.com/en/learn/ndt-tutorials/flaw-detection/calibration-concepts) explains why velocity/zero and reference calibration are separate requirements. This package neither measures these constants nor verifies user declarations. It does not estimate physical crack length, area, orientation, or size.

## Frozen synthetic experiment

Seed: 20261027. The generator uses a separate SHA256-derived random stream for each deterministic specimen ID. It makes 184 specimens with three repeated captures each: 64 normal calibration specimens, 80 evaluation specimens (40 normal and 40 extra-reflector), 20 high-noise stress specimens, and 20 low-coupling stress specimens. All three captures remain in the same group.

The model sums Gaussian-windowed 0.95–1.05 MHz carriers: a transmit pulse, a delayed backwall pulse, a small background echo, and an optional extra reflector. It adds trigger jitter, specimen/capture gain variation, and white noise. The approximately 2200 m/s velocity and 20 mm thickness are illustrative simulation assumptions, not measured PLA properties. The extra reflector is not a simulated crack geometry. The model omits beam propagation, rough interfaces, anisotropy, pores, attenuation physics, scattering, complex electronics, and many printed-material effects.

A specimen score is the median of its accepted repeat scores, requiring at least two valid repeats. Fit the 95th percentile using NumPy's `higher` method on **normal calibration specimens only**. Freeze this threshold before evaluating other groups. A synthetic indication requires `score > threshold`, with equality negative. Calibration outcomes are descriptive fitting-set results, not held-out validation. Stress groups are separate from the ordinary held-out group and never change the fitted threshold.

Sensitivity denominator is accepted extra-reflector specimens. False-positive-rate denominator is accepted normal-model specimens. Indeterminate specimens are counted by label and excluded from those denominators; they are never silently counted as true negatives. Repeated captures are not independent specimens. No uncertainty interval or generalization estimate is claimed from this small parametric generator.

## Physical limitations

Normalization assumes a usable backwall and sufficiently similar gain/coupling effects on the reference and indication paths. Real coupling changes need not affect both equally. A poor reference can increase a ratio; attenuation or a missing backwall can make a real flaw indeterminate. Thresholds fitted to generated signals have no demonstrated validity on measured signals. The single-file adapter therefore returns a score and quality result without applying the synthetic threshold or making a physical crack decision.

Actual measured acquisitions, matched known-good/known-defect specimens, independent labels, calibration records, repeatability studies, and a specimen-level held-out physical evaluation remain pending. Do not use these results to certify a printed part or make a safety decision.
