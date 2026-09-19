#!/usr/bin/env python3
"""Prove VoiceFX processing with Main-L -> physical-input waveform capture.

The physical loop is deterministic: USB playback channel 1 leaves Main L,
returns on physical Input 1 or 2, and the six-channel USB capture records that
input plus Mix A. The physical input is the timing reference; Mix A carries the
return.  Reverb must first produce a tail on that exact return or the VoiceFX
result is invalid.

Live execution is deliberately narrow.  It requires an exact Host shadow for
every write-only route it changes, mutes the selected input before breaking the
two Main feedback legs, raises only that input's readable gain after those legs
are off,
never changes output volume, DSP Amount, processingChannel, slots, phantom,
link, or firmware, and restores all changed state in ``finally``.
Without ``--execute`` it only prints the plan.
"""

import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RE_DIR = Path(__file__).resolve().parent
for _directory in (ROOT, RE_DIR):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import io24_fx  # noqa: E402
import io24_loopback_foundation as foundation  # noqa: E402
import io24_fx_shared_return_probe as shared  # noqa: E402


SCHEMA = "io24-voicefx-physical-input-waveform-probe-v2"
RATE = shared.RATE
CHANNELS = shared.CHANNELS
MIX_A_CHANNELS = shared.MIX_A_CHANNELS
INPUT_REFERENCE_CHANNELS = {1: 0, 2: 1}  # zero-based USB capture channels
INPUT2_REFERENCE_CHANNEL = INPUT_REFERENCE_CHANNELS[2]  # legacy test alias
CAPTURE_SECONDS = shared.CAPTURE_SECONDS
TEST_INPUT_GAIN_DB = 60.0
TEST_INPUT2_GAIN_DB = TEST_INPUT_GAIN_DB  # legacy test alias

REVERB_CONTROL = {
    "on": True, "size": 0.95, "mix": 1.0, "predelay": 0.02,
    "hp_freq": 200.0, "fs": float(RATE),
}
DELAY_TEST = {
    "time_s": shared.DELAY_TIME_S, "feedback": 0.65, "mix": 1.0,
}

REFERENCE_MIN_BURST_DBFS = -75.0
REFERENCE_MIN_GATE_CONTRAST_DB = 8.0
REFERENCE_MAX_DRIFT_DB = 1.5
OFF_MAX_DRIFT_DB = 2.0


class WaveformProbeError(RuntimeError):
    """Fail closed before playback whenever a safety premise is missing."""


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _delta(after, before):
    if after is None or before is None:
        return None
    return after - before


def build_stimulus(path):
    return shared.build_stimulus(path)


def _input_channel(value):
    channel = int(value)
    if channel not in INPUT_REFERENCE_CHANNELS:
        raise WaveformProbeError("input channel must be 1 or 2")
    return channel


def required_routes(input_channel=2):
    channel = _input_channel(input_channel)
    return (
        ("line/ch%d" % channel, "main"),
        ("fxreturn/ch1", "main"),
        ("return/ch1", "main"),
        ("return/ch1", "mixa"),
        ("fxreturn/ch1", "mixa"),
    )


def resolve_playback_sink_state(runner=subprocess.run,
                                expect=foundation.EXPECTED_SERIAL):
    """Return the exact io24 PipeWire sink plus its current mute state."""
    completed = runner(["pw-dump"], capture_output=True, text=True)
    if completed.returncode != 0:
        raise WaveformProbeError(
            "pw-dump failed: %s" % (completed.stderr or "").strip())
    try:
        objects = json.loads(completed.stdout)
    except ValueError as error:
        raise WaveformProbeError("pw-dump output was not JSON: %s" % error)
    matches = []
    for entry in objects:
        info = entry.get("info") or {}
        props = info.get("props") or {}
        name = str(props.get("node.name") or "")
        if not str(props.get("media.class", "")).startswith("Audio/Sink"):
            continue
        if expect not in name:
            continue
        values = {}
        for item in (info.get("params") or {}).get("Props", []):
            if isinstance(item, dict):
                values.update(item)
        if "mute" not in values:
            raise WaveformProbeError(
                "io24 PipeWire sink does not expose its mute state")
        matches.append({
            "id": int(entry.get("id", props.get("object.id"))),
            "name": name,
            "muted": bool(values["mute"]),
            "soft_muted": bool(values.get("softMute", values["mute"])),
            "channel_volumes": list(values.get("channelVolumes") or []),
        })
    if not matches:
        raise WaveformProbeError(
            "no PipeWire sink carries %s" % expect)
    if len(matches) != 1:
        raise WaveformProbeError(
            "several PipeWire sinks carry %s" % expect)
    return matches[0]


