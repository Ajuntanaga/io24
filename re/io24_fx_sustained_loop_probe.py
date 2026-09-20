#!/usr/bin/env python3
"""Does toggling block 201 change what the sustained Main loop carries?

The rig the user built is a better instrument than a played stimulus, and it
needs no playback stream at all.  Main Out L is cabled into Input 1 and
`line/ch1 -> main` is open, so the unit is running a regenerative loop that
sits at about -15 dBFS.  The Host shadow also shows `fxreturn/ch1 -> main`
already open at +6.8 dB with a fully wet 250 ms delay armed at feedback 1.0.

So block 201's output, if it reaches Main at all, is inside that loop.  A
regenerative loop is an extremely sensitive detector: a small change in loop
gain moves the equilibrium a lot, or stops the oscillation outright.  Toggling
only the `on` flag of the armed model therefore answers the whole question --
does block 201 contribute to Main? -- with no routing change whatsoever.

The shared reverb (block 202) is toggled the same way in the same run as the
positive control, because it is the one engine that has always been audible.

Writes: block 201 and block 202 only.  No mixer frame, no `'Appl'` frame, so
nothing that feeds Main is reconfigured and the user's loop gain is untouched
throughout.  Captures use the capture substream, which PipeWire leaves free;
no playback stream is opened, and no control write overlaps a capture.

Live execution requires --execute.
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

import io24_loopback_foundation as foundation  # noqa: E402
import io24_fx_shared_return_probe as shared  # noqa: E402


SCHEMA = "io24-fx-sustained-loop-ab-v1"
CAPTURE_SECONDS = 4
SETTLE_SECONDS = 2.5          # a regenerative loop needs time to re-settle
RATE = shared.RATE
CHANNELS = shared.CHANNELS

BUSES = {"input1": (0,), "input2": (1,), "mixa": (2, 3), "mixb": (4, 5)}
EFFECT_MIN_DB = 3.0           # a real contribution moves a bus by this
DRIFT_MAX_DB = 2.0            # ... and the loop itself must be steadier
CONTROL_MIN_DB = 3.0


class LoopProbeError(RuntimeError):
    """Fail closed; no further mutation is attempted."""


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def capture_stage(label, output_dir, seconds=CAPTURE_SECONDS,
                  endpoint=shared.CAPTURE_ENDPOINT, runner=subprocess.run):
    """Record the sustained loop. No write may be in flight: see the header."""
    path = Path(output_dir) / ("%s.wav" % label)
    if path.exists():
        raise LoopProbeError("capture path already exists: %s" % path)
    completed = runner(
        ["arecord", "-q", "-D", endpoint, "-t", "wav", "-f", "S32_LE",
         "-r", str(RATE), "-c", str(CHANNELS), "-d", str(seconds), str(path)],
        capture_output=True, text=True)
    if completed.returncode != 0:
        raise LoopProbeError(
            "arecord failed: %s" % (completed.stderr or "").strip())
    return path


def measure(path):
    """Every bus, in dBFS, from one capture."""
    _rate, frames = shared.read_capture(path)
    result = {"capture": Path(path).name,
              "channel_rms_dbfs": [shared.rms_dbfs(frames[:, index])
                                   for index in range(frames.shape[1])]}
    for name, channels in BUSES.items():
        result[name] = shared.rms_dbfs(shared.bus_signal(frames, channels))
    return result


def _delta(after, before):
    if after is None or before is None:
        return None
    return after - before


def compare(off, on):
    """Per-bus change between an engine's off and on states."""
    buses = {}
    for name in BUSES:
        buses[name] = {"off_dbfs": off[name], "on_dbfs": on[name],
                       "delta_db": _delta(on[name], off[name])}
    moved = [abs(value["delta_db"]) for value in buses.values()
             if value["delta_db"] is not None and value is not buses["input2"]]
    return {
        "buses": buses,
        "max_abs_delta_db": max(moved) if moved else None,
        "detected": bool(moved and max(moved) >= EFFECT_MIN_DB),
    }


def classify(stages):
    """Block 201's verdict, gated on the reverb control and on loop stability."""
    drift = {name: _delta(stages["final"][name], stages["initial"][name])
             for name in BUSES}
    usable = [abs(value) for name, value in drift.items()
              if value is not None and name != "input2"]
    steady = bool(usable and max(usable) <= DRIFT_MAX_DB)

    block201 = compare(stages["fx_off"], stages["fx_on"])
    control = compare(stages["reverb_off"], stages["reverb_on"])
    control_ok = bool(control["max_abs_delta_db"] is not None
                      and control["max_abs_delta_db"] >= CONTROL_MIN_DB)

    if not steady:
        status = "INVALID_LOOP_DRIFTED_MORE_THAN_THE_EFFECT_WINDOW"
    elif not control_ok:
        status = "INVALID_REVERB_CONTROL_DID_NOT_MOVE_THE_LOOP"
    elif block201["detected"]:
        status = "BLOCK201_CONTRIBUTES_TO_MAIN"
    else:
        status = "BLOCK201_DOES_NOT_CONTRIBUTE_TO_MAIN"
    return {
        "status": status,
        "run_valid": bool(steady and control_ok),
        "loop_drift_db": drift,
        "loop_steady": steady,
        "block201": block201,
        "reverb_control": dict(control, fired=control_ok),
    }


