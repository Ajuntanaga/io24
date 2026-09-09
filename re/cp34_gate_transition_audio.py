#!/usr/bin/env python3
"""Classify a CP34 gate-transition WAV without opening audio or USB hardware."""

import hashlib
import json
import math
import os
import sys
import wave

import numpy as np


RATE_HZ = 48000
CHANNELS = 6
SAMPLE_WIDTH = 4
DELAY_SAMPLES = 7200
REQUIRED_EVENTS = (
    "baseline_confirmed",
    "channel2_slot2_confirmed",
    "link_on_confirmed",
    "channel2_slot3_confirmed",
    "factory_gate_on_sent",
    "factory_gate_off_sent",
    "factory_gate_restored",
    "link_off_confirmed",
)


def _invalid(*reasons):
    return {
        "schema": "cp34-gate-transition-audio-analysis-v1",
        "status": "INVALID_CAPTURE",
        "capture_tap": "UNPROVED",
        "repeat_result": "UNPROVED",
        "effect_conclusion": "UNPROVED_INVALID_CAPTURE",
        "reasons": list(reasons),
        "monitor_channels": [],
    }


def _read_wav(path):
    with wave.open(os.fspath(path), "rb") as handle:
        metadata = {
            "channels": handle.getnchannels(),
            "sample_width_bytes": handle.getsampwidth(),
            "rate_hz": handle.getframerate(),
            "frames": handle.getnframes(),
        }
        raw = handle.readframes(metadata["frames"])
    if metadata["sample_width_bytes"] != SAMPLE_WIDTH:
        return metadata, None
    values = np.frombuffer(raw, dtype="<i4")
    if metadata["channels"] <= 0 or len(values) % metadata["channels"]:
        return metadata, None
    audio = values.reshape(-1, metadata["channels"]).astype(np.float64) / (2**31)
    return metadata, audio


def _event_offsets(events):
    if not isinstance(events, list):
        return None, ["events_not_a_list"]
    names = []
    offsets = {}
    reasons = []
    for event in events:
        if not isinstance(event, dict):
            reasons.append("event_not_an_object")
            continue
        name = event.get("event")
        offset = event.get("capture_offset_seconds")
        if name in REQUIRED_EVENTS:
            names.append(name)
            if name in offsets:
                reasons.append("duplicate_event:%s" % name)
            if isinstance(offset, bool) or not isinstance(offset, (int, float)) \
                    or not math.isfinite(offset):
                reasons.append("invalid_event_offset:%s" % name)
            else:
                offsets[name] = float(offset)
    if names != list(REQUIRED_EVENTS):
        reasons.append("required_event_order_mismatch")
    for name in REQUIRED_EVENTS:
        if name not in offsets:
            reasons.append("missing_event:%s" % name)
    if len(offsets) == len(REQUIRED_EVENTS):
        values = [offsets[name] for name in REQUIRED_EVENTS]
        if any(right <= left for left, right in zip(values, values[1:])):
            reasons.append("event_offsets_not_strictly_increasing")
    return offsets if not reasons else None, reasons


def _rms(values):
    return float(np.sqrt(np.mean(values * values)))


def _db(value):
    return 20.0 * math.log10(max(float(value), 1e-15))


def _fit_channel(audio, channel, start, end):
    source = audio[:, 1]
    indexes = np.arange(start, end)
    design = np.column_stack((
        source[indexes],
        source[indexes - DELAY_SAMPLES],
        source[indexes - 2 * DELAY_SAMPLES],
        np.ones(len(indexes)),
    ))
    observed = audio[indexes, channel]
    coefficients, _, _, _ = np.linalg.lstsq(design, observed, rcond=None)
    predicted = design @ coefficients
    if np.std(observed) == 0 or np.std(predicted) == 0:
        correlation = 0.0
    else:
        correlation = float(np.corrcoef(observed, predicted)[0, 1])
    direct = float(coefficients[0])
    ratio = (float(coefficients[1]) / direct
             if abs(direct) > 1e-12 else float("inf"))
    return {
        "channel": channel + 1,
        "direct_coefficient": direct,
        "lag150_coefficient": float(coefficients[1]),
        "lag300_coefficient": float(coefficients[2]),
        "lag150_over_direct": ratio,
        "model_correlation": correlation,
    }


