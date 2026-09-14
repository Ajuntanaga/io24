#!/usr/bin/env python3
"""Objectively classify the io24 DSP Amount transfer from five WAV captures.

The analyzer is hardware-free.  Each capture must contain the same deterministic
stimulus on the raw Input 2 USB channel and the corresponding processed Mix A
return.  It aligns captures by the raw reference, compensates small analog gain
drift, and compares the processed waveforms against four distinct models.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import sys
import wave

import numpy as np


SCHEMA = "io24-dsp-amount-captures-v1"
RESULT_SCHEMA = "io24-dsp-amount-audio-analysis-v1"
RATE_HZ = 96000
CHANNELS = 6
SAMPLE_WIDTH_BYTES = 4
REQUIRED_AMOUNTS = (0.0, 0.25, 0.5, 0.75, 1.0)
CLIP_LIMIT_DBFS = -6.0
MIN_ENDPOINT_DELTA_RATIO = 0.05
MODEL_RESIDUAL_LIMIT = 0.08
POSITION_TOLERANCE = 0.07
LEVEL_SILENCE_RATIO = 0.08
TEMPLATE_FRAMES = 32768
ANALYSIS_FRAMES = 65536


def _invalid(*reasons):
    return {
        "schema": RESULT_SCHEMA,
        "status": "INVALID_CAPTURE_SET",
        "classification": "UNPROVED",
        "reasons": list(reasons),
        "amount_measurements": [],
    }


def _dbfs(value):
    return 20.0 * math.log10(max(float(value), 1e-15))


def _read_wav(path):
    with wave.open(os.fspath(path), "rb") as handle:
        metadata = {
            "channels": handle.getnchannels(),
            "sample_width_bytes": handle.getsampwidth(),
            "rate_hz": handle.getframerate(),
            "frames": handle.getnframes(),
        }
        raw = handle.readframes(metadata["frames"])
    if metadata["sample_width_bytes"] != SAMPLE_WIDTH_BYTES:
        return metadata, None
    values = np.frombuffer(raw, dtype="<i4")
    if metadata["channels"] <= 0 or len(values) % metadata["channels"]:
        return metadata, None
    audio = values.reshape(-1, metadata["channels"]).astype(np.float64)
    audio /= 2**31
    return metadata, audio


def _first_active_block(signal, block=1024):
    count = len(signal) // block
    if count < 4:
        raise ValueError("capture_too_short_for_activity_detection")
    trimmed = signal[:count * block].reshape(count, block)
    levels = np.sqrt(np.mean(trimmed * trimmed, axis=1))
    peak = float(np.max(levels))
    if peak < 10 ** (-80.0 / 20.0):
        raise ValueError("reference_below_minus_80_dbfs")
    active = np.flatnonzero(levels >= peak * 0.25)
    if not len(active):
        raise ValueError("reference_activity_not_found")
    return int(active[0] * block)


def _valid_correlation(signal, template):
    """Return np.correlate(signal, template, 'valid') using an FFT."""
    if len(signal) < len(template):
        raise ValueError("capture_shorter_than_alignment_template")
    full_length = len(signal) + len(template) - 1
    fft_length = 1 << (full_length - 1).bit_length()
    spectrum = np.fft.rfft(signal, fft_length)
    reverse = np.fft.rfft(template[::-1], fft_length)
    convolution = np.fft.irfft(spectrum * reverse, fft_length)[:full_length]
    return convolution[len(template) - 1:len(signal)]


def _alignment_start(signal, template):
    correlation = _valid_correlation(signal, template)
    start = int(np.argmax(np.abs(correlation)))
    left = signal[start:start + len(template)]
    denominator = float(np.linalg.norm(left) * np.linalg.norm(template))
    score = (0.0 if denominator == 0.0 else
             abs(float(np.dot(left, template)) / denominator))
    if score < 0.90:
        raise ValueError("reference_alignment_below_0_90")
    return start, score


def classify_outputs(amounts, outputs):
    """Classify aligned, input-gain-normalized monitor waveforms."""
    values = [np.asarray(output, dtype=np.float64) for output in outputs]
    if tuple(float(value) for value in amounts) != REQUIRED_AMOUNTS:
        raise ValueError("amounts_must_equal_0_25_50_75_100_percent")
    if not values or any(value.shape != values[0].shape for value in values):
        raise ValueError("aligned_output_shapes_differ")
    values = [value - np.mean(value) for value in values]
    dry, wet = values[0], values[-1]
    dry_norm = float(np.linalg.norm(dry))
    wet_norm = float(np.linalg.norm(wet))
    endpoint_scale = max(dry_norm, wet_norm, 1e-15)
    delta = wet - dry
    delta_norm = float(np.linalg.norm(delta))
    endpoint_delta_ratio = delta_norm / endpoint_scale

    rows = []
    denominator = max(delta_norm * delta_norm, 1e-30)
    for amount, observed in zip(amounts, values):
        position = float(np.dot(observed - dry, delta) / denominator)
        affine = dry + position * delta
        rows.append({
            "amount": float(amount),
            "endpoint_position": position,
            "affine_residual_ratio": (
                float(np.linalg.norm(observed - affine)) /
                max(delta_norm, 1e-15)),
            "distance_to_dry_ratio": (
                float(np.linalg.norm(observed - dry)) /
                max(delta_norm, 1e-15)),
            "distance_to_wet_ratio": (
                float(np.linalg.norm(observed - wet)) /
                max(delta_norm, 1e-15)),
            "level_model_residual_ratio": (
                float(np.linalg.norm(observed - float(amount) * wet)) /
                max(wet_norm, 1e-15)),
            "rms_dbfs": _dbfs(np.sqrt(np.mean(observed * observed))),
        })

    result = {
        "status": "VALID",
        "classification": "INCONCLUSIVE",
        "interpretation": "NO_DEVICE_ARCHITECTURE_CONCLUSION",
        "reasons": [],
        "endpoint_delta_ratio": endpoint_delta_ratio,
        "endpoint_rms_dbfs": {
            "amount_0": _dbfs(dry_norm / math.sqrt(len(dry))),
            "amount_100": _dbfs(wet_norm / math.sqrt(len(wet))),
        },
        "thresholds": {
            "minimum_endpoint_delta_ratio": MIN_ENDPOINT_DELTA_RATIO,
            "model_residual_limit": MODEL_RESIDUAL_LIMIT,
            "endpoint_position_tolerance": POSITION_TOLERANCE,
            "level_silence_ratio": LEVEL_SILENCE_RATIO,
        },
        "amount_measurements": rows,
    }
    if endpoint_delta_ratio < MIN_ENDPOINT_DELTA_RATIO:
        result.update({
            "status": "INCONCLUSIVE",
            "classification": "ENDPOINTS_INDISTINGUISHABLE",
            "reasons": ["endpoint_delta_below_threshold"],
        })
        return result

    dry_to_wet_ratio = dry_norm / max(wet_norm, 1e-15)
    level_error = max(row["level_model_residual_ratio"] for row in rows)
    positive_midpoints = rows[1:-1]
    gate_error = max(row["distance_to_wet_ratio"]
                     for row in positive_midpoints)
    affine_error = max(row["affine_residual_ratio"] for row in rows)
    position_error = max(abs(row["endpoint_position"] - row["amount"])
                         for row in rows)
    positions = [row["endpoint_position"] for row in rows]
    monotonic = all(right >= left - POSITION_TOLERANCE
                    for left, right in zip(positions, positions[1:]))

    if dry_to_wet_ratio <= LEVEL_SILENCE_RATIO and \
            level_error <= MODEL_RESIDUAL_LIMIT:
        result["classification"] = "ZERO_ANCHORED_OUTPUT_LEVEL_SCALING"
    elif gate_error <= MODEL_RESIDUAL_LIMIT:
        result["classification"] = "ZERO_NONZERO_GATE"
    elif affine_error <= MODEL_RESIDUAL_LIMIT and \
            position_error <= POSITION_TOLERANCE:
        result["classification"] = "LINEAR_ENDPOINT_INTERPOLATION"
        result["interpretation"] = \
            "CONSISTENT_WITH_DRY_WET_NOT_ARCHITECTURE_PROOF"
    elif affine_error <= MODEL_RESIDUAL_LIMIT and monotonic and \
            positions[0] <= POSITION_TOLERANCE and \
            positions[-1] >= 1.0 - POSITION_TOLERANCE:
        result["classification"] = "NONLINEAR_ENDPOINT_BLEND"
    else:
        result["reasons"] = ["no_candidate_model_met_frozen_thresholds"]
    return result


def analyze_manifest(manifest_path):
    manifest_path = Path(manifest_path)
    try:
        with manifest_path.open(encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as error:
        return _invalid("manifest_read_failed:%s" % error)

    reasons = []
    if manifest.get("schema") != SCHEMA:
        reasons.append("manifest_schema_mismatch")
    for key, expected in (("rate_hz", RATE_HZ), ("channels", CHANNELS),
                          ("sample_width_bytes", SAMPLE_WIDTH_BYTES)):
        if manifest.get(key) != expected:
            reasons.append("%s_must_equal_%s" % (key, expected))
    reference_channel = manifest.get("reference_channel")
    monitor_channel = manifest.get("monitor_channel")
    if reference_channel not in range(1, CHANNELS + 1):
        reasons.append("reference_channel_out_of_range")
    if monitor_channel not in range(1, CHANNELS + 1):
        reasons.append("monitor_channel_out_of_range")
    if reference_channel == monitor_channel:
        reasons.append("reference_and_monitor_channels_must_differ")

    entries = manifest.get("captures")
    if not isinstance(entries, list):
        reasons.append("captures_not_a_list")
        entries = []
    amounts = []
    for entry in entries:
        if not isinstance(entry, dict):
            reasons.append("capture_entry_not_an_object")
            continue
        amount = entry.get("amount")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            reasons.append("capture_amount_not_numeric")
        else:
            amounts.append(float(amount))
    if tuple(amounts) != REQUIRED_AMOUNTS:
        reasons.append("capture_amounts_must_equal_0_25_50_75_100_percent")
    if reasons:
        return _invalid(*reasons)

    captures = []
    capture_reports = []
    for entry in entries:
        path = Path(entry["path"])
        if not path.is_absolute():
            path = manifest_path.parent / path
        try:
            metadata, audio = _read_wav(path)
        except (OSError, EOFError, wave.Error, ValueError) as error:
            reasons.append("wav_read_failed:%s:%s" % (path, error))
            continue
        for key, expected in (("rate_hz", RATE_HZ), ("channels", CHANNELS),
                              ("sample_width_bytes", SAMPLE_WIDTH_BYTES)):
            if metadata[key] != expected:
                reasons.append("%s:%s_must_equal_%s" %
                               (path.name, key, expected))
        if audio is None:
            reasons.append("%s:pcm_layout_invalid" % path.name)
            continue
        peak = float(np.max(np.abs(audio)))
        if peak >= 10 ** (CLIP_LIMIT_DBFS / 20.0):
            reasons.append("%s:peak_reached_minus_6_dbfs" % path.name)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        captures.append(audio)
        capture_reports.append({
            "amount": float(entry["amount"]),
            "path": str(path),
            "sha256": digest,
            **metadata,
            "peak_dbfs": _dbfs(peak),
        })
    if reasons or len(captures) != len(REQUIRED_AMOUNTS):
        return _invalid(*reasons)

    reference_index = int(reference_channel) - 1
    monitor_index = int(monitor_channel) - 1
    try:
        base_reference = captures[0][:, reference_index]
        active_start = _first_active_block(base_reference)
        template_start = active_start + int(0.20 * RATE_HZ)
        template_end = template_start + TEMPLATE_FRAMES
        analysis_end = template_start + ANALYSIS_FRAMES
        if analysis_end > len(base_reference):
            raise ValueError("base_capture_too_short_for_analysis_window")
        template = base_reference[template_start:template_end]
        base_segment = base_reference[template_start:analysis_end]
        base_energy = float(np.dot(base_segment, base_segment))
        if base_energy <= 0.0:
            raise ValueError("base_reference_window_has_no_energy")

        outputs = []
        for audio, report in zip(captures, capture_reports):
            reference = audio[:, reference_index]
            start, score = _alignment_start(reference, template)
            end = start + ANALYSIS_FRAMES
            if end > len(reference):
                raise ValueError("aligned_analysis_window_outside_capture")
            reference_segment = reference[start:end]
            gain = float(np.dot(reference_segment, base_segment) / base_energy)
            if not 0.5 <= gain <= 2.0:
                raise ValueError("reference_gain_compensation_out_of_range")
            outputs.append(audio[start:end, monitor_index] / gain)
            report["alignment"] = {
                "start_frame": start,
                "correlation": score,
                "reference_gain_vs_amount_0": gain,
                "analysis_frames": ANALYSIS_FRAMES,
            }
        result = classify_outputs(REQUIRED_AMOUNTS, outputs)
    except (ValueError, FloatingPointError) as error:
        return _invalid("analysis_failed:%s" % error)

    result.update({
        "schema": RESULT_SCHEMA,
        "manifest": str(manifest_path),
        "capture_contract": {
            "rate_hz": RATE_HZ,
            "channels": CHANNELS,
            "sample_width_bytes": SAMPLE_WIDTH_BYTES,
            "reference_channel": reference_channel,
            "monitor_channel": monitor_channel,
            "required_amounts": list(REQUIRED_AMOUNTS),
            "clip_limit_dbfs": CLIP_LIMIT_DBFS,
        },
        "captures": capture_reports,
    })
    return result


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else list(argv)
    if len(arguments) != 1:
        print("usage: io24_dsp_amount_audio.py CAPTURES.json", file=sys.stderr)
        return 2
    result = analyze_manifest(arguments[0])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in ("VALID", "INCONCLUSIVE") else 3


if __name__ == "__main__":
    sys.exit(main())
