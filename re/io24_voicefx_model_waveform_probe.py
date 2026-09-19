#!/usr/bin/env python3
"""Verify every VoiceFX model except the already-proven Delay on hardware.

The rig and safety envelope are inherited from ``io24_voicefx_waveform_probe``:
Main Out L returns through physical Input 1 (or 2), the input capture provides
the gate reference, and Mix A observes only the VoiceFX return.  Every model is
fully materialized while off, then independently toggled on/off twice.  A
reverb tail is the in-run positive control.

Without ``--execute`` this command only prints its plan.
"""

import argparse
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RE_DIR = Path(__file__).resolve().parent
for _directory in (ROOT, RE_DIR):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import io24_fx  # noqa: E402
import io24_voicefx_waveform_probe as base  # noqa: E402
import io24_fx_shared_return_probe as shared  # noqa: E402


SCHEMA = "io24-voicefx-model-waveform-probe-v1"
RATE = base.RATE
CAPTURE_SECONDS = base.CAPTURE_SECONDS

# Exact UC XML control names mapped to the recovered protocol builders.  Delay
# is absent because the same physical rig already proved it twice at 250 ms.
MODEL_PROFILES = {
    "transformer": {"lows": 1.0, "width": 1.0, "mix": 1.0,
                    "fs": float(RATE)},
    "detuner": {"detune": 0, "mix": 1.0, "fs": float(RATE)},
    "vocoder": {"carrier_type": 1, "carrier_freq": 220.0,
                "vol": 1.0, "mix": 1.0, "fs": float(RATE)},
    "ringmod": {"carrier_hz": 313.7, "dist": 0.0, "vol": 1.0,
                "carrier2": False, "carrier2_hz": 50.0, "mix": 1.0},
    "filters": {"pitch": 0.5, "regeneration": 1.0, "damping": 0.0,
                "distortion": 0.0, "volume": 1.0, "mix": 1.0},
}

SHAPE_LOW_HZ = 60.0
SHAPE_HIGH_HZ = 12000.0
SHAPE_BANDS = 64
SHAPE_MIN_DISTANCE_DB = 2.0
SHAPE_DRIFT_MARGIN_DB = 1.5
OFF_BURST_MAX_DRIFT_DB = 2.0
DETUNER_MIN_RISE_DB = 12.0
DETUNER_MIN_PROMINENCE_DB = 10.0
DETUNER_GUARD_OFFSET_HZ = 40.0


class ModelProbeError(base.WaveformProbeError):
    """Fail closed before playback whenever a premise is missing."""


def _delta(after, before):
    if after is None or before is None:
        return None
    return after - before


def _spectral_profile(stage, bands=SHAPE_BANDS):
    """Return a gain-normalized log-band profile in dB."""
    freqs = stage.get("_freqs")
    mags = stage.get("_mags")
    if freqs is None or mags is None:
        raise ModelProbeError("stage has no analysable burst spectrum")
    freqs = np.asarray(freqs, dtype=np.float64)
    mags = np.asarray(mags, dtype=np.float64)
    edges = np.geomspace(SHAPE_LOW_HZ, SHAPE_HIGH_HZ, bands + 1)
    values = []
    for index, (low, high) in enumerate(zip(edges[:-1], edges[1:])):
        inclusive = freqs <= high if index == bands - 1 else freqs < high
        mask = (freqs >= low) & inclusive
        if mask.any():
            power = float(np.mean(np.square(mags[mask])))
        else:
            centre = math.sqrt(low * high)
            nearest = int(np.argmin(np.abs(freqs - centre)))
            power = float(mags[nearest] ** 2)
        values.append(10.0 * math.log10(max(power, 1e-24)))
    profile = np.asarray(values, dtype=np.float64)
    return profile - float(np.median(profile))


def spectral_shape_distance(first, second):
    """RMS dB distance after removing broadband gain."""
    delta = _spectral_profile(second) - _spectral_profile(first)
    return float(np.sqrt(np.mean(np.square(delta))))


