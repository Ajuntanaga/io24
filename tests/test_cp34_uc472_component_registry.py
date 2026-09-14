#!/usr/bin/env python3
"""Hardware-free contracts for the UC 4.7.2 component registry decoder.

The decoder's point is that a creator can be referenced by neither a pointer
nor a call and still be live, because a CRT static initializer loads it with a
RIP-relative lea. These tests pin that claim and the decoded table, so a future
reader cannot repeat the "no references, therefore dead code" mistake.
Nothing here opens USB.
"""

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
RE_DIR = ROOT / "re"
for path in (str(ROOT), str(RE_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

SPEC = importlib.util.spec_from_file_location(
    "cp34_uc472_component_registry",
    RE_DIR / "cp34_uc472_component_registry.py")
REGISTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REGISTRY)

MODULE_PATH = (ROOT / ".superpowers/sdd/2026-08-28-cp34-preset-effect-control"
               / "runs/20260906T001130-0700-uc472-official-reacquisition"
               / "extracted/hwaccess/dspusbdevice.dll")

EXPECTED = [
    ("EQCompSelectorComponent", "0x18004b2e0", "0x18004b350"),
    ("FilterComponent", "0x18004b420", "0x18004b460"),
    ("GateComponent", "0x18004b530", "0x18004b570"),
    ("LimiterComponent", "0x18004b640", "0x18004b680"),
    ("InsertFXSelectorComponent", "0x18004b750", "0x18004b7b0"),
    ("VocalReverbComponent", "0x18004b880", "0x18004b8c0"),
]


class RetainedModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MODULE_PATH.exists():
            raise unittest.SkipTest("retained UC 4.7.2 dsp module not present")
        cls.module = REGISTRY.Module(MODULE_PATH.read_bytes())
        cls.result = REGISTRY.analyze(cls.module)

    def test_the_six_dsp_components_are_recovered_in_order(self):
        got = [(c["component"], c["creator"], c["destroyer"])
               for c in self.result["components"]]
        self.assertEqual(got, EXPECTED)

    def test_the_voice_fx_component_is_the_insert_fx_selector(self):
        entry = next(c for c in self.result["components"]
                     if c["creator"] == "0x18004b750")
        self.assertEqual(entry["component"], "InsertFXSelectorComponent")

    def test_the_registry_is_built_by_a_crt_static_initializer(self):
        self.assertTrue(self.result["registered_at_load"])
        self.assertIn("0x1800e4898", self.result["crt_initializer_slots"])

    def test_the_creators_are_referenced_by_neither_pointer_nor_call(self):
        # This is the whole reason the instantiation site was not found
        # earlier: absence of pointers and calls is not absence of references.
        for _name, creator, _destroyer in EXPECTED:
            self.assertEqual(self.module.vtable_slots(int(creator, 16)), [],
                             "%s is stored as a pointer" % creator)

    def test_every_registered_creator_is_a_real_function(self):
        starts = {begin for begin, _end in self.module.functions()}
        for _name, creator, destroyer in EXPECTED:
            self.assertIn(int(creator, 16), starts)
            self.assertIn(int(destroyer, 16), starts)


class DecoderTests(unittest.TestCase):
    def test_a_module_without_the_initializer_is_refused(self):
        class Stub:
            data = b"\x00" * 64
            sha256 = "0" * 64

            def offset_of(self, _address):
                return None

        with self.assertRaises(REGISTRY.RegistryError):
            REGISTRY.decode_registry(Stub())


if __name__ == "__main__":
    unittest.main()
