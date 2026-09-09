#!/usr/bin/env python3
"""Build and measure the safe Main-L -> Input-2 CP34 loopback foundation.

Dry-run is the default.  The live path is serial- and firmware-pinned, checks
the battery before opening USB, refuses either active phantom supply, and does
not play audio until readable mute/gain/preset guards and the two critical
write-only anti-feedback routes have been sent through a strict USB writer.
"""

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import wave

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import io24  # noqa: E402


EXPECTED_SERIAL = "AB7C22200355"
EXPECTED_BCD_DEVICE = 0x0128
BATTERY_FLOOR = 10
RATE = 48000
CHANNELS = 6
CAPTURE_SECONDS = 5
STIMULUS_SECONDS = 3.5
STIMULUS_RMS_DBFS = -30.0
CAPTURE_ENDPOINT = "hw:CARD=R24,DEV=0"
PLAYBACK_ENDPOINT = "hw:CARD=R24,DEV=0"
MIX_A_CHANNELS = (2, 3)  # zero based: USB capture 3-4
INPUT2_REFERENCE_CHANNEL = 1  # zero based: the source used for correlation
MIX_A_MIN_CORRELATION = 0.80
MIX_A_MIN_RMS_DBFS = -90.0


class FoundationError(RuntimeError):
    pass


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _battery(path):
    try:
        return int(Path(path).read_text(encoding="ascii").strip())
    except (OSError, ValueError) as error:
        raise FoundationError("battery unavailable: %s" % error) from error


def _dbfs(value):
    return None if value <= 0.0 else 20.0 * math.log10(value)


def _state(params):
    if params is None:
        raise FoundationError("JaSt read failed")
    flags = int(params["flags"])
    return {
        "flags_word": flags,
        "input1_muted": bool(flags >> 3 & 1),
        "input2_muted": bool(flags >> 4 & 1),
        "input1_preset_enabled": not bool(flags >> 5 & 1),
        "input2_preset_enabled": not bool(flags >> 6 & 1),
        "channel_linked": bool(flags >> 12 & 1),
        "input1_slot_index": int(params["input1SlotIndex"]),
        "input2_slot_index": int(params["input2SlotIndex"]),
        "input1_processing_channel": int(params["input1ProcessingChannel"]),
        "input2_processing_channel": int(params["input2ProcessingChannel"]),
        "input1_gain_db": float(params["input1Gain"]),
        "input2_gain_db": float(params["input2Gain"]),
        "input1_phantom": bool(params["input1PhantomPower"]),
        "input2_phantom": bool(params["input2PhantomPower"]),
        "hp_volume": float(params["hpVolume"]),
        "main_volume": float(params["mainVolume"]),
        "monitor_mix": float(params["monitorMix"]),
    }


class AuditedIo24(io24.Io24):
    """Io24 whose SetP transport raises instead of hiding an endpoint error."""

    def __init__(self, *args, **kwargs):
        self.transport_log = []
        super().__init__(*args, **kwargs)

    def _exec(self, payload, wait=1.5):
        command = struct.unpack_from("<I", payload, 0)[0] if len(payload) >= 4 else None
        if command != io24.SETP:
            return super()._exec(payload, wait)
        uid = self._next_uid()
        frame = (struct.pack("<H", len(payload) + 8) +
                 bytes((0x01, 0x01, uid, 0, 0, 0)) + payload)
        written = self.ep_out.write(frame, timeout=2000)
        if written != len(frame):
            raise FoundationError("short USB write: %s of %s" % (written, len(frame)))
        block = block_index = blob_tag = None
        if len(payload) >= 16:
            _, block, block_index, blob_tag = struct.unpack_from("<IIII", payload, 0)
        event = {
            "timestamp": _now(),
            "uid": uid,
            "frame_bytes": len(frame),
            "frame_sha256": hashlib.sha256(frame).hexdigest(),
            "command": "SetP",
            "block": block,
            "block_index": block_index,
            "blob_tag": blob_tag,
            "transport": "USB_WRITE_EXACT_LENGTH",
            "device_readback": "WRITE_SENT_NOT_READABLE",
        }

        # Match the proven Host cadence.  SetP is semantically fire-and-forget,
        # but the established transport still services EP_IN for one 400 ms
        # interval after every write.  Sleeping only 250 ms made the third
        # consecutive write time out on the real unit; it did not provide the
        # endpoint service/spacing that io24.Io24._exec has always supplied.
        response = b""
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            try:
                chunk = self.ep_in.read(2048, timeout=400)
            except io24.usb.core.USBTimeoutError:
                if response:
                    break
                continue
            except io24.usb.core.USBError as error:
                raise FoundationError("USB response service failed: %s" % error) from error
            if chunk:
                response += bytes(chunk)
                if len(response) >= 2:
                    total, = struct.unpack_from("<H", response, 0)
                    if 8 <= total <= len(response):
                        break
        event["response_frame_bytes"] = len(response)
        if response:
            event["response_frame_sha256"] = hashlib.sha256(response).hexdigest()
        self.transport_log.append(event)
        return response[8:] if len(response) > 8 else b""


