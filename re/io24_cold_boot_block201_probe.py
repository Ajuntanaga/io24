#!/usr/bin/env python3
"""Does a direct block-201 write do anything on a freshly booted unit?

12S reported block 201 inert from a cold boot. That result has steered CP34
ever since. It now conflicts with the firmware: constructor 0x591bc satisfies
all three gate conditions, so the gate is open from boot.

This re-runs 12S's question with the rig that is known to work -- the same
Main-to-input ratio that resolved a Channel-2 gate change at about 28 dB.

Minimal touch by design. It reads which channel owns the singleton Voice FX
rather than assigning it, because the assignment is permutation-sensitive and
would itself be a state change. The only writes are main volume, one preamp
gain, and the block-201 model itself.

Model: delay, fully wet, maximum feedback. The blob stores feedback/2, so a
requested 1.0 is a 0.5 loop gain and a sustained input should settle about
6 dB up -- comfortably above the detector's threshold. A delay at unity
feedback would not change level on stationary noise, which is why feedback
matters here.

Live execution requires --execute.
"""

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import io24  # noqa: E402

SCHEMA = "io24-cold-boot-block201-probe-v1"
EXPECTED_SERIAL = "AB7C22200355"
EXPECTED_VID_PID = (0x194F, 0x0422)
EXPECTED_FIRMWARE = 0x0128
PROBE_GAIN_DB = 60.0
SAFE_MAIN_VOLUME = 0.01
SAMPLES = 40
SAMPLE_INTERVAL = 0.05
SETTLE = 0.6
DRIFT_MAX_DB = 0.75
EFFECT_MIN_DB = 1.0
MIN_BATTERY = 11


class ProbeError(RuntimeError):
    """Fail closed; no further mutation is attempted."""


def _now():
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def _identity(device):
    h = device.dev
    serial = getattr(h, "serial_number", None)
    vid, pid = getattr(h, "idVendor", None), getattr(h, "idProduct", None)
    bcd = getattr(h, "bcdDevice", None)
    if serial != EXPECTED_SERIAL or (vid, pid) != EXPECTED_VID_PID or \
            bcd != EXPECTED_FIRMWARE:
        raise ProbeError("unexpected unit: %r %r/%r %r" % (serial, vid, pid, bcd))
    return {"serial": serial, "vendor_id": "%04x" % vid,
            "product_id": "%04x" % pid, "bcd_device": "%04x" % bcd}


def _state(device):
    p = device.read_params()
    if not p:
        raise ProbeError("JaSt state unreadable")
    flags = int(p["flags"])
    return {
        "flags": flags,
        "input1_gain_db": p["input1Gain"], "input2_gain_db": p["input2Gain"],
        "input1_slot": int(p["input1SlotIndex"]),
        "input2_slot": int(p["input2SlotIndex"]),
        "input1_processing_channel": int(p["input1ProcessingChannel"]),
        "input2_processing_channel": int(p["input2ProcessingChannel"]),
        "input1_processing_enabled": not bool(flags >> 5 & 1),
        "input2_processing_enabled": not bool(flags >> 6 & 1),
        "main_volume": p["mainVolume"], "hp_volume": p["hpVolume"],
    }


def voicefx_owner(state):
    """UC treats the chain whose processing value is 0 as the Voice FX owner."""
    if state["input1_processing_channel"] == 0:
        return 1
    if state["input2_processing_channel"] == 0:
        return 2
    raise ProbeError("no chain reports processing channel 0")


def window(device, label, source_slot):
    ratios, sources, outputs = [], [], []
    for _ in range(SAMPLES):
        response = device.read_state()
        if response is None:
            raise ProbeError("JaSt read failed mid-window")
        v = device.floats(response)
        source = float(v[source_slot])
        output = (float(v[12]) + float(v[13])) / 2.0
        if source <= 0.0 or output <= 0.0:
            raise ProbeError("a meter reached zero")
        sources.append(source); outputs.append(output)
        ratios.append(20.0 * math.log10(output / source))
        time.sleep(SAMPLE_INTERVAL)
    median = statistics.median(ratios)
    return {"label": label, "samples": SAMPLES,
            "median_source": statistics.median(sources),
            "median_main": statistics.median(outputs),
            "median_ratio_db": median,
            "mad_db": statistics.median(abs(r - median) for r in ratios),
            "min_db": min(ratios), "max_db": max(ratios)}