def analyze_capture(wav_path, events):
    """Return a fail-closed gate-observability and 150 ms transfer result."""
    try:
        metadata, audio = _read_wav(wav_path)
    except (OSError, EOFError, wave.Error, ValueError) as error:
        return _invalid("wav_read_failed:%s" % error)

    reasons = []
    if metadata["channels"] != CHANNELS:
        reasons.append("channels_must_equal_6")
    if metadata["sample_width_bytes"] != SAMPLE_WIDTH:
        reasons.append("sample_width_must_equal_4")
    if metadata["rate_hz"] != RATE_HZ:
        reasons.append("rate_must_equal_48000")
    if audio is None:
        reasons.append("pcm_layout_invalid")

    offsets, event_reasons = _event_offsets(events)
    reasons.extend(event_reasons)
    if reasons:
        result = _invalid(*reasons)
        result["capture"] = metadata
        return result

    duration = len(audio) / RATE_HZ
    if offsets["link_off_confirmed"] >= duration:
        reasons.append("events_outside_capture")
    on_window = (offsets["factory_gate_on_sent"] + 0.5,
                 offsets["factory_gate_off_sent"] - 0.25)
    off_window = (offsets["factory_gate_off_sent"] + 0.35,
                  offsets["factory_gate_restored"] - 0.25)
    for name, window in (("gate_on", on_window), ("gate_off", off_window)):
        if window[1] - window[0] < 0.5:
            reasons.append("%s_window_too_short" % name)
        if window[0] < 2 * DELAY_SAMPLES / RATE_HZ or window[1] > duration:
            reasons.append("%s_window_outside_capture" % name)
    peak = float(np.max(np.abs(audio)))
    if peak >= 10 ** (-0.1 / 20.0):
        reasons.append("capture_clips_or_exceeds_minus_0_1_dbfs")
    if reasons:
        result = _invalid(*reasons)
        result["capture"] = metadata
        return result

    on_start, on_end = (int(round(value * RATE_HZ)) for value in on_window)
    off_start, off_end = (int(round(value * RATE_HZ)) for value in off_window)
    monitor = []
    for channel in range(2, 6):
        gate_on_rms = _rms(audio[on_start:on_end, channel])
        gate_off_rms = _rms(audio[off_start:off_end, channel])
        fitted = _fit_channel(audio, channel, off_start, off_end)
        fitted.update({
            "gate_on_rms_dbfs": _db(gate_on_rms),
            "gate_off_rms_dbfs": _db(gate_off_rms),
            "gate_delta_db": _db(gate_off_rms) - _db(gate_on_rms),
        })
        monitor.append(fitted)

    gate_observable = all(row["gate_delta_db"] >= 12.0 for row in monitor)
    repeat = gate_observable and all(
        row["model_correlation"] > 0.95 and
        abs(row["lag150_over_direct"]) >= 0.05
        for row in monitor)
    if not gate_observable:
        capture_tap = "CAPTURE_TAP_NOT_GATE_OBSERVABLE"
        repeat_result = "UNPROVED"
        conclusion = "UNPROVED_CAPTURE_TAP"
    elif repeat:
        capture_tap = "DOWNSTREAM_GATE_OBSERVABLE"
        repeat_result = "REPEAT_150MS_SIGNATURE"
        conclusion = "WAVEFORM_EVIDENCE_MODEL_IDENTITY_UNRESOLVED"
    else:
        capture_tap = "DOWNSTREAM_GATE_OBSERVABLE"
        repeat_result = "NO_REPEAT_DOWNSTREAM_GATE_OFF"
        conclusion = "LINKED_PATH_NEGATIVE_STORAGE_UNRESOLVED"

    with open(wav_path, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    metadata.update({"duration_seconds": duration, "sha256": digest,
                     "peak_dbfs": _db(peak)})
    return {
        "schema": "cp34-gate-transition-audio-analysis-v1",
        "status": "VALID",
        "capture": metadata,
        "windows": {
            "gate_on_seconds": list(on_window),
            "gate_off_seconds": list(off_window),
        },
        "capture_tap": capture_tap,
        "repeat_result": repeat_result,
        "effect_conclusion": conclusion,
        "reasons": [],
        "monitor_channels": monitor,
    }


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else list(argv)
    if len(arguments) != 2:
        print("usage: cp34_gate_transition_audio.py LIVE-TRIAL.json CAPTURE.wav",
              file=sys.stderr)
        return 2
    with open(arguments[0], encoding="utf-8") as handle:
        report = json.load(handle)
    result = analyze_capture(arguments[1], report.get("events"))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "VALID" else 3


if __name__ == "__main__":
    sys.exit(main())
