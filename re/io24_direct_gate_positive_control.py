#!/usr/bin/env python3
"""Positive control for the native active-slot gate null.

The 2026-09-14 active-slot probe wrote native ``MemP/Stat`` gate bodies and
measured no effect on the Main/Input-2 ratio.  That null is only decisive if
the same metric can observe a Channel-2 gate change *at all*.  PROTOCOL.md
§12Y records what happens without that check: a null was published, then voided
when the rig turned out to lack the sensitivity to see the thing it was
looking for.

This probe holds everything constant -- same device, same channel, same meter,
same window size, same gate parameters -- and changes only the WRITE ROUTE.
Instead of a native record it uses the direct ``SetP``/``gate`` setter, whose
transfer curves are already measured on this hardware.

    effect seen here  -> the meter observes Channel-2 DSP, so the native
                         null is a genuine negative about that write route
    no effect here    -> the rig was blind and the native null says nothing

Live execution requires ``--execute``.  The default invocation is hardware-free.
"""

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RE_DIR = ROOT / "re"
for path in (str(ROOT), str(RE_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

import io24  # noqa: E402
import io24_native_standard_slot_probe as common  # noqa: E402
import io24_native_gate_slot_probe as gate  # noqa: E402

SCHEMA = "io24-direct-gate-positive-control-v1"
EXPECTED_SERIAL = "AB7C22200355"
EXPECTED_VID_PID = (0x194F, 0x0422)
EXPECTED_FIRMWARE = 0x0128
MINIMUM_BATTERY_PERCENT = 11


class ControlError(RuntimeError):
    """Fail-closed error; no further device mutation is attempted."""


def _now():
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def _battery(path):
    try:
        return int(Path(path).read_text(encoding="ascii").strip())
    except (OSError, ValueError) as error:
        raise ControlError("battery unavailable: %s" % error) from error


def _readable(device):
    params = device.read_params()
    if not params:
        raise ControlError("JaSt state is unreadable")
    flags = int(params["flags"])
    return {
        "flags": flags,
        "channel_linked": bool(flags >> 12 & 1),
        "input1_gain_db": params["input1Gain"],
        "input2_gain_db": params["input2Gain"],
        "input1_slot": int(params["input1SlotIndex"]),
        "input2_slot": int(params["input2SlotIndex"]),
        "input2_processing_enabled": not bool(flags >> 6 & 1),
        "input1_processing_channel": int(params["input1ProcessingChannel"]),
        "input2_processing_channel": int(params["input2ProcessingChannel"]),
        "main_volume": params.get("mainVolume"),
        "headphone_volume": params.get("hpVolume"),
    }


def _verify_identity(device):
    handle = device.dev
    serial = getattr(handle, "serial_number", None)
    vid = getattr(handle, "idVendor", None)
    pid = getattr(handle, "idProduct", None)
    bcd = getattr(handle, "bcdDevice", None)
    if serial != EXPECTED_SERIAL or (vid, pid) != EXPECTED_VID_PID or \
            bcd != EXPECTED_FIRMWARE:
        raise ControlError(
            "unexpected unit: serial=%r vid/pid=%r/%r bcdDevice=%r"
            % (serial, vid, pid, bcd))
    return {"serial": serial, "vendor_id": "%04x" % vid,
            "product_id": "%04x" % pid, "bcd_device": "%04x" % bcd}


def run_control(device, sample_one, settle=time.sleep):
    """Measure gate off / on / off using the direct live setter only."""
    baseline = _readable(device)
    windows = []
    restored = []
    started = _now()
    try:
        # Protect the outputs and raise the preamp noise floor exactly as the
        # native probe did, so the two runs are directly comparable.
        device.set_main_volume(common.SAFE_OUTPUT_VOLUME)
        device.set_gain(common.TARGET_CHANNEL, common.PROBE_INPUT_GAIN_DB)
        settle(common.SETTLE_SECONDS)

        for label, gate_on in (("direct_gate_off_before", False),
                               ("direct_gate_on", True),
                               ("direct_gate_off_after", False)):
            if gate_on:
                device.set_gate(
                    common.TARGET_CHANNEL, on=True,
                    threshold_db=gate.GATE_THRESHOLD_DB,
                    range_db=gate.GATE_RANGE_DB,
                    attack_s=gate.GATE_ATTACK_SECONDS,
                    release_s=gate.GATE_RELEASE_SECONDS,
                    keyfilter_hz=gate.GATE_KEYFILTER_HZ,
                    expander=True, keylisten=False,
                    fs=gate.GATE_SAMPLE_RATE_HZ)
            else:
                device.gate_off(common.TARGET_CHANNEL)
            settle(common.SETTLE_SECONDS)
            windows.append({"label": label,
                            "gate_written_on": gate_on,
                            "meter": sample_one(label),
                            "readable": _readable(device)})
    finally:
        # Restore in the reverse order of disturbance. gate_off writes the
        # byte-exact firmware power-on gate state, which is a defined landing
        # point -- not a guess at whatever the channel held before.
        try:
            device.gate_off(common.TARGET_CHANNEL)
            restored.append("gate_powered_on_state")
        except Exception as error:                       # noqa: BLE001
            restored.append("gate_restore_failed:%s" % error)
        try:
            device.set_gain(common.TARGET_CHANNEL,
                            float(baseline["input2_gain_db"]))
            restored.append("input2_gain_db")
        except Exception as error:                       # noqa: BLE001
            restored.append("gain_restore_failed:%s" % error)
        if baseline.get("main_volume") is not None:
            try:
                device.set_main_volume(float(baseline["main_volume"]))
                restored.append("main_volume")
            except Exception as error:                   # noqa: BLE001
                restored.append("main_restore_failed:%s" % error)

    after = _readable(device)
    analysis = common_classify(windows)
    return {
        "schema": SCHEMA,
        "started": started,
        "finished": _now(),
        "write_route": "DIRECT_SETP_GATE_BLOB",
        "comparison_target": "native MemP/Stat active-slot gate probe",
        "observation": "SIMULTANEOUS_JAST_INPUT2_AND_MAIN_METERS",
        "stimulus": "INPUT2_PREAMP_SELF_NOISE",
        "playback": "NONE",
        "mixer_routes": "UNTOUCHED",
        "processing_channel": "UNTOUCHED",
        "target_channel": common.TARGET_CHANNEL,
        "gate": {
            "threshold_db": gate.GATE_THRESHOLD_DB,
            "range_db": gate.GATE_RANGE_DB,
            "attack_s": gate.GATE_ATTACK_SECONDS,
            "release_s": gate.GATE_RELEASE_SECONDS,
            "keyfilter_hz": gate.GATE_KEYFILTER_HZ,
            "fs": gate.GATE_SAMPLE_RATE_HZ,
        },
        "readable_before": baseline,
        "readable_after": after,
        "restored_controls": restored,
        "windows": windows,
        "analysis": analysis,
    }


def common_classify(windows):
    """Same arithmetic as the native probe, relabelled for this route."""
    off_before, active, off_after = (w["meter"] for w in windows)
    before = float(off_before["median_main_to_input2_db"])
    effect = float(active["median_main_to_input2_db"])
    after = float(off_after["median_main_to_input2_db"])
    drift = after - before
    delta = effect - (before + after) / 2.0
    uncertainty = max(float(w["mad_main_to_input2_db"])
                      for w in (off_before, active, off_after))
    stable = abs(drift) <= common.FLAT_DRIFT_MAX_DB
    detected = stable and abs(delta) >= max(
        common.EFFECT_DELTA_MIN_DB, 6.0 * uncertainty)
    return {
        "classification": (
            "DIRECT_GATE_EFFECT_DETECTED" if detected else
            "INCONCLUSIVE_BASELINE_DRIFT" if not stable else
            "NO_DIRECT_GATE_EFFECT_DETECTED"),
        "effect_delta_db": delta,
        "gate_off_drift_db": drift,
        "maximum_window_mad_db": uncertainty,
        "detection_threshold_db": max(common.EFFECT_DELTA_MIN_DB,
                                      6.0 * uncertainty),
        "stable": stable,
        "effect_detected": detected,
        "meaning": (
            "the Main/Input-2 meter observes a Channel-2 gate change, so the "
            "native active-slot null is a genuine negative about that write "
            "route" if detected else
            "the rig did not see a known-good Channel-2 gate change, so the "
            "native active-slot null cannot distinguish a failed write from "
            "a blind meter"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--battery-path", type=Path,
                        default=Path("/sys/class/power_supply/BAT0/capacity"))
    args = parser.parse_args(argv)

    plan = {
        "schema": SCHEMA,
        "status": "OFFLINE_READY",
        "write_route": "DIRECT_SETP_GATE_BLOB",
        "target_channel": common.TARGET_CHANNEL,
        "probe_input_gain_db": common.PROBE_INPUT_GAIN_DB,
        "safe_output_volume": common.SAFE_OUTPUT_VOLUME,
        "samples_per_window": common.SAMPLES_PER_WINDOW,
        "gate_threshold_db": gate.GATE_THRESHOLD_DB,
        "gate_range_db": gate.GATE_RANGE_DB,
        "writes": ["set_main_volume", "set_gain", "set_gate", "gate_off"],
        "no_native_record_written": True,
    }
    if not args.execute:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    battery = _battery(args.battery_path)
    if battery <= MINIMUM_BATTERY_PERCENT:
        print(json.dumps({"status": "BLOCKED_BATTERY",
                          "battery_percent": battery}, sort_keys=True))
        return 3

    device = io24.Io24(shadow=False)
    try:
        identity = _verify_identity(device)
        report = run_control(
            device, lambda label: common.summarize_window(device, label))
    finally:
        try:
            device.close()
        except Exception:                                # noqa: BLE001
            pass
    report["device"] = identity
    report["battery_before"] = battery
    report["battery_after"] = _battery(args.battery_path)
    report["status"] = "COMPLETED"
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