def run_sequence(device, output_dir, fx_call, reverb_state,
                 capture=capture_stage, measure=measure, settle=time.sleep,
                 progress=lambda _message: None, stages=None):
    """Toggle each engine's own `on` flag, and nothing else.

    Every other field of the Host-known call is resent unchanged, so the only
    variable is whether the engine is running.
    """
    stages = {} if stages is None else stages
    model, kwargs = fx_call

    def observe(label):
        progress("capturing %s" % label)
        settle(SETTLE_SECONDS)
        stages[label] = measure(capture(label, output_dir))  # noqa: F823
        return stages[label]

    observe("initial")

    progress("block 201 %s off" % model)
    device.set_fx(model, **dict(kwargs, on=False))
    observe("fx_off")
    progress("block 201 %s on" % model)
    device.set_fx(model, **dict(kwargs, on=True))
    observe("fx_on")

    progress("positive control: shared reverb off")
    device.reverb_off()
    observe("reverb_off")
    progress("positive control: shared reverb on")
    device.set_reverb(**dict(reverb_state, on=True))
    observe("reverb_on")

    observe("final")
    return stages


def run_live(output_dir, battery_path, shadow_path,
             progress=lambda _message: None):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise LoopProbeError("output directory must exist and be empty")
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": _now(),
        "device": {"serial": foundation.EXPECTED_SERIAL,
                   "bcd_device": "%04x" % foundation.EXPECTED_BCD_DEVICE},
        "rig": {
            "cable": "MAIN_OUT_L_TO_INPUT_1",
            "loop": "REGENERATIVE_VIA_LINE_CH1_TO_MAIN_USER_ESTABLISHED",
            "stimulus": "THE_LOOP_ITSELF_NO_PLAYBACK_STREAM_OPENED",
            "observation": "NATIVE_6CH_CAPTURE_OF_EVERY_BUS",
        },
        "writes": "BLOCK_201_AND_BLOCK_202_ON_FLAGS_ONLY",
        "mixer_routes": "UNTOUCHED",
        "processing_channel": "UNTOUCHED_IDENTITY_0_1_REQUIRED",
        "preset_slots": "UNTOUCHED",
    }
    device = None
    stages = {}
    try:
        prior = shared.known_prior_state(shadow_path)
        report["prior_host_known_state"] = prior
        if not prior.get("fx"):
            raise LoopProbeError(
                "the Host shadow holds no complete Voice FX call; this probe "
                "toggles the armed model and must restore it exactly")
        if not prior.get("reverb"):
            raise LoopProbeError(
                "the Host shadow holds no complete reverb call; the positive "
                "control must be restorable exactly")
        battery = foundation._battery(battery_path)
        report["battery_before"] = battery
        if battery <= foundation.BATTERY_FLOOR:
            report["status"] = "BLOCKED_BATTERY"
            return report
        device = foundation._open_checked()
        before = shared.readable_state(device.read_params())
        report["readable_state_before"] = before
        shared.assert_guards(before)

        fx_call = (prior["fx"]["model"], dict(prior["fx"]["kwargs"]))
        run_sequence(device, output_dir, fx_call, dict(prior["reverb"]),
                     progress=progress, stages=stages)
        report["verdict"] = classify(stages)
        report["status"] = report["verdict"]["status"]
    except BaseException as error:                  # noqa: BLE001 - fail closed
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        report["stages"] = stages
        if device is not None:
            if any(event.get("command") == "SetP"
                   for event in device.transport_log):
                try:
                    progress("restoring")
                    report["restoration_notes"] = shared.restore(
                        device, report.get("prior_host_known_state") or {})
                    after = shared.readable_state(device.read_params())
                    report["readable_state_after"] = after
                    report["readable_state_matches"] = after == before
                except BaseException as error:      # noqa: BLE001
                    report["restoration_error"] = {
                        "type": type(error).__name__, "message": str(error)}
                    report["status"] = "RESTORATION_FAILED"
            else:
                report["restoration_notes"] = ["nothing written"]
            report["transport"] = list(device.transport_log)
            report["transport_validation"] = shared.validate_transport_log(
                report["transport"])
            if not report["transport_validation"]["main_path_untouched"]:
                report["status"] = "SAFETY_INVARIANT_VIOLATED"
            try:
                device.close()
            except BaseException as error:          # noqa: BLE001
                report["close_error"] = {"type": type(error).__name__,
                                         "message": str(error)}
        try:
            report["battery_after"] = foundation._battery(battery_path)
        except BaseException as error:              # noqa: BLE001
            report["battery_after_error"] = str(error)
        report["finished"] = _now()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    parser.add_argument("--shadow-path",
                        default=str(Path.home() / ".cache" / "io24"
                                    / "shadow.json"))
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"schema": SCHEMA, "writes": "block 201/202 on flags",
                          "playback": "none", "stages": 6}, indent=2,
                         sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--execute requires --output-dir")
    report = run_live(args.output_dir, args.battery_path, args.shadow_path,
                      progress=lambda message: print(message, flush=True))
    with (Path(args.output_dir) / "live-report.json").open(
            "x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({key: report[key] for key in
                      ("status", "battery_before", "battery_after", "error",
                       "readable_state_matches")
                      if key in report}, indent=2, sort_keys=True))
    if report.get("verdict"):
        print(json.dumps(report["verdict"], indent=2, sort_keys=True))
    return 0 if report.get("status", "").startswith("BLOCK201_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
