import importlib.util
import datetime as dt
import json
import os
import tempfile
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "io24_dsp_amount_capture.py")
SPEC = importlib.util.spec_from_file_location("io24_dsp_amount_capture", SCRIPT)
CAPTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAPTURE)


def _params(enabled=True):
    flags = 0
    if not enabled:
        flags |= 1 << 6
    return {
        "flags": flags,
        "input1Gain": 30.0,
        "input2Gain": 24.0,
        "mainVolume": 0.42,
        "input1ProcessingChannel": 0,
        "input2ProcessingChannel": 1,
        "input1PhantomPower": False,
        "input2PhantomPower": False,
    }


class FakeDevice:
    def __init__(self, params=None, fail_at=None):
        self.params = dict(params or _params())
        self.fail_at = fail_at
        self.calls = []

    def _call(self, name, *args):
        self.calls.append((name, *args))
        if self.fail_at == len(self.calls):
            raise RuntimeError("injected write failure")

    def set_fx_mix(self, channel, value):
        self._call("set_fx_mix", channel, value)
        if value == 0.0:
            self.params["flags"] |= 1 << (4 + channel)
        else:
            self.params["flags"] &= ~(1 << (4 + channel))

    def set_gain(self, channel, value):
        self._call("set_gain", channel, value)
        self.params["input%dGain" % channel] = value

    def set_main_volume(self, value):
        self._call("set_main_volume", value)
        self.params["mainVolume"] = value

    def read_params(self):
        return dict(self.params)

    def close(self):
        self.calls.append(("close",))