def set_playback_sink_mute(expected_name, muted, runner=subprocess.run):
    """Set one exact sink mute bit and verify the same named node afterward."""
    before = resolve_playback_sink_state(runner=runner)
    if before["name"] != expected_name:
        raise WaveformProbeError(
            "io24 PipeWire sink identity changed before mute operation")
    completed = runner(
        ["wpctl", "set-mute", str(before["id"]), "1" if muted else "0"],
        capture_output=True, text=True)
    if completed.returncode != 0:
        raise WaveformProbeError(
            "wpctl set-mute failed: %s" % (completed.stderr or "").strip())
    after = resolve_playback_sink_state(runner=runner)
    if after["name"] != expected_name or after["muted"] != bool(muted):
        raise WaveformProbeError("io24 PipeWire sink mute did not verify")
    return after


def _shadow_calls(path):
    try:
        with Path(path).open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError) as error:
        raise WaveformProbeError("Host shadow is unreadable: %s" % error) from error
    if not isinstance(value, dict):
        raise WaveformProbeError("Host shadow root is not an object")
    return value


def load_exact_prior_state(path, input_channel=2):
    """Load every write-only value the live run will have to restore.

    Missing is not treated as default: the firmware cannot read these values
    back, so absence means there is no exact-restoration proof and playback is
    refused.
    """
    routes_required = required_routes(input_channel)
    calls = _shadow_calls(path)
    routes = {}
    for entry in calls.values():
        if not isinstance(entry, dict) or entry.get("fn") not in (
                "set_send_db", "set_mix_db"):
            continue
        kwargs = entry.get("kwargs")
        if not isinstance(kwargs, dict):
            continue
        key = (kwargs.get("source"), kwargs.get("bus"))
        if key in routes_required:
            routes[key] = kwargs.get("gain_db", kwargs.get("value"))
    missing = ["%s -> %s" % route for route in routes_required
               if route not in routes]
    if missing:
        raise WaveformProbeError(
            "exact restoration unavailable for: %s" % ", ".join(missing))

    fx_entry = calls.get("set_fx")
    reverb_entry = calls.get("set_reverb")
    if not isinstance(fx_entry, dict) or not isinstance(
            fx_entry.get("kwargs"), dict):
        raise WaveformProbeError("exact prior VoiceFX state is absent")
    if not isinstance(reverb_entry, dict) or not isinstance(
            reverb_entry.get("kwargs"), dict):
        raise WaveformProbeError("exact prior reverb state is absent")
    fx_kwargs = dict(fx_entry["kwargs"])
    model = str(fx_kwargs.pop("model", "")).lower()
    builder = getattr(io24_fx, "set_fx_" + model, None)
    if not model or builder is None:
        raise WaveformProbeError("prior VoiceFX model is invalid: %r" % model)
    builder(**fx_kwargs)                    # pure schema/range validation

    return {
        "source": str(path),
        "routes": routes,
        "fx": {"model": model, "kwargs": fx_kwargs},
        "reverb": dict(reverb_entry["kwargs"]),
    }


def readable_state(params):
    state = shared.readable_state(params)
    flags = state["flags"]
    state.update({
        "input1_muted": bool(flags >> 3 & 1),
        "input2_muted": bool(flags >> 4 & 1),
        "input1_slot_index": int(params["input1SlotIndex"]),
        "input2_slot_index": int(params["input2SlotIndex"]),
        "input1_gain_db": float(params["input1Gain"]),
        "input2_gain_db": float(params["input2Gain"]),
        "monitor_mix": float(params["monitorMix"]),
    })
    return state


