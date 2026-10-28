import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from hashlib import sha256
from pathlib import Path

import numpy as np

from ultrasonic_lab.cli import main
from ultrasonic_lab.core import DEFAULTS
from ultrasonic_lab.workflow import run_benchmark


class WorkflowTests(unittest.TestCase):
    def test_full_frozen_benchmark_has_disjoint_ids_and_honest_quality_denominators(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "study"
            metrics = run_benchmark(root)
            self.assertEqual(metrics["source_kind"], "synthetic")
            groups = metrics["groups"]
            self.assertEqual(groups["evaluation"]["total_specimens"], 80)
            self.assertEqual(groups["calibration"]["total_specimens"], 64)
            rows = json.loads((root / "specimens.json").read_text())
            self.assertEqual(len(rows), 184)
            self.assertEqual(len({r["specimen_id"] for r in rows}), len(rows))
            self.assertTrue(all(r["label"] == 0 for r in rows if r["split"] == "calibration"))
            self.assertEqual(metrics["threshold_fit"]["split"], "calibration-normal only")
            for result in groups.values():
                self.assertEqual(
                    result["determinate_specimens"]
                    + sum(result["indeterminate_by_label"].values()),
                    result["total_specimens"],
                )
                self.assertEqual(sum(result["confusion"].values()), result["determinate_specimens"])
            self.assertIn("SYNTHETIC", (root / "index.html").read_text())
            self.assertTrue((root / "waveforms.png").stat().st_size > 1000)
            self.assertTrue((root / "synthetic-traces.npz").is_file())
            with self.assertRaises(FileExistsError):
                run_benchmark(root)
            example = root / "examples/evaluation-040-r0"
            output = root / "imported"
            self.assertEqual(
                main(
                    [
                        "analyze",
                        "--trace",
                        str(example.with_suffix(".csv")),
                        "--metadata",
                        str(example.with_suffix(".json")),
                        "--output",
                        str(output),
                    ]
                ),
                0,
            )
            imported = json.loads((output / "metrics.json").read_text())
            self.assertIsNone(imported["decision"])
            self.assertIn("no benchmark threshold", imported["interpretation"])
            self.assertEqual(imported["source_kind"], "synthetic")

    def test_measured_declaration_adapter_keeps_unknown_velocity_and_no_decision(self):
        # Generated voltage fixture exercises the measured import path; it is not a real scan.
        from test_core import known_trace

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            trace, metadata = root / "trace.csv", root / "capture.json"
            time, volts = known_trace()
            np.savetxt(
                trace,
                np.column_stack([time, volts]),
                delimiter=",",
                header="time_s,amplitude_v",
                comments="",
            )
            metadata.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "capture_id": "operator_01",
                        "source_kind": "measured_unverified",
                        "notes": "Generated parser fixture; no physical evidence.",
                    }
                )
            )
            out = root / "report"
            self.assertEqual(
                main(
                    [
                        "analyze",
                        "--trace",
                        str(trace),
                        "--metadata",
                        str(metadata),
                        "--output",
                        str(out),
                    ]
                ),
                0,
            )
            metrics = json.loads((out / "metrics.json").read_text())
            self.assertEqual(metrics["source_kind"], "measured_unverified")
            self.assertIsNone(metrics["decision"])
            self.assertIsNone(metrics["result"]["apparent_depth_mm"])
            self.assertEqual(
                metrics["input_sha256"]["trace"], sha256(trace.read_bytes()).hexdigest()
            )
            self.assertEqual(
                metrics["input_sha256"]["metadata"], sha256(metadata.read_bytes()).hexdigest()
            )
            self.assertIn("MEASURED_UNVERIFIED", (out / "index.html").read_text())

    def test_actual_adapter_rejects_ambiguous_settings_before_output(self):
        example = Path(__file__).resolve().parents[1] / "demo/examples/evaluation-040-r0"
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            settings = root / "settings.json"
            settings.write_text(json.dumps(DEFAULTS)[:-1] + ',"time_zero_s":0.000001}')
            output = root / "output"
            error = io.StringIO()
            with redirect_stderr(error):
                code = main(
                    [
                        "analyze",
                        "--trace",
                        str(example.with_suffix(".csv")),
                        "--metadata",
                        str(example.with_suffix(".json")),
                        "--settings",
                        str(settings),
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(code, 1)
            self.assertIn("unique", error.getvalue())
            self.assertNotIn("Traceback", error.getvalue())
            self.assertFalse(output.exists())

    def test_cli_controlled_input_failure_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "missing"
            self.assertEqual(
                main(
                    [
                        "analyze",
                        "--trace",
                        str(output / "trace.csv"),
                        "--metadata",
                        str(output / "metadata.json"),
                        "--output",
                        str(output),
                    ]
                ),
                1,
            )
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
