#!/usr/bin/env python3
"""Guarded objective A/B for the UC-derived Host Multiband processor.

Dry-run is the default.  The live path is serial/firmware pinned and uses the
physical Main-L -> Input-1/2 cable only as an observation loop. It first breaks
both Host-known input-to-Main paths plus the FX feedback path, attenuates the
headphone output, applies the previously proven 60 dB capture gain only after
those feedback paths are open, and unmutes the exact PipeWire sink long enough
to verify the selected physical input and compare:

  crossover only -> Standard -> Tube -> FET -> crossover only

All five cases use the same bundled four-band graph.  The result is measured
from the io24's real Input-2 capture; no ears or subjective attestation are
needed.  Every temporary node, readable device control, PipeWire sink control,
and touched write-only route intent is restored in ``finally``.
"""

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
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

import io24_mbc  # noqa: E402
import io24_uc_comp  # noqa: E402
import io24gtk  # noqa: E402
import io24_loopback_foundation as foundation  # noqa: E402


SCHEMA = "io24-uc-multiband-live-v1"
MODELS = ("standard", "tube", "fet")
CASES = ("baseline_before",) + MODELS + ("baseline_after",)
RATE = 48000
CAPTURE_SECONDS = 5
CAPTURE_CHANNELS = 3
INPUT2_CHANNEL = 1                 # zero based: PipeWire capture FR
INPUT_CHANNELS = {1: 0, 2: 1}      # physical input -> PipeWire capture index
TONE_HZ = 1000.0
STIMULUS_SECONDS = 3.5
STIMULUS_PEAK_DBFS = -30.0
TEST_INPUT_GAIN_DB = 60.0
MAX_PRESTATE_MAIN_VOLUME = 0.50
SAFE_HP_VOLUME = 0.01
SAFE_PIPEWIRE_VOLUME = 0.40
MIN_BASELINE_DBFS = -75.0
MIN_TREATMENT_DBFS = -90.0
MIN_MODEL_CHANGE_DB = 0.5
MIN_MODEL_TO_DRIFT_RATIO = 3.0
# Exact production-graph transfer for this probe's -30 dBFS state is
# Standard -2.0195 dB, Tube -5.0000 dB and FET +4.3495 dB. FET's recovered
# fixed-threshold/auto-makeup law makes an increase the correct discriminator.
EXPECTED_MODEL_DELTA_SIGN = {
    "standard": -1,
    "tube": -1,
    "fet": 1,
}
MAX_BASELINE_DRIFT_DB = 1.0
MAX_CAPTURE_PEAK_DBFS = -6.0
SHADOW_PATH = Path.home() / ".cache" / "io24" / "shadow.json"