def classify(before, active, after):
    b, e, a = (float(w["median_ratio_db"]) for w in (before, active, after))
    drift = a - b
    delta = e - (b + a) / 2.0
    mad = max(float(w["mad_db"]) for w in (before, active, after))
    stable = abs(drift) <= DRIFT_MAX_DB
    threshold = max(EFFECT_MIN_DB, 6.0 * mad)
    detected = stable and abs(delta) >= threshold
    return {
        "classification": ("COLD_BOOT_BLOCK201_EFFECT_DETECTED" if detected
                           else "INCONCLUSIVE_BASELINE_DRIFT" if not stable
                           else "NO_COLD_BOOT_BLOCK201_EFFECT_DETECTED"),
        "effect_delta_db": delta, "drift_db": drift,
        "maximum_window_mad_db": mad, "detection_threshold_db": threshold,
        "stable": stable, "effect_detected": detected,
    }


def run(device, model, kwargs):
    base = _state(device)
    owner = voicefx_owner(base)
    source_slot = 4 if owner == 1 else 6
    report = {"schema": SCHEMA, "started": _now(),
              "voicefx_owner_channel": owner, "source_meter_slot": source_slot,
              "model": model, "model_kwargs": dict(kwargs),
              "readable_before": base, "writes": [], "windows": []}
    restored = []
    try:
        device.set_main_volume(SAFE_MAIN_VOLUME); report["writes"].append("set_main_volume")
        device.set_gain(owner, PROBE_GAIN_DB); report["writes"].append("set_gain")
        time.sleep(SETTLE)
        report["windows"].append(window(device, "cold_boot_baseline", source_slot))
        device.set_fx(model, on=True, **kwargs); report["writes"].append("set_fx on")
        time.sleep(SETTLE)
        report["windows"].append(window(device, "block201_armed", source_slot))
        device.set_fx(model, on=False, **kwargs); report["writes"].append("set_fx off")
        time.sleep(SETTLE)
        report["windows"].append(window(device, "block201_off", source_slot))
    finally:
        try:
            device.set_gain(owner, float(base["input%d_gain_db" % owner]))
            restored.append("preamp_gain")
        except Exception as error:                        # noqa: BLE001
            restored.append("gain_restore_failed:%s" % error)
        try:
            device.set_main_volume(float(base["main_volume"]))
            restored.append("main_volume")
        except Exception as error:                        # noqa: BLE001
            restored.append("main_restore_failed:%s" % error)
    report["restored"] = restored
    report["readable_after"] = _state(device)
    if len(report["windows"]) == 3:
        report["analysis"] = classify(*report["windows"])
    report["finished"] = _now()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--model", default="delay")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--battery-path", type=Path,
                        default=Path("/sys/class/power_supply/BAT0/capacity"))
    args = parser.parse_args(argv)

    presets = {
        "delay": {"time_s": 0.25, "feedback": 1.0, "mix": 1.0},
        "filters": {"pitch": 0.05, "regeneration": 0.9, "damping": 0.1, "mix": 1.0},
        "ringmod": {"carrier_hz": 220.0, "dist": 0.0, "vol": 1.0, "mix": 1.0},
    }
    if args.model not in presets:
        raise SystemExit("unknown model %r" % args.model)
    kwargs = presets[args.model]

    if not args.execute:
        print(json.dumps({"schema": SCHEMA, "status": "OFFLINE_READY",
                          "model": args.model, "model_kwargs": kwargs,
                          "writes": ["set_main_volume", "set_gain", "set_fx"],
                          "reads_ownership_never_assigns": True},
                         indent=2, sort_keys=True))
        return 0

    battery = int(args.battery_path.read_text(encoding="ascii").strip())
    if battery <= MIN_BATTERY:
        print(json.dumps({"status": "BLOCKED_BATTERY", "battery": battery}))
        return 3

    device = io24.Io24(shadow=False)
    try:
        ident = _identity(device)
        report = run(device, args.model, kwargs)
    finally:
        try:
            device.close()
        except Exception:                                 # noqa: BLE001
            pass
    report["device"] = ident
    report["battery_before"] = battery
    report["battery_after"] = int(args.battery_path.read_text(encoding="ascii").strip())
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
