"""Reproducible synthetic experiment and local file-analysis exports."""

import html
import json
from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

import numpy as np

from . import __version__
from .core import (
    DEFAULTS,
    analyze_trace,
    parse_metadata,
    parse_settings,
    parse_trace,
    read_bounded,
)
from .evaluation import aggregate_specimens, evaluate, fit_threshold
from .synthetic import ASSUMPTIONS, generate_dataset


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def provenance():
    modules = sorted(Path(__file__).parent.glob("*.py"))
    return {
        "package_version": __version__,
        "created_utc": datetime.now(UTC).isoformat(),
        "source_sha256": sha256(
            b"".join(p.name.encode() + p.read_bytes() for p in modules)
        ).hexdigest(),
        "dependency_versions": {name: version(name) for name in ["numpy", "scipy", "matplotlib"]},
    }


def plot_waveforms(path, captures, title):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(
        len(captures), 1, figsize=(10, 3.1 * len(captures)), squeeze=False, constrained_layout=True
    )
    for ax, (capture, result, filtered, envelope) in zip(axes[:, 0], captures, strict=True):
        time = capture["time"] * 1e6
        ax.plot(time, capture["volts"], color="#b0b0a8", lw=0.65, label="Raw volts")
        ax.plot(time, filtered, color="#244953", lw=0.8, label="Offline band-pass")
        ax.plot(time, envelope, color="#bd623d", lw=1.2, label="Hilbert envelope")
        for name, color in [
            ("indication", "#dba75d"),
            ("backwall", "#5c9f9a"),
            ("noise", "#a8a5b9"),
        ]:
            lo, hi = capture["settings"][name + "_gate_s"]
            ax.axvspan(lo * 1e6, hi * 1e6, color=color, alpha=0.13, label=name + " gate")
        score = "null (indeterminate)" if result["score"] is None else f"{result['score']:.4f}"
        ax.set(
            title=f"{capture['specimen_id']} / repeat {capture['repeat']} · score {score}",
            xlabel="Time from capture start (µs)",
            ylabel="Amplitude (V)",
            xlim=(time[0], time[-1]),
        )
        ax.legend(loc="upper right", fontsize=7, ncol=3)
        ax.grid(alpha=0.18)
    fig.suptitle(title)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_scores(path, rows, threshold):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    upper = max(
        [0.7, threshold * 1.1]
        + [r["score"] * 1.05 for r in rows if r["split"] == "evaluation" and r["score"] is not None]
    )
    for label, color, name in [
        (0, "#315b64", "Normal model"),
        (1, "#bf633a", "Extra reflector model"),
    ]:
        selected = [
            r["score"]
            for r in rows
            if r["split"] == "evaluation" and r["label"] == label and r["score"] is not None
        ]
        axes[0].hist(selected, bins=np.linspace(0, upper, 24), alpha=0.6, color=color, label=name)
    axes[0].axvline(
        threshold, color="black", ls="--", label=f"Calibration threshold {threshold:.4f}"
    )
    axes[0].set(
        xlabel="Specimen median envelope ratio",
        ylabel="Determinate held-out specimens",
        title="Synthetic held-out evaluation only",
    )
    axes[0].legend(fontsize=8)
    splits = ["calibration", "evaluation", "stress_noise", "stress_coupling"]
    fractions = [
        sum(r["score"] is not None for r in rows if r["split"] == s)
        / sum(r["split"] == s for r in rows)
        for s in splits
    ]
    axes[1].bar(range(4), fractions, color=["#868f89", "#315b64", "#bf633a", "#9b7794"])
    axes[1].set(
        xticks=range(4),
        xticklabels=["Calibration", "Evaluation", "High noise", "Low coupling"],
        ylim=(0, 1.1),
        ylabel="Determinate fraction",
        title="Quality rejection is not a negative result",
    )
    fig.suptitle("SYNTHETIC data · no measured crack-detection accuracy")
    fig.savefig(path, dpi=150)
    plt.close(fig)


