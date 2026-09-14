#!/usr/bin/env python3
"""Classify io24 DSP Amount from simultaneous Input-2/Mix-A self-noise.

This no-playback path is intentionally narrower than the deterministic
loopback runner.  It estimates the Input-2 to Mix-A transfer independently in
each capture, so the source noise need not repeat.  Only DSP Amount and the
readable Main volume are written; both are restored in a finally block.
"""

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import wave

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RE_DIR = Path(__file__).resolve().parent
for directory in (ROOT, RE_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import io24_dsp_amount_capture as amount_capture  # noqa: E402
import io24_loopback_foundation as foundation  # noqa: E402


CAPTURE_SCHEMA = "io24-dsp-amount-passive-captures-v1"
RESULT_SCHEMA = "io24-dsp-amount-passive-analysis-v1"
LIVE_SCHEMA = "io24-dsp-amount-passive-live-v1"
CAPTURE_ORDER = (0.0, 1.0, 0.25, 0.75, 0.5)
SORTED_AMOUNTS = (0.0, 0.25, 0.5, 0.75, 1.0)
RATE_HZ = 96000
CHANNELS = 6
SAMPLE_WIDTH_BYTES = 4
REFERENCE_CHANNEL = 2
MONITOR_CHANNELS = (3, 4)
CAPTURE_SECONDS = 8
PERIOD_FRAMES = 512
BUFFER_FRAMES = 2048
SAFE_MAIN_VOLUME = 0.01
PROBE_HIGHPASS_HZ = 1000.0
IDENTITY_HIGHPASS_HZ = 24.0
PROBE_EQ_FREQ_HZ = 1000.0
PROBE_EQ_GAIN_DB = 15.0
PROBE_EQ_Q = 0.7
FFT_FRAMES = 8192
HOP_FRAMES = FFT_FRAMES // 2
LOW_HZ = 40.0
HIGH_HZ = 20000.0
MIN_REFERENCE_DBFS = -120.0
CLIP_LIMIT_DBFS = -6.0
MIN_MEDIAN_COHERENCE = 0.90
MIN_ENDPOINT_DELTA_RATIO = 0.05
MODEL_RESIDUAL_LIMIT = 0.08
POSITION_TOLERANCE = 0.07
LEVEL_SILENCE_RATIO = 0.08


class PassiveError(RuntimeError):
    pass


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _db(value):
    return 20.0 * math.log10(max(float(value), 1e-15))


def _invalid(*reasons):
    return {
        "schema": RESULT_SCHEMA,
        "status": "INVALID_CAPTURE_SET",
        "classification": "UNPROVED",
        "interpretation": "NO_DEVICE_ARCHITECTURE_CONCLUSION",
        "reasons": list(reasons),
    }


def _read_wav(path):
    with wave.open(str(path), "rb") as handle:
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
    return metadata, audio / 2**31


def _estimate_transfer(reference, monitor):
    reference = np.asarray(reference, dtype=np.float64)
    monitor = np.asarray(monitor, dtype=np.float64)
    if reference.shape != monitor.shape or len(reference) < FFT_FRAMES * 4:
        raise ValueError("capture_too_short_for_transfer_estimate")
    reference = reference - np.mean(reference)
    monitor = monitor - np.mean(monitor)
    reference_rms = float(np.sqrt(np.mean(reference * reference)))
    monitor_rms = float(np.sqrt(np.mean(monitor * monitor)))
    if _db(reference_rms) < MIN_REFERENCE_DBFS:
        raise ValueError("reference_below_minus_120_dbfs")
    if _db(max(np.max(np.abs(reference)), np.max(np.abs(monitor)))) >= \
            CLIP_LIMIT_DBFS:
        raise ValueError("capture_peak_reached_minus_6_dbfs")

    starts = range(0, len(reference) - FFT_FRAMES + 1, HOP_FRAMES)
    window = np.hanning(FFT_FRAMES)
    sxx = np.zeros(FFT_FRAMES // 2 + 1, dtype=np.float64)
    syy = np.zeros_like(sxx)
    sxy = np.zeros_like(sxx, dtype=np.complex128)
    segment_count = 0
    for start in starts:
        x = np.fft.rfft(reference[start:start + FFT_FRAMES] * window)
        y = np.fft.rfft(monitor[start:start + FFT_FRAMES] * window)
        sxx += np.abs(x) ** 2
        syy += np.abs(y) ** 2
        sxy += np.conj(x) * y
        segment_count += 1
    frequencies = np.fft.rfftfreq(FFT_FRAMES, 1.0 / RATE_HZ)
    band = (frequencies >= LOW_HZ) & (frequencies <= HIGH_HZ)
    floor = max(float(np.max(sxx)) * 1e-12, 1e-30)
    transfer = sxy / np.maximum(sxx, floor)

    silence_ratio = monitor_rms / max(reference_rms, 1e-30)
    effectively_silent = silence_ratio <= 0.002
    if effectively_silent:
        coherence = np.ones(np.count_nonzero(band), dtype=np.float64)
        transfer[band] = 0.0
    else:
        coherence = (np.abs(sxy[band]) ** 2 /
                     np.maximum(sxx[band] * syy[band], 1e-30))
    median_coherence = float(np.median(coherence))
    if not effectively_silent and median_coherence < MIN_MEDIAN_COHERENCE:
        raise ValueError("median_transfer_coherence_below_0_90")
    selected = transfer[band]
    vector = np.concatenate((selected.real, selected.imag))
    if not np.all(np.isfinite(vector)):
        raise ValueError("transfer_contains_nonfinite_values")
    return vector, {
        "reference_rms_dbfs": _db(reference_rms),
        "monitor_rms_dbfs": _db(monitor_rms),
        "median_coherence": median_coherence,
        "effectively_silent_monitor": effectively_silent,
        "fft_frames": FFT_FRAMES,
        "hop_frames": HOP_FRAMES,
        "segments": segment_count,
        "band_hz": [LOW_HZ, HIGH_HZ],
        "transfer_bins": int(np.count_nonzero(band)),
    }


def classify_transfers(amounts, vectors):
    values = [np.asarray(value, dtype=np.float64) for value in vectors]
    if tuple(float(value) for value in amounts) != SORTED_AMOUNTS:
        raise ValueError("amounts_must_equal_0_25_50_75_100_percent")
    if not values or any(value.shape != values[0].shape for value in values):
        raise ValueError("transfer_vector_shapes_differ")
    dry, wet = values[0], values[-1]
    dry_norm = float(np.linalg.norm(dry))
    wet_norm = float(np.linalg.norm(wet))
    endpoint_scale = max(dry_norm, wet_norm, 1e-15)
    delta = wet - dry
    delta_norm = float(np.linalg.norm(delta))
    endpoint_delta_ratio = delta_norm / endpoint_scale
    denominator = max(delta_norm * delta_norm, 1e-30)
    rows = []
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
            "transfer_vector_norm_db": _db(
                np.linalg.norm(observed) / math.sqrt(len(observed))),
        })
    result = {
        "status": "VALID",
        "classification": "INCONCLUSIVE",
        "interpretation": "NO_DEVICE_ARCHITECTURE_CONCLUSION",
        "reasons": [],
        "endpoint_delta_ratio": endpoint_delta_ratio,
        "amount_measurements": rows,
    }
    if endpoint_delta_ratio < MIN_ENDPOINT_DELTA_RATIO:
        result.update({
            "status": "INCONCLUSIVE",
            "classification": "ENDPOINT_TRANSFERS_INDISTINGUISHABLE",
            "reasons": ["endpoint_transfer_delta_below_threshold"],
        })
        return result

    dry_to_wet_ratio = dry_norm / max(wet_norm, 1e-15)
    level_error = max(row["level_model_residual_ratio"] for row in rows)
    gate_error = max(row["distance_to_wet_ratio"] for row in rows[1:-1])
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
    if manifest.get("schema") != CAPTURE_SCHEMA:
        reasons.append("manifest_schema_mismatch")
    for key, expected in (("rate_hz", RATE_HZ), ("channels", CHANNELS),
                          ("sample_width_bytes", SAMPLE_WIDTH_BYTES),
                          ("reference_channel", REFERENCE_CHANNEL)):
        if manifest.get(key) != expected:
            reasons.append("%s_must_equal_%s" % (key, expected))
    if tuple(manifest.get("monitor_channels", ())) != MONITOR_CHANNELS:
        reasons.append("monitor_channels_must_equal_3_4")
    entries = manifest.get("captures")
    if not isinstance(entries, list):
        entries = []
        reasons.append("captures_not_a_list")
    amounts = [entry.get("amount") for entry in entries
               if isinstance(entry, dict)]
    if tuple(amounts) != SORTED_AMOUNTS:
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
        captures.append(audio)
        capture_reports.append({
            "amount": float(entry["amount"]),
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            **metadata,
        })
    if reasons or len(captures) != len(SORTED_AMOUNTS):
        return _invalid(*reasons)

    monitor_results = []
    all_coherence = []
    for monitor_channel in MONITOR_CHANNELS:
        vectors = []
        estimates = []
        try:
            for audio in captures:
                vector, estimate = _estimate_transfer(
                    audio[:, REFERENCE_CHANNEL - 1],
                    audio[:, monitor_channel - 1])
                vectors.append(vector)
                estimates.append(estimate)
                all_coherence.append(estimate["median_coherence"])
            classified = classify_transfers(SORTED_AMOUNTS, vectors)
        except (ValueError, FloatingPointError) as error:
            return _invalid(
                "monitor_channel_%d_analysis_failed:%s" %
                (monitor_channel, error))
        monitor_results.append({
            "monitor_channel": monitor_channel,
            "estimates": estimates,
            **classified,
        })

    classifications = {row["classification"] for row in monitor_results}
    statuses = {row["status"] for row in monitor_results}
    if len(classifications) != 1 or len(statuses) != 1:
        return _invalid("mix_a_channels_disagree")
    first = monitor_results[0]
    return {
        "schema": RESULT_SCHEMA,
        "status": first["status"],
        "classification": first["classification"],
        "interpretation": first["interpretation"],
        "reasons": first["reasons"],
        "minimum_median_coherence": min(all_coherence),
        "capture_contract": {
            "rate_hz": RATE_HZ,
            "channels": CHANNELS,
            "sample_width_bytes": SAMPLE_WIDTH_BYTES,
            "reference_channel": REFERENCE_CHANNEL,
            "monitor_channels": list(MONITOR_CHANNELS),
            "source": "simultaneous_input2_device_self_noise",
            "no_playback": True,
        },
        "captures": capture_reports,
        "monitor_results": monitor_results,
    }


