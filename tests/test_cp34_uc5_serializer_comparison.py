#!/usr/bin/env python3
"""Hardware-free contract for the CP34 UC5 serializer comparison."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "cp34_uc5_serializer_comparison.py"
UC5_DLL = Path(
    "/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll")


def _load_analyzer(test_case):
    test_case.assertTrue(ANALYZER.is_file(), "UC5 serializer analyzer is missing")
    spec = importlib.util.spec_from_file_location(
        "cp34_uc5_serializer_comparison", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Uc5SerializerComparisonTests(unittest.TestCase):
    maxDiff = None

    @unittest.skipUnless(UC5_DLL.is_file(), "pinned installed UC5 DLL unavailable")
    def test_dynamic_stat_save_serializer_emits_tagged_map_opener_before_fragmentation(self):
        module = _load_analyzer(self)
        report = module.analyze(UC5_DLL.read_bytes())

        self.assertEqual(
            report,
            {
                "archive_open": {
                    "empty_name_branch": "0x180069c76 -> 0x180069d96",
                    "first_emitted_ascii": "{",
                    "first_emitted_byte": "0x7b",
                    "first_output_call": "0x180069dae -> vtable+0x8",
                    "first_output_size": 1,
                    "function": "0x180069c40",
                    "native_u32_two_prefix": False,
                },
                "boundary": (
                    "UC5_ONLY_UC472_AND_FIRMWARE_RECALL_TO_LIVE_STAT_"
                    "BRIDGE_UNRESOLVED"
                ),
                "fragmenter": {
                    "function": "0x180052270",
                    "memp_length": "0x7ec",
                    "memp_tag": "MemP",
                    "queue_call": "0x18005238e -> 0x1800546b0",
                    "record_copy_call": "0x18005235a -> memcpy",
                    "record_data_member": "+0x10",
                    "record_length_member": "+0x30",
                },
                "serializer": {
                    "archive_open_call": "0x18002ec07 -> 0x180069c40",
                    "archive_open_name_argument": "null/empty",
                    "function": "0x18002e9e0",
                    "output_record_flow": "rcx -> r14 -> writer.output",
                    "record_length_clear": (
                        "0x18002ebbd: [r14+0x30] = 0"
                    ),
                    "record_reset_call": (
                        "0x18002ebba -> record.vtable+0x8"
                    ),
                },
                "slot_snapshot_then_send": {
                    "call_pair": {
                        "send_call": "0x1800423b3 -> 0x180042940",
                        "slot_register": "r14d",
                        "snapshot_call": "0x18004239c -> 0x180042840",
                    },
                    "record_lookup_call": "0x180042888 -> 0x1800427e0",
                    "serializer_call": "0x180042893 -> 0x18002e9e0",
                },
                "source": {
                    "image_base": "0x180000000",
                    "sha256": (
                        "567892d75c7243b3cc30487f7431933e593f3c288ea6add84"
                        "c21d4e8678f877b"
                    ),
                    "size": 4_984_704,
                },
                "stat_sender": {
                    "application_index": 0,
                    "application_tag": "Appl",
                    "function": "0x180042940",
                    "record_argument": "r9",
                    "record_member": "controller+0x2d8",
                    "record_stride": "0x38",
                    "sender_member": "controller+0x308",
                    "sender_target": "0x180052270",
                    "sender_virtual_slot": "0x10",
                    "sender_vtable": "0x18043a5b0",
                    "stat_index": "slot",
                    "stat_tag": "Stat",
                },
                "status": (
                    "UC5_SAVE_SERIALIZER_SOURCE_BOUND_TAGGED_MAP_OPENER_"
                    "NOT_NATIVE_U32_TWO"
                ),
            },
        )

    @unittest.skipUnless(UC5_DLL.is_file(), "pinned installed UC5 DLL unavailable")
    def test_analyzer_rejects_a_same_size_unpinned_image(self):
        module = _load_analyzer(self)
        changed = bytearray(UC5_DLL.read_bytes())
        changed[-1] ^= 1
        with self.assertRaisesRegex(module.AnalysisError, "SHA-256 differs"):
            module.analyze(bytes(changed))


if __name__ == "__main__":
    unittest.main()