class DspAmountCaptureTests(unittest.TestCase):
    def test_restore_amount_rejects_matching_positive_shadow_value_as_stale(self):
        shadow = {"set_fx_mix#channel=2": {
            "fn": "set_fx_mix", "kwargs": {"channel": 2, "value": 0.73}}}

        with self.assertRaisesRegex(CAPTURE.CaptureError,
                                    "positive write-only prestate is unknown"):
            CAPTURE.resolve_restore_amount(shadow, _params(enabled=True), 2)

    def test_restore_amount_accepts_exact_zero_readback_without_shadow(self):
        result = CAPTURE.resolve_restore_amount({}, _params(enabled=False), 2)

        self.assertEqual({"value": 0.0, "source": "exact_zero_device_readback"},
                         result)

    def test_restore_amount_uses_exact_zero_even_if_shadow_is_stale_positive(self):
        shadow = {"set_fx_mix#channel=2": {
            "fn": "set_fx_mix", "kwargs": {"channel": 2, "value": 0.73}}}

        result = CAPTURE.resolve_restore_amount(shadow, _params(enabled=False), 2)

        self.assertEqual({"value": 0.0, "source": "exact_zero_device_readback"},
                         result)

    def test_restore_amount_rejects_unknown_positive_or_shadow_mismatch(self):
        with self.assertRaisesRegex(CAPTURE.CaptureError,
                                    "positive write-only prestate is unknown"):
            CAPTURE.resolve_restore_amount({}, _params(enabled=True), 2)

    def test_linked_device_is_rejected_before_any_write(self):
        device = FakeDevice(_params())
        device.params["flags"] |= 1 << 12

        with self.assertRaisesRegex(CAPTURE.CaptureError, "stereo link"):
            CAPTURE.run_amount_sequence(
                device, restore_amount=0.0,
                capture_one=lambda amount: {"amount": amount},
                settle=lambda _seconds: None)

        self.assertEqual([], device.calls)

    def test_sequence_captures_all_amounts_and_restores_readable_state(self):
        device = FakeDevice()
        seen = []

        result = CAPTURE.run_amount_sequence(
            device, restore_amount=0.73,
            capture_one=lambda amount: seen.append(amount) or
            {"amount": amount, "path": "amount.wav"},
            settle=lambda _seconds: None)

        self.assertEqual(list(CAPTURE.AMOUNTS), seen)
        self.assertEqual("CAPTURED_AND_RESTORED", result["status"])
        self.assertEqual(24.0, device.params["input2Gain"])
        self.assertEqual(0.42, device.params["mainVolume"])
        self.assertEqual(("set_fx_mix", 2, 0.73), device.calls[-1])
        self.assertTrue(result["restoration"]["readable_exact"])
        self.assertTrue(result["restoration"]["amount_restore_sent"])

    def test_sequence_restores_after_capture_failure(self):
        device = FakeDevice()

        def fail_at_midpoint(amount):
            if amount == 0.5:
                raise RuntimeError("capture broke")
            return {"amount": amount}

        result = CAPTURE.run_amount_sequence(
            device, restore_amount=0.5, capture_one=fail_at_midpoint,
            settle=lambda _seconds: None)

        self.assertEqual("CAPTURE_FAILED_RESTORED", result["status"])
        self.assertEqual("capture broke", result["error"]["message"])
        self.assertEqual(24.0, device.params["input2Gain"])
        self.assertEqual(0.42, device.params["mainVolume"])
        self.assertEqual(("set_fx_mix", 2, 0.5), device.calls[-1])

    def test_capture_commands_pin_96k_s32_six_channels_and_512_period(self):
        recorder, player = CAPTURE.capture_commands("stimulus.wav", "capture.wav")

        self.assertIn("96000", recorder)
        self.assertIn("S32_LE", recorder)
        self.assertIn("6", recorder)
        self.assertIn("512", recorder)
        self.assertIn("--period-size", recorder)
        self.assertIn("96000", player)
        self.assertIn("512", player)

    def test_stimulus_is_six_channel_96k_and_below_minus_12_dbfs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "stimulus.wav")
            result = CAPTURE.write_stimulus(path)

        self.assertEqual(96000, result["rate_hz"])
        self.assertEqual(6, result["channels"])
        self.assertLessEqual(result["peak_dbfs"], -12.0)
        self.assertEqual(1, result["active_playback_channel"])

    def test_live_device_absence_is_an_explicit_blocker(self):
        with tempfile.TemporaryDirectory() as temp:
            output = os.path.join(temp, "output")
            os.mkdir(output)
            battery = os.path.join(temp, "battery")
            with open(battery, "w", encoding="ascii") as handle:
                handle.write("98\n")
            proof = os.path.join(temp, "foundation.json")
            with open(proof, "w", encoding="utf-8") as handle:
                json.dump(_foundation_proof(), handle)
            with mock.patch.object(
                    CAPTURE.foundation, "_open_checked",
                    side_effect=SystemExit("Revelator io24 not found")):
                result = CAPTURE.run_live(output, battery, proof)

        self.assertEqual("BLOCKED_DEVICE_ABSENT", result["status"])
        self.assertEqual("SystemExit", result["error"]["type"])
        self.assertNotIn("sequence", result)

    def test_foundation_proof_freezes_safe_route_and_mix_a_channel(self):
        result = CAPTURE.validate_foundation_proof(
            _foundation_proof(
                monitor_channel=4,
                finished="2026-09-13T22:39:00-07:00"),
            now=dt.datetime(2026, 9, 13, 22, 40,
                            tzinfo=dt.timezone(dt.timedelta(hours=-7))))

        self.assertEqual(4, result["monitor_channel"])
        self.assertEqual("FOUNDATION_CALIBRATED", result["status"])

    def test_foundation_proof_rejects_stale_unsafe_or_ambiguous_route(self):
        now = dt.datetime(2026, 9, 13, 23, 0, tzinfo=dt.timezone.utc)
        cases = []
        unsafe = _foundation_proof()
        unsafe["restoration"]["write_only"]["line_ch2_to_main"] = "UNKNOWN"
        cases.append(unsafe)
        overwritten_amount = _foundation_proof()
        overwritten_amount["readable_before"]["input2_preset_enabled"] = True
        cases.append(overwritten_amount)
        ambiguous = _foundation_proof(monitor_channel=None)
        cases.append(ambiguous)
        stale = _foundation_proof()
        stale["finished"] = "2026-09-13T21:00:00+00:00"
        cases.append(stale)
        for value in cases:
            with self.assertRaises(CAPTURE.CaptureError):
                CAPTURE.validate_foundation_proof(value, now=now)

    def test_manifest_uses_calibrated_monitor_and_local_capture_names(self):
        result = CAPTURE.capture_manifest([
            {"amount": amount, "path": "/tmp/run/amount-%03d.wav" %
             round(amount * 100)} for amount in CAPTURE.SORTED_AMOUNTS
        ], monitor_channel=4)

        self.assertEqual(4, result["monitor_channel"])
        self.assertEqual(
            ["amount-000.wav", "amount-025.wav", "amount-050.wav",
             "amount-075.wav", "amount-100.wav"],
            [row["path"] for row in result["captures"]])


def _foundation_proof(monitor_channel=3, finished=None):
    if finished is None:
        finished = dt.datetime.now().astimezone().isoformat()
    return {
        "schema": "io24-loopback-foundation-v1",
        "status": "FOUNDATION_CALIBRATED",
        "finished": finished,
        "device": {"serial": "AB7C22200355", "bcd_device": "0128"},
        "audio": {
            "status": "CALIBRATED",
            "frozen_mix_a_capture_channel": monitor_channel,
        },
        "readable_before": {"input2_preset_enabled": False},
        "readable_restored": {"input2_preset_enabled": False},
        "restoration": {
            "readable_exact": True,
            "write_only": {
                "line_ch2_to_main": "PARKED_OFF",
                "fx_return_to_main": "PARKED_OFF",
                "return_ch1_to_main": "PARKED_OFF",
                "mix_a": "PARKED_WITH_LINE_CH2_ONLY_AT_0_DB",
            },
        },
    }


if __name__ == "__main__":
    unittest.main()
