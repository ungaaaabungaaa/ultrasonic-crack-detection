import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ultrasonic_lab.core import DEFAULTS, load_metadata, load_settings, load_trace, read_bounded
from ultrasonic_lab.evaluation import aggregate_specimens, evaluate, fit_threshold


class BoundaryTests(unittest.TestCase):
    def test_file_byte_bounds_empty_rows_and_extra_csv_columns(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "trace.csv"
            with path.open("wb") as stream:
                stream.truncate(8_000_001)
            with self.assertRaises(ValueError):
                load_trace(path)
            for content in [
                "time_s,amplitude_v\n",
                "time_s,amplitude_v\n0,1,2\n",
                "time_s,amplitude_v\nhello,1\n",
            ]:
                path.write_text(content)
                with self.assertRaises(ValueError):
                    load_trace(path)

    @unittest.skipIf(os.name == "nt", "Symlink creation needs Windows developer privileges")
    def test_symlink_and_fifo_are_rejected_without_reading(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "file").write_text("private")
            (root / "link").symlink_to(root / "file")
            os.mkfifo(root / "fifo")
            for name in ["link", "fifo"]:
                with self.assertRaises(ValueError):
                    read_bounded(root / name, 100)

    def test_metadata_declarations_and_complete_settings_are_strict(self):
        meta = {
            "schema_version": 1,
            "capture_id": "test",
            "source_kind": "measured_unverified",
            "notes": "",
        }
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "metadata.json"
            for change in [
                {"schema_version": True},
                {"source_kind": "verified"},
                {"extra": 1},
                {"velocity_m_s": 2200},
                {"velocity_basis": "unknown"},
                {"notes": "x" * 2001},
                {"velocity_m_s": float("nan"), "velocity_basis": "bad"},
            ]:
                path.write_text(json.dumps({**meta, **change}))
                with self.assertRaises(ValueError):
                    load_metadata(path)
            path.write_text(
                json.dumps({**meta, "velocity_m_s": 2200, "velocity_basis": "user assumption"})
            )
            self.assertEqual(load_metadata(path)["velocity_m_s"], 2200)
            for change in [
                {"band_hz": [600000]},
                {"adc_full_scale_v": False},
                {"min_backwall_snr": 0},
                {"indication_gate_s": [0, 15e-6]},
            ]:
                path.write_text(json.dumps({**DEFAULTS, **change}))
                with self.assertRaises(ValueError):
                    load_settings(path)
            path.write_text("{}")
            with self.assertRaises(ValueError):
                load_settings(path)

    def test_acquisition_json_rejects_duplicate_keys_and_excessive_nesting(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "input.json"
            cases = [
                (
                    load_metadata,
                    '{"schema_version":1,"capture_id":"first","capture_id":"second","source_kind":"measured_unverified","notes":""}',
                ),
                (load_settings, json.dumps(DEFAULTS)[:-1] + ',"time_zero_s":0.000001}'),
                (load_metadata, "[" * 2000 + "0" + "]" * 2000),
                (load_settings, "[" * 2000 + "0" + "]" * 2000),
            ]
            for loader, payload in cases:
                with self.subTest(loader=loader.__name__, payload=payload[:50]):
                    path.write_text(payload)
                    with self.assertRaises(ValueError):
                        loader(path)

    def test_older_decoder_nesting_error_is_a_value_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "metadata.json"
            path.write_text("{}")
            with patch("ultrasonic_lab.core.json.loads", side_effect=RecursionError("nested")):
                with self.assertRaisesRegex(ValueError, "nesting"):
                    load_metadata(path)

    def test_threshold_equality_and_missing_calibration_data_are_explicit(self):
        row = {"specimen_id": "x", "label": 1, "score": 0.5}
        self.assertEqual(evaluate([row], 0.5)["confusion"]["fn"], 1)
        for rows in [
            [],
            [{"specimen_id": "a", "split": "calibration", "label": 0, "score": None}] * 20,
        ]:
            with self.assertRaises(ValueError):
                fit_threshold(rows)
        for rows, threshold in [
            ([row], float("nan")),
            ([row, row], 0.5),
            ([{**row, "label": 2}], 0.5),
            ([{**row, "score": -1}], 0.5),
        ]:
            with self.assertRaises(ValueError):
                evaluate(rows, threshold)
        repeats = [
            {"specimen_id": "x", "split": "evaluation", "label": 1, "repeat": i, "score": 0.5}
            for i in range(4)
        ]
        with self.assertRaises(ValueError):
            aggregate_specimens(repeats)
        with self.assertRaises(ValueError):
            aggregate_specimens([repeats[0], repeats[0]])