def classify_shape_repeatability(off_stages, on_stages):
    """Require the same spectral change twice and stable intervening offs."""
    if len(off_stages) != 3 or len(on_stages) != 2:
        raise ModelProbeError("shape vote requires three offs and two ons")
    off_distances = [
        spectral_shape_distance(off_stages[0], off_stages[1]),
        spectral_shape_distance(off_stages[1], off_stages[2]),
        spectral_shape_distance(off_stages[0], off_stages[2]),
    ]
    off_max = max(off_distances)
    threshold = max(SHAPE_MIN_DISTANCE_DB,
                    off_max + SHAPE_DRIFT_MARGIN_DB)
    cycles = []
    for off, on in zip(off_stages[:2], on_stages):
        distance = spectral_shape_distance(off, on)
        cycles.append({"distance_db": distance, "threshold_db": threshold,
                       "detected": bool(distance >= threshold)})
    return {
        "metric": "gain_normalized_log_band_rms_db",
        "off_state_distances_db": off_distances,
        "maximum_off_state_distance_db": off_max,
        "threshold_db": threshold,
        "cycle_1": cycles[0],
        "cycle_2": cycles[1],
        "detected": bool(all(cycle["detected"] for cycle in cycles)),
    }


def classify_detuner_signature(off, on):
    """Detect both stimulus tones at the programmed -8-semitone ratio.

    A de-tuner legitimately redistributes the whole spectrum, so the older
    generic test's requirement that one distant guard rise by at most 3 dB is
    not appropriate here.  The discriminating facts are that both predicted
    frequency bins rise strongly and become isolated local peaks.
    """
    if off.get("_freqs") is None or on.get("_freqs") is None:
        return {"ratio": shared.DETUNE_RATIO, "tones": [],
                "inconclusive": True, "detected": False,
                "reason": "no analysable burst content"}
    tones = []
    for source_hz in shared.STIMULUS_TONES:
        shifted_hz = source_hz * shared.DETUNE_RATIO
        before = shared.band_dbfs(off["_freqs"], off["_mags"], shifted_hz)
        after = shared.band_dbfs(on["_freqs"], on["_mags"], shifted_hz)
        guards = []
        for guard_hz in (shifted_hz - DETUNER_GUARD_OFFSET_HZ,
                         shifted_hz + DETUNER_GUARD_OFFSET_HZ):
            guards.append({
                "hz": guard_hz,
                "on_dbfs": shared.band_dbfs(
                    on["_freqs"], on["_mags"], guard_hz),
            })
        usable_guards = [row["on_dbfs"] for row in guards
                         if row["on_dbfs"] is not None]
        rise = _delta(after, before)
        prominence = (after - max(usable_guards)
                      if after is not None and usable_guards else None)
        detected = bool(
            rise is not None and rise >= DETUNER_MIN_RISE_DB
            and prominence is not None
            and prominence >= DETUNER_MIN_PROMINENCE_DB)
        tones.append({
            "source_hz": source_hz,
            "shifted_hz": shifted_hz,
            "off_dbfs": before,
            "on_dbfs": after,
            "delta_db": rise,
            "guards": guards,
            "prominence_db": prominence,
            "detected": detected,
        })
    return {"ratio": shared.DETUNE_RATIO, "tones": tones,
            "inconclusive": False,
            "detected": bool(tones and all(row["detected"] for row in tones))}


def analyse_stage(path, input_channel=1):
    """Add burst spectrum to the proven physical-input analysis."""
    stage = base.analyse_stage(path, input_channel=input_channel)
    inside = stage["_inside"]
    if inside.size >= 1024:
        freqs, mags = shared.spectrum(inside, stage["rate_hz"])
        stage["_freqs"], stage["_mags"] = freqs, mags
        stage["dominant_partial"] = shared.dominant_partial(freqs, mags)
    else:
        stage["_freqs"] = stage["_mags"] = None
        stage["dominant_partial"] = {"hz": None, "dbfs": None}
    return stage


def _capture(label, output_dir, stimulus, sink, input_channel=1):
    path = shared.capture_stage(
        label, output_dir, stimulus, seconds=CAPTURE_SECONDS,
        playback_sink=sink)
    return analyse_stage(path, input_channel=input_channel)