def _open_checked():
    device = AuditedIo24(shadow=False)
    serial = device.dev.serial_number
    firmware = int(getattr(device.dev, "bcdDevice", 0))
    if serial != EXPECTED_SERIAL:
        device.close()
        raise FoundationError("serial mismatch: %r" % serial)
    if firmware != EXPECTED_BCD_DEVICE:
        device.close()
        raise FoundationError("bcdDevice mismatch: %04x" % firmware)
    return device


def _write_stimulus(path):
    if path.exists():
        raise FoundationError("stimulus path already exists")
    frames = int(round(STIMULUS_SECONDS * RATE))
    audio = np.zeros((frames, CHANNELS), dtype=np.float64)
    start = int(0.5 * RATE)
    stop = int(3.0 * RATE)
    rng = np.random.default_rng(0x1024)
    signal = rng.normal(0.0, 10.0 ** (STIMULUS_RMS_DBFS / 20.0), stop - start)
    fade = int(0.02 * RATE)
    signal[:fade] *= np.linspace(0.0, 1.0, fade, endpoint=False)
    signal[-fade:] *= np.linspace(1.0, 0.0, fade, endpoint=False)
    audio[start:stop, 0] = signal
    pcm = np.rint(np.clip(audio, -1.0, 1.0) * (2**31 - 1)).astype("<i4")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(CHANNELS)
        handle.setsampwidth(4)
        handle.setframerate(RATE)
        handle.writeframes(pcm.tobytes())
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rate_hz": RATE,
        "channels": CHANNELS,
        "format": "S32_LE_PCM",
        "active_playback_channel": 1,
        "rms_dbfs": STIMULUS_RMS_DBFS,
    }


def _best_correlation(source, candidate, max_lag=256):
    source = source - np.mean(source)
    candidate = candidate - np.mean(candidate)
    best = {"absolute_correlation": 0.0, "lag_samples": None}
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            left, right = source[-lag:], candidate[:lag]
        elif lag > 0:
            left, right = source[:-lag], candidate[lag:]
        else:
            left, right = source, candidate
        denom = float(np.linalg.norm(left) * np.linalg.norm(right))
        score = 0.0 if denom == 0.0 else abs(float(np.dot(left, right)) / denom)
        if score > best["absolute_correlation"]:
            best = {"absolute_correlation": score, "lag_samples": lag}
    return best


