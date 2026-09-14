import importlib.util
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "io24_dsp_amount_meter_probe.py")
SPEC = importlib.util.spec_from_file_location("io24_dsp_amount_meter_probe", SCRIPT)
METER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(METER)


class MeterClassificationTests(unittest.TestCase):
    def test_classifies_linear_gate_curve_and_unchanged(self):
        cases = {
            "linear": ([0.5, 0.75, 1.0, 1.25, 1.5],
                       "LINEAR_METER_ENDPOINT_INTERPOLATION"),
            "gate": ([0.5, 1.5, 1.5, 1.5, 1.5], "ZERO_NONZERO_GATE"),
            "curve": ([0.5, 0.5625, 0.75, 1.0625, 1.5],
                      "NONLINEAR_MONOTONIC_METER_BLEND"),
            "same": ([0.5, 0.501, 0.499, 0.5, 0.5],
                     "ENDPOINT_RATIOS_INDISTINGUISHABLE"),
        }
        for name, (ratios, expected) in cases.items():
            with self.subTest(name=name):
                result = METER.classify_ratios(METER.SORTED_AMOUNTS, ratios)
                self.assertEqual(expected, result["classification"])


class _Device:
    def __init__(self):
        self.amount = 0.0
        self.main = 0.76
        self.eq_writes = []

    def read_params(self):
        return {
            "flags": 449 if self.amount == 0.0 else 385,
            "input1Gain": 30.0,
            "input2Gain": 24.287769317626953,
            "mainVolume": self.main,
            "input1ProcessingChannel": 0,
            "input2ProcessingChannel": 1,
            "input1PhantomPower": False,
            "input2PhantomPower": False,
        }

    def set_main_volume(self, value):
        self.main = value

    def set_fx_mix(self, channel, value):
        self.amount = value

    def set_eq_band(self, channel, band, **kwargs):
        self.eq_writes.append((channel, band, kwargs))


class MeterSequenceTests(unittest.TestCase):
    def test_sequence_restores_zero_main_and_identity_eq(self):
        device = _Device()
        seen = []
        result = METER.run_meter_sequence(
            device,
            lambda amount: seen.append(amount) or {
                "amount": amount, "median_main_to_input2": 0.5 + amount},
            settle=lambda _seconds: None)
        self.assertEqual("MEASURED_AND_RESTORED", result["status"])
        self.assertEqual(list(METER.CAPTURE_ORDER), seen)
        self.assertEqual(0.0, device.amount)
        self.assertEqual(0.76, device.main)
        self.assertEqual("highshelf", device.eq_writes[0][2]["shape"])
        self.assertEqual("off", device.eq_writes[-1][2]["shape"])
        self.assertTrue(result["restoration"]["readable_exact"])

    def test_measurement_failure_still_restores(self):
        device = _Device()

        def fail(amount):
            if amount == 0.25:
                raise RuntimeError("meter failed")
            return {"amount": amount}

        result = METER.run_meter_sequence(
            device, fail, settle=lambda _seconds: None)
        self.assertEqual("MEASUREMENT_FAILED_RESTORED", result["status"])
        self.assertEqual(0.0, device.amount)
        self.assertEqual(0.76, device.main)
        self.assertEqual("off", device.eq_writes[-1][2]["shape"])


if __name__ == "__main__":
    unittest.main()