class ProbeError(RuntimeError):
    pass


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _dbfs(value):
    return None if value <= 0.0 else 20.0 * math.log10(value)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_json(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def model_state(model):
    """Aggressive bounded settings with a measured model-specific A/B sign."""
    if model not in MODELS:
        raise ValueError("model must be standard, tube or fet")
    state = io24_mbc.default_snapshot(enabled=True)
    settings = {
        "standard": {
            "threshold_db": -40.0,
            "ratio": 4.0,
            "attack_s": 0.001,
            "release_s": 0.15,
            "gain_db": 0.0,
            "softknee": False,
            "automode": False,
        },
        "tube": {"peak": 75.0, "gain": 30.0, "limit_mode": False},
        "fet": {
            "input_db": 0.0,
            "output_db": -35.0,
            "attack_s": 0.0001,
            "release_s": 0.25,
            "ratio_index": 0,
        },
    }
    for band in io24_mbc.BANDS:
        state["bands"][band]["type"] = model
        state["bands"][band][model] = dict(settings[model])
    return io24_mbc.validate_snapshot(state)


def _shadow_entry(data, key, function, source, field):
    raw = data.get(key)
    if not isinstance(raw, dict) or raw.get("fn") != function or \
            not isinstance(raw.get("kwargs"), dict):
        raise ProbeError("missing route prestate: %s" % key)
    values = raw["kwargs"]
    if values.get("source") != source or values.get("bus") != "main" or \
            field not in values:
        raise ProbeError("invalid route prestate: %s" % key)
    return values[field]


def load_route_prestate(path=SHADOW_PATH):
    """Load only the write-only controls this probe will touch."""
    path = Path(path)
    try:
        raw = path.read_bytes()
        data = json.loads(raw)
    except (OSError, ValueError) as error:
        raise ProbeError("cannot read Host route prestate: %s" % error) from error
    lines = {}
    for channel in INPUT_CHANNELS:
        source = "line/ch%d" % channel
        gain = _shadow_entry(
            data, "set_send_db#source=%s,bus=main" % source,
            "set_send_db", source, "gain_db")
        assigned = _shadow_entry(
            data, "set_send_assigned#source=%s,bus=main" % source,
            "set_send_assigned", source, "on")
        if not isinstance(assigned, bool):
            raise ProbeError("route assignment prestate must be Boolean")
        lines[channel] = {"gain_db": gain, "assigned": assigned}
    fx_gain = _shadow_entry(
        data, "set_send_db#source=fxreturn/ch1,bus=main",
        "set_send_db", "fxreturn/ch1", "gain_db")
    fx_assigned = _shadow_entry(
        data, "set_send_assigned#source=fxreturn/ch1,bus=main",
        "set_send_assigned", "fxreturn/ch1", "on")
    return_gain = _shadow_entry(
        data, "set_send_db#source=return/ch1,bus=main",
        "set_send_db", "return/ch1", "gain_db")
    if not isinstance(fx_assigned, bool):
        raise ProbeError("route assignment prestate must be Boolean")
    for name, value in (("line/ch1", lines[1]["gain_db"]),
                        ("line/ch2", lines[2]["gain_db"]),
                        ("fxreturn/ch1", fx_gain),
                        ("return/ch1", return_gain)):
        if value is not None and (isinstance(value, bool) or
                                  not isinstance(value, (int, float)) or
                                  not math.isfinite(float(value))):
            raise ProbeError("route gain prestate is invalid for %s" % name)
    if return_gain is None:
        raise ProbeError("USB playback return is off in Host route prestate")
    return {
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "line_ch1_main": lines[1],
        "line_ch2_main": lines[2],
        "fxreturn_ch1_main": {
            "gain_db": fx_gain, "assigned": fx_assigned},
        "return_ch1_main": {"gain_db": return_gain},
    }


def _clock():
    settings = io24gtk.pw_settings()
    return {
        "rate": int(settings.get("clock.rate", "0") or 0),
        "quantum": int(settings.get("clock.quantum", "0") or 0),
        "force_rate": int(settings.get("clock.force-rate", "0") or 0),
        "force_quantum": int(settings.get("clock.force-quantum", "0") or 0),
    }


def _assert_clock(clock):
    if clock["rate"] != RATE:
        raise ProbeError("PipeWire clock.rate must be %d, got %r" % (RATE, clock))
    if not 32 <= clock["quantum"] <= 2048:
        raise ProbeError("PipeWire quantum is outside the guarded range: %r" % clock)


def _wpctl(arguments):
    try:
        result = subprocess.run(
            ["wpctl"] + list(arguments), capture_output=True, text=True,
            timeout=5, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        raise ProbeError("wpctl failed: %s" % error) from error
    if result.returncode:
        raise ProbeError("wpctl failed: %s" %
                         (result.stderr or result.stdout).strip())
    return result.stdout.strip()


def _wpctl_state(node_id):
    output = _wpctl(["get-volume", str(node_id)])
    match = re.search(r"Volume:\s+([0-9.]+)", output)
    if not match:
        raise ProbeError("cannot parse PipeWire sink volume: %r" % output)
    return {"volume": float(match.group(1)), "muted": "[MUTED]" in output}


def _set_wpctl_state(node_id, state):
    _wpctl(["set-volume", str(node_id), "%.8f" % state["volume"]])
    _wpctl(["set-mute", str(node_id), "1" if state["muted"] else "0"])


def _write_stimulus(path):
    path = Path(path)
    if path.exists():
        raise ProbeError("stimulus path already exists")
    frames = int(round(STIMULUS_SECONDS * RATE))
    audio = np.zeros((frames, 2), dtype=np.float64)
    start, stop = int(0.5 * RATE), int(3.0 * RATE)
    phase = np.arange(stop - start, dtype=np.float64)
    amplitude = 10.0 ** (STIMULUS_PEAK_DBFS / 20.0)
    signal = amplitude * np.sin(2.0 * math.pi * TONE_HZ * phase / RATE)
    fade = int(0.02 * RATE)
    signal[:fade] *= np.linspace(0.0, 1.0, fade, endpoint=False)
    signal[-fade:] *= np.linspace(1.0, 0.0, fade, endpoint=False)
    audio[start:stop, 0] = signal
    pcm = np.rint(audio * (2**31 - 1)).astype("<i4")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(4)
        handle.setframerate(RATE)
        handle.writeframes(pcm.tobytes())
    return {
        "path": str(path), "sha256": _sha256(path),
        "rate_hz": RATE, "channels": 2, "tone_hz": TONE_HZ,
        "active_playback_channel": "FL", "peak_dbfs": STIMULUS_PEAK_DBFS,
    }


def _wait_node_absent(name, timeout=4.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if io24_mbc.node_id(name) is None:
            return True
        time.sleep(0.05)
    return io24_mbc.node_id(name) is None


def _wrap_raw_capture(raw_path, path):
    """Wrap pw-record's exact interleaved S32 output in a WAV container.

    This PipeWire/libsndfile build rejects WAV files with more than two
    channels, while raw mode correctly records the io24's three-channel node.
    It also exits 1 after reaching ``--sample-count`` despite writing the full
    requested buffer, so byte count is the authoritative completion check.
    """
    raw_path = Path(raw_path)
    path = Path(path)
    expected = RATE * CAPTURE_SECONDS * CAPTURE_CHANNELS * 4
    actual = raw_path.stat().st_size if raw_path.is_file() else 0
    if actual != expected:
        raise ProbeError(
            "recorder produced %d bytes; expected %d" % (actual, expected))
    data = raw_path.read_bytes()
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(CAPTURE_CHANNELS)
        handle.setsampwidth(4)
        handle.setframerate(RATE)
        handle.writeframes(data)
    raw_path.unlink()


def _record_playback(name, path, stimulus, playback_target):
    path = Path(path)
    raw_path = path.with_suffix(path.suffix + ".raw")
    if path.exists() or raw_path.exists():
        raise ProbeError("capture path already exists: %s" % path)
    recorder = None
    try:
        recorder_cmd = [
            "pw-record", "--target", io24_mbc.find_io24_capture_source(),
            "--rate", str(RATE), "--channels", str(CAPTURE_CHANNELS),
            "--channel-map", "FL,FR,LFE", "--format", "s32",
            "--latency", "256",
            "-P", "stream.dont-remix=true", "-n",
            str(RATE * CAPTURE_SECONDS), "-a", str(raw_path),
        ]
        recorder = subprocess.Popen(
            recorder_cmd, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, text=True)
        time.sleep(0.5)
        if recorder.poll() is not None:
            _stdout, stderr = recorder.communicate(timeout=2)
            raise ProbeError("%s recorder failed before playback: %s" %
                             (name, stderr.strip()))
        played = subprocess.run(
            ["pw-play", "--target", playback_target,
             "--latency", "256", str(stimulus)],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True, timeout=10, check=False)
        if played.returncode:
            raise ProbeError("%s playback failed: %s" %
                             (name, played.stderr.strip()))
        _stdout, stderr = recorder.communicate(timeout=10)
        try:
            _wrap_raw_capture(raw_path, path)
        except ProbeError as error:
            raise ProbeError("%s %s (exit %s): %s" %
                             (name, error, recorder.returncode,
                              stderr.strip())) from error
    finally:
        if recorder is not None and recorder.poll() is None:
            recorder.terminate()
            try:
                recorder.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                recorder.kill()
                recorder.communicate(timeout=2)
        raw_path.unlink(missing_ok=True)
    return {"path": str(path), "sha256": _sha256(path),
            "recorder_returncode": recorder.returncode}


def _capture_direct(name, path, stimulus, target):
    if io24_mbc.node_id(io24_mbc.SINK_NAME) is not None:
        raise ProbeError("an unrelated io24 Multiband node already exists")
    return _record_playback(name, path, stimulus, target)


def _capture_case(name, path, stimulus, target, state, with_comp, plugin):
    if io24_mbc.node_id(io24_mbc.SINK_NAME) is not None:
        raise ProbeError("an unrelated io24 Multiband node already exists")
    chain = io24_mbc.Chain()
    try:
        if not chain.start(
                target=target, with_comp=with_comp, state=state,
                sample_rate=RATE, plugin=plugin):
            raise ProbeError("%s graph did not start: %s" %
                             (name, chain.last_error))
        return _record_playback(
            name, path, stimulus, io24_mbc.SINK_NAME)
    finally:
        chain.stop()
        if not _wait_node_absent(io24_mbc.SINK_NAME):
            raise ProbeError("%s Multiband node remained after stop" % name)


def _preflight_graph(target, plugin):
    """Prove the compiled plugin loads before any device control write."""
    chain = io24_mbc.Chain()
    try:
        if not chain.start(
                target=target, with_comp=True, state=model_state("standard"),
                sample_rate=RATE, plugin=plugin):
            raise ProbeError("plugin graph preflight failed: %s" %
                             chain.last_error)
        node = chain.node_id()
        if node is None:
            raise ProbeError("plugin graph preflight node disappeared")
        return {"node_id": node, "result": "PLUGIN_GRAPH_LOADED"}
    finally:
        chain.stop()
        if not _wait_node_absent(io24_mbc.SINK_NAME):
            raise ProbeError("plugin preflight node remained after stop")


def capture_metrics(path, input_channel=2):
    path = Path(path)
    if input_channel not in INPUT_CHANNELS:
        raise ProbeError("input channel must be 1 or 2")
    with wave.open(str(path), "rb") as handle:
        shape = {
            "channels": handle.getnchannels(),
            "sample_width_bytes": handle.getsampwidth(),
            "rate_hz": handle.getframerate(),
            "frames": handle.getnframes(),
        }
        raw = handle.readframes(handle.getnframes())
    if shape["channels"] != CAPTURE_CHANNELS or \
            shape["sample_width_bytes"] != 4 or shape["rate_hz"] != RATE:
        raise ProbeError("capture is not three-channel S32_LE/48 kHz")
    audio = np.frombuffer(raw, dtype="<i4").reshape(-1, CAPTURE_CHANNELS)
    audio = audio.astype(np.float64) / 2**31
    maximum = float(np.max(np.abs(audio)))
    maximum_dbfs = _dbfs(maximum)
    if maximum_dbfs is not None and maximum_dbfs >= MAX_CAPTURE_PEAK_DBFS:
        raise ProbeError("capture reached or exceeded -6 dBFS")

    signal = audio[:, INPUT_CHANNELS[input_channel]]
    window = RATE // 2
    step = RATE // 8
    if len(signal) < window:
        raise ProbeError("capture is too short")
    phase = np.arange(window, dtype=np.float64)
    cosine = np.cos(2.0 * math.pi * TONE_HZ * phase / RATE)
    sine = np.sin(2.0 * math.pi * TONE_HZ * phase / RATE)
    best = None
    for start in range(0, len(signal) - window + 1, step):
        segment = signal[start:start + window]
        amplitude = 2.0 / window * math.hypot(
            float(np.dot(segment, cosine)), float(np.dot(segment, sine)))
        tone_rms = amplitude / math.sqrt(2.0)
        if best is None or tone_rms > best[0]:
            total_rms = float(np.sqrt(np.mean(np.square(segment))))
            best = (tone_rms, total_rms, start)
    tone_rms, total_rms, start = best
    return {
        "path": str(path), "sha256": _sha256(path), "shape": shape,
        "maximum_peak_dbfs": maximum_dbfs,
        "input_channel": input_channel,
        "active_window": {"start_frame": start, "frames": window},
        "input_tone_rms_dbfs": _dbfs(tone_rms),
        "input_total_rms_dbfs": _dbfs(total_rms),
    }


def select_loopback_input(path):
    channels = {str(channel): capture_metrics(path, channel)
                for channel in INPUT_CHANNELS}
    selected = max(
        INPUT_CHANNELS,
        key=lambda channel: channels[str(channel)]["input_tone_rms_dbfs"]
        if channels[str(channel)]["input_tone_rms_dbfs"] is not None
        else -math.inf)
    level = channels[str(selected)]["input_tone_rms_dbfs"]
    return {
        "selected_input": (selected if level is not None and
                           level >= MIN_BASELINE_DBFS else None),
        "channels": channels,
        "minimum_usable_tone_dbfs": MIN_BASELINE_DBFS,
    }


def analyze_captures(paths, input_channel=2):
    missing = set(CASES) - set(paths)
    if missing:
        raise ProbeError("missing capture cases: %s" % ", ".join(sorted(missing)))
    cases = {name: capture_metrics(paths[name], input_channel)
             for name in CASES}
    before = cases["baseline_before"]["input_tone_rms_dbfs"]
    after = cases["baseline_after"]["input_tone_rms_dbfs"]
    reasons = []
    if before is None or after is None or \
            min(before, after) < MIN_BASELINE_DBFS:
        reasons.append("baseline_below_detection_floor")
        return {"status": "BLOCKED_NO_LOOPBACK_SIGNAL",
                "cases": cases, "models_passed": [], "reasons": reasons}
    drift = after - before
    reference = (before + after) / 2.0
    if abs(drift) > MAX_BASELINE_DRIFT_DB:
        reasons.append("baseline_drift_exceeded")
    passed = []
    minimum_change = max(
        MIN_MODEL_CHANGE_DB,
        MIN_MODEL_TO_DRIFT_RATIO * abs(drift))
    for model in MODELS:
        level = cases[model]["input_tone_rms_dbfs"]
        delta = None if level is None else level - reference
        cases[model]["delta_db"] = delta
        cases[model]["expected_delta_direction"] = (
            "increase" if EXPECTED_MODEL_DELTA_SIGN[model] > 0
            else "decrease")
        cases[model]["minimum_significant_change_db"] = minimum_change
        if level is None or level < MIN_TREATMENT_DBFS:
            reasons.append("%s_below_detection_floor" % model)
        elif abs(delta) < minimum_change:
            reasons.append("%s_delta_too_small" % model)
        elif delta * EXPECTED_MODEL_DELTA_SIGN[model] <= 0.0:
            reasons.append("%s_delta_wrong_direction" % model)
        else:
            passed.append(model)
    return {
        "status": ("MULTIBAND_AUDIBLE_ALL_MODELS"
                   if not reasons else "MULTIBAND_AUDIBILITY_INCONCLUSIVE"),
        "baseline_reference_dbfs": reference,
        "baseline_drift_db": drift,
        "input_channel": input_channel,
        "cases": cases,
        "models_passed": passed,
        "thresholds": {
            "minimum_baseline_dbfs": MIN_BASELINE_DBFS,
            "minimum_treatment_dbfs": MIN_TREATMENT_DBFS,
            "minimum_model_change_db": MIN_MODEL_CHANGE_DB,
            "minimum_model_to_drift_ratio": MIN_MODEL_TO_DRIFT_RATIO,
            "expected_model_delta_sign": EXPECTED_MODEL_DELTA_SIGN,
            "maximum_baseline_drift_db": MAX_BASELINE_DRIFT_DB,
            "maximum_capture_peak_dbfs": MAX_CAPTURE_PEAK_DBFS,
        },
        "reasons": reasons,
    }


def _assert_device_guards(state, test_input=None):
    if state["input1_phantom"] or state["input2_phantom"]:
        raise ProbeError("phantom must be off on both inputs")
    if state["channel_linked"]:
        raise ProbeError("stereo link must be off")
    if (state["input1_processing_channel"],
            state["input2_processing_channel"]) != (0, 1):
        raise ProbeError("processing-channel permutation must remain 0/1")
    for channel in INPUT_CHANNELS:
        gain = state["input%d_gain_db" % channel]
        ceiling = TEST_INPUT_GAIN_DB if channel == test_input else 12.0
        if gain > ceiling:
            raise ProbeError(
                "Input %d gain exceeds the guarded %.0f dB ceiling" %
                (channel, ceiling))
    if state["main_volume"] > MAX_PRESTATE_MAIN_VOLUME:
        raise ProbeError("Main volume exceeds the guarded 0.50 ceiling")


def _readable_comparison(before, after):
    return {key: {"before": value, "after": after.get(key),
                  "equal": after.get(key) == value}
            for key, value in before.items()}


def _safe_device_state(device, route, input_channel):
    device.set_mute(1, True)
    device.set_mute(2, True)
    device.set_hp_volume(SAFE_HP_VOLUME)
    device.set_send_assigned("line/ch1", "main", False)
    device.set_send_assigned("line/ch2", "main", False)
    device.set_send_assigned("fxreturn/ch1", "main", False)
    device.set_send_db(
        "return/ch1", "main", route["return_ch1_main"]["gain_db"])
    time.sleep(0.5)
    guarded = foundation._state(device.read_params())
    _assert_device_guards(guarded)
    if not guarded["input1_muted"] or not guarded["input2_muted"]:
        raise ProbeError("input mute guard did not read back")
    if not math.isclose(guarded["hp_volume"], SAFE_HP_VOLUME, abs_tol=1e-6):
        raise ProbeError("safe headphone attenuation did not latch")
    device.set_gain(input_channel, TEST_INPUT_GAIN_DB)
    device.set_mute(input_channel, False)
    time.sleep(0.35)
    ready = foundation._state(device.read_params())
    _assert_device_guards(ready, test_input=input_channel)
    other = 2 if input_channel == 1 else 1
    if ready["input%d_muted" % input_channel] or not ready[
            "input%d_muted" % other]:
        raise ProbeError("capture mute state did not read back")
    if ready["input%d_gain_db" % input_channel] != TEST_INPUT_GAIN_DB:
        raise ProbeError("guarded input gain did not read back")
    return guarded, ready


def _restore_device(device, before, route):
    device.set_mute(1, True)
    device.set_mute(2, True)
    device.set_send_assigned("line/ch1", "main", False)
    device.set_send_assigned("line/ch2", "main", False)
    device.set_send_assigned("fxreturn/ch1", "main", False)
    device.set_send_db(
        "line/ch1", "main", route["line_ch1_main"]["gain_db"])
    device.set_send_db(
        "line/ch2", "main", route["line_ch2_main"]["gain_db"])
    device.set_send_db(
        "fxreturn/ch1", "main", route["fxreturn_ch1_main"]["gain_db"])
    device.set_send_db(
        "return/ch1", "main", route["return_ch1_main"]["gain_db"])
    device.set_gain(1, before["input1_gain_db"])
    device.set_gain(2, before["input2_gain_db"])
    device.set_hp_volume(before["hp_volume"])
    device.set_send_assigned(
        "line/ch1", "main", route["line_ch1_main"]["assigned"])
    device.set_send_assigned(
        "line/ch2", "main", route["line_ch2_main"]["assigned"])
    device.set_send_assigned(
        "fxreturn/ch1", "main", route["fxreturn_ch1_main"]["assigned"])
    device.set_mute(1, before["input1_muted"])
    device.set_mute(2, before["input2_muted"])
    time.sleep(0.5)
    restored = foundation._state(device.read_params())
    _assert_device_guards(restored)
    return restored


def run_live(output_dir, battery_path, shadow_path=SHADOW_PATH,
             input_channel=1):
    output_dir = Path(output_dir)
    if input_channel not in INPUT_CHANNELS:
        raise ProbeError("input channel must be 1 or 2")
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise ProbeError("output directory must exist and be empty")
    report = {
        "schema": SCHEMA, "status": "LIVE_FAILED", "started": _now(),
        "device": {"serial": foundation.EXPECTED_SERIAL,
                   "bcd_device": "%04x" % foundation.EXPECTED_BCD_DEVICE},
        "scope": "Main Left physical loopback to Input %d; Host Multiband A/B"
                 % input_channel,
        "requested_input": input_channel,
        "firmware": "UNTOUCHED", "preset_slots": "UNTOUCHED",
        "processing_channel": "UNTOUCHED",
    }
    device = None
    before = None
    route = None
    sink_id = None
    sink_before = None
    transport = []
    failure = None
    analysis = None
    audio_permitted = False
    try:
        report["battery_before"] = foundation._battery(battery_path)
        if report["battery_before"] <= foundation.BATTERY_FLOOR:
            report["status"] = "BLOCKED_BATTERY"
            return report

        clock_before = _clock()
        _assert_clock(clock_before)
        report["clock_before"] = clock_before
        capture = io24_mbc.find_io24_capture_source()
        sink = io24_mbc.find_io24_sink()
        if not capture or not sink or \
                "usb-presonus_revelator_io_24" not in capture.casefold() or \
                "usb-presonus_revelator_io_24" not in sink.casefold():
            raise ProbeError("the exact io24 PipeWire pair is absent")
        positions = io24_mbc.capture_positions(capture)
        if len(positions) != CAPTURE_CHANNELS:
            raise ProbeError("expected three capture channels, got %r" %
                             (positions,))
        report["pipewire_targets"] = {
            "capture": capture, "playback": sink,
            "capture_positions": list(positions)}
        if io24_mbc.node_id(io24_mbc.SINK_NAME) is not None:
            raise ProbeError("an io24 Multiband node already exists")

        route = load_route_prestate(shadow_path)
        report["route_prestate"] = route
        # Chain._launch advertises the default cache through LADSPA_PATH;
        # PipeWire's LADSPA loader accepts only the basename here, not an
        # absolute path. Building into the runtime cache also exercises the
        # exact production Host loading path.
        plugin = io24_uc_comp.build_plugin()
        plugin_reference = io24_uc_comp.plugin_reference()
        report["plugin"] = {
            "path": str(plugin), "sha256": _sha256(plugin),
            "reference": plugin_reference,
        }
        report["plugin_preflight"] = _preflight_graph(
            sink, plugin_reference)
        stimulus = output_dir / "stimulus.wav"
        report["stimulus"] = _write_stimulus(stimulus)

        sink_id = io24_mbc.node_id(sink)
        if sink_id is None:
            raise ProbeError("the io24 playback node has no PipeWire id")
        sink_before = _wpctl_state(sink_id)
        report["pipewire_sink_before"] = sink_before

        device = foundation._open_checked()
        before = foundation._state(device.read_params())
        _assert_device_guards(before)
        report["readable_before"] = before
        guarded, ready = _safe_device_state(device, route, input_channel)
        report["readable_guarded"] = guarded
        report["readable_ready"] = ready
        transport.extend(device.transport_log)
        device.close()
        device = None

        _set_wpctl_state(sink_id, {
            "volume": SAFE_PIPEWIRE_VOLUME, "muted": False})
        report["pipewire_sink_guarded"] = _wpctl_state(sink_id)
        audio_permitted = True

        direct_path = output_dir / "direct_positive_control.wav"
        direct = _capture_direct(
            "direct_positive_control", direct_path, stimulus, sink)
        direct["detection"] = select_loopback_input(direct_path)
        report["direct_positive_control"] = direct
        detected_input = direct["detection"]["selected_input"]
        if detected_input != input_channel:
            analysis = {
                "status": "BLOCKED_NO_PHYSICAL_LOOPBACK",
                "models_passed": [],
                "reasons": ["direct_positive_control_below_detection_floor"],
                "direct_positive_control": direct["detection"],
            }
            report["analysis"] = analysis
            report["status"] = analysis["status"] + "_RESTORATION_PENDING"
        else:
            report["physical_loopback_input"] = input_channel

        paths = {}
        baseline_state = io24_mbc.default_snapshot(enabled=True)
        if input_channel is not None:
            for name in CASES:
                state = (baseline_state if name.startswith("baseline")
                         else model_state(name))
                path = output_dir / (name + ".wav")
                report.setdefault("captures", {})[name] = _capture_case(
                    name, path, stimulus, sink, state,
                    not name.startswith("baseline"),
                    plugin_reference)
                paths[name] = path
                # Fail closed immediately on a hot capture. After the first
                # baseline, also avoid four needless passes when the graph's
                # physical return is absent.
                metric = capture_metrics(path, input_channel)
                report["captures"][name]["metrics"] = metric
                if name == "baseline_before" and (
                        metric["input_tone_rms_dbfs"] is None or
                        metric["input_tone_rms_dbfs"] < MIN_BASELINE_DBFS):
                    analysis = {
                        "status": "BLOCKED_NO_LOOPBACK_SIGNAL",
                        "input_channel": input_channel,
                        "cases": {name: metric}, "models_passed": [],
                        "reasons": ["baseline_below_detection_floor"],
                    }
                    break
            if analysis is None:
                analysis = analyze_captures(paths, input_channel)
            report["analysis"] = analysis
            report["status"] = analysis["status"] + "_RESTORATION_PENDING"
    except BaseException as error:
        failure = error
        report["error"] = {"type": type(error).__name__,
                           "message": str(error)}
    finally:
        remaining = []
        if not _wait_node_absent(io24_mbc.SINK_NAME):
            remaining.append(io24_mbc.SINK_NAME)
        restoration_errors = []
        sink_after = None
        readable_after = None
        if sink_id is not None and sink_before is not None:
            try:
                _wpctl(["set-mute", str(sink_id), "1"])
            except BaseException as error:
                restoration_errors.append({
                    "control": "pipewire_emergency_mute",
                    "type": type(error).__name__, "message": str(error)})
        if device is not None:
            transport.extend(device.transport_log)
            try:
                device.close()
            except BaseException as error:
                restoration_errors.append({
                    "control": "usb_close", "type": type(error).__name__,
                    "message": str(error)})
            device = None
        if before is not None and route is not None:
            cleanup = None
            try:
                cleanup = foundation._open_checked()
                readable_after = _restore_device(cleanup, before, route)
                transport.extend(cleanup.transport_log)
            except BaseException as error:
                if cleanup is not None:
                    transport.extend(cleanup.transport_log)
                restoration_errors.append({
                    "control": "device_restore", "type": type(error).__name__,
                    "message": str(error)})
            finally:
                if cleanup is not None:
                    try:
                        cleanup.close()
                    except BaseException as error:
                        restoration_errors.append({
                            "control": "cleanup_usb_close",
                            "type": type(error).__name__,
                            "message": str(error)})
        if sink_id is not None and sink_before is not None:
            try:
                _set_wpctl_state(sink_id, sink_before)
                sink_after = _wpctl_state(sink_id)
            except BaseException as error:
                restoration_errors.append({
                    "control": "pipewire_sink_restore",
                    "type": type(error).__name__, "message": str(error)})

        comparison = (_readable_comparison(before, readable_after)
                      if before is not None and readable_after is not None
                      else {})
        readable_exact = bool(comparison) and all(
            item["equal"] for item in comparison.values())
        sink_exact = (sink_before is not None and sink_after is not None and
                      sink_before["muted"] == sink_after["muted"] and
                      math.isclose(sink_before["volume"], sink_after["volume"],
                                   abs_tol=1e-6))
        clock_exact = False
        try:
            clock_after = _clock()
            report["clock_after"] = clock_after
            clock_exact = report.get("clock_before") == clock_after
        except BaseException as error:
            restoration_errors.append({
                "control": "pipewire_clock_readback",
                "type": type(error).__name__, "message": str(error)})
        shadow_unchanged = False
        if route is not None:
            try:
                shadow_unchanged = _sha256(shadow_path) == route["sha256"]
            except BaseException as error:
                restoration_errors.append({
                    "control": "shadow_hash_readback",
                    "type": type(error).__name__, "message": str(error)})
        report["readable_after"] = readable_after
        report["transport"] = transport
        report["restoration"] = {
            "readable_comparison": comparison,
            "readable_exact": readable_exact,
            "write_only_route_intent_resent": before is not None and route is not None,
            "write_only_route_readback": "UNAVAILABLE",
            "pipewire_sink_before": sink_before,
            "pipewire_sink_after": sink_after,
            "pipewire_sink_exact": sink_exact,
            "clock_exact": clock_exact,
            "shadow_unchanged": shadow_unchanged,
            "temporary_nodes_remaining": remaining,
            "errors": restoration_errors,
        }
        try:
            report["battery_after"] = foundation._battery(battery_path)
        except BaseException as error:
            report["battery_after_error"] = str(error)
        restored = (not restoration_errors and not remaining and
                    (before is None or readable_exact) and
                    (sink_before is None or sink_exact) and clock_exact and
                    (route is None or shadow_unchanged))
        if not restored:
            report["status"] = "RESTORATION_FAILED"
        elif failure is not None:
            report["status"] = "LIVE_FAILED_RESTORED"
        elif analysis is not None and \
                analysis["status"] == "MULTIBAND_AUDIBLE_ALL_MODELS":
            report["status"] = "MULTIBAND_AUDIBLE_ALL_MODELS_AND_RESTORED"
        elif analysis is not None:
            report["status"] = analysis["status"] + "_RESTORED"
        report["audio_was_permitted"] = audio_permitted
        report["finished"] = _now()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    parser.add_argument("--shadow", default=str(SHADOW_PATH))
    parser.add_argument("--input-channel", type=int, choices=(1, 2), default=1)
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "DRY_RUN_ONLY",
            "device": {"serial": foundation.EXPECTED_SERIAL,
                       "bcd_device": "%04x" % foundation.EXPECTED_BCD_DEVICE},
            "cases": list(CASES),
            "signal_path": "direct-positive-control then PipeWire Multiband "
                           "-> io24 Main L -> selected physical input capture",
            "input_channel": args.input_channel,
            "touched_device_controls": [
                "input 1/2 mute", "selected input gain 60 dB",
                "headphone volume",
                "line/ch1 and line/ch2 -> main assignments",
                "fxreturn/ch1 -> main assignment",
                "return/ch1 -> main gain"],
            "firmware": "UNTOUCHED",
        }, indent=2, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--execute requires --output-dir")
    report = run_live(
        args.output_dir, args.battery_path, args.shadow, args.input_channel)
    _write_json(Path(args.output_dir) / "live-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == \
        "MULTIBAND_AUDIBLE_ALL_MODELS_AND_RESTORED" else 3


if __name__ == "__main__":
    sys.exit(main())
