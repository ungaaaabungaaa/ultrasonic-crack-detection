"""Bounded local A-scan input, offline filtering, and explicit quality results."""

import csv
import io
import json
import os
import re
import stat
from pathlib import Path

import numpy as np
from scipy.signal import butter, hilbert, sosfiltfilt

DEFAULTS = {
    "band_hz": [600_000, 1_400_000],
    "indication_gate_s": [5e-6, 15e-6],
    "backwall_gate_s": [17e-6, 24e-6],
    "noise_gate_s": [32e-6, 45e-6],
    "time_zero_s": 2e-6,
    "min_backwall_snr": 8,
    "adc_full_scale_v": 2,
}


def number(value, low, high):
    if type(value) not in (int, float) or not np.isfinite(value) or not low <= value <= high:
        raise ValueError("Expected a finite number in the supported range.")
    return float(value)


def read_bounded(path: Path, limit):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError("Input must be a bounded regular file without symlinks.")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError("Input type or byte bound changed.")
        payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("Input exceeds its byte bound.")
    return payload


def validate_settings(settings):
    if not isinstance(settings, dict) or set(settings) != set(DEFAULTS):
        raise ValueError("Settings must use the complete known schema.")
    for name in ["band_hz", "indication_gate_s", "backwall_gate_s", "noise_gate_s"]:
        pair = settings[name]
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("Each band or gate needs two limits.")
        lo, hi = [number(x, 0, 50_000_000 if name == "band_hz" else 0.01) for x in pair]
        if not 0 < lo < hi:
            raise ValueError("Band and gate limits must increase.")
    zero = number(settings["time_zero_s"], 0, 0.01)
    if not (
        zero < settings["indication_gate_s"][0]
        and settings["indication_gate_s"][1] < settings["backwall_gate_s"][0]
        and settings["backwall_gate_s"][1] < settings["noise_gate_s"][0]
    ):
        raise ValueError("Time zero and gates must be ordered and nonoverlapping.")
    number(settings["min_backwall_snr"], 1, 1000)
    number(settings["adc_full_scale_v"], 0.001, 1000)
    return settings


def load_settings(path):
    return validate_settings(json.loads(read_bounded(path, 32_000)))


def load_metadata(path):
    return parse_metadata(read_bounded(path, 32_000))


def parse_metadata(payload):
    if len(payload) > 32_000:
        raise ValueError("Metadata exceeds its byte bound.")
    meta = json.loads(payload)
    required = {"schema_version", "capture_id", "source_kind", "notes"}
    optional = {"velocity_m_s", "velocity_basis"}
    if not isinstance(meta, dict) or not required <= set(meta) or set(meta) - required - optional:
        raise ValueError("Metadata fields do not match the schema.")
    if type(meta["schema_version"]) is not int or meta["schema_version"] != 1:
        raise ValueError("Unsupported metadata version.")
    if not isinstance(meta["capture_id"], str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,80}", meta["capture_id"]
    ):
        raise ValueError("Capture ID must contain only safe identifier characters.")
    if meta["source_kind"] not in ["synthetic", "measured_unverified"]:
        raise ValueError("Source kind must state synthetic or measured_unverified.")
    if not isinstance(meta["notes"], str) or len(meta["notes"]) > 2000:
        raise ValueError("Notes exceed the supported bound.")
    if "velocity_m_s" in meta:
        number(meta["velocity_m_s"], 100, 20_000)
        if (
            not isinstance(meta.get("velocity_basis"), str)
            or not 0 < len(meta["velocity_basis"]) <= 500
        ):
            raise ValueError("A declared velocity requires its calibration or assumption basis.")
    elif "velocity_basis" in meta:
        raise ValueError("Velocity basis requires a velocity value.")
    return meta


