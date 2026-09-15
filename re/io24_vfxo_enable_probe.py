#!/usr/bin/env python3
"""Send a correctly shaped 'VFxO' message to block 201 and measure.

12X shortlisted `'VFxO'` as the single best candidate for the missing insert-FX
enable: "block 201 accepting model coefficient blobs and producing no audio. If
it is an enable, writing it should make an already-armed model audible."

12Y tested it and reported a negative. That negative is void twice over, as 12Z
and 13 both record: the blob was built in the parameter shape
`[tag][size][index][id][value]`, so the value never landed where the handler
reads it, and the metric of the day did not cancel the source.

Nobody has since sent the shape the firmware itself uses. At fw `0x3f26e` the
firmware builds the message as three words and calls the block-201 handler
`0x553d4` directly:

    [tag 'VFxO'][size 0x0c][value 1]

and the handler agrees: `ldm r1, {r0, r1, r2}` copies exactly three words to
`object+0x2860`. Compare `'VoFx'`, which is four words and whose model is read
from `+0x0c`.

The sequence isolates `VFxO` as the only variable. A model is armed first and
measured, then `VFxO=1` is sent and the same model measured again. Ring Mod is
fully wet with `vol = 0`, so an enabled model drives both dry and wet output
gains to zero and the channel collapses.

Live execution requires ``--execute``.
"""

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import statistics
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import io24  # noqa: E402

SCHEMA = "io24-vfxo-enable-probe-v1"
TAG_VFXO = 0x5646784F
EXPECTED_SERIAL = "AB7C22200355"
EXPECTED_FIRMWARE = 0x0128
PROBE_GAIN_DB = 60.0
SAFE_MAIN_VOLUME = 0.01
SAMPLES = 40
SAMPLE_INTERVAL = 0.05
SETTLE = 0.8
DRIFT_MAX_DB = 0.75
EFFECT_MIN_DB = 1.0
MIN_BATTERY = 11

RINGMOD = {"carrier_hz": 1000.0, "dist": 0.0, "vol": 0.0,
           "carrier2": False, "carrier2_hz": 50.0, "mix": 1.0}


class ProbeError(RuntimeError):
    """Fail closed; no further mutation is attempted."""


def vfxo_blob(value):
    """The firmware's own three-word shape, from fw 0x3f26e."""
    return struct.pack("<III", TAG_VFXO, 0x0C, int(value))


def _now():
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def _identity(device):
    h = device.dev
    if getattr(h, "serial_number", None) != EXPECTED_SERIAL or \
            getattr(h, "bcdDevice", None) != EXPECTED_FIRMWARE:
        raise ProbeError("unexpected unit")
    return {"serial": h.serial_number, "bcd_device": "%04x" % h.bcdDevice}


def _state(device):
    p = device.read_params()
    if not p:
        raise ProbeError("JaSt state unreadable")
    f = int(p["flags"])
    return {"flags": f, "input1_gain_db": p["input1Gain"],
            "input2_gain_db": p["input2Gain"], "main_volume": p["mainVolume"],
            "hp_volume": p["hpVolume"],
            "input1_slot": int(p["input1SlotIndex"]),
            "input1_processing_channel": int(p["input1ProcessingChannel"])}


def window(device, label):
    ratios, srcs, outs = [], [], []
    for _ in range(SAMPLES):
        r = device.read_state()
        if r is None:
            raise ProbeError("JaSt read failed mid-window")
        v = device.floats(r)
        s = float(v[4])
        o = (float(v[12]) + float(v[13])) / 2.0
        if s <= 0.0 or o <= 0.0:
            raise ProbeError("a meter reached zero")
        srcs.append(s); outs.append(o)
        ratios.append(20.0 * math.log10(o / s))
        time.sleep(SAMPLE_INTERVAL)
    m = statistics.median(ratios)
    return {"label": label, "median_input1": statistics.median(srcs),
            "median_main": statistics.median(outs), "median_ratio_db": m,
            "mad_db": statistics.median(abs(x - m) for x in ratios)}


def compare(before, active, after, detected_name, null_name):
    b, e, a = (float(w["median_ratio_db"]) for w in (before, active, after))
    drift, delta = a - b, e - (b + a) / 2.0
    mad = max(float(w["mad_db"]) for w in (before, active, after))
    stable = abs(drift) <= DRIFT_MAX_DB
    threshold = max(EFFECT_MIN_DB, 6.0 * mad)
    detected = stable and abs(delta) >= threshold
    return {"classification": (detected_name if detected else
                               "INCONCLUSIVE_BASELINE_DRIFT" if not stable
                               else null_name),
            "effect_delta_db": delta, "drift_db": drift,
            "maximum_window_mad_db": mad,
            "detection_threshold_db": threshold,
            "stable": stable, "effect_detected": detected}