def write_report(output, metrics, single=False):
    title = "Single A-scan analysis" if single else "Pulse-echo research lab"
    kind = metrics["source_kind"].upper()
    if single:
        result = metrics["result"]
        detail = f"<p>Status: <b>{html.escape(result['status'])}</b>. Envelope ratio: {html.escape(str(result['score']))}.</p>"
        detail += "<p>No automatic physical crack decision is made. A user-declared velocity, if supplied, gives only an apparent depth.</p>"
    else:
        threshold = metrics["threshold_fit"]["value"]
        detail = f"<p>The threshold <b>{threshold:.5f}</b> was fitted on calibration-normal specimens only. All repeats stay with their specimen.</p>"
        detail += "<table><caption>Synthetic specimen outcomes; accepted-only denominators</caption><thead><tr><th>Group</th><th>Determinate / total</th><th>TP / FN</th><th>FP / TN</th><th>Sensitivity</th><th>False-positive rate</th></tr></thead><tbody>"
        for name, group in metrics["groups"].items():
            c = group["confusion"]

            def rate(key, denominator):
                value = group[key]
                return (
                    "not defined (n=0)"
                    if value is None
                    else f"{100 * value:.1f}% (n={group[denominator]})"
                )

            detail += (
                f"<tr><th>{html.escape(name)}</th><td>{group['determinate_specimens']} / {group['total_specimens']}</td>"
                f"<td>{c['tp']} / {c['fn']}</td><td>{c['fp']} / {c['tn']}</td>"
                f"<td>{rate('sensitivity', 'sensitivity_denominator')}</td>"
                f"<td>{rate('false_positive_rate', 'false_positive_rate_denominator')}</td></tr>"
            )
        noisy = metrics["groups"]["stress_noise"]
        weak = metrics["groups"]["stress_coupling"]
        detail += (
            f'</tbody></table><p class="notice"><b>Stress failure:</b> high noise falsely flags '
            f"{noisy['confusion']['fp']} of {noisy['false_positive_rate_denominator']} accepted normal-model specimens. "
            f"Low coupling leaves only {weak['determinate_specimens']} of {weak['total_specimens']} specimens determinate. "
            "Accepted-only sensitivity must not hide these failures.</p>"
            '<img src="scores.png" alt="Actual synthetic score distributions and quality coverage" />'
        )
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>{title}</title>
<style>body{{margin:0;background:#f2f1eb;color:#22302f;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1100px;padding:38px 24px;margin:auto}}h1{{font:clamp(2.2rem,6vw,4.5rem)/1.1 Georgia,serif;letter-spacing:-.04em;margin:.35em 0}}.label{{font:12px ui-monospace,monospace;letter-spacing:.1em}}.notice{{border-left:4px solid #b75e38;background:#eae3d8;padding:18px}}img{{display:block;max-width:100%;height:auto;margin:24px 0;border:1px solid #d2d1c9}}table{{width:100%;border-collapse:collapse;font-size:14px;display:block;overflow:auto}}th,td{{border-bottom:1px solid #ccc;padding:10px;text-align:left}}caption{{text-align:left;font-weight:bold}}a{{color:#245f65}}details{{margin:24px 0}}code{{overflow-wrap:anywhere}}</style></head><body><main>
<p class="label">ULTRASONIC SIGNAL LAB / {kind} / V{__version__}</p><h1>{title}.</h1>
<p class="notice"><b>{kind}.</b> Offline signal processing. No measured physical crack accuracy, material calibration, safety certification, or hardware test is established by this report.</p>
{detail}<h2>Raw signal, band-pass output, and envelope</h2><p>Shaded gates separate the indication, backwall, and quiet-noise regions. Forward/backward filtering and Hilbert processing use future samples. The score depends on coupling, attenuation, the reference echo, and the chosen gates.</p><img src="waveforms.png" alt="Actual processed A-scan waveforms and configured gates" />
<details><summary>Quality rules and reproducibility</summary><p>Clipping or a weak backwall makes a capture indeterminate. Two valid repeats are required for a synthetic specimen score. Missing results are excluded from classification denominators and counted separately in the JSON. The synthetic model adds Gaussian-windowed carriers, noise, jitter, and a reflector; it does not model physical crack shape, beam propagation, pores, or printed-part anisotropy.</p><p>Code SHA256: <code>{metrics["source_sha256"]}</code></p><p>No external scripts, maps, account, telemetry, or network requests are used.</p></details>
<p><a href="metrics.json">Full metrics and provenance JSON</a> · <a href="settings.json">Exact settings</a></p><p>Built in October 2026. Use independent instrument and specimen calibration before interpreting measured scans.</p></main></body></html>"""
    (output / "index.html").write_text(page, encoding="utf-8")


def run_benchmark(output):
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    captures = generate_dataset()
    processed, examples = [], []
    for array_row, capture in enumerate(captures):
        result, filtered, envelope = analyze_trace(capture["time"], capture["volts"], DEFAULTS)
        processed.append(
            {k: capture[k] for k in ["specimen_id", "split", "label", "repeat"]}
            | result
            | {"array_row": array_row, "simulation_parameters": capture["parameters"]}
        )
        if capture["repeat"] == 0 and capture["specimen_id"] in [
            "evaluation-000",
            "evaluation-040",
            "stress_noise-010",
            "stress_coupling-010",
        ]:
            examples.append(({**capture, "settings": DEFAULTS}, result, filtered, envelope))
    rows = aggregate_specimens(processed)
    calibration = [row for row in rows if row["split"] == "calibration"]
    threshold = fit_threshold(calibration)
    groups = {
        split: evaluate([r for r in rows if r["split"] == split], threshold)
        for split in ["calibration", "evaluation", "stress_noise", "stress_coupling"]
    }
    for row in rows:
        row["decision"] = None if row["score"] is None else int(row["score"] > threshold)
    metrics = provenance() | {
        "schema_version": 1,
        "source_kind": "synthetic",
        "simulation": ASSUMPTIONS,
        "threshold_fit": {
            "value": threshold,
            "quantile": 0.95,
            "method": "higher",
            "split": "calibration-normal only",
            "specimen_ids": [r["specimen_id"] for r in calibration],
            "determinate_specimens": sum(r["score"] is not None for r in calibration),
        },
        "groups": groups,
        "trace_count": len(captures),
        "specimen_count": len(rows),
        "quality": {
            "rejected_traces": sum(r["score"] is None for r in processed),
            "total_traces": len(processed),
        },
        "interpretation": "Synthetic model results only; no measured crack-detection accuracy or calibrated probability.",
    }
    output.mkdir(parents=True)
    metrics["settings_sha256"] = sha256(json.dumps(DEFAULTS, sort_keys=True).encode()).hexdigest()
    save_json(output / "settings.json", DEFAULTS)
    save_json(output / "specimens.json", rows)
    save_json(output / "captures.json", processed)
    np.savez_compressed(
        output / "synthetic-traces.npz",
        time_s=captures[0]["time"],
        amplitude_v=np.stack([c["volts"] for c in captures]),
    )
    (output / "examples").mkdir()
    for capture, _, _, _ in examples:
        name = f"{capture['specimen_id']}-r{capture['repeat']}"
        np.savetxt(
            output / "examples" / (name + ".csv"),
            np.column_stack([capture["time"], capture["volts"]]),
            delimiter=",",
            header="time_s,amplitude_v",
            comments="",
        )
        save_json(
            output / "examples" / (name + ".json"),
            {
                "schema_version": 1,
                "capture_id": name,
                "source_kind": "synthetic",
                "notes": "Generated Gaussian-carrier example, not a measured scan.",
                "velocity_m_s": capture["assumed_velocity_m_s"],
                "velocity_basis": "Illustrative simulated velocity, not calibrated printed material.",
            },
        )
    plot_waveforms(
        output / "waveforms.png", examples, "SYNTHETIC A-scans · actual processing output"
    )
    plot_scores(output / "scores.png", rows, threshold)
    metrics["data_sha256"] = sha256((output / "synthetic-traces.npz").read_bytes()).hexdigest()
    save_json(output / "metrics.json", metrics)
    write_report(output, metrics)
    return metrics


def analyze_file(trace_path, metadata_path, output, settings_path=None):
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    trace_bytes = read_bounded(trace_path, 8_000_000)
    metadata_bytes = read_bounded(metadata_path, 32_000)
    metadata = parse_metadata(metadata_bytes)
    time, volts = parse_trace(trace_bytes)
    settings = parse_settings(read_bounded(settings_path, 32_000)) if settings_path else DEFAULTS
    result, filtered, envelope = analyze_trace(time, volts, settings, metadata.get("velocity_m_s"))
    metrics = provenance() | {
        "schema_version": 1,
        "source_kind": metadata["source_kind"],
        "metadata": metadata,
        "result": result,
        "decision": None,
        "input_sha256": {
            "trace": sha256(trace_bytes).hexdigest(),
            "metadata": sha256(metadata_bytes).hexdigest(),
        },
        "interpretation": "Envelope score only; no benchmark threshold is applied and no physical crack decision is made.",
    }
    metrics["settings_sha256"] = sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    output.mkdir(parents=True)
    save_json(output / "settings.json", settings)
    save_json(output / "metrics.json", metrics)
    capture = {
        "time": time,
        "volts": volts,
        "specimen_id": metadata["capture_id"],
        "repeat": 0,
        "settings": settings,
    }
    plot_waveforms(
        output / "waveforms.png",
        [(capture, result, filtered, envelope)],
        metadata["source_kind"].upper() + " · local-file analysis (source declaration unverified)",
    )
    write_report(output, metrics, single=True)
    return metrics
