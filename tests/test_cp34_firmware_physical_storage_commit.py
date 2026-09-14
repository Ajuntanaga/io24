#!/usr/bin/env python3
"""Hardware-free contract for the CP34 physical storage write completion."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "cp34_firmware_physical_storage_commit.py"
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
        test_case, "io24_firmware_physical_storage_package",
        ROOT / "io24_firmware.py")
    dll = UC5_DLL.read_bytes()
    package = dll[
        package_module.DLL_FW_START:package_module.DLL_FW_END]
    package_module.inspect_io24_recovery_package(package)
    return package[:FIRMWARE_SIZE]


class FirmwarePhysicalStorageCommitTests(unittest.TestCase):
    maxDiff = None

    @unittest.skipUnless(UC5_DLL.is_file(), "pinned installed UC5 DLL unavailable")
    def test_stat_write_reaches_synchronous_compare_program_path(self):
        module = _load_module(
            self, "cp34_firmware_physical_storage_commit", ANALYZER)
        report = module.analyze(_pinned_application(self))

        self.assertEqual(
            report,
            {
                "backend_resolution": {
                    "adapter_receiver_join": (
                        "0x20d3c passes device+8 to 0x3d4bc; 0x3d4bc "
                        "stores it at singleton+0x38; 0x316dc/0x316b0 "
                        "reloads that field before device vtable +0x10"
                    ),
                    "device_constructor": "0x4b748",
                    "device_storage_subobject": "device+0xe9c",
                    "manager_constructor": "0x4c120 at device+0x1108",
                    "physical_interface": "manager+0x27c = device+0x1384",
                    "physical_interface_constructor": "0x4ab24",
                    "physical_vtable": "0x6012bc80",
                    "query_chain": (
                        "0x20808 -> device vtable +0x84/0x4b410 -> "
                        "manager vtable +0x14/0x4bf04"
                    ),
                    "read_slot": "+0x8 -> 0x4aaf4",
                    "write_slot": "+0x4 -> 0x4aa90",
                },
                "completion_semantics": {
                    "backend_flag_one": "compare before program",
                    "changed_bytes": "0x52cd8 -> 0x52c0c",
                    "compare": "0x52d50 -> memcmp 0x6012d8b8",
                    "program_transaction": "0x52c5e -> 0x526dc",
                    "ready_poll_after_program": "0x52c68 -> 0x52a70",
                    "separate_commit_after_success": False,
                    "unchanged_bytes": "successful no-op after comparison",
                    "write_return": (
                        "success only after compare and, when changed, "
                        "program transaction plus ready poll"
                    ),
                },
                "logical_region": {
                    "capacity": 0x7FC0,
                    "descriptor": "0x6012bc68",
                    "descriptor_words": [0x8000, 0x40, 1, 10],
                },
                "remaining_live_boundary": (
                    "SET_P_TRANSPORT_HAS_NO_READABLE_STORAGE_RESULT; stored "
                    "bytes and successful physical return remain unobserved"
                ),
                "source": {
                    "image_base": "0x60020000",
                    "sha256": (
                        "65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a"
                        "7679e387952eb1a"
                    ),
                    "size": 1_104_448,
                },
                "status": (
                    "FIRMWARE_STAT_PHYSICAL_BACKEND_SOURCE_BOUND_SYNCHRONOUS_"
                    "COMPARE_PROGRAM_NO_SEPARATE_COMMIT"
                ),
            },
        )

    @unittest.skipUnless(UC5_DLL.is_file(), "pinned installed UC5 DLL unavailable")
    def test_analyzer_rejects_a_same_size_unpinned_firmware(self):
        module = _load_module(
            self, "cp34_firmware_physical_storage_commit_mutation", ANALYZER)
        changed = bytearray(_pinned_application(self))
        changed[-1] ^= 1
        with self.assertRaisesRegex(module.AnalysisError, "SHA-256 differs"):
            module.analyze(bytes(changed))


if __name__ == "__main__":
    unittest.main()