def assert_input_guards(state, input_channel=2):
    channel = _input_channel(input_channel)
    if state["input1_phantom"] or state["input2_phantom"]:
        raise WaveformProbeError("phantom must be off on both inputs")
    if state["channel_linked"]:
        raise WaveformProbeError("stereo link must be off")
    if (state["input1_processing_channel"],
            state["input2_processing_channel"]) != (0, 1):
        raise WaveformProbeError(
            "processing-channel permutation must remain 0/1")
    if not state["input%d_processing_enabled" % channel]:
        raise WaveformProbeError(
            "Input %d processing is bypassed; the probe will not change "
            "DSP Amount" % channel)


def assert_input2_guards(state):
    """Compatibility name retained for the sealed Input-2 evidence."""
    return assert_input_guards(state, input_channel=2)


def configure_safe_path(device, input_was_muted, input_channel=2):
    """Break feedback before opening the deterministic stimulus/return path."""
    channel = _input_channel(input_channel)
    line_source = "line/ch%d" % channel
    device.set_mute(channel, True)
    device.set_send_db(line_source, "main", None)
    device.set_send_db("fxreturn/ch1", "main", None)
    device.set_gain(channel, TEST_INPUT_GAIN_DB)
    device.set_send_db("return/ch1", "main", 0.0)
    device.set_send_db("return/ch1", "mixa", None)
    device.set_send_db("fxreturn/ch1", "mixa", 0.0)
    device.set_mute(channel, bool(input_was_muted))


def restore_exact_state(device, prior, input_was_muted, input_gain_db,
                        input_channel=2):
    """Restore all changed state, reopening Main routes only while muted."""
    channel = _input_channel(input_channel)
    line_source = "line/ch%d" % channel
    device.set_mute(channel, True)
    device.set_fx(prior["fx"]["model"], **prior["fx"]["kwargs"])
    device.set_reverb(**prior["reverb"])
    device.set_gain(channel, input_gain_db)
    routes = prior["routes"]
    # Observation bus first, then the USB stimulus. Feedback legs are last.
    for route in (("return/ch1", "mixa"), ("fxreturn/ch1", "mixa"),
                  ("return/ch1", "main"), ("fxreturn/ch1", "main"),
                  (line_source, "main")):
        device.set_send_db(route[0], route[1], routes[route])
    device.set_mute(channel, bool(input_was_muted))


def _protected_readable_comparison(before, after):
    keys = (
        "input1_muted", "input2_muted", "input1_gain_db", "input2_gain_db",
        "headphone_volume", "main_volume", "monitor_mix",
        "input1_processing_channel", "input2_processing_channel",
        "input1_processing_enabled", "input2_processing_enabled",
        "channel_linked", "input1_slot_index", "input2_slot_index",
        "input1_phantom", "input2_phantom",
    )
    return {key: {"before": before[key], "after": after[key],
                  "equal": before[key] == after[key]} for key in keys}


def analyse_stage(path, input_channel=2):
    """Measure Mix A using gates aligned from the selected physical input."""
    channel = _input_channel(input_channel)
    rate, frames = shared.read_capture(path)
    if frames.shape[1] != CHANNELS:
        raise WaveformProbeError("capture is not six-channel")
    reference = frames[:, INPUT_REFERENCE_CHANNELS[channel]]
    signal = shared.bus_signal(frames, MIX_A_CHANNELS)
    bursts, alignment = shared.align_bursts(reference, rate)
    inside = shared.burst_slices(signal, bursts)
    gaps = shared.gap_slices(signal, bursts, rate)
    ref_inside = shared.burst_slices(reference, bursts)
    ref_gaps = shared.gap_slices(reference, bursts, rate)
    stage = {
        "capture": Path(path).name,
        "rate_hz": rate,
        "frames": int(frames.shape[0]),
        "reference_bursts_found": len(bursts),
        "reference_gate_alignment_score": alignment,
        "reference_burst_rms_dbfs": shared.rms_dbfs(ref_inside),
        "reference_gap_rms_dbfs": shared.rms_dbfs(ref_gaps),
        "rms_dbfs": shared.rms_dbfs(signal),
        "burst_rms_dbfs": shared.rms_dbfs(inside),
        "gap_rms_dbfs": shared.rms_dbfs(gaps),
        "channel_rms_dbfs": [shared.rms_dbfs(frames[:, index])
                             for index in range(frames.shape[1])],
        "tap_rms_dbfs": {},
        "_signal": signal,
        "_bursts": bursts,
        "_inside": inside,
        "_gaps": gaps,
    }
    for tap, segment in shared.tap_windows(signal, bursts, rate=rate).items():
        stage["tap_rms_dbfs"][str(tap)] = shared.rms_dbfs(segment)
    return stage


