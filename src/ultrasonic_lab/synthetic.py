"""A documented waveform generator, not a validated acoustic model of printed parts."""

from hashlib import sha256

import numpy as np

SEED = 20261027
TIME = np.arange(1024, dtype="float64") / 20_000_000
ASSUMPTIONS = {
    "source_kind": "synthetic",
    "seed": SEED,
    "sample_rate_hz": 20_000_000,
    "samples_per_trace": 1024,
    "captures_per_specimen": 3,
    "carrier_hz": [950_000, 1_050_000],
    "pulse_sigma_s": 0.55e-6,
    "assumed_velocity_m_s": [2120, 2280],
    "assumed_thickness_m": 0.02,
    "time_zero_s": 2e-6,
    "trigger_jitter_sd_s": 0.06e-6,
    "coupling_multiplier": [0.4, 1.1],
    "white_noise_sd_v": [0.015, 0.05],
    "background_echo_amplitude_ratio": [0.02, 0.08],
    "extra_reflector_amplitude_ratio": [0.08, 0.35],
    "extra_reflector_delay_after_zero_s": [6e-6, 12e-6],
    "stress_noise_sd_v": 0.18,
    "stress_coupling_multiplier": 0.04,
    "limitations": "Gaussian carrier sums; no beam, pore, scattering, anisotropy, or physical crack model.",
}


def generate_dataset():
    result = []
    for split, count in [
        ("calibration", 64),
        ("evaluation", 80),
        ("stress_noise", 20),
        ("stress_coupling", 20),
    ]:
        for index in range(count):
            specimen_id = f"{split}-{index:03d}"
            rng = np.random.default_rng(
                int.from_bytes(sha256(f"{SEED}:{specimen_id}".encode()).digest()[:8], "big")
            )
            label = int(split != "calibration" and index >= count // 2)
            frequency = rng.uniform(950_000, 1_050_000)
            velocity = rng.uniform(2120, 2280)
            coupling = rng.uniform(0.4, 1.1)
            noise = rng.uniform(0.015, 0.05)
            background = rng.uniform(0.02, 0.08)
            reflector = rng.uniform(0.08, 0.35) if label else 0
            reflector_delay = rng.uniform(6e-6, 12e-6)
            if split == "stress_noise":
                noise = 0.18
            if split == "stress_coupling":
                coupling = 0.04
            for repeat in range(3):
                jitter = rng.normal(0, 0.06e-6)
                gain = coupling * rng.uniform(0.95, 1.05)

                def pulse(center, amplitude):
                    delta = TIME - center - jitter
                    return (
                        gain
                        * amplitude
                        * np.exp(-0.5 * (delta / 0.55e-6) ** 2)
                        * np.cos(2 * np.pi * frequency * delta)
                    )

                volts = (
                    pulse(2e-6, 1)
                    + pulse(2e-6 + 0.04 / velocity, 0.75)
                    + pulse(11e-6, background)
                    + pulse(2e-6 + reflector_delay, reflector)
                    + rng.normal(0, noise, len(TIME))
                )
                result.append(
                    {
                        "specimen_id": specimen_id,
                        "split": split,
                        "label": label,
                        "repeat": repeat,
                        "time": TIME.copy(),
                        "volts": volts,
                        "assumed_velocity_m_s": velocity,
                        "parameters": {
                            "carrier_hz": frequency,
                            "velocity_m_s": velocity,
                            "coupling_multiplier": coupling,
                            "capture_gain": gain,
                            "noise_sd_v": noise,
                            "background_amplitude_ratio": background,
                            "reflector_amplitude_ratio": reflector,
                            "reflector_delay_after_zero_s": reflector_delay,
                            "jitter_s": jitter,
                        },
                    }
                )
    return result
