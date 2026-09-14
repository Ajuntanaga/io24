#!/usr/bin/env python3
"""Acquire the five objective io24 DSP Amount captures at 96 kHz / 512.

Dry-run is the default.  The live path never changes a write-only mixer route.
It lowers only readable Main/gain controls, requires an exactly recoverable
DSP Amount prestate, captures endpoints first to limit drift, and restores in a
finally block.  A missing existing Input-2 -> Mix-A route produces an honest
inconclusive analysis rather than a routing mutation.
"""

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import wave

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RE_DIR = Path(__file__).resolve().parent
for directory in (ROOT, RE_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import io24  # noqa: E402
import io24_loopback_foundation as foundation  # noqa: E402


AMOUNTS = (0.0, 1.0, 0.25, 0.75, 0.5)
SORTED_AMOUNTS = (0.0, 0.25, 0.5, 0.75, 1.0)
RATE_HZ = 96000
CHANNELS = 6
PERIOD_FRAMES = 512
BUFFER_FRAMES = 2048
CAPTURE_SECONDS = 4
STIMULUS_SECONDS = 3.0
SAFE_MAIN_VOLUME = 0.01
SAFE_INPUT2_GAIN_DB = 0.0
STIMULUS_PEAK_DBFS = -12.1
CAPTURE_ENDPOINT = "hw:CARD=R24,DEV=0"
PLAYBACK_ENDPOINT = "hw:CARD=R24,DEV=0"


class CaptureError(RuntimeError):
    pass


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _enabled(params, channel):
    bit = 5 if channel == 1 else 6
    return not bool(int(params["flags"]) >> bit & 1)


def resolve_restore_amount(shadow, params, channel=2):
    """Return an exact restorable scalar or fail before the first write."""
    _ = shadow
    enabled = _enabled(params, channel)
    if not enabled:
        return {"value": 0.0, "source": "exact_zero_device_readback"}
    raise CaptureError(
        "positive write-only prestate is unknown even when the Host shadow "
        "has a matching nonzero value; no device write was attempted")


def _readable_state(params):
    if params is None:
        raise CaptureError("JaSt read failed")
    return {
        "flags": int(params["flags"]),
        "input1_gain_db": float(params["input1Gain"]),
        "input2_gain_db": float(params["input2Gain"]),
        "main_volume": float(params["mainVolume"]),
        "input1_processing_channel": int(params["input1ProcessingChannel"]),
        "input2_processing_channel": int(params["input2ProcessingChannel"]),
        "input1_phantom": bool(params["input1PhantomPower"]),
        "input2_phantom": bool(params["input2PhantomPower"]),
        "input2_processing_enabled": _enabled(params, 2),
        "channel_linked": bool(int(params["flags"]) >> 12 & 1),
    }


def _assert_identity_guards(state):
    if state["input1_phantom"] or state["input2_phantom"]:
        raise CaptureError("phantom must be off on both inputs")
    if state["channel_linked"]:
        raise CaptureError("stereo link must be off before any test write")
    if (state["input1_processing_channel"],
            state["input2_processing_channel"]) != (0, 1):
        raise CaptureError("processing-channel permutation must remain 0/1")


def run_amount_sequence(device, restore_amount, capture_one, settle=time.sleep):
    """Run the scalar sequence against an open controller and always restore."""
    before = _readable_state(device.read_params())
    _assert_identity_guards(before)
    result = {
        "status": "CAPTURE_FAILED_RESTORATION_PENDING",
        "started": _now(),
        "readable_before": before,
        "capture_order": list(AMOUNTS),
        "captures": [],
    }
    failure = None
    try:
        device.set_main_volume(SAFE_MAIN_VOLUME)
        device.set_gain(2, SAFE_INPUT2_GAIN_DB)
        settle(0.35)
        guarded = _readable_state(device.read_params())
        _assert_identity_guards(guarded)
        if guarded["main_volume"] != SAFE_MAIN_VOLUME or \
                guarded["input2_gain_db"] != SAFE_INPUT2_GAIN_DB:
            raise CaptureError("readable low-output safety guard did not latch")
        result["readable_guarded"] = guarded

        for amount in AMOUNTS:
            device.set_fx_mix(2, amount)
            settle(0.35)
            observed = _readable_state(device.read_params())
            if observed["input2_processing_enabled"] != (amount > 0.0):
                raise CaptureError(
                    "DSP Amount zero/nonzero readback mismatch at %.2f" % amount)
            if (observed["input1_processing_channel"],
                    observed["input2_processing_channel"]) != (0, 1):
                raise CaptureError("DSP Amount changed processing-channel routing")
            item = capture_one(amount)
            result["captures"].append(item)
        result["status"] = "CAPTURED_RESTORATION_PENDING"
    except BaseException as error:
        failure = error
        result["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        restoration_errors = []
        amount_restore_sent = False
        for action, description in (
                (lambda: device.set_gain(2, before["input2_gain_db"]),
                 "input2_gain"),
                (lambda: device.set_main_volume(before["main_volume"]),
                 "main_volume"),
                (lambda: device.set_fx_mix(2, restore_amount), "dsp_amount")):
            try:
                action()
                if description == "dsp_amount":
                    amount_restore_sent = True
            except BaseException as error:
                restoration_errors.append({
                    "control": description,
                    "type": type(error).__name__,
                    "message": str(error),
                })
        try:
            settle(0.35)
            after = _readable_state(device.read_params())
            _assert_identity_guards(after)
            readable_exact = (
                after["input1_gain_db"] == before["input1_gain_db"] and
                after["input2_gain_db"] == before["input2_gain_db"] and
                after["main_volume"] == before["main_volume"] and
                after["input2_processing_enabled"] == (restore_amount > 0.0))
            result["readable_after"] = after
        except BaseException as error:
            readable_exact = False
            restoration_errors.append({
                "control": "readback", "type": type(error).__name__,
                "message": str(error),
            })
        result["restoration"] = {
            "readable_exact": readable_exact,
            "amount_restore_sent": amount_restore_sent,
            "write_only_mixer_routes": "UNTOUCHED",
            "errors": restoration_errors,
        }
        if restoration_errors or not readable_exact or not amount_restore_sent:
            result["status"] = "RESTORATION_FAILED"
        elif failure is not None:
            result["status"] = "CAPTURE_FAILED_RESTORED"
        else:
            result["status"] = "CAPTURED_AND_RESTORED"
        result["finished"] = _now()
    return result


def capture_commands(stimulus_path, capture_path):
    recorder = [
        "arecord", "-q", "-D", CAPTURE_ENDPOINT, "-t", "wav", "-f", "S32_LE",
        "-r", str(RATE_HZ), "-c", str(CHANNELS),
        "--period-size", str(PERIOD_FRAMES), "--buffer-size", str(BUFFER_FRAMES),
        "-d", str(CAPTURE_SECONDS), str(capture_path),
    ]
    player = [
        "aplay", "-q", "-D", PLAYBACK_ENDPOINT, "-r", str(RATE_HZ),
        "--period-size", str(PERIOD_FRAMES), "--buffer-size", str(BUFFER_FRAMES),
        str(stimulus_path),
    ]
    return recorder, player


def write_stimulus(path):
    path = Path(path)
    if path.exists():
        raise CaptureError("stimulus path already exists")
    frames = int(round(STIMULUS_SECONDS * RATE_HZ))
    audio = np.zeros((frames, CHANNELS), dtype=np.float64)
    start = int(0.35 * RATE_HZ)
    stop = int(2.65 * RATE_HZ)
    rng = np.random.default_rng(0xD5A024)
    signal = rng.normal(0.0, 1.0, stop - start)
    fade = int(0.02 * RATE_HZ)
    signal[:fade] *= np.linspace(0.0, 1.0, fade, endpoint=False)
    signal[-fade:] *= np.linspace(1.0, 0.0, fade, endpoint=False)
    peak_target = 10 ** (STIMULUS_PEAK_DBFS / 20.0)
    signal *= peak_target / float(np.max(np.abs(signal)))
    audio[start:stop, 0] = signal
    pcm = np.rint(audio * (2**31 - 1)).astype("<i4")
    with path.open("xb") as raw_handle:
        with wave.open(raw_handle, "wb") as handle:
            handle.setnchannels(CHANNELS)
            handle.setsampwidth(4)
            handle.setframerate(RATE_HZ)
            handle.writeframes(pcm.tobytes())
    actual_peak = float(np.max(np.abs(pcm.astype(np.float64) / (2**31))))
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "rate_hz": RATE_HZ,
        "channels": CHANNELS,
        "sample_width_bytes": 4,
        "active_playback_channel": 1,
        "peak_dbfs": 20.0 * math.log10(actual_peak),
    }


def _capture_one(stimulus_path, capture_path):
    capture_path = Path(capture_path)
    if capture_path.exists():
        raise CaptureError("capture path already exists")
    recorder_cmd, player_cmd = capture_commands(stimulus_path, capture_path)
    recorder = subprocess.Popen(recorder_cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True)
    try:
        time.sleep(0.5)
        if recorder.poll() is not None:
            _, stderr = recorder.communicate(timeout=2)
            raise CaptureError("arecord failed before playback: %s" % stderr.strip())
        played = subprocess.run(player_cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True, timeout=8)
        if played.returncode != 0:
            raise CaptureError("aplay failed: %s" % played.stderr.strip())
        _, stderr = recorder.communicate(timeout=8)
        if recorder.returncode != 0:
            raise CaptureError("arecord failed: %s" % stderr.strip())
    finally:
        if recorder.poll() is None:
            recorder.terminate()
            try:
                recorder.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                recorder.kill()
                recorder.communicate(timeout=2)
    return {
        "path": str(capture_path),
        "bytes": capture_path.stat().st_size,
        "sha256": hashlib.sha256(capture_path.read_bytes()).hexdigest(),
        "recorder_command": recorder_cmd,
        "player_command": player_cmd,
    }


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _load_analyzer():
    path = RE_DIR / "io24_dsp_amount_audio.py"
    spec = importlib.util.spec_from_file_location("io24_dsp_amount_audio", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_foundation_proof(report, now=None):
    """Validate a fresh foundation that leaves a known feedback-safe route."""
    if not isinstance(report, dict):
        raise CaptureError("foundation proof must be an object")
    if report.get("schema") != "io24-loopback-foundation-v1" or \
            report.get("status") != "FOUNDATION_CALIBRATED":
        raise CaptureError("foundation proof is not calibrated")
    device = report.get("device", {})
    if device.get("serial") != foundation.EXPECTED_SERIAL or \
            device.get("bcd_device") != "%04x" % foundation.EXPECTED_BCD_DEVICE:
        raise CaptureError("foundation proof device identity mismatch")
    audio = report.get("audio", {})
    monitor_channel = audio.get("frozen_mix_a_capture_channel")
    if audio.get("status") != "CALIBRATED" or monitor_channel not in (3, 4):
        raise CaptureError("foundation proof has no unambiguous Mix A channel")
    restoration = report.get("restoration", {})
    expected = {
        "line_ch2_to_main": "PARKED_OFF",
        "fx_return_to_main": "PARKED_OFF",
        "return_ch1_to_main": "PARKED_OFF",
        "mix_a": "PARKED_WITH_LINE_CH2_ONLY_AT_0_DB",
    }
    if restoration.get("readable_exact") is not True or \
            restoration.get("write_only") != expected:
        raise CaptureError("foundation proof did not leave the exact safe route")
    if report.get("readable_before", {}).get("input2_preset_enabled") is not False or \
            report.get("readable_restored", {}).get("input2_preset_enabled") is not False:
        raise CaptureError(
            "foundation proof must start and finish at exact DSP Amount zero")
    try:
        finished = dt.datetime.fromisoformat(str(report["finished"]))
    except (KeyError, TypeError, ValueError) as error:
        raise CaptureError("foundation proof has no valid finish time") from error
    if finished.tzinfo is None:
        raise CaptureError("foundation proof finish time must include a timezone")
    current = dt.datetime.now().astimezone() if now is None else now
    age = (current.astimezone(dt.timezone.utc) -
           finished.astimezone(dt.timezone.utc)).total_seconds()
    if not 0.0 <= age <= 600.0:
        raise CaptureError("foundation proof must be from the preceding 10 minutes")
    return {
        "status": report["status"],
        "finished": report["finished"],
        "age_seconds": age,
        "monitor_channel": monitor_channel,
        "safe_route": expected,
    }


def capture_manifest(captures, monitor_channel):
    ordered = sorted(captures, key=lambda row: row["amount"])
    if tuple(float(row["amount"]) for row in ordered) != SORTED_AMOUNTS:
        raise CaptureError("capture set does not contain the five required amounts")
    if monitor_channel not in (3, 4):
        raise CaptureError("Mix A monitor channel must be calibrated to 3 or 4")
    return {
        "schema": "io24-dsp-amount-captures-v1",
        "rate_hz": RATE_HZ,
        "channels": CHANNELS,
        "sample_width_bytes": 4,
        "reference_channel": 2,
        "monitor_channel": monitor_channel,
        "captures": [
            {"amount": row["amount"], "path": Path(row["path"]).name}
            for row in ordered
        ],
    }


def run_live(output_dir, battery_path, foundation_report_path=None):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise CaptureError("output directory must exist and be empty")
    report = {
        "schema": "io24-dsp-amount-live-capture-v1",
        "status": "LIVE_FAILED",
        "started": _now(),
        "device": {"serial": foundation.EXPECTED_SERIAL,
                   "bcd_device": "%04x" % foundation.EXPECTED_BCD_DEVICE},
        "write_only_mixer_routes": "UNTOUCHED",
        "clock": {"rate_hz": RATE_HZ, "period_frames": PERIOD_FRAMES,
                  "buffer_frames": BUFFER_FRAMES},
    }
    try:
        if foundation_report_path is None:
            raise CaptureError("fresh loopback foundation proof is required")
        with Path(foundation_report_path).open(encoding="utf-8") as handle:
            foundation_report = json.load(handle)
        route_proof = validate_foundation_proof(foundation_report)
        report["route_proof"] = route_proof
    except (OSError, ValueError, CaptureError) as error:
        report["status"] = "BLOCKED_ROUTE_PROOF_REQUIRED"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        report["finished"] = _now()
        return report
    battery = foundation._battery(battery_path)
    report["battery_before"] = battery
    if battery <= foundation.BATTERY_FLOOR:
        report["status"] = "BLOCKED_BATTERY"
        return report
    stimulus = output_dir / "stimulus.wav"
    report["stimulus"] = write_stimulus(stimulus)

    device = None
    playback_return_open = False
    try:
        device = foundation._open_checked()
        params = device.read_params()
        before = _readable_state(params)
        _assert_identity_guards(before)
        restore = resolve_restore_amount(io24._load_shadow(), params, 2)
        report["dsp_amount_prestate"] = restore

        def capture(amount):
            name = "amount-%03d.wav" % round(amount * 100)
            value = _capture_one(stimulus, output_dir / name)
            value["amount"] = amount
            return value

        # The fresh foundation parked playback return 1 -> Main off after
        # proving Input 2 cannot feed Main and Mix A contains Input 2 alone.
        # Open only this known cell, then restore its exact parked-off state
        # before analysis or controller close.
        device._write_mix("return/ch1", "main", 0.0)
        playback_return_open = True
        report["write_only_mixer_routes"] = \
            "PLAYBACK_RETURN_OPENED_FROM_FRESH_PROVEN_OFF_STATE"
        try:
            sequence = run_amount_sequence(
                device, restore_amount=restore["value"], capture_one=capture)
        finally:
            if playback_return_open:
                device._write_mix("return/ch1", "main", None)
                playback_return_open = False
                report["playback_route_restoration"] = \
                    "RETURN_CH1_TO_MAIN_PARKED_OFF_SENT"
                report["write_only_mixer_routes"] = \
                    "FRESH_FOUNDATION_SAFE_ROUTE_RESTORED"
        report["sequence"] = sequence
        report["transport"] = list(device.transport_log)
        if sequence["status"] != "CAPTURED_AND_RESTORED":
            report["status"] = sequence["status"]
            return report

        manifest = capture_manifest(
            sequence["captures"], route_proof["monitor_channel"])
        manifest_path = output_dir / "captures.json"
        _write_json(manifest_path, manifest)
        analysis = _load_analyzer().analyze_manifest(manifest_path)
        _write_json(output_dir / "analysis.json", analysis)
        report["analysis"] = analysis
        report["status"] = (
            "CAPTURED_ANALYZED_RESTORED" if analysis["status"] == "VALID"
            else "CAPTURED_INCONCLUSIVE_RESTORED")
    except BaseException as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        if isinstance(error, SystemExit) and "not found" in str(error).lower():
            report["status"] = "BLOCKED_DEVICE_ABSENT"
    finally:
        if device is not None:
            if playback_return_open:
                try:
                    device._write_mix("return/ch1", "main", None)
                    report["playback_route_restoration"] = \
                        "RETURN_CH1_TO_MAIN_PARKED_OFF_SENT_DURING_CLEANUP"
                    report["write_only_mixer_routes"] = \
                        "FRESH_FOUNDATION_SAFE_ROUTE_RESTORED_DURING_CLEANUP"
                except BaseException as error:
                    report["route_cleanup_error"] = {
                        "type": type(error).__name__, "message": str(error)}
                    report["status"] = "RESTORATION_FAILED"
            report.setdefault("transport", []).extend(
                device.transport_log[len(report.get("transport", [])):])
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
    parser.add_argument("--foundation-report")
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": "io24-dsp-amount-live-capture-v1",
            "status": "DRY_RUN_ONLY",
            "capture_order": list(AMOUNTS),
            "clock": {"rate_hz": RATE_HZ, "period_frames": PERIOD_FRAMES,
                      "buffer_frames": BUFFER_FRAMES},
            "safety": {
                "write_only_mixer_routes": (
                    "fresh foundation required; playback return is opened "
                    "from and restored to a proven off state"),
                "requires_exact_zero_amount_prestate": True,
                "requires_fresh_loopback_foundation": True,
                "safe_main_volume": SAFE_MAIN_VOLUME,
                "safe_input2_gain_db": SAFE_INPUT2_GAIN_DB,
                "restoration": "finally_block_plus_readback",
            },
        }, indent=2, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--execute requires --output-dir")
    report = run_live(args.output_dir, args.battery_path,
                      args.foundation_report)
    report_path = Path(args.output_dir) / "live-report.json"
    _write_json(report_path, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "CAPTURED_ANALYZED_RESTORED" else 3


if __name__ == "__main__":
    sys.exit(main())
