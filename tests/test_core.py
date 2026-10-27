import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from ultrasonic_lab.core import DEFAULTS, analyze_trace, load_metadata, load_settings, load_trace


def echo(time, center, amplitude=1.0):
    delta = time - center
    return amplitude * np.exp(-0.5 * (delta / 0.55e-6) ** 2) * np.cos(2 * np.pi * 1e6 * delta)


def known_trace():
    time = np.arange(1024) / 20e6
    volts = echo(time, 2e-6) + echo(time, 20e-6, 0.8) + echo(time, 10e-6, 0.4)
    return time, volts


class CoreTests(unittest.TestCase):
    def test_echo_envelope_score_and_apparent_pulse_echo_depth(self):
        time, volts = known_trace()
        result, filtered, envelope = analyze_trace(time, volts, DEFAULTS, velocity_m_s=2200)
        self.assertEqual(result["status"], "valid")
        self.assertAlmostEqual(result["score"], 0.5, delta=0.03)
        self.assertAlmostEqual(result["indication_peak_time_s"], 10e-6, delta=0.1e-6)
        self.assertAlmostEqual(result["apparent_depth_mm"], 8.8, delta=0.11)
        self.assertEqual(filtered.shape, volts.shape)
        self.assertTrue(np.isfinite(envelope).all())
        self.assertTrue((envelope >= 0).all())

    def test_weak_backwall_and_clipping_are_indeterminate_not_negative(self):
        time, volts = known_trace()
        for signal, reason in [
            (np.zeros_like(volts), "weak_backwall"),
            (np.full_like(volts, 2.0), "clipping"),
        ]:
            result, _, _ = analyze_trace(time, signal, DEFAULTS)
            self.assertEqual(result["status"], "indeterminate")
            self.assertIn(reason, result["quality_reasons"])
            self.assertIsNone(result["score"])
            self.assertIsNone(result["apparent_depth_mm"])

    def test_timestamps_sampling_and_gate_bounds_are_enforced(self):
        time, volts = known_trace()
        irregular = time.copy()
        irregular[100] += 1e-8
        for times, values in [
            (time[:100], volts[:100]),
            (irregular, volts),
            (time[::-1], volts),
            (time, volts * np.nan),
        ]:
            with self.assertRaises(ValueError):
                analyze_trace(times, values, DEFAULTS)
        with self.assertRaisesRegex(ValueError, "sampling"):
            analyze_trace(np.arange(1024) / 4e6, volts, DEFAULTS)
        with self.assertRaisesRegex(ValueError, "gate"):
            analyze_trace(time, volts, {**DEFAULTS, "noise_gate_s": [0.0001, 0.0002]})

    def test_measured_csv_and_metadata_validate_units_and_do_not_invent_velocity(self):
        time, volts = known_trace()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            trace = root / "trace.csv"
            np.savetxt(
                trace,
                np.column_stack([time, volts]),
                delimiter=",",
                header="time_s,amplitude_v",
                comments="",
            )
            loaded_t, loaded_v = load_trace(trace)
            np.testing.assert_allclose(loaded_t, time)
            np.testing.assert_allclose(loaded_v, volts)
            meta = root / "meta.json"
            meta.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "capture_id": "scan_01",
                        "source_kind": "measured_unverified",
                        "notes": "Imported scope CSV",
                    }
                )
            )
            self.assertNotIn("velocity_m_s", load_metadata(meta))
            result, _, _ = analyze_trace(loaded_t, loaded_v, DEFAULTS)
            self.assertIsNone(result["apparent_depth_mm"])
            trace.write_text("time_ms,amplitude_v\n0,1\n")
            with self.assertRaisesRegex(ValueError, "header"):
                load_trace(trace)
            meta.write_text(
                '{"schema_version": 1, "capture_id": "../private", "source_kind": "measured"}'
            )
            with self.assertRaises(ValueError):
                load_metadata(meta)

    def test_settings_require_known_complete_schema(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "settings.json"
            p.write_text(json.dumps(DEFAULTS))
            self.assertEqual(load_settings(p), DEFAULTS)
            for change in [
                {"band_hz": [1.4e6, 0.6e6]},
                {"time_zero_s": float("nan")},
                {"backwall_gate_s": [8e-6, 20e-6]},
                {"unknown": 1},
            ]:
                p.write_text(json.dumps({**DEFAULTS, **change}))
                with self.assertRaises(ValueError):
                    load_settings(p)


if __name__ == "__main__":
    unittest.main()
