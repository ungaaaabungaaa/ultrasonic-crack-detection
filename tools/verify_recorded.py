"""Recompute the checked-in synthetic study without changing its results."""

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ultrasonic_lab.core import analyze_trace
from ultrasonic_lab.evaluation import aggregate_specimens, evaluate, fit_threshold
from ultrasonic_lab.synthetic import generate_dataset


def main():
    root = Path(__file__).resolve().parents[1]
    demo = root / "demo"
    metrics = json.loads((demo / "metrics.json").read_text())
    settings = json.loads((demo / "settings.json").read_text())
    archive = demo / "synthetic-traces.npz"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == metrics["data_sha256"]
    with zipfile.ZipFile(archive) as zipped:
        assert set(zipped.namelist()) == {"time_s.npy", "amplitude_v.npy"}
        assert sum(entry.file_size for entry in zipped.infolist()) < 6_000_000
    with np.load(archive, allow_pickle=False) as data:
        time, volts = data["time_s"], data["amplitude_v"]
    assert time.shape == (1024,) and volts.shape == (552, 1024)
    assert np.isfinite(volts).all()
    generated = generate_dataset()
    np.testing.assert_allclose(
        np.stack([r["volts"] for r in generated]), volts, rtol=1e-12, atol=1e-12
    )
    saved = json.loads((demo / "captures.json").read_text())
    rows = []
    for index, (capture, record) in enumerate(zip(generated, saved, strict=True)):
        for key in ["specimen_id", "split", "label", "repeat"]:
            assert capture[key] == record[key]
        assert record["array_row"] == index
        result, _, _ = analyze_trace(time, volts[index], settings)
        assert result["quality_reasons"] == record["quality_reasons"]
        if result["score"] is None:
            assert record["score"] is None
        else:
            np.testing.assert_allclose(result["score"], record["score"], rtol=1e-10, atol=1e-12)
        rows.append(
            {key: record[key] for key in ["specimen_id", "split", "label", "repeat"]} | result
        )
    specimens = aggregate_specimens(rows)
    calibration = [r for r in specimens if r["split"] == "calibration"]
    threshold = fit_threshold(calibration)
    np.testing.assert_allclose(threshold, metrics["threshold_fit"]["value"], rtol=1e-10, atol=1e-12)
    for split, expected in metrics["groups"].items():
        assert evaluate([r for r in specimens if r["split"] == split], threshold) == expected
    modules = sorted((root / "src/ultrasonic_lab").glob("*.py"))
    digest = hashlib.sha256(b"".join(p.name.encode() + p.read_bytes() for p in modules)).hexdigest()
    assert digest == metrics["source_sha256"], (
        "Source changed; refresh and review the recorded study."
    )
    assert (
        hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
        == metrics["settings_sha256"]
    )
    print(
        "Recorded study: source/data/settings hashes, all552 signals, calibration, quality, and group outcomes verified."
    )


if __name__ == "__main__":
    main()