def analyse_stage_from_input2(path):
    """Compatibility name retained for the sealed Input-2 evidence."""
    return analyse_stage(path, input_channel=2)


def classify(stages, input_channel=2):
    channel = _input_channel(input_channel)
    required = (
        "control_off", "control_reverb", "control_off_after",
        "delay_on_1", "delay_off_1", "delay_on_2", "delay_off_2",
    )
    absent = [name for name in required if name not in stages]
    if absent:
        raise WaveformProbeError("missing capture stages: %s" % ", ".join(absent))

    baseline = stages["control_off"]
    contrast = _delta(baseline["reference_burst_rms_dbfs"],
                      baseline["reference_gap_rms_dbfs"])
    stimulus_ok = bool(
        baseline["reference_bursts_found"] >= shared.MIN_BURSTS
        and baseline["reference_burst_rms_dbfs"] is not None
        and baseline["reference_burst_rms_dbfs"] >= REFERENCE_MIN_BURST_DBFS
        and contrast is not None
        and contrast >= REFERENCE_MIN_GATE_CONTRAST_DB)

    control = shared.classify_gap_energy(
        stages["control_off"], stages["control_reverb"],
        shared.CONTROL_MIN_GAP_RISE_DB)
    cycle_1 = shared.classify_repeat_taps(
        stages["control_off_after"], stages["delay_on_1"])
    cycle_2 = shared.classify_repeat_taps(
        stages["delay_off_1"], stages["delay_on_2"])

    off_pairs = (
        ("control_off", "control_off_after"),
        ("control_off_after", "delay_off_1"),
        ("delay_off_1", "delay_off_2"),
    )
    off_drifts = {
        "%s_to_%s" % pair: _delta(
            stages[pair[1]]["gap_rms_dbfs"],
            stages[pair[0]]["gap_rms_dbfs"])
        for pair in off_pairs
    }
    off_ok = bool(all(value is not None and abs(value) <= OFF_MAX_DRIFT_DB
                      for value in off_drifts.values()))

    # Capture inputs can be configured post-DSP (the UC component model's
    # `dawpostdsp` default is post).  An insert effect is therefore allowed to
    # change the captured reference while it is on.  Diagnose physical source
    # drift only from stages where VoiceFX is off; otherwise a working effect
    # invalidates its own proof.
    reference_stability_stages = (
        "control_off", "control_reverb", "control_off_after",
        "delay_off_1", "delay_off_2",
    )
    reference_levels = [stages[name]["reference_burst_rms_dbfs"]
                        for name in reference_stability_stages]
    reference_drifts = [abs(value - reference_levels[0])
                        for value in reference_levels
                        if value is not None and reference_levels[0] is not None]
    reference_max_drift = max(reference_drifts) if reference_drifts else None
    reference_stable = bool(reference_max_drift is not None
                            and reference_max_drift <= REFERENCE_MAX_DRIFT_DB)

    run_valid = bool(stimulus_ok and control["detected"] and off_ok
                     and reference_stable)
    detected_count = sum((bool(cycle_1["detected"]),
                          bool(cycle_2["detected"])))
    if not stimulus_ok:
        status = "BLOCKED_PHYSICAL_INPUT%d_STIMULUS_UNUSABLE" % channel
    elif not control["detected"]:
        status = "INVALID_REVERB_CONTROL_NO_SHARED_RETURN_TAIL"
    elif not reference_stable:
        status = "INVALID_INPUT%d_SOURCE_DRIFTED" % channel
    elif not off_ok:
        status = "INVALID_OFF_STATE_DRIFTED"
    elif detected_count == 2:
        status = "VOICEFX_DELAY_PROCESSING_DETECTED"
    elif detected_count == 1:
        status = "INCONCLUSIVE_VOICEFX_DELAY_NOT_REPEATABLE"
    else:
        status = "NO_VOICEFX_DELAY_PROCESSING_DETECTED"
    return {
        "status": status,
        "run_valid": run_valid,
        "physical_input%d_stimulus" % channel: {
            "bursts_found": baseline["reference_bursts_found"],
            "burst_rms_dbfs": baseline["reference_burst_rms_dbfs"],
            "gap_rms_dbfs": baseline["reference_gap_rms_dbfs"],
            "gate_contrast_db": contrast,
            "maximum_burst_drift_db": reference_max_drift,
            "stability_stages": list(reference_stability_stages),
            "usable": stimulus_ok,
            "stable": reference_stable,
        },
        "reverb_control": control,
        "off_state_gap_drift_db": off_drifts,
        "off_state_held": off_ok,
        "delay_repeatability": {"cycle_1": cycle_1, "cycle_2": cycle_2},
    }


