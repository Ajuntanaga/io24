#!/usr/bin/env python3
"""Bounded 96 kHz/512 smoke for Host-only io24 features.

The live part publishes the passive Mix A/B sources and starts/stops the
Multiband insert without changing the device's write-only mixer. Main and
headphone outputs are attenuated first. Auto Gain's actual clip decision is
sent to the readable preamp and restored. Solo remains hardware-free because
the current shadow does not contain every write-only send that Solo rewrites.
"""

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RE_DIR = Path(__file__).resolve().parent
for directory in (ROOT, RE_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import io24_mbc  # noqa: E402
import io24gtk  # noqa: E402
import io24_loopback_foundation as foundation  # noqa: E402
import io24_voicefx_meter_probe as meter  # noqa: E402


SCHEMA = "io24-host-feature-smoke-v1"
SAFE_OUTPUT_VOLUME = 0.01
SETTLE_SECONDS = 0.5
EXPECTED_RATE = 96000
EXPECTED_QUANTUM = 512


class SmokeError(RuntimeError):
    pass


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _clock():
    settings = io24gtk.pw_settings()
    return {
        "force_rate": int(settings.get("clock.force-rate", "0") or 0),
        "force_quantum": int(
            settings.get("clock.force-quantum", "0") or 0),
    }


def _assert_clock(clock):
    if clock != {"force_rate": EXPECTED_RATE,
                 "force_quantum": EXPECTED_QUANTUM}:
        raise SmokeError("PipeWire must be forced to 96000/512, got %r" % clock)


def _assert_device_guards(state):
    if state["input1_phantom"] or state["input2_phantom"]:
        raise SmokeError("phantom must be off on both inputs")
    if state["channel_linked"]:
        raise SmokeError("stereo link must be off")
    if (state["input1_processing_channel"],
            state["input2_processing_channel"]) != (0, 1):
        raise SmokeError("processing-channel permutation must remain 0/1")


def _wait_for_absence(names, timeout=3.0):
    deadline = time.monotonic() + timeout
    remaining = set(names)
    while time.monotonic() < deadline:
        remaining = set(names) & io24_mbc._present_nodes()
        if not remaining:
            return []
        time.sleep(0.05)
    return sorted(remaining)


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def run_live(output_dir, battery_path):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise SmokeError("output directory must exist and be empty")
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": _now(),
        "device": {"serial": foundation.EXPECTED_SERIAL,
                   "bcd_device": "%04x" % foundation.EXPECTED_BCD_DEVICE},
        "mixer_routes": "UNTOUCHED",
        "preset_slots": "UNTOUCHED",
        "dsp_amount": "UNTOUCHED",
        "processing_channel": "UNTOUCHED",
        "solo": {
            "live": "NOT_RUN_WRITE_ONLY_ROUTING_PRESTATE_INCOMPLETE",
            "reason": ("Solo rewrites every source in one bus and the current "
                       "Host shadow does not contain an exact value for every "
                       "write-only source"),
        },
    }
    device = None
    sources = io24_mbc.BusSourceManager()
    insert = io24_mbc.InsertChain()
    before = None
    failure = None
    try:
        report["battery_before"] = foundation._battery(battery_path)
        if report["battery_before"] <= foundation.BATTERY_FLOOR:
            report["status"] = "BLOCKED_BATTERY"
            return report

        before_clock = _clock()
        _assert_clock(before_clock)
        report["clock_before"] = before_clock

        capture = io24_mbc.find_io24_capture_source()
        sink = io24_mbc.find_io24_sink()
        if not capture or not sink:
            raise SmokeError("the io24 PipeWire capture/playback pair is absent")
        if "usb-presonus_revelator_io_24" not in capture.casefold() or \
                "usb-presonus_revelator_io_24" not in sink.casefold():
            raise SmokeError("PipeWire discovery selected non-io24 nodes")
        report["pipewire_targets"] = {"capture": capture, "playback": sink}

        device = foundation._open_checked()
        before = meter._readable_state(device.read_params())
        _assert_device_guards(before)
        report["readable_before"] = before
        device.set_main_volume(SAFE_OUTPUT_VOLUME)
        device.set_main_volume(SAFE_OUTPUT_VOLUME)
        device.set_hp_volume(SAFE_OUTPUT_VOLUME)
        time.sleep(SETTLE_SECONDS)
        guarded = meter._readable_state(device.read_params())
        _assert_device_guards(guarded)
        if not math.isclose(guarded["main_volume"], SAFE_OUTPUT_VOLUME,
                            abs_tol=1e-6) or not math.isclose(
                                guarded["headphone_volume"],
                                SAFE_OUTPUT_VOLUME, abs_tol=1e-6):
            raise SmokeError("safe output attenuation did not latch")
        report["readable_guarded"] = guarded

        controller = io24gtk.AutoGain((1,))
        decision = controller.step(
            0.0, {1: -0.2}, {1: before["input1_gain_db"]})
        if decision is None:
            raise SmokeError("Auto Gain clip input produced no correction")
        device.set_gain(1, decision)
        time.sleep(SETTLE_SECONDS)
        auto_readback = meter._readable_state(device.read_params())
        if not math.isclose(auto_readback["input1_gain_db"], decision,
                            abs_tol=1e-6):
            raise SmokeError("Auto Gain correction did not reach the preamp")
        report["auto_gain"] = {
            "input": "synthetic clip decision at -0.2 dBFS",
            "gain_before_db": before["input1_gain_db"],
            "decision_db": decision,
            "readback_db": auto_readback["input1_gain_db"],
            "result": "HOST_DECISION_AND_DEVICE_GAIN_WRITE_CONFIRMED",
        }

        deadline = time.monotonic() + sources.START_TIMEOUT_S
        statuses = sources.reconcile(capture)
        while set(statuses.values()) != {"ready"} and \
                time.monotonic() < deadline:
            time.sleep(0.05)
            statuses = sources.reconcile(capture)
        if statuses != {"mixa": "ready", "mixb": "ready"}:
            raise SmokeError("passive bus sources did not become ready: %r" %
                             statuses)
        report["mix_a_b"] = {
            "statuses": statuses,
            "nodes": {bus: sources.chains[bus].NODE_NAME
                      for bus in io24_mbc.BUS_SOURCE_KEYS},
            "result": "PASSIVE_SOURCES_PUBLISHED",
        }

        state = io24_mbc.default_snapshot(enabled=True)
        if not insert.start({1: state}, capture, sink, with_comp=True):
            raise SmokeError("Multiband failed to start: %s" %
                             insert.last_error)
        controls_moved = insert.set_channel_controls(
            1, {"c0:Ratio (1:n)": 4.0})
        if not controls_moved:
            raise SmokeError("Multiband live control update failed")
        present = sorted(set(insert.READY_NODES) & io24_mbc._present_nodes())
        if present != sorted(insert.READY_NODES):
            raise SmokeError("Multiband ready nodes disappeared during smoke")
        report["multiband"] = {
            "channels": list(insert.channels),
            "ready_nodes": present,
            "live_control_update": True,
            "device_mixer_reroute": "NOT_PERFORMED",
            "result": "PROCESS_STARTED_CONTROLLED_AND_STOPPED",
        }

        during_clock = _clock()
        _assert_clock(during_clock)
        report["clock_during"] = during_clock
        report["status"] = "SMOKE_PASSED_RESTORATION_PENDING"
    except BaseException as error:
        failure = error
        report["error"] = {"type": type(error).__name__,
                           "message": str(error)}
    finally:
        insert.stop()
        sources.stop()
        smoke_nodes = set(io24_mbc.InsertChain.READY_NODES) | {
            io24_mbc.BUS_SOURCE_NAMES[bus]
            for bus in io24_mbc.BUS_SOURCE_KEYS
        }
        remaining = _wait_for_absence(smoke_nodes)
        restoration_errors = []
        after = None
        if device is not None and before is not None:
            for action, control in (
                    (lambda: device.set_gain(1, before["input1_gain_db"]),
                     "input1_gain"),
                    (lambda: device.set_main_volume(before["main_volume"]),
                     "main_volume"),
                    (lambda: device.set_hp_volume(before["headphone_volume"]),
                     "headphone_volume")):
                try:
                    action()
                except BaseException as error:
                    restoration_errors.append({
                        "control": control, "type": type(error).__name__,
                        "message": str(error)})
            try:
                time.sleep(SETTLE_SECONDS)
                after = meter._readable_state(device.read_params())
                _assert_device_guards(after)
            except BaseException as error:
                restoration_errors.append({
                    "control": "readback", "type": type(error).__name__,
                    "message": str(error)})
        readable_exact = before is not None and after is not None and all(
            after[key] == before[key] for key in (
                "flags", "input1_gain_db", "input2_gain_db",
                "headphone_volume", "main_volume",
                "input1_processing_channel", "input2_processing_channel",
                "input1_phantom", "input2_phantom", "channel_linked"))
        try:
            after_clock = _clock()
            _assert_clock(after_clock)
            report["clock_after"] = after_clock
        except BaseException as error:
            restoration_errors.append({
                "control": "pipewire_clock", "type": type(error).__name__,
                "message": str(error)})
        report["readable_after"] = after
        report["restoration"] = {
            "readable_exact": readable_exact,
            "temporary_nodes_remaining": remaining,
            "mixer_routes": "UNTOUCHED",
            "errors": restoration_errors,
        }
        if device is not None:
            report["transport"] = list(device.transport_log)
            try:
                device.close()
            except BaseException as error:
                restoration_errors.append({
                    "control": "usb_close", "type": type(error).__name__,
                    "message": str(error)})
        try:
            report["battery_after"] = foundation._battery(battery_path)
        except BaseException as error:
            report["battery_after_error"] = str(error)
        if restoration_errors or remaining or (before is not None and
                                               not readable_exact):
            report["status"] = "RESTORATION_FAILED"
        elif failure is not None:
            report["status"] = "SMOKE_FAILED_RESTORED"
        elif report["status"] != "BLOCKED_BATTERY":
            report["status"] = "SMOKE_PASSED_AND_RESTORED"
        report["finished"] = _now()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "DRY_RUN_ONLY",
            "expected_clock": {"force_rate": EXPECTED_RATE,
                               "force_quantum": EXPECTED_QUANTUM},
            "live": ["Auto Gain clip decision/readback",
                     "passive Mix A/B source publish/remove",
                     "Multiband process start/control/stop"],
            "solo": "hardware-free only; exact write-only route prestate absent",
            "mixer_routes": "UNTOUCHED",
        }, indent=2, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--execute requires --output-dir")
    report = run_live(args.output_dir, args.battery_path)
    _write_json(Path(args.output_dir) / "live-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "SMOKE_PASSED_AND_RESTORED" else 3


if __name__ == "__main__":
    sys.exit(main())