def run_sequence(device, output_dir, stimulus, sink, input_channel=1,
                 progress=lambda _message: None, capture=None,
                 settle=time.sleep):
    """Positive control, then two independent on/off cycles per model."""
    capture = _capture if capture is None else capture
    stages = {}

    def observe(label):
        progress("capturing %s" % label)
        settle(shared.SETTLE_SECONDS)
        stages[label] = capture(
            label, output_dir, stimulus, sink, input_channel=input_channel)

    # Use the already-proven Delay bypass for the rig control, keeping every
    # remaining model's selection sequence identical and independently auditable.
    device.set_fx("delay", on=False, **base.DELAY_TEST)
    device.set_reverb(on=False, size=0.1, mix=0.0, predelay=0.02,
                      hp_freq=200.0, fs=float(RATE))
    observe("control_off")
    progress("positive control: reverb on")
    device.set_reverb(**base.REVERB_CONTROL)
    observe("control_reverb")
    progress("positive control: reverb off")
    device.set_reverb(on=False, size=0.1, mix=0.0, predelay=0.02,
                      hp_freq=200.0, fs=float(RATE))
    observe("control_off_after")

    for model, profile in MODEL_PROFILES.items():
        progress("materializing %s off" % model)
        device.set_fx(model, on=False, **profile)
        observe(model + "_off_0")
        for cycle in (1, 2):
            progress("VoiceFX %s on, cycle %d" % (model, cycle))
            device.set_fx(model, on=True, **profile)
            observe("%s_on_%d" % (model, cycle))
            progress("VoiceFX %s off, cycle %d" % (model, cycle))
            device.set_fx(model, on=False, **profile)
            observe("%s_off_%d" % (model, cycle))
    return stages


def _model_stages(stages, model):
    return (
        [stages[model + "_off_0"], stages[model + "_off_1"],
         stages[model + "_off_2"]],
        [stages[model + "_on_1"], stages[model + "_on_2"]],
    )


def _exact_signature(model, offs, ons):
    """Return model-specific evidence where the stimulus permits it."""
    if model == "detuner":
        cycles = [classify_detuner_signature(off, on)
                  for off, on in zip(offs[:2], ons)]
        return {"kind": "two_tone_minus_8_semitone_partners", "cycles": cycles,
                "detected": bool(all(row["detected"] for row in cycles))}
    if model == "ringmod":
        cycles = []
        carrier = MODEL_PROFILES[model]["carrier_hz"]
        for off, on in zip(offs[:2], ons):
            partial = off["dominant_partial"]["hz"]
            cycles.append(shared.classify_sidebands(off, on, partial, carrier))
        return {"kind": "carrier_sidebands", "cycles": cycles,
                "detected": bool(all(row["detected"] for row in cycles))}
    if model == "filters":
        cycles = [shared.classify_gap_energy(off, on, 4.0)
                  for off, on in zip(offs[:2], ons)]
        return {"kind": "resonant_gap_tail", "cycles": cycles,
                "detected": bool(all(row["detected"] for row in cycles))}
    return None