def _capture(label, output_dir, stimulus, sink, input_channel=2):
    path = shared.capture_stage(
        label, output_dir, stimulus, seconds=CAPTURE_SECONDS,
        playback_sink=sink)
    return analyse_stage(path, input_channel=input_channel)


def run_sequence(device, output_dir, stimulus, sink, input_channel=2,
                 progress=lambda _message: None):
    channel = _input_channel(input_channel)
    stages = {}

    def observe(label):
        progress("capturing %s" % label)
        time.sleep(shared.SETTLE_SECONDS)
        stages[label] = _capture(
            label, output_dir, stimulus, sink, input_channel=channel)

    progress("materializing Delay off with the corrected UC 4.7.2 sequence")
    device.set_fx("delay", on=False, **DELAY_TEST)
    device.set_reverb(on=False, size=0.1, mix=0.0, predelay=0.02,
                      hp_freq=200.0, fs=float(RATE))
    observe("control_off")

    progress("positive control: reverb on")
    device.set_reverb(**REVERB_CONTROL)
    observe("control_reverb")
    progress("positive control: reverb off")
    device.set_reverb(on=False, size=0.1, mix=0.0, predelay=0.02,
                      hp_freq=200.0, fs=float(RATE))
    observe("control_off_after")

    for cycle in (1, 2):
        progress("VoiceFX Delay on, cycle %d" % cycle)
        device.set_fx("delay", on=True, **DELAY_TEST)
        observe("delay_on_%d" % cycle)
        progress("VoiceFX Delay off, cycle %d" % cycle)
        device.set_fx("delay", on=False, **DELAY_TEST)
        observe("delay_off_%d" % cycle)
    return stages


def _strip_arrays(value):
    if isinstance(value, dict):
        return {key: _strip_arrays(item) for key, item in value.items()
                if not key.startswith("_")}
    if isinstance(value, list):
        return [_strip_arrays(item) for item in value]
    return value