def analyze_capture(path):
    with wave.open(str(path), "rb") as handle:
        shape = {
            "channels": handle.getnchannels(),
            "sample_width_bytes": handle.getsampwidth(),
            "rate_hz": handle.getframerate(),
            "frames": handle.getnframes(),
        }
        raw = handle.readframes(handle.getnframes())
    if shape["channels"] != CHANNELS or shape["sample_width_bytes"] != 4 or \
            shape["rate_hz"] != RATE:
        raise FoundationError("capture is not six-channel S32_LE/48 kHz")
    audio = np.frombuffer(raw, dtype="<i4").reshape(-1, CHANNELS).astype(np.float64)
    audio /= 2**31
    peaks = np.max(np.abs(audio), axis=0)
    peak_dbfs = [_dbfs(float(value)) for value in peaks]
    max_peak = max(peaks)
    if max_peak >= 10.0 ** (-6.0 / 20.0):
        raise FoundationError("capture reached or exceeded -6 dBFS")

    raw_input = audio[:, 1]
    window = 8192
    if len(raw_input) < window:
        raise FoundationError("capture too short")
    starts = range(0, len(raw_input) - window + 1, window // 2)
    active_start = max(starts, key=lambda start: float(
        np.sqrt(np.mean(np.square(raw_input[start:start + window])))))
    segment = raw_input[active_start:active_start + window]
    input_rms = float(np.sqrt(np.mean(np.square(segment))))
    correlations = []
    for channel in range(CHANNELS):
        candidate = audio[active_start:active_start + window, channel]
        rms = float(np.sqrt(np.mean(np.square(candidate))))
        if channel == INPUT2_REFERENCE_CHANNEL:
            role = "physical_input2_reference"
        elif channel in MIX_A_CHANNELS:
            role = "expected_mix_a"
        else:
            role = "outside_expected_mix_a"
        correlations.append({
            "capture_channel": channel + 1,
            "role": role,
            "rms_dbfs": _dbfs(rms),
            **_best_correlation(segment, candidate),
        })
    candidates = [row for row in correlations
                  if row["role"] == "expected_mix_a"]
    routed = [row for row in correlations
              if row["role"] != "physical_input2_reference"]
    best = max(routed, key=lambda item: item["absolute_correlation"])
    best_expected = max(candidates,
                        key=lambda item: item["absolute_correlation"])
    leakage = [
        row for row in correlations
        if row["role"] == "outside_expected_mix_a"
        and row["absolute_correlation"] >= MIX_A_MIN_CORRELATION
        and row["rms_dbfs"] is not None
        and row["rms_dbfs"] >= MIX_A_MIN_RMS_DBFS
    ]
    reasons = []
    if _dbfs(input_rms) is None or _dbfs(input_rms) < -80.0:
        reasons.append("physical_input2_below_detection_floor")
    if best["absolute_correlation"] < MIX_A_MIN_CORRELATION:
        reasons.append("no_correlated_mix_a_channel")
    elif best["role"] != "expected_mix_a":
        reasons.append("mix_a_channel_outside_expected_pair")
    if leakage:
        reasons.append("mix_a_leakage_outside_expected_pair")
    if (best_expected["rms_dbfs"] is None or
            best_expected["rms_dbfs"] < MIX_A_MIN_RMS_DBFS):
        reasons.append("mix_a_below_detection_floor")
    return {
        "status": "CALIBRATED" if not reasons else "INCONCLUSIVE",
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "shape": shape,
        "peak_dbfs_by_channel": peak_dbfs,
        "maximum_peak_dbfs": _dbfs(float(max_peak)),
        "active_window": {"start_frame": active_start, "frames": window},
        "physical_input2_rms_dbfs": _dbfs(input_rms),
        "capture_channel_correlations": correlations,
        "mix_a_candidates": candidates,
        "mix_a_exclusion_thresholds": {
            "absolute_correlation": MIX_A_MIN_CORRELATION,
            "rms_dbfs": MIX_A_MIN_RMS_DBFS,
            "physical_input2_reference_exempt": True,
        },
        "frozen_mix_a_capture_channel": (
            best_expected["capture_channel"] if not reasons else None),
        "reasons": reasons,
    }


def _capture(stimulus_path, capture_path):
    if capture_path.exists():
        raise FoundationError("capture path already exists")
    recorder_cmd = [
        "arecord", "-q", "-D", CAPTURE_ENDPOINT, "-t", "wav", "-f", "S32_LE",
        "-r", str(RATE), "-c", str(CHANNELS), "-d", str(CAPTURE_SECONDS),
        str(capture_path),
    ]
    player_cmd = ["aplay", "-q", "-D", PLAYBACK_ENDPOINT, str(stimulus_path)]
    recorder = subprocess.Popen(recorder_cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True)
    try:
        time.sleep(0.5)
        if recorder.poll() is not None:
            _, stderr = recorder.communicate(timeout=2)
            raise FoundationError("arecord failed before playback: %s" % stderr.strip())
        played = subprocess.run(player_cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True, timeout=8)
        if played.returncode != 0:
            raise FoundationError("aplay failed: %s" % played.stderr.strip())
        _, stderr = recorder.communicate(timeout=8)
        if recorder.returncode != 0:
            raise FoundationError("arecord failed: %s" % stderr.strip())
    finally:
        if recorder.poll() is None:
            recorder.terminate()
            try:
                recorder.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                recorder.kill()
                recorder.communicate(timeout=2)


def _guard_configuration(before, after):
    if not after["input1_muted"] or not after["input2_muted"]:
        raise FoundationError("input mute guard did not read back")
    if after["input2_gain_db"] != 0.0:
        raise FoundationError("Channel 2 zero-gain guard did not read back")
    if after["input2_preset_enabled"]:
        raise FoundationError("Channel 2 dry-bypass guard did not read back")
    for key in ("input1_slot_index", "input2_slot_index",
                "input1_processing_channel", "input2_processing_channel"):
        if after[key] != before[key]:
            raise FoundationError("configuration changed protected field %s" % key)


def _guard_ready(before, ready):
    if not ready["input1_muted"] or ready["input2_muted"]:
        raise FoundationError("capture mute state did not read back")
    if ready["input2_gain_db"] != 0.0 or ready["input2_preset_enabled"]:
        raise FoundationError("capture gain/preset guard drifted")
    for key in ("input1_slot_index", "input2_slot_index",
                "input1_processing_channel", "input2_processing_channel"):
        if ready[key] != before[key]:
            raise FoundationError("capture changed protected field %s" % key)


def _guard_restored(before, restored):
    keys = (
        "input1_muted", "input2_muted", "input1_preset_enabled",
        "input2_preset_enabled", "channel_linked", "input1_slot_index",
        "input2_slot_index", "input1_processing_channel",
        "input2_processing_channel", "input1_gain_db", "input2_gain_db",
        "input1_phantom", "input2_phantom", "hp_volume", "main_volume",
        "monitor_mix",
    )
    return {key: {"before": before[key], "after": restored[key],
                  "equal": before[key] == restored[key]} for key in keys}


def run_live(battery_path, stimulus_path, capture_path):
    report = {
        "schema": "io24-loopback-foundation-v1",
        "started": _now(),
        "status": "LIVE_FAILED",
        "device": {"serial": EXPECTED_SERIAL,
                   "bcd_device": "%04x" % EXPECTED_BCD_DEVICE},
        "scope": "Main Left physical loopback to Channel 2; Mix A USB 3-4",
        "transport": [],
        "write_only_route_state": "NOT_ATTEMPTED",
    }
    battery_before = _battery(battery_path)
    report["battery_before"] = battery_before
    if battery_before <= BATTERY_FLOOR:
        report["status"] = "BLOCKED_BATTERY"
        return report
    report["stimulus"] = _write_stimulus(stimulus_path)

    device = cleanup_device = None
    before = None
    audio_permitted = False
    try:
        device = _open_checked()
        before = _state(device.read_params())
        report["readable_before"] = before
        if before["input1_phantom"] or before["input2_phantom"]:
            raise FoundationError("phantom must be off on both inputs")
        if before["channel_linked"]:
            raise FoundationError("stereo link must be off")
        if (before["input1_processing_channel"],
                before["input2_processing_channel"]) != (0, 1):
            raise FoundationError("processing-channel permutation must be 0/1")

        device.set_mute(1, True)
        device.set_mute(2, True)
        device.set_gain(2, 0.0)
        device.set_preset_enabled(2, False)
        time.sleep(0.35)
        configured = _state(device.read_params())
        report["readable_guarded"] = configured
        _guard_configuration(before, configured)

        # Critical order: break both possible Channel-2 feedback returns first.
        device.set_send_db("line/ch2", "main", None)
        device.set_send_db("fxreturn/ch1", "main", None)
        report["write_only_route_state"] = "ANTI_FEEDBACK_OFF_SENTINELS_SENT"

        # Mix A is the measurement bus. Hard-off every contributor, then add
        # only physical Channel 2. Main receives only playback return 1.
        for source in device.MIXER_SOURCES:
            device.set_send_db(source, "mixa", None)
        device.set_send_db("line/ch2", "mixa", 0.0)
        device.set_send_db("return/ch1", "main", 0.0)
        report["write_only_route_state"] = "SAFE_CALIBRATION_ROUTE_SENT"

        device.set_mute(2, False)
        time.sleep(0.35)
        ready = _state(device.read_params())
        report["readable_ready"] = ready
        _guard_ready(before, ready)
        report["transport"].extend(device.transport_log)
        device.close()
        device = None
        audio_permitted = True

        _capture(stimulus_path, capture_path)
        report["audio"] = analyze_capture(capture_path)
        report["status"] = ("FOUNDATION_CALIBRATED" if
                            report["audio"]["status"] == "CALIBRATED" else
                            "FOUNDATION_INCONCLUSIVE")
    except BaseException as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        if device is not None:
            report["transport"].extend(device.transport_log)
            try:
                device.close()
            except BaseException:
                pass
        if before is not None:
            try:
                cleanup_device = _open_checked()
                cleanup_device.set_mute(2, True)
                cleanup_device.set_send_db("return/ch1", "main", None)
                cleanup_device.set_send_db("line/ch2", "main", None)
                cleanup_device.set_send_db("fxreturn/ch1", "main", None)
                cleanup_device.set_gain(2, before["input2_gain_db"])
                cleanup_device.set_preset_enabled(
                    2, before["input2_preset_enabled"])
                cleanup_device.set_mute(1, before["input1_muted"])
                cleanup_device.set_mute(2, before["input2_muted"])
                time.sleep(0.35)
                restored = _state(cleanup_device.read_params())
                report["readable_restored"] = restored
                comparison = _guard_restored(before, restored)
                report["restoration"] = {
                    "comparison": comparison,
                    "readable_exact": all(item["equal"] for item in comparison.values()),
                    "write_only": {
                        "line_ch2_to_main": "PARKED_OFF",
                        "fx_return_to_main": "PARKED_OFF",
                        "return_ch1_to_main": "PARKED_OFF",
                        "mix_a": "PARKED_WITH_LINE_CH2_ONLY_AT_0_DB",
                        "historical_state": "UNREADABLE_AND_NOT_CLAIMED_RESTORED",
                    },
                }
                report["transport"].extend(cleanup_device.transport_log)
                if not report["restoration"]["readable_exact"]:
                    report["status"] = "RESTORATION_FAILED"
            except BaseException as error:
                report["cleanup_error"] = {
                    "type": type(error).__name__, "message": str(error)}
                report["status"] = "RESTORATION_FAILED"
            finally:
                if cleanup_device is not None:
                    try:
                        cleanup_device.close()
                    except BaseException:
                        pass
        try:
            report["battery_after"] = _battery(battery_path)
        except FoundationError as error:
            report["battery_after_error"] = str(error)
        report["audio_was_permitted"] = audio_permitted
        report["finished"] = _now()
    return report


def _write_report(path, report):
    if path.exists():
        raise FoundationError("report path already exists")
    with path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    parser.add_argument("--stimulus")
    parser.add_argument("--capture")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": "io24-loopback-foundation-v1",
            "status": "DRY_RUN_ONLY",
            "serial": EXPECTED_SERIAL,
            "bcd_device": "%04x" % EXPECTED_BCD_DEVICE,
            "critical_first_writes": [
                "line/ch2 -> main off", "fxreturn/ch1 -> main off"],
            "audio": {"rate_hz": RATE, "channels": CHANNELS,
                      "stimulus_rms_dbfs": STIMULUS_RMS_DBFS,
                      "capture_seconds": CAPTURE_SECONDS},
        }, indent=2, sort_keys=True))
        return 0
    if not args.stimulus or not args.capture or not args.report:
        parser.error("--execute requires --stimulus, --capture, and --report")
    paths = [Path(args.stimulus), Path(args.capture), Path(args.report)]
    if len(set(paths)) != 3 or any(not path.parent.is_dir() for path in paths):
        parser.error("output paths must be distinct and have existing parents")
    report = run_live(args.battery_path, paths[0], paths[1])
    _write_report(paths[2], report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "FOUNDATION_CALIBRATED" else 3


if __name__ == "__main__":
    sys.exit(main())
