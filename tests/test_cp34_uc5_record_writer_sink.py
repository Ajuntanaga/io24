#!/usr/bin/env python3
"""Hardware-free contract for the CP34 UC5 record-writer sink."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "cp34_uc5_record_writer_sink.py"
UC5_DLL = Path(
    "/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll")


def _load_analyzer(test_case):
    test_case.assertTrue(ANALYZER.is_file(), "UC5 writer-sink analyzer is missing")
    spec = importlib.util.spec_from_file_location(
        "cp34_uc5_record_writer_sink", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Uc5RecordWriterSinkTests(unittest.TestCase):
    maxDiff = None

    @unittest.skipUnless(UC5_DLL.is_file(), "pinned installed UC5 DLL unavailable")
    def test_first_logical_archive_byte_becomes_physical_record_byte_zero(self):
        module = _load_analyzer(self)
        report = module.analyze(UC5_DLL.read_bytes())

        self.assertEqual(
            report,
            {
                "boundary": (
                    "UC5_ONLY_UC472_AND_FIRMWARE_INGRESS_STORAGE_"
                    "TRANSFORM_UNRESOLVED"
                ),
                "first_write": {
                    "adapter": "0x180065d30",
                    "adapter_record_flow": (
                        "writer+8 receiver +0x10 -> writer+0x18 -> r14 record"
                    ),
                    "archive_call": "0x180069dae -> writer vtable+0x8",
                    "cursor_after_success": 1,
                    "cursor_before": 0,
                    "destination": "record.data(+0x10)+record.cursor(+0x2c)",
                    "length_after_success": 1,
                    "length_before": 0,
                    "logical_byte_hex": "7b",
                    "logical_size": 1,
                    "native_u32_two_prefix_inserted": False,
                    "physical_prefix_hex": "7b",
                    "record_append": "0x1800643f0",
                    "record_copy": "0x180064470 -> memcpy",
                },
                "post_serializer_send": {
                    "caller_pair": (
                        "0x18004239c snapshot then 0x1800423b3 send, "
                        "same r14d slot"
                    ),
                    "fragmenter": "0x180052270",
                    "fragmenter_record_members": "data +0x10, length +0x30",
                    "post_serializer_mutation": False,
                    "snapshot_return": (
                        "0x180042893 serializer call -> 0x180042898 success return"
                    ),
                },
                "reconciliation": {
                    "firmware_recall": (
                        "stored_record[0:4] reaches 0x531e0 unchanged"
                    ),
                    "firmware_required_native_u32": "0x00000002",
                    "uc5_physical_first_byte": "0x7b",
                    "uc5_prefix_eligible_for_native_u32_two": False,
                },
                "record_collection": {
                    "count": 4,
                    "element_constructor": "0x180030570",
                    "element_stride": "0x38",
                    "owner_member": (
                        "controller+0x2d8 -> controller+0x340"
                    ),
                    "record_append_target": "0x1800643f0",
                    "record_reset_target": "0x1800643b0",
                    "record_vtable": "0x18043b828",
                    "vector_constructor_call": (
                        "0x180030dff -> 0x1800d18a0"
                    ),
                },
                "serializer_writer": {
                    "adapter_output_member": "writer+0x18 = r14 record",
                    "adapter_primary_vtable": "0x18043bbd8",
                    "adapter_secondary_vtable": "0x18043bc20",
                    "cursor_reset": (
                        "0x18002ebba -> record vtable+0x8 -> 0x1800643b0"
                    ),
                    "function": "0x18002e9e0",
                    "length_reset": "0x18002ebbd: record+0x30 = 0",
                    "output_record": "r14",
                },
                "source": {
                    "image_base": "0x180000000",
                    "sha256": (
                        "567892d75c7243b3cc30487f7431933e593f3c288ea6add84"
                        "c21d4e8678f877b"
                    ),
                    "size": 4_984_704,
                },
                "status": (
                    "UC5_RECORD_WRITER_SOURCE_BOUND_PHYSICAL_BYTE_ZERO_"
                    "0X7B_NO_PREFIX_INSERTION"
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
