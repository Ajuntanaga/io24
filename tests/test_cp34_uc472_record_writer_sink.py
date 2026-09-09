#!/usr/bin/env python3
"""Hardware-free contract for the CP34 UC 4.7.2 record-writer sink."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "cp34_uc472_record_writer_sink.py"
UC472_DLL = (
    ROOT
    / ".superpowers"
    / "sdd"
    / "2026-08-28-cp34-preset-effect-control"
    / "runs"
    / "20260906T001130-0700-uc472-official-reacquisition"
    / "extracted"
    / "hwaccess"
    / "dspusbdevice.dll"
)


def _load_analyzer(test_case):
    test_case.assertTrue(
        ANALYZER.is_file(), "UC 4.7.2 writer-sink analyzer is missing")
    spec = importlib.util.spec_from_file_location(
        "cp34_uc472_record_writer_sink", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Uc472RecordWriterSinkTests(unittest.TestCase):
    maxDiff = None

    @unittest.skipUnless(UC472_DLL.is_file(), "pinned UC 4.7.2 DLL unavailable")
    def test_save_record_starts_with_tagged_map_not_native_u32_two(self):
        module = _load_analyzer(self)
        report = module.analyze(UC472_DLL.read_bytes())

        self.assertEqual(
            report,
            {
                "boundary": (
                    "UC472_SERIALIZER_RESOLVED_DEVICE_COMMIT_RUNTIME_"
                    "COMPONENT_SELECTION_AND_AUDIBILITY_REMAIN_UNOBSERVED"
                ),
                "first_write": {
                    "adapter": "0x1800649a0",
                    "adapter_record_flow": (
                        "writer+8 receiver +0x10 -> writer+0x18 -> r14 record"
                    ),
                    "archive_call": "0x180068a1e -> writer vtable+0x8",
                    "cursor_after_success": 1,
                    "cursor_before": 0,
                    "destination": "record.data(+0x10)+record.cursor(+0x2c)",
                    "length_after_success": 1,
                    "length_before": 0,
                    "logical_byte_hex": "7b",
                    "logical_size": 1,
                    "native_u32_two_prefix_inserted": False,
                    "physical_prefix_hex": "7b",
                    "record_append": "0x180063060",
                    "record_copy": "0x1800630e0 -> memcpy",
                },
                "post_serializer_send": {
                    "caller_pair": (
                        "0x180041c1c snapshot then 0x180041c33 send, "
                        "same r14d slot"
                    ),
                    "fragmenter": "0x180050f10",
                    "fragmenter_record_members": "data +0x10, length +0x30",
                    "post_serializer_mutation": False,
                    "snapshot_return": (
                        "0x180042113 serializer call -> 0x180042118 success return"
                    ),
                },
                "reconciliation": {
                    "firmware_recall": (
                        "stored_record[0:4] reaches 0x531e0 unchanged"
                    ),
                    "firmware_required_native_u32": "0x00000002",
                    "uc472_physical_first_byte": "0x7b",
                    "uc472_prefix_eligible_for_native_u32_two": False,
                },
                "record_collection": {
                    "count": 4,
                    "element_constructor": "0x18002fdf0",
                    "element_stride": "0x38",
                    "owner_member": "controller+0x2d8 -> controller+0x340",
                    "record_append_target": "0x180063060",
                    "record_reset_target": "0x180063020",
                    "record_vtable": "0x18043a658",
                    "vector_constructor_call": (
                        "0x18003067f -> 0x1800d0930"
                    ),
                },
                "serializer_writer": {
                    "adapter_output_member": "writer+0x18 = r14 record",
                    "adapter_primary_vtable": "0x18043aa08",
                    "adapter_secondary_vtable": "0x18043aa50",
                    "cursor_reset": (
                        "0x18002e44a -> record vtable+0x8 -> 0x180063020"
                    ),
                    "function": "0x18002e270",
                    "length_reset": "0x18002e44d: record+0x30 = 0",
                    "output_record": "r14",
                },
                "source": {
                    "image_base": "0x180000000",
                    "sha256": (
                        "de685e89c88b191b9709145056aa37d58a76f141a53a9c153"
                        "3dff917f611fd28"
                    ),
                    "size": 4_979_672,
                },
                "status": (
                    "UC472_SAVE_SERIALIZER_SOURCE_BOUND_RECORD_BYTE_ZERO_"
                    "0X7B_NO_NATIVE_U32_TWO_PREFIX"
                ),
            },
        )

    @unittest.skipUnless(UC472_DLL.is_file(), "pinned UC 4.7.2 DLL unavailable")
    def test_analyzer_rejects_a_same_size_unpinned_image(self):
        module = _load_analyzer(self)
        changed = bytearray(UC472_DLL.read_bytes())
        changed[-1] ^= 1
        with self.assertRaisesRegex(module.AnalysisError, "SHA-256 differs"):
            module.analyze(bytes(changed))


if __name__ == "__main__":
    unittest.main()
