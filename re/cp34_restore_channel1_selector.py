#!/usr/bin/env python3
"""Restore only the Channel-1 selector displaced by the CP34 live test."""

import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import io24  # noqa: E402


EXPECTED_SERIAL = "AB7C22200355"
EXPECTED_FIRMWARE_VERSION = 0x0128
EXPECTED_CURRENT_SLOT = 3
RESTORE_SLOT = 0


def _state(params):
    flags = int(params["flags"])
    return {
        "channel_linked": bool(flags >> 12 & 1),
        "input1_gain_db": params["input1Gain"],
        "input2_gain_db": params["input2Gain"],
        "input1_preset_enabled": not bool(flags >> 5 & 1),
        "input2_preset_enabled": not bool(flags >> 6 & 1),
        "input1_slot_index": int(params["input1SlotIndex"]),
        "input2_slot_index": int(params["input2SlotIndex"]),
        "input1_processing_channel": int(params["input1ProcessingChannel"]),
        "input2_processing_channel": int(params["input2ProcessingChannel"]),
    }


def _preserved(state):
    return {
        key: value for key, value in state.items()
        if key != "input1_slot_index"
    }


def main():
    battery = int(Path("/sys/class/power_supply/BAT0/capacity").read_text().strip())
    if battery <= 10:
        print(json.dumps({"status": "BLOCKED_BATTERY",
                          "battery_percent": battery}, sort_keys=True))
        return 3

    device = None
    try:
        device = io24.Io24(shadow=False)
        serial = device.dev.serial_number
        firmware = int(getattr(device.dev, "bcdDevice", 0))
        if serial != EXPECTED_SERIAL or firmware != EXPECTED_FIRMWARE_VERSION:
            print(json.dumps({
                "status": "IDENTITY_MISMATCH",
                "expected_serial": EXPECTED_SERIAL,
                "observed_serial": serial,
                "expected_bcd_device": "%04x" % EXPECTED_FIRMWARE_VERSION,
                "observed_bcd_device": "%04x" % firmware,
            }, sort_keys=True))
            return 3

        params = device.read_params()
        if params is None:
            raise RuntimeError("readable baseline unavailable")
        before = _state(params)
        if before["channel_linked"]:
            raise RuntimeError("stereo link is on")
        if before["input1_slot_index"] != EXPECTED_CURRENT_SLOT:
            raise RuntimeError(
                "Channel 1 selector is no longer at the displaced slot 3")
        if before["input1_preset_enabled"]:
            raise RuntimeError(
                "Channel 1 is no longer in the expected bypassed state")

        device.set_preset_slot(1, RESTORE_SLOT)
        time.sleep(0.5)
        params = device.read_params()
        if params is None:
            raise RuntimeError("restoration readback unavailable")
        after = _state(params)
        if after["input1_slot_index"] != RESTORE_SLOT:
            raise RuntimeError("Channel 1 selector did not read back as slot 0")
        if after["input1_preset_enabled"]:
            raise RuntimeError("Channel 1 preset unexpectedly became enabled")
        if _preserved(after) != _preserved(before):
            raise RuntimeError("state outside the Channel 1 selector changed")

        print(json.dumps({
            "status": "RESTORED",
            "battery_percent": battery,
            "device": {"serial": serial,
                       "bcd_device": "%04x" % firmware},
            "before": before,
            "after": after,
            "record_write_attempted": False,
            "channel1_preset_body_written": False,
        }, indent=2, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({
            "status": "RESTORE_FAILED",
            "error": "%s: %s" % (type(error).__name__, error),
            "record_write_attempted": False,
        }, sort_keys=True))
        return 3
    finally:
        if device is not None:
            device.close()


if __name__ == "__main__":
    raise SystemExit(main())
