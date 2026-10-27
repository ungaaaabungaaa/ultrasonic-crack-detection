"""Specimen-level calibration and explicit accepted-only synthetic evaluation."""

import numpy as np


def aggregate_specimens(rows):
    groups = {}
    for row in rows:
        group = groups.setdefault(row["specimen_id"], [])
        if any(
            (x["split"], x["label"]) != (row["split"], row["label"]) or x["repeat"] == row["repeat"]
            for x in group
        ):
            raise ValueError(
                "Specimen repeats must have one split, one label, and unique repeat IDs."
            )
        group.append(row)
    result = []
    for specimen_id, captures in sorted(groups.items()):
        if len(captures) > 3:
            raise ValueError("A specimen supports at most three captures.")
        valid = [r["score"] for r in captures if r["score"] is not None]
        if not all(np.isfinite(x) and x >= 0 for x in valid):
            raise ValueError("Indication scores must be finite and nonnegative or null.")
        result.append(
            {
                "specimen_id": specimen_id,
                "split": captures[0]["split"],
                "label": captures[0]["label"],
                "valid_repeats": len(valid),
                "total_repeats": len(captures),
                "score": float(np.median(valid)) if len(valid) >= 2 else None,
            }
        )
    return result


def fit_threshold(calibration):
    if not calibration or any(r["split"] != "calibration" or r["label"] != 0 for r in calibration):
        raise ValueError("Threshold fitting accepts calibration-normal specimens only.")
    if len({r["specimen_id"] for r in calibration}) != len(calibration):
        raise ValueError("Calibration specimen IDs must be unique.")
    scores = [r["score"] for r in calibration if r["score"] is not None]
    if len(scores) < 20 or not all(np.isfinite(x) and x >= 0 for x in scores):
        raise ValueError("At least twenty determinate calibration specimens are required.")
    return float(np.quantile(scores, 0.95, method="higher"))


def evaluate(rows, threshold):
    if not np.isfinite(threshold) or threshold < 0:
        raise ValueError("Threshold must be finite and nonnegative.")
    if not rows or len({r["specimen_id"] for r in rows}) != len(rows):
        raise ValueError("Evaluation requires unique specimen IDs.")
    counts = {"tn": 0, "fp": 0, "fn": 0, "tp": 0}
    missing = {"normal": 0, "reflector": 0}
    for row in rows:
        if row["label"] not in (0, 1):
            raise ValueError("Synthetic evaluation labels must be zero or one.")
        if row["score"] is None:
            missing["reflector" if row["label"] else "normal"] += 1
            continue
        if not np.isfinite(row["score"]) or row["score"] < 0:
            raise ValueError("Invalid evaluation score.")
        predicted = row["score"] > threshold
        counts[
            "tp"
            if predicted and row["label"]
            else "fp"
            if predicted
            else "fn"
            if row["label"]
            else "tn"
        ] += 1
    positive = counts["tp"] + counts["fn"]
    negative = counts["tn"] + counts["fp"]
    valid = positive + negative
    return {
        "total_specimens": len(rows),
        "determinate_specimens": valid,
        "indeterminate_by_label": missing,
        "coverage": valid / len(rows),
        "confusion": counts,
        "sensitivity": counts["tp"] / positive if positive else None,
        "sensitivity_denominator": positive,
        "false_positive_rate": counts["fp"] / negative if negative else None,
        "false_positive_rate_denominator": negative,
    }