def classify(stages, input_channel=1):
    channel = base._input_channel(input_channel)
    required = ["control_off", "control_reverb", "control_off_after"]
    for model in MODEL_PROFILES:
        required.extend((model + "_off_0", model + "_on_1",
                         model + "_off_1", model + "_on_2",
                         model + "_off_2"))
    absent = [name for name in required if name not in stages]
    if absent:
        raise ModelProbeError("missing capture stages: %s" % ", ".join(absent))

    baseline = stages["control_off"]
    contrast = _delta(baseline["reference_burst_rms_dbfs"],
                      baseline["reference_gap_rms_dbfs"])
    stimulus_ok = bool(
        baseline["reference_bursts_found"] >= shared.MIN_BURSTS
        and baseline["reference_burst_rms_dbfs"] is not None
        and baseline["reference_burst_rms_dbfs"] >= base.REFERENCE_MIN_BURST_DBFS
        and contrast is not None
        and contrast >= base.REFERENCE_MIN_GATE_CONTRAST_DB)
    control = shared.classify_gap_energy(
        stages["control_off"], stages["control_reverb"],
        shared.CONTROL_MIN_GAP_RISE_DB)

    # The physical-input USB sends are post-DSP.  Only off stages diagnose
    # source stability; an armed effect is allowed to change its own reference.
    off_names = ["control_off", "control_reverb", "control_off_after"]
    for model in MODEL_PROFILES:
        off_names.extend((model + "_off_0", model + "_off_1",
                          model + "_off_2"))
    reference_levels = [stages[name]["reference_burst_rms_dbfs"]
                        for name in off_names]
    reference_levels = [value for value in reference_levels if value is not None]
    reference_drift = ((max(reference_levels) - min(reference_levels))
                       if reference_levels else None)
    reference_stable = bool(reference_drift is not None
                            and reference_drift <= base.REFERENCE_MAX_DRIFT_DB)
    off_bursts = [stages[name]["burst_rms_dbfs"] for name in off_names
                  if name != "control_reverb"
                  and stages[name]["burst_rms_dbfs"] is not None]
    off_burst_drift = ((max(off_bursts) - min(off_bursts))
                       if off_bursts else None)
    off_stable = bool(off_burst_drift is not None
                      and off_burst_drift <= OFF_BURST_MAX_DRIFT_DB)

    models = {}
    for model in MODEL_PROFILES:
        offs, ons = _model_stages(stages, model)
        shape = classify_shape_repeatability(offs, ons)
        exact = _exact_signature(model, offs, ons)
        if model in ("detuner", "ringmod"):
            detected = bool(exact and exact["detected"])
        elif model == "filters":
            detected = bool(shape["detected"] or (exact and exact["detected"]))
        else:
            detected = bool(shape["detected"])
        models[model] = {
            "profile": MODEL_PROFILES[model],
            "shape": shape,
            "exact_signature": exact,
            "processing_detected": detected,
        }

    run_valid = bool(stimulus_ok and control["detected"]
                     and reference_stable and off_stable)
    detected = sorted(name for name, row in models.items()
                      if row["processing_detected"])
    missing = sorted(set(MODEL_PROFILES) - set(detected))
    if not stimulus_ok:
        status = "BLOCKED_PHYSICAL_INPUT%d_STIMULUS_UNUSABLE" % channel
    elif not control["detected"]:
        status = "INVALID_REVERB_CONTROL_NO_SHARED_RETURN_TAIL"
    elif not reference_stable:
        status = "INVALID_INPUT%d_SOURCE_DRIFTED" % channel
    elif not off_stable:
        status = "INVALID_OFF_STATE_DRIFTED"
    elif not missing:
        status = "VOICEFX_REMAINING_MODELS_PROCESSING_DETECTED"
    elif detected:
        status = "VOICEFX_MODELS_PARTIAL"
    else:
        status = "NO_REMAINING_VOICEFX_PROCESSING_DETECTED"
    return {
        "status": status,
        "run_valid": run_valid,
        "physical_input%d_stimulus" % channel: {
            "bursts_found": baseline["reference_bursts_found"],
            "burst_rms_dbfs": baseline["reference_burst_rms_dbfs"],
            "gap_rms_dbfs": baseline["reference_gap_rms_dbfs"],
            "gate_contrast_db": contrast,
            "maximum_off_stage_drift_db": reference_drift,
            "usable": stimulus_ok,
            "stable": reference_stable,
        },
        "reverb_control": control,
        "off_state_burst_drift_db": off_burst_drift,
        "off_state_held": off_stable,
        "models": models,
        "detected_models": detected,
        "missing_models": missing,
    }


def plan(input_channel=1):
    channel = base._input_channel(input_channel)
    value = base.plan(input_channel=channel)
    value.update({
        "schema": SCHEMA,
        "measurement": [
            "reverb off/on/off positive control",
            "fully materialize each remaining model while off",
            "toggle each model on/off twice with its own XML On control",
            "Input %d is the post-DSP timing reference; Mix A is the return"
            % channel,
        ],
        "models": MODEL_PROFILES,
        "already_proven_separately": "delay",
    })
    return value


