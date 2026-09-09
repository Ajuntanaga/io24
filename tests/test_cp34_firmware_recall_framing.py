#!/usr/bin/env python3
"""Hardware-free contract for CP34 stored-Stat recall framing."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "cp34_firmware_recall_framing.py"
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
        test_case, "io24_firmware_recall_framing_package",
        ROOT / "io24_firmware.py")
    dll = UC5_DLL.read_bytes()
    package = dll[
        package_module.DLL_FW_START:package_module.DLL_FW_END]
    package_module.inspect_io24_recovery_package(package)
    return package[:FIRMWARE_SIZE]


class FirmwareRecallFramingTests(unittest.TestCase):
    maxDiff = None

    @unittest.skipUnless(UC5_DLL.is_file(), "pinned installed UC5 DLL unavailable")
    def test_stored_stat_recall_preserves_bytes_to_structured_state(self):
        module = _load_module(
            self, "cp34_firmware_recall_framing", ANALYZER)
        report = module.analyze(_pinned_application(self))

        self.assertEqual(
            report,
            {
                "boundary": (
                    "PHYSICAL_STORED_BYTES_AND_UC472_SERIALIZER_REMAIN_"
                    "UNOBSERVED"
                ),
                "final_receiver_construction": {
                    "base_constructor": "0x5e018 -> 0x5d990",
                    "base_vtable_lifetime": (
                        "0x6008d3a8 transient during construction and teardown"
                    ),
                    "derived_constructor": "0x3d52a -> 0x5e014",
                    "final_primary_vtable": (
                        "0x5e02a/0x5e036 -> 0x6012cb40"
                    ),
                    "final_slot_0x38": "0x10cb78 -> 0x531e0",
                    "global": "0x20216660",
                    "registered_teardown": "0x41580 after construction",
                },
                "known_host_prefix_effect": {
                    "copied_into_accumulation_if_recalled": True,
                    "first_native_word_if_present": "0x700b697b",
                    "interpreted_on_zero_selector_route": True,
                    "linux_tagged_map_prefix_hex": "7b690b70",
                    "physical_device_presence": "UNOBSERVED",
                    "required_native_word": "0x00000002",
                },
                "live_stat_handoff": {
                    "accumulation_destination": (
                        "device+0x18+fragment_offset"
                    ),
                    "constructed_stack_reader_cursor": 0,
                    "dispatcher": "0x420bc",
                    "first_callback": "0x42266 -> 0x531e0",
                    "first_callback_arguments": "r1=0, r3=1",
                    "nested_payload_source": "Stat+0x1d",
                    "prefix_inserted": False,
                    "second_callback": "0x42280 -> 0x531e0",
                    "second_callback_arguments": "r1=1, r3=0",
                    "stat_branch": "0x42200",
                    "structured_state_reached": True,
                },
                "packet_router": {
                    "device_lookup": (
                        "device+8 final vtable slot -> 0x3cf20/0x3ce98"
                    ),
                    "device_lookup_query": "packet+4 = {0, 0}",
                    "device_lookup_result": "final derived device global",
                    "dispatcher_vtable": (
                        "0x6012cb40 slot 0 -> 0x420bc"
                    ),
                    "function": "0x419a0",
                    "nested_stat_argument": "r1 = packet+0xc",
                    "setp_branch": "0x41aaa -> 0x41b44",
                },
                "recall_wrapper": {
                    "callback": "0x2f8ac",
                    "copy_call": "0x2f8ea -> memcpy",
                    "driver": "0x2f0d0",
                    "nested_stat_offset": 12,
                    "packet_layout": "SetP | 0 | 0 | nested Stat message",
                },
                "route_reconciliation": {
                    "exact_route": (
                        "0x3cc40 -> 0x41b6c/0x419a0 -> "
                        "0x3cf20/0x3ce98 -> 0x420bc -> 0x531e0"
                    ),
                    "intermediate_noop_claim_retracted": True,
                    "old_shorthand": "0x3cc40 -> 0x420bc",
                    "ultimate_dispatcher_unchanged": True,
                },
                "singleton_forwarding": {
                    "application_router": "0x20790/0x20754 -> 0x34cb8",
                    "device_router_adjustor": "0x41b6c -> 0x419a0",
                    "device_router_cell": (
                        "0x20216664 -> final secondary vtable -> 0x41b6c"
                    ),
                    "manager_bridge": "0x31674/0x3163c",
                    "projection": "vtable 0x6d40c -> 0x3cc08",
                    "secondary_forwarder": (
                        "vtable 0x6d434 -> 0x3cc40"
                    ),
                    "singleton_field": (
                        "primary+0x13c -> cell 0x20216664"
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
                    "STORED_STAT_RECALL_SOURCE_BOUND_BYTE_PRESERVING_NO_"
                    "PREFIX_INSERTION"
                ),
                "stored_record_reader": {
                    "entry": "0x30be0",
                    "fallback_copy": "0x30c2a -> 0x30708",
                    "fallback_payload_flow": (
                        "descriptor bytes -> message+0x1d unchanged"
                    ),
                    "slot_range": "0..3",
                    "stat_tag": "Stat",
                    "storage_payload_flow": (
                        "stored bytes -> message+0x1d unchanged"
                    ),
                    "storage_payload_read": "0x30b16 -> 0x2c0a8",
                    "storage_record_length_member": "message+0x19",
                    "storage_reader": "0x30a90",
                },
            },
        )

    @unittest.skipUnless(UC5_DLL.is_file(), "pinned installed UC5 DLL unavailable")
    def test_analyzer_rejects_a_same_size_unpinned_firmware(self):
        module = _load_module(
            self, "cp34_firmware_recall_framing_mutation", ANALYZER)
        changed = bytearray(_pinned_application(self))
        changed[-1] ^= 1
        with self.assertRaisesRegex(module.AnalysisError, "SHA-256 differs"):
            module.analyze(bytes(changed))


if __name__ == "__main__":
    unittest.main()
