import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cp34_ringmod_discriminator_static",
    ROOT / "re" / "cp34_ringmod_discriminator_static.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
FIRMWARE = Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin")


class RingModDiscriminatorStaticTests(unittest.TestCase):
    def setUp(self):
        self.result = MODULE.analyze_firmware(FIRMWARE.read_bytes())

    def test_model3_constructor_handler_and_process_are_source_bound(self):
        model = self.result["model3_execution"]
        self.assertEqual(3, model["model_id"])
        self.assertEqual("botb", model["tag"])
        self.assertEqual("0x58920", model["constructor_raw_offset"])
        self.assertEqual("0x58db0", model["tagged_handler_raw_offset"])
        self.assertEqual("0x4ff6c", model["process_raw_offset"])

    def test_handler_fields_feed_the_process_gain_equation(self):
        model = self.result["model3_execution"]
        self.assertEqual("model+0x14", model["parameter_fields"]["on"])
        self.assertEqual("model+0x20", model["parameter_fields"]["volume"])
        self.assertEqual("model+0x2c", model["parameter_fields"]["mix"])
        self.assertEqual("volume * (1 - mix)",
                         model["process_equation"]["dry_gain"])
        self.assertEqual("2 * volume * mix",
                         model["process_equation"]["wet_gain"])

    def test_probe_profile_mutes_active_output_and_off_is_dry(self):
        profile = self.result["zero_output_discriminator"]
        self.assertEqual({"dry": 0.0, "wet": 0.0},
                         profile["active_output_gains"])
        self.assertEqual({"dry": 1.0, "wet": 0.0},
                         profile["off_output_gains"])
        self.assertTrue(profile["resolved_scalar_discriminator"])


if __name__ == "__main__":
    unittest.main()
