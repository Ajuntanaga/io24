#!/usr/bin/env python3
"""Hardware-free contract for CP34 firmware ingress/storage framing."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "cp34_firmware_ingress_storage_framing.py"
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
        test_case, "io24_firmware_ingress_storage_package",
        ROOT / "io24_firmware.py")
    dll = UC5_DLL.read_bytes()
    package = dll[
        package_module.DLL_FW_START:package_module.DLL_FW_END]
    package_module.inspect_io24_recovery_package(package)
    return package[:FIRMWARE_SIZE]


class FirmwareIngressStorageFramingTests(unittest.TestCase):
    maxDiff = None

    @unittest.skipUnless(UC5_DLL.is_file(), "pinned installed UC5 DLL unavailable")
    def test_stat_payload_byte_zero_survives_storage_wrapper_round_trip(self):
        module = _load_module(
            self, "cp34_firmware_ingress_storage_framing", ANALYZER)
        report = module.analyze(_pinned_application(self))

        self.assertEqual(
            report,
            {
                "backend_forwarding": {
                    "backend_vtable": "0x600876ec",
                    "checksum": (
                        "slot +0xc -> 0x3198c/0x3196c -> CRC32 0x3665c"
                    ),
                    "read": (
                        "slot +0x4 -> 0x3170c/0x316e4, same "
                        "address/destination/length"
                    ),
                    "write": (
                        "slot +0x0 -> 0x316dc/0x316b0, same "
                        "address/source/length, flag 1"
                    ),
                },
                "boundary": (
                    "PHYSICAL_BACKEND_COMMIT_AND_UC472_SERIALIZER_REMAIN_"
                    "UNOBSERVED"
                ),
                "ingress_dispatch": {
                    "component_binding": "root+0x70 = root+0x1240",
                    "component_vtable": (
                        "0x600874f8 slot +0x18 -> 0x3099c"
                    ),
                    "handler": "0x2f210",
                    "message_argument_preserved": True,
                    "root_vtable_slot": "0x6d288 -> 0x2f210",
                    "slot_range": "0..3",
                    "stat_tag": "Stat",
                    "writer_call": "0x30a06 -> 0x3092c",
                },
                "paired_record_reader": {
                    "entry": "0x30a90",
                    "first_fragment_storage_advance": (
                        "4 logical length bytes + 8 wrapper bytes"
                    ),
                    "logical_round_trip": (
                        "incoming message+0x1d -> recalled message+0x1d"
                    ),
                    "payload_destination": "message+0x1d",
                    "payload_read": "0x30b16 -> 0x2c0a8",
                    "prefix_inserted": False,
                    "record_length_destination": "message+0x19",
                    "record_length_read": "0x30ab8 -> 0x2c0a8",
                },
                "reconciliation": {
                    "logical_byte_zero_at_paired_reader_output": (
                        "incoming_payload[0]"
                    ),
                    "parser_visible_first_word": (
                        "little_endian_u32(incoming_payload[0:4])"
                    ),
                    "structured_state_0x531e0_reached_on_zero_route": True,
                    "structured_state_0x531e0_source_bound_caller": (
                        "0x42266/0x42280 via final derived vtable 0x6012cb40"
                    ),
                    "wrapper_header_exposed_to_paired_reader_caller": False,
                    "zero_selector_recall_after_accumulation": (
                        "two structured-state callbacks through slot +0x38"
                    ),
                },
                "record_writer": {
                    "entry": "0x3092c",
                    "first_fragment_condition": "fragment_offset == 0",
                    "first_fragment_length_write": (
                        "0x30948 -> 0x2bfe4, message+0x19, 4 bytes"
                    ),
                    "fragment_length": "u16(message+0x17)",
                    "fragment_offset": "u32(message+0x12)",
                    "native_u32_two_inserted": False,
                    "payload_source": "message+0x1d",
                    "payload_source_preserved": True,
                    "payload_write": "0x30988 -> 0x2bfe4",
                    "total_record_length": "u32(message+0x19)",
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
                    "FIRMWARE_STAT_INGRESS_RECALL_SOURCE_BOUND_LOGICAL_BYTE_"
                    "ZERO_UNCHANGED_NO_PREFIX_INSERTION"
                ),
                "storage_wrapper": {
                    "backend_address_layout": (
                        "crc32@+0 | payload_length@+4 | payload@+8"
                    ),
                    "checksum_validation": (
                        "CRC32(original payload) stored and checked on read"
                    ),
                    "header_size": 8,
                    "read": "0x2c0a8",
                    "read_destination_preserved": True,
                    "read_payload_source": "storage_address+8",
                    "wrapper_header_exposed_to_caller": False,
                    "wrapper_vtable": "0x60086994",
                    "write": "0x2bfe4",
                    "write_payload_destination": "storage_address+8",
                    "write_payload_source_preserved": True,
                },
            },
        )

    @unittest.skipUnless(UC5_DLL.is_file(), "pinned installed UC5 DLL unavailable")
    def test_analyzer_rejects_a_same_size_unpinned_firmware(self):
        module = _load_module(
            self, "cp34_firmware_ingress_storage_framing_mutation", ANALYZER)
        changed = bytearray(_pinned_application(self))
        changed[-1] ^= 1
        with self.assertRaisesRegex(module.AnalysisError, "SHA-256 differs"):
            module.analyze(bytes(changed))


if __name__ == "__main__":
    unittest.main()