def run(device):
    base = _state(device)
    if base["input1_processing_channel"] != 0:
        raise ProbeError("Channel 1 does not own the Voice FX singleton")
    report = {"schema": SCHEMA, "started": _now(), "readable_before": base,
              "vfxo_blob_hex": vfxo_blob(1).hex(" "), "windows": {}, "writes": []}
    restored = []
    try:
        device.set_main_volume(SAFE_MAIN_VOLUME)
        device.set_gain(1, PROBE_GAIN_DB)
        device.gate_off(1)
        time.sleep(SETTLE)

        # Positive control: the rig must see Channel-1 DSP.
        control = [window(device, "control_gate_off_before")]
        device.set_gate(1, on=True, threshold_db=-40.0, range_db=-84.0,
                        attack_s=0.005, release_s=0.05, keyfilter_hz=20.0,
                        expander=True, keylisten=False, fs=48000.0)
        time.sleep(SETTLE)
        control.append(window(device, "control_gate_on"))
        device.gate_off(1)
        time.sleep(SETTLE)
        control.append(window(device, "control_gate_off_after"))
        report["windows"]["positive_control"] = control
        report["positive_control"] = compare(
            *control, "DIRECT_GATE_EFFECT_DETECTED", "NO_DIRECT_GATE_EFFECT")

        # Arm the model, with VFxO untouched.
        device.set_fx("ringmod", on=True, **RINGMOD)
        report["writes"].append("set_fx ringmod on")
        time.sleep(SETTLE)
        armed_before = window(device, "armed_vfxo_untouched")

        # The single variable: a correctly shaped VFxO = 1.
        device._dsp(io24.SETP, 201, 0, vfxo_blob(1))
        report["writes"].append("VFxO=1")
        time.sleep(SETTLE)
        armed_enabled = window(device, "armed_vfxo_1")

        device._dsp(io24.SETP, 201, 0, vfxo_blob(0))
        report["writes"].append("VFxO=0")
        time.sleep(SETTLE)
        armed_after = window(device, "armed_vfxo_0")

        report["windows"]["vfxo"] = [armed_before, armed_enabled, armed_after]
        report["vfxo"] = compare(armed_before, armed_enabled, armed_after,
                                 "VFXO_ENABLE_EFFECT_DETECTED",
                                 "NO_VFXO_ENABLE_EFFECT_DETECTED")
    finally:
        for label, action in (
                ("vfxo_zero", lambda: device._dsp(io24.SETP, 201, 0, vfxo_blob(0))),
                ("ringmod_off", lambda: device.set_fx("ringmod", on=False, **RINGMOD)),
                ("gate_power_on", lambda: device.gate_off(1)),
                ("input1_gain", lambda: device.set_gain(1, float(base["input1_gain_db"]))),
                ("main_volume", lambda: device.set_main_volume(float(base["main_volume"])))):
            try:
                action(); restored.append(label)
            except Exception as error:                     # noqa: BLE001
                restored.append("%s_failed:%s" % (label, error))
    report["restored"] = restored
    report["readable_after"] = _state(device)
    report["finished"] = _now()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--battery-path", type=Path,
                        default=Path("/sys/class/power_supply/BAT0/capacity"))
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": SCHEMA, "status": "OFFLINE_READY",
            "vfxo_blob_hex": vfxo_blob(1).hex(" "),
            "vfxo_layout": "[tag 'VFxO'][size 0x0c][value] -- fw 0x3f26e",
            "contrast_vofx": "[tag 'VoFx'][size 0x10][index][model] -- 4 words",
            "sequence": ["gate positive control",
                         "arm ringmod fully wet vol=0, VFxO untouched",
                         "VFxO=1", "VFxO=0"],
            "writes": ["set_main_volume", "set_gain", "gate_off", "set_gate",
                       "set_fx", "SetP block 201 VFxO"],
        }, indent=2, sort_keys=True))
        return 0
    battery = int(args.battery_path.read_text(encoding="ascii").strip())
    if battery <= MIN_BATTERY:
        print(json.dumps({"status": "BLOCKED_BATTERY", "battery": battery}))
        return 3
    device = io24.Io24(shadow=False)
    try:
        ident = _identity(device)
        report = run(device)
    finally:
        try:
            device.close()
        except Exception:                                  # noqa: BLE001
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