def run_live(output_dir, battery_path, shadow_path, input_channel=1,
             progress=lambda _message: None):
    """Run inside the prior probe's exact-restoration safety envelope."""
    channel = base._input_channel(input_channel)
    mute_key = "input%d_muted" % channel
    gain_key = "input%d_gain_db" % channel
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise ModelProbeError("output directory must exist and be empty")
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": base._now(),
        "plan": plan(input_channel=channel),
        "device": {"serial": base.foundation.EXPECTED_SERIAL,
                   "bcd_device": "%04x" % base.foundation.EXPECTED_BCD_DEVICE},
        "cable": "MAIN_OUT_L_TO_INPUT_%d" % channel,
        "processing_channel": "UNTOUCHED_IDENTITY_0_1_REQUIRED",
        "dsp_amount": "UNTOUCHED_INPUT%d_POSITIVE_REQUIRED" % channel,
        "preset_slots": "UNTOUCHED",
    }
    device = None
    stages = {}
    before = None
    prior = None
    wrote = False
    sink_state = None
    sink_restore_required = False
    try:
        prior = base.load_exact_prior_state(shadow_path, input_channel=channel)
        report["prior_host_known_state"] = {
            "source": prior["source"],
            "routes": {"%s -> %s" % key: value
                       for key, value in prior["routes"].items()},
            "fx": prior["fx"], "reverb": prior["reverb"],
        }
        battery = base.foundation._battery(battery_path)
        report["battery_before"] = battery
        if battery <= base.foundation.BATTERY_FLOOR:
            report["status"] = "BLOCKED_BATTERY"
            return report
        stimulus = base.build_stimulus(output_dir / "stimulus.wav")
        sink_state = base.resolve_playback_sink_state()
        sink = sink_state["name"]
        report["playback_sink_before"] = sink_state
        device = base.foundation._open_checked()
        before = base.readable_state(device.read_params())
        report["readable_state_before"] = before
        base.assert_input_guards(before, input_channel=channel)

        progress("muting Input %d and breaking both Main feedback paths"
                 % channel)
        wrote = True
        base.configure_safe_path(device, before[mute_key], input_channel=channel)
        time.sleep(0.35)
        guarded = base.readable_state(device.read_params())
        report["readable_state_guarded"] = guarded
        if guarded[mute_key] != before[mute_key]:
            raise ModelProbeError("Input %d mute did not return to prestate"
                                  % channel)
        if guarded[gain_key] != base.TEST_INPUT_GAIN_DB:
            raise ModelProbeError("Input %d test gain did not read back" % channel)
        report["input%d_gain_for_run_db" % channel] = guarded[gain_key]
        protected_gain = "input%d_gain_db" % (1 if channel == 2 else 2)
        for key in (protected_gain, "main_volume", "headphone_volume",
                    "monitor_mix", "input1_processing_channel",
                    "input2_processing_channel", "input1_processing_enabled",
                    "input2_processing_enabled", "input1_slot_index",
                    "input2_slot_index"):
            if guarded[key] != before[key]:
                raise ModelProbeError("protected readable field changed: %s" % key)

        if sink_state["muted"]:
            sink_restore_required = True
            progress("temporarily unmuting the exact io24 PipeWire sink")
            report["playback_sink_for_run"] = base.set_playback_sink_mute(
                sink, False)
        else:
            report["playback_sink_for_run"] = sink_state
        stages = run_sequence(device, output_dir, stimulus, sink,
                              input_channel=channel, progress=progress)
        report["verdict"] = classify(stages, input_channel=channel)
        report["status"] = report["verdict"]["status"]
    except BaseException as error:  # noqa: BLE001 - restore on Ctrl-C too
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        report["stages"] = base._strip_arrays(stages)
        if sink_restore_required and sink_state is not None:
            try:
                progress("restoring the io24 PipeWire sink mute")
                report["playback_sink_restored"] = base.set_playback_sink_mute(
                    sink_state["name"], True)
                report["playback_sink_mute_restored"] = True
            except BaseException as error:  # noqa: BLE001
                report["playback_sink_restoration_error"] = {
                    "type": type(error).__name__, "message": str(error)}
                report["playback_sink_mute_restored"] = False
                report["status"] = "RESTORATION_FAILED"
        if device is not None:
            if wrote and prior is not None and before is not None:
                try:
                    progress("restoring exact prior state")
                    base.restore_exact_state(
                        device, prior, before[mute_key], before[gain_key],
                        input_channel=channel)
                    time.sleep(0.35)
                    after = base.readable_state(device.read_params())
                    report["readable_state_after"] = after
                    comparison = base._protected_readable_comparison(before, after)
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
                except BaseException as error:  # noqa: BLE001
                    report["restoration_error"] = {
                        "type": type(error).__name__, "message": str(error)}
                    report["status"] = "RESTORATION_FAILED"
            report["transport"] = list(device.transport_log)
            try:
                device.close()
            except BaseException as error:  # noqa: BLE001
                report["close_error"] = {
                    "type": type(error).__name__, "message": str(error)}
                report["status"] = "RESTORATION_FAILED"
        try:
            report["battery_after"] = base.foundation._battery(battery_path)
        except BaseException as error:  # noqa: BLE001
            report["battery_after_error"] = str(error)
        report["finished"] = base._now()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--input-channel", type=int, choices=(1, 2), default=1)
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
    base._write_json(Path(args.output_dir) / "live-report.json", report)
    summary = {key: report[key] for key in (
        "status", "battery_before", "battery_after", "error")
        if key in report}
    print(json.dumps(summary, indent=2, sort_keys=True))
    if report.get("verdict"):
        print(json.dumps(report["verdict"], indent=2, sort_keys=True))
    return 0 if report.get("verdict", {}).get("run_valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