def plan(input_channel=2):
    channel = _input_channel(input_channel)
    other = 1 if channel == 2 else 2
    return {
        "schema": SCHEMA,
        "rig": "Main Out L -> Input %d" % channel,
        "stimulus": {
            "shape": "gated deterministic tone plus noise",
            "rms_dbfs": shared.STIMULUS_RMS_DBFS,
            "playback_channel": 1,
        },
        "pre_playback_order": [
            "mute Input %d" % channel,
            "line/ch%d -> Main off" % channel,
            "fxreturn/ch1 -> Main off",
            "Input %d gain 60 dB while both feedback routes are off" % channel,
            "return/ch1 -> Main 0 dB",
            "return/ch1 -> Mix A off",
            "fxreturn/ch1 -> Mix A 0 dB",
            "restore prior Input %d mute state" % channel,
            "temporarily unmute only the exact io24 PipeWire sink",
        ],
        "measurement": [
            "reverb off/on/off positive control",
            "Delay on/off twice at 250 ms, feedback 0.65, wet 1.0",
            "Input %d is the timing/reference capture; Mix A is the return"
            % channel,
        ],
        "never_written": [
            "Input %d gain or Main/headphone volume" % other, "DSP Amount",
            "processingChannel", "preset slots", "phantom or link",
            "firmware, reset, or DFU",
        ],
        "restoration": (
            "exact Host shadow plus readable-state equality; restore the "
            "PipeWire sink's original mute bit first, and restore Input %d "
            "gain before device feedback routes" % channel),
    }