def run_passive_sequence(device, capture_one, settle):
    before = amount_capture._readable_state(device.read_params())
    amount_capture._assert_identity_guards(before)
    if before["input2_processing_enabled"]:
        raise PassiveError("Input 2 DSP Amount prestate must be exact zero")
    result = {
        "status": "CAPTURE_FAILED_RESTORATION_PENDING",
        "started": _now(),
        "readable_before": before,
        "capture_order": list(CAPTURE_ORDER),
        "captures": [],
    }
    failure = None
    try:
        device.set_main_volume(SAFE_MAIN_VOLUME)
        settle(0.35)
        guarded = amount_capture._readable_state(device.read_params())
        amount_capture._assert_identity_guards(guarded)
        if not math.isclose(guarded["main_volume"], SAFE_MAIN_VOLUME,
                            abs_tol=1e-6):
            raise PassiveError("safe Main volume did not latch")
        result["readable_guarded"] = guarded
        for amount in CAPTURE_ORDER:
            device.set_fx_mix(2, amount)
            settle(0.35)
            observed = amount_capture._readable_state(device.read_params())
            amount_capture._assert_identity_guards(observed)
            if observed["input2_processing_enabled"] != (amount > 0.0):
                raise PassiveError(
                    "DSP Amount zero/nonzero readback mismatch at %.2f" % amount)
            result["captures"].append(capture_one(amount))
        result["status"] = "CAPTURED_RESTORATION_PENDING"
    except BaseException as error:
        failure = error
        result["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        restoration_errors = []
        for action, control in (
                (lambda: device.set_fx_mix(2, 0.0), "dsp_amount"),
                (lambda: device.set_main_volume(before["main_volume"]),
                 "main_volume")):
            try:
                action()
            except BaseException as error:
                restoration_errors.append({
                    "control": control,
                    "type": type(error).__name__,
                    "message": str(error),
                })
        try:
            settle(0.35)
            after = amount_capture._readable_state(device.read_params())
            amount_capture._assert_identity_guards(after)
            readable_exact = (
                not after["input2_processing_enabled"] and
                math.isclose(after["main_volume"], before["main_volume"],
                             abs_tol=1e-6) and
                after["input1_gain_db"] == before["input1_gain_db"] and
                after["input2_gain_db"] == before["input2_gain_db"])
            result["readable_after"] = after
        except BaseException as error:
            readable_exact = False
            restoration_errors.append({
                "control": "readback",
                "type": type(error).__name__,
                "message": str(error),
            })
        result["restoration"] = {
            "readable_exact": readable_exact,
            "dsp_amount": "EXACT_ZERO_SENT",
            "main_volume": "RESTORE_SENT",
            "input_gains": "UNTOUCHED",
            "mixer_routes": "UNTOUCHED",
            "errors": restoration_errors,
        }
        if restoration_errors or not readable_exact:
            result["status"] = "RESTORATION_FAILED"
        elif failure is not None:
            result["status"] = "CAPTURE_FAILED_RESTORED"
        else:
            result["status"] = "CAPTURED_AND_RESTORED"
        result["finished"] = _now()
    return result


def run_known_highpass_sequence(device, capture_one, settle):
    """Run against one known LTI processor and restore its identity BQDF."""
    result = None
    activation_sent = False
    restoration_error = None
    try:
        device.set_highpass_freq(2, PROBE_HIGHPASS_HZ, fs=float(RATE_HZ))
        activation_sent = True
        result = run_passive_sequence(device, capture_one, settle)
    except BaseException as error:
        result = {
            "status": "CAPTURE_FAILED_RESTORATION_PENDING",
            "started": _now(),
            "error": {"type": type(error).__name__, "message": str(error)},
        }
    finally:
        try:
            device.set_fx_mix(2, 0.0)
            device.set_highpass_freq(
                2, IDENTITY_HIGHPASS_HZ, fs=float(RATE_HZ))
        except BaseException as error:
            restoration_error = {
                "type": type(error).__name__, "message": str(error)}
    result["controlled_processor"] = {
        "block": "filt",
        "channel": 2,
        "probe_highpass_hz": PROBE_HIGHPASS_HZ,
        "activation_sent": activation_sent,
        "prestate_basis": (
            "neutral_live_transfer_plus_host_shadow_24_hz_identity"),
        "restoration": (
            "IDENTITY_COEFFICIENTS_SENT" if restoration_error is None
            else "RESTORATION_FAILED"),
        "restoration_error": restoration_error,
    }
    if restoration_error is not None:
        result["status"] = "RESTORATION_FAILED"
    return result


def run_known_eq_sequence(device, capture_one, settle):
    """Run against one known EQ biquad and restore the band to identity."""
    result = None
    activation_sent = False
    restoration_error = None
    try:
        device.set_eq_band(
            2, 0, shape="peaking", freq_hz=PROBE_EQ_FREQ_HZ,
            gain_db=PROBE_EQ_GAIN_DB, q=PROBE_EQ_Q, fs=float(RATE_HZ))
        activation_sent = True
        result = run_passive_sequence(device, capture_one, settle)
    except BaseException as error:
        result = {
            "status": "CAPTURE_FAILED_RESTORATION_PENDING",
            "started": _now(),
            "error": {"type": type(error).__name__, "message": str(error)},
        }
    finally:
        try:
            device.set_fx_mix(2, 0.0)
            device.set_eq_band(
                2, 0, shape="off", freq_hz=PROBE_EQ_FREQ_HZ,
                gain_db=0.0, q=PROBE_EQ_Q, fs=float(RATE_HZ))
        except BaseException as error:
            restoration_error = {
                "type": type(error).__name__, "message": str(error)}
    result["controlled_processor"] = {
        "block": "eq",
        "band": 0,
        "channel": 2,
        "probe": {
            "shape": "peaking",
            "frequency_hz": PROBE_EQ_FREQ_HZ,
            "gain_db": PROBE_EQ_GAIN_DB,
            "q": PROBE_EQ_Q,
        },
        "activation_sent": activation_sent,
        "prestate_basis": (
            "neutral_live_transfer_plus_host_shadow_band_0_off"),
        "restoration": (
            "IDENTITY_COEFFICIENTS_SENT" if restoration_error is None
            else "RESTORATION_FAILED"),
        "restoration_error": restoration_error,
    }
    if restoration_error is not None:
        result["status"] = "RESTORATION_FAILED"
    return result


def _capture_one(path):
    command = [
        "arecord", "-q", "-D", "hw:CARD=R24,DEV=0", "-t", "wav",
        "-f", "S32_LE", "-r", str(RATE_HZ), "-c", str(CHANNELS),
        "--period-size", str(PERIOD_FRAMES),
        "--buffer-size", str(BUFFER_FRAMES),
        "-d", str(CAPTURE_SECONDS), str(path),
    ]
    completed = subprocess.run(command, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE, text=True,
                               timeout=CAPTURE_SECONDS + 6)
    if completed.returncode != 0:
        raise PassiveError("arecord failed: %s" % completed.stderr.strip())
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "recorder_command": command,
    }


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def run_live(output_dir, battery_path, known_highpass=False, known_eq=False):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise PassiveError("output directory must exist and be empty")
    report = {
        "schema": LIVE_SCHEMA,
        "status": "LIVE_FAILED",
        "started": _now(),
        "device": {
            "serial": foundation.EXPECTED_SERIAL,
            "bcd_device": "%04x" % foundation.EXPECTED_BCD_DEVICE,
        },
        "clock": {
            "rate_hz": RATE_HZ,
            "period_frames": PERIOD_FRAMES,
            "buffer_frames": BUFFER_FRAMES,
        },
        "playback": "NONE",
        "mixer_routes": "UNTOUCHED",
        "input_gains": "UNTOUCHED",
        "known_highpass_probe": bool(known_highpass),
        "known_eq_probe": bool(known_eq),
    }
    device = None
    try:
        battery = foundation._battery(battery_path)
        report["battery_before"] = battery
        if battery <= foundation.BATTERY_FLOOR:
            report["status"] = "BLOCKED_BATTERY"
            return report
        device = foundation._open_checked()
        before = amount_capture._readable_state(device.read_params())
        amount_capture._assert_identity_guards(before)
        report["dsp_amount_prestate"] = \
            amount_capture.resolve_restore_amount({}, device.read_params(), 2)

        def capture(amount):
            path = output_dir / ("amount-%03d.wav" % round(amount * 100))
            value = _capture_one(path)
            value["amount"] = amount
            return value

        sequence_runner = (run_known_eq_sequence if known_eq else
                           run_known_highpass_sequence if known_highpass else
                           run_passive_sequence)
        sequence = sequence_runner(
            device, capture, settle=__import__("time").sleep)
        report["sequence"] = sequence
        report["transport"] = list(device.transport_log)
        if sequence["status"] != "CAPTURED_AND_RESTORED":
            report["status"] = sequence["status"]
            return report
        ordered = sorted(sequence["captures"], key=lambda row: row["amount"])
        manifest = {
            "schema": CAPTURE_SCHEMA,
            "rate_hz": RATE_HZ,
            "channels": CHANNELS,
            "sample_width_bytes": SAMPLE_WIDTH_BYTES,
            "reference_channel": REFERENCE_CHANNEL,
            "monitor_channels": list(MONITOR_CHANNELS),
            "captures": [
                {"amount": row["amount"], "path": Path(row["path"]).name}
                for row in ordered
            ],
        }
        manifest_path = output_dir / "captures.json"
        _write_json(manifest_path, manifest)
        analysis = analyze_manifest(manifest_path)
        _write_json(output_dir / "analysis.json", analysis)
        report["analysis"] = analysis
        report["status"] = (
            "CAPTURED_ANALYZED_RESTORED" if analysis["status"] == "VALID"
            else "CAPTURED_INCONCLUSIVE_RESTORED" if
            analysis["status"] == "INCONCLUSIVE" else
            "CAPTURED_INVALID_RESTORED")
    except BaseException as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        if device is not None:
            report.setdefault("transport", list(device.transport_log))
            try:
                device.close()
            except BaseException as error:
                report["close_error"] = {
                    "type": type(error).__name__, "message": str(error)}
                report["status"] = "RESTORATION_FAILED"
        try:
            report["battery_after"] = foundation._battery(battery_path)
        except BaseException as error:
            report["battery_after_error"] = str(error)
        report["finished"] = _now()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--known-highpass", action="store_true")
    parser.add_argument("--known-eq", action="store_true")
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": LIVE_SCHEMA,
            "status": "DRY_RUN_ONLY",
            "capture_order": list(CAPTURE_ORDER),
            "capture_seconds": CAPTURE_SECONDS,
            "safety": {
                "requires_exact_zero_amount_prestate": True,
                "requires_link_and_phantom_off": True,
                "playback": "NONE",
                "mixer_routes": "UNTOUCHED",
                "input_gains": "UNTOUCHED",
                "writes": ["DSP Amount channel 2", "Main volume"],
                "restoration": "finally_block_plus_readback",
            },
        }, indent=2, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--execute requires --output-dir")
    if args.known_highpass and args.known_eq:
        parser.error("choose at most one controlled processor")
    report = run_live(args.output_dir, args.battery_path,
                      args.known_highpass, args.known_eq)
    _write_json(Path(args.output_dir) / "live-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in (
        "CAPTURED_ANALYZED_RESTORED",
        "CAPTURED_INCONCLUSIVE_RESTORED") else 3


if __name__ == "__main__":
    sys.exit(main())