def validate_samples(time, volts):
    time, volts = np.asarray(time, dtype="float64"), np.asarray(volts, dtype="float64")
    if time.ndim != 1 or volts.shape != time.shape or not 256 <= len(time) <= 100_000:
        raise ValueError("Trace must have 256 to 100000 paired one-dimensional samples.")
    if not np.isfinite(time).all() or not np.isfinite(volts).all() or np.max(np.abs(volts)) > 1000:
        raise ValueError("Trace values must be finite.")
    intervals = np.diff(time)
    step = float(np.median(intervals))
    if (
        time[0] < 0
        or time[-1] - time[0] > 0.01
        or step <= 0
        or not np.allclose(intervals, step, rtol=1e-4, atol=0)
    ):
        raise ValueError("Trace timestamps must increase uniformly within the duration bound.")
    fs = 1 / step
    if not 100_000 <= fs <= 100_000_000:
        raise ValueError("Trace sampling frequency is outside the supported bound.")
    return time, volts, fs


def load_trace(path):
    return parse_trace(read_bounded(path, 8_000_000))


def parse_trace(payload):
    if len(payload) > 8_000_000:
        raise ValueError("Trace exceeds its byte bound.")
    rows = csv.reader(io.StringIO(payload.decode("utf-8")))
    if next(rows, None) != ["time_s", "amplitude_v"]:
        raise ValueError("CSV header must be time_s,amplitude_v.")
    values = []
    for row in rows:
        if len(row) != 2 or len(values) >= 100_000:
            raise ValueError("CSV sample fields or count exceed the contract.")
        values.append([float(x) for x in row])
    if not values:
        raise ValueError("CSV contains no samples.")
    array = np.asarray(values)
    time, volts, _ = validate_samples(array[:, 0], array[:, 1])
    return time, volts


def analyze_trace(time, volts, settings, velocity_m_s=None):
    validate_settings(settings)
    time, volts, fs = validate_samples(time, volts)
    if fs < 4 * settings["band_hz"][1]:
        raise ValueError("Trace sampling must provide four samples per highest passband cycle.")
    gates = {}
    for name in ["indication", "backwall", "noise"]:
        lo, hi = settings[name + "_gate_s"]
        mask = (time >= lo) & (time <= hi)
        if lo < time[0] or hi > time[-1] or mask.sum() < 8:
            raise ValueError("Every gate must fit the trace and contain at least eight samples.")
        gates[name] = mask
    if velocity_m_s is not None:
        number(velocity_m_s, 100, 20_000)
    sos = butter(4, settings["band_hz"], btype="bandpass", output="sos", fs=fs)
    filtered = sosfiltfilt(sos, volts)
    envelope = np.abs(hilbert(filtered))
    noise_rms = float(np.sqrt(np.mean(filtered[gates["noise"]] ** 2)))
    backwall = float(np.max(envelope[gates["backwall"]]))
    snr = backwall / max(noise_rms, 1e-12)
    clip_fraction = float(np.mean(np.abs(volts) >= 0.999 * settings["adc_full_scale_v"]))
    reasons = []
    if clip_fraction >= 0.001:
        reasons.append("clipping")
    if snr < settings["min_backwall_snr"] or backwall <= 1e-12:
        reasons.append("weak_backwall")
    indices = np.flatnonzero(gates["indication"])
    peak_index = indices[np.argmax(envelope[gates["indication"]])]
    peak_time = float(time[peak_index])
    score = None if reasons else float(envelope[peak_index] / backwall)
    result = {
        "status": "indeterminate" if reasons else "valid",
        "quality_reasons": reasons,
        "score": score,
        "sample_rate_hz": fs,
        "sample_count": len(time),
        "noise_rms_v": noise_rms,
        "backwall_peak_v": backwall,
        "backwall_snr": snr,
        "clipped_fraction": clip_fraction,
        "indication_peak_time_s": None if reasons else peak_time,
        "apparent_depth_mm": (peak_time - settings["time_zero_s"]) * velocity_m_s * 500
        if velocity_m_s is not None and not reasons
        else None,
        "interpretation": "Envelope ratio only; no confirmed physical crack or calibrated probability.",
    }
    return result, filtered, envelope