def run_live(output_dir, battery_path, shadow_path, input_channel=2,
             progress=lambda _message: None):
    channel = _input_channel(input_channel)
    mute_key = "input%d_muted" % channel
    gain_key = "input%d_gain_db" % channel
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise WaveformProbeError("output directory must exist and be empty")
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": _now(),
        "plan": plan(input_channel=channel),
        "device": {"serial": foundation.EXPECTED_SERIAL,
                   "bcd_device": "%04x" % foundation.EXPECTED_BCD_DEVICE},
        "cable": "MAIN_OUT_L_TO_INPUT_%d" % channel,
        "processing_channel": "UNTOUCHED_IDENTITY_0_1_REQUIRED",
        "dsp_amount": "UNTOUCHED_INPUT%d_POSITIVE_REQUIRED" % channel,
        "preset_slots": "UNTOUCHED",
    }
    device = None
    stages = {}
    before = None
    wrote = False
    sink_state = None
    sink_restore_required = False
    try:
        prior = load_exact_prior_state(shadow_path, input_channel=channel)
        report["prior_host_known_state"] = {
            "source": prior["source"],
            "routes": {"%s -> %s" % key: value
                       for key, value in prior["routes"].items()},
            "fx": prior["fx"], "reverb": prior["reverb"],
        }
        battery = foundation._battery(battery_path)
        report["battery_before"] = battery
        if battery <= foundation.BATTERY_FLOOR:
            report["status"] = "BLOCKED_BATTERY"
            return report
        stimulus = build_stimulus(output_dir / "stimulus.wav")
        sink_state = resolve_playback_sink_state()
        sink = sink_state["name"]
        report["playback_sink_before"] = sink_state
        device = foundation._open_checked()
        before = readable_state(device.read_params())
        report["readable_state_before"] = before
        assert_input_guards(before, input_channel=channel)

        progress("muting Input %d and breaking both Main feedback paths"
                 % channel)
        # Set this before the first write. A USB response-service failure can
        # happen after the device accepted a frame but before the audited
        # transport records it; that still requires the full restoration.
        wrote = True
        configure_safe_path(
            device, before[mute_key], input_channel=channel)
        time.sleep(0.35)
        guarded = readable_state(device.read_params())
        report["readable_state_guarded"] = guarded
        if guarded[mute_key] != before[mute_key]:
            raise WaveformProbeError(
                "Input %d mute did not return to prestate" % channel)
        if guarded[gain_key] != TEST_INPUT_GAIN_DB:
            raise WaveformProbeError(
                "Input %d test gain did not read back" % channel)
        report["input%d_gain_for_run_db" % channel] = guarded[gain_key]
        protected_gain = "input%d_gain_db" % (1 if channel == 2 else 2)
        for key in (protected_gain, "main_volume",
                    "headphone_volume", "monitor_mix",
                    "input1_processing_channel", "input2_processing_channel",
                    "input1_processing_enabled", "input2_processing_enabled",
                    "input1_slot_index", "input2_slot_index"):
            if guarded[key] != before[key]:
                raise WaveformProbeError("protected readable field changed: %s" % key)

        if sink_state["muted"]:
            # Mark before the command: as with USB, a host command can take
            # effect even if its verification read subsequently fails.
            sink_restore_required = True
            progress("temporarily unmuting the exact io24 PipeWire sink")
            report["playback_sink_for_run"] = set_playback_sink_mute(
                sink, False)
        else:
            report["playback_sink_for_run"] = sink_state
        stages = run_sequence(device, output_dir, stimulus, sink,
                              input_channel=channel,
                              progress=progress)
        report["verdict"] = classify(stages, input_channel=channel)
        report["status"] = report["verdict"]["status"]
    except BaseException as error:                 # noqa: BLE001 - restore on Ctrl-C
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        report["stages"] = _strip_arrays(stages)
        # Re-mute the host sink before restoring a device route that could feed
        # the physical cable. This is intentionally ahead of USB restoration.
        if sink_restore_required and sink_state is not None:
            try:
                progress("restoring the io24 PipeWire sink mute")
                report["playback_sink_restored"] = set_playback_sink_mute(
                    sink_state["name"], True)
                report["playback_sink_mute_restored"] = True
            except BaseException as error:         # noqa: BLE001
                report["playback_sink_restoration_error"] = {
                    "type": type(error).__name__, "message": str(error)}
                report["playback_sink_mute_restored"] = False
                report["status"] = "RESTORATION_FAILED"
        if device is not None:
            if wrote:
                try:
                    progress("restoring exact prior state")
                    restore_exact_state(
                        device, prior, before[mute_key], before[gain_key],
                        input_channel=channel)
                    time.sleep(0.35)
                    after = readable_state(device.read_params())
                    report["readable_state_after"] = after
                    comparison = _protected_readable_comparison(before, after)
                    report["readable_restoration"] = comparison
                    report["readable_state_matches"] = all(
                        row["equal"] for row in comparison.values())
                    report["write_only_restoration"] = {
                        "exact_host_known_values_resent": True,
                        "routes": report["prior_host_known_state"]["routes"],
                        "fx": prior["fx"], "reverb": prior["reverb"],
                    }
                    if not report["readable_state_matches"]:
                        report["status"] = "RESTORATION_FAILED"
                except BaseException as error:     # noqa: BLE001
                    report["restoration_error"] = {
                        "type": type(error).__name__, "message": str(error)}
                    report["status"] = "RESTORATION_FAILED"
            else:
                report["restoration_notes"] = [
                    "no SetP sequence began; no restoration was required"]
            report["transport"] = list(device.transport_log)
            try:
                device.close()
            except BaseException as error:         # noqa: BLE001
                report["close_error"] = {
                    "type": type(error).__name__, "message": str(error)}
                report["status"] = "RESTORATION_FAILED"
        try:
            report["battery_after"] = foundation._battery(battery_path)
        except BaseException as error:             # noqa: BLE001
            report["battery_after_error"] = str(error)
        report["finished"] = _now()
    return report


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--input-channel", type=int, choices=(1, 2), default=2)
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    parser.add_argument("--shadow-path",
                        default=str(Path.home() / ".cache" / "io24"
                                    / "shadow.json"))
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps(plan(input_channel=args.input_channel),
                         indent=2, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--execute requires --output-dir")
    report = run_live(args.output_dir, args.battery_path, args.shadow_path,
                      input_channel=args.input_channel,
                      progress=lambda message: print(message, flush=True))
    _write_json(Path(args.output_dir) / "live-report.json", report)
    summary = {key: report[key] for key in (
        "status", "battery_before", "battery_after", "error")
        if key in report}
    print(json.dumps(summary, indent=2, sort_keys=True))
    if report.get("verdict"):
        print(json.dumps(report["verdict"], indent=2, sort_keys=True))
    decisive = ("VOICEFX_DELAY_PROCESSING_DETECTED",
                "NO_VOICEFX_DELAY_PROCESSING_DETECTED")
    return 0 if report.get("status") in decisive else 1


if __name__ == "__main__":
    raise SystemExit(main())
