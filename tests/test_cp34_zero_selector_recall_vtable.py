#!/usr/bin/env python3
"""Contract for the final CP34 zero-selector Stat receiver vtable."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "cp34_zero_selector_recall_vtable.py"
UC5_DLL = Path(
    "/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll")
FIRMWARE_SIZE = 1_104_448


def _load_module(test_case, name, path):
    test_case.assertTrue(path.is_file(), "%s is missing" % path.name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pinned_application(test_case):
    package_module = _load_module(
        test_case, "io24_zero_selector_vtable_package",
        ROOT / "io24_firmware.py")
    dll = UC5_DLL.read_bytes()
    package = dll[
        package_module.DLL_FW_START:package_module.DLL_FW_END]
    package_module.inspect_io24_recovery_package(package)
    return package[:FIRMWARE_SIZE]


class ZeroSelectorRecallVtableTests(unittest.TestCase):
    maxDiff = None

    @unittest.skipUnless(UC5_DLL.is_file(), "pinned installed UC5 DLL unavailable")
    def test_zero_selector_stat_callbacks_use_final_derived_vtable(self):
        module = _load_module(
            self, "cp34_zero_selector_recall_vtable", ANALYZER)
        report = module.analyze(_pinned_application(self))

        self.assertEqual(
            report,
            {
                "boundary": (
                    "0X531E0_RUNTIME_COMPLETION_SELECTED_COMPONENT_AND_"
                    "PHYSICAL_OUTCOMES_REMAIN_UNRESOLVED"
                ),
                "base_constructor": {
                    "call": "0x5e018 -> 0x5d990",
                    "installed_primary_vtable": "0x6008d3a8",
                    "lifetime": "transient during construction and teardown",
                    "slot_0x38": "0x6d3e0 -> 0x3ccb4",
                },
                "construction_order": {
                    "derived_constructor_call": "0x3d52a -> 0x5e014",
                    "global": "0x20216660",
                    "lazy_initializer": "0x3d4f0",
                    "registered_teardown_callback": "0x41580",
                    "teardown_registration_call": "0x3d536 -> 0x5fc04",
                },
                "final_derived_constructor": {
                    "constructor": "0x5e014",
                    "header_literal": "0x5e08c -> 0x6012cb38",
                    "header_literal_exact_occurrences": 1,
                    "primary_vtable_formation": (
                        "0x5e02a: 0x6012cb38 + 8 -> 0x6012cb40"
                    ),
                    "primary_vtable_store": "0x5e036 -> [global+0]",
                    "slot_0x0": "0x10cb40 -> 0x420bc",
                    "slot_0x38": "0x10cb78 -> 0x531e0",
                },
                "retraction": {
                    "retracted_intermediate_claim": (
                        "0x42266 and 0x42280 -> base vtable +0x38 -> 0x3ccb4"
                    ),
                    "root_cause": (
                        "base-constructor and registered-teardown vtable writes "
                        "were mistaken for the final derived construction state"
                    ),
                },
                "dispatcher": {
                    "accumulation_copy": (
                        "Stat+0x1d -> primary+0x18+fragment_offset"
                    ),
                    "entry": "0x420bc",
                    "first_callback": "0x42266 -> 0x531e0",
                    "first_callback_arguments": "r1=0, r3=1",
                    "receiver_capture": "0x420c8: r5 = selected primary",
                    "second_callback": "0x42280 -> 0x531e0",
                    "second_callback_arguments": "r1=1, r3=0",
                    "structured_state_reached_on_zero_route": True,
                },
                "route_effect": {
                    "incoming_or_stored_payload_prefix_interpreted": True,
                    "structured_prefix_gate_applicable": True,
                    "zero_route_after_accumulation": (
                        "two structured-state callbacks"
                    ),
                },
                "source": {
                    "image_base": "0x60020000",
                    "sha256": (
                        "65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a"
                        "7679e387952eb1a"
                    ),
                    "size": 1_104_448,
                },
                "status": (
                    "ZERO_SELECTOR_STAT_ROUTE_SOURCE_BOUND_FINAL_DERIVED_"
                    "SLOT_0X38_0X531E0"
                ),
                "zero_selector": {
                    "callback_query": "{0, 0}",
                    "packet_layout": "SetP | 0 | 0 | nested Stat message",
                    "packet_router": "0x419a0",
                    "result": "final derived device global unchanged",
                    "selector": "0x3cf20/0x3ce98",
                    "zero_branch": "0x3cebe -> 0x3ceec",
                },
            },
        )

    @unittest.skipUnless(UC5_DLL.is_file(), "pinned installed UC5 DLL unavailable")
    def test_analyzer_rejects_a_same_size_unpinned_firmware(self):
        module = _load_module(
            self, "cp34_zero_selector_recall_vtable_mutation", ANALYZER)
        changed = bytearray(_pinned_application(self))
        changed[-1] ^= 1
        with self.assertRaisesRegex(module.AnalysisError, "SHA-256 differs"):
            module.analyze(bytes(changed))


if __name__ == "__main__":
    unittest.main()
