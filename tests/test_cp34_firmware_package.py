#!/usr/bin/env python3
"""Offline contracts for the UC 4.7.2 io24 vendor firmware package."""

import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zlib


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("io24_firmware", ROOT / "io24_firmware.py")
FIRMWARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIRMWARE)

# This artifact is local investigator evidence, never a required repository
# fixture.  CI and clean checkouts exercise the synthetic package below.
UC472_DLL = Path("/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll")
HISTORICAL_TRUNCATION = Path("/tmp/io24-fw-1.28.7DrxHf.bin")


def synthetic_package():
    """Build a minimal structurally valid package for parser-only tests."""
    protected_length = 0x139
    package = bytearray(protected_length + FIRMWARE.TL_METADATA_TRAILER_SIZE)
    struct.pack_into("<II", package, 0, 0x20000600, 0x60020335)
    metadata = 0x80
    struct.pack_into("<HHI", package, metadata,
                     FIRMWARE.TL_METADATA_HEADER_SIZE, 1,
                     FIRMWARE.TL_METADATA_MAGIC)
    package[metadata + 8:metadata + 8 + len(FIRMWARE.TL_METADATA_TAG)] = \
        FIRMWARE.TL_METADATA_TAG
    struct.pack_into("<I", package, metadata + 0x18, 0x3C)
    struct.pack_into("<I", package, metadata + 0x20, 0x194F0407)
    struct.pack_into("<I", package, metadata + 0x24, 1)
    struct.pack_into("<I", package, metadata + 0x30, protected_length)
    struct.pack_into("<I", package, len(package) - 4,
                     zlib.crc32(package[:protected_length]) & 0xffffffff)
    return bytes(package)


class FirmwarePackageTests(unittest.TestCase):
    def test_synthetic_package_parses_and_verifies(self):
        info = FIRMWARE.inspect_firmware_package(synthetic_package())
        self.assertEqual(info["package_length"], 0x140)
        self.assertEqual(info["protected_length"], 0x139)
        self.assertEqual(info["metadata_offset"], 0x80)
        self.assertEqual(info["target"], 0x194F0407)
        self.assertEqual(info["image_id"], 1)

    def test_missing_tail_is_rejected_even_if_metadata_is_present(self):
        with self.assertRaisesRegex(FIRMWARE.FirmwarePackageError,
                                    "incomplete or trailing data"):
            FIRMWARE.inspect_firmware_package(synthetic_package()[:-1])

    def test_crc_mismatch_is_rejected(self):
        corrupted = bytearray(synthetic_package())
        corrupted[0x20] ^= 1
        with self.assertRaisesRegex(FIRMWARE.FirmwarePackageError, "CRC32 mismatch"):
            FIRMWARE.inspect_firmware_package(bytes(corrupted))

    def test_raw_dfu_write_is_refused(self):
        ok, message = FIRMWARE.flash("irrelevant.bin")
        self.assertFalse(ok)
        self.assertIn("offline-only", message)

    def test_generic_parser_is_not_mistaken_for_a_recovery_acceptance_gate(self):
        # The synthetic fixture is structurally sound but has neither the
        # complete known length nor the pinned package digest.  It must remain
        # usable for parser tests while being rejected as a recovery source.
        with self.assertRaisesRegex(FIRMWARE.FirmwarePackageError,
                                    "unexpected io24 package length"):
            FIRMWARE.inspect_io24_recovery_package(synthetic_package())

    def test_offline_tool_contains_no_live_defaults_or_detach_path(self):
        source = (ROOT / "io24_firmware.py").read_text()
        self.assertNotIn("restore_defaults", source)
        self.assertNotIn("detach_to_bootloader", source)
        self.assertNotIn("usb.core", source)
        self.assertNotIn("/sys/bus/usb/devices", source)

    @unittest.skipUnless(UC472_DLL.is_file(), "local UC 4.7.2 DLL is unavailable")
    def test_uc472_registered_package_is_full_and_self_validating(self):
        data = UC472_DLL.read_bytes()
        package = data[FIRMWARE.DLL_FW_START:FIRMWARE.DLL_FW_END]
        info = FIRMWARE.inspect_firmware_package(package)
        self.assertEqual(len(package), FIRMWARE.VENDOR_PACKAGE_LENGTH)
        self.assertEqual(info["package_length"], 0x12A694)
        self.assertEqual(info["protected_length"], 0x12A68D)
        self.assertEqual(info["metadata_offset"], 0x205E0)
        self.assertEqual(info["target"], 0x194F0407)
        self.assertEqual(info["stored_crc32"], 0xED65737C)
        self.assertEqual(
            FIRMWARE.inspect_io24_recovery_package(package)["sha256"],
            FIRMWARE.UC472_IO24_PACKAGE_SHA256)

        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "io24-vendor-package.bin"
            _, size, _ = FIRMWARE.extract_firmware(str(UC472_DLL), str(out))
            self.assertEqual(size, FIRMWARE.VENDOR_PACKAGE_LENGTH)
            self.assertEqual(out.read_bytes(), package)

    @unittest.skipUnless(HISTORICAL_TRUNCATION.is_file(),
                         "historical truncated extraction is unavailable")
    def test_historical_0x10da40_extraction_is_rejected(self):
        truncated = HISTORICAL_TRUNCATION.read_bytes()
        self.assertEqual(len(truncated), 0x10DA40)
        with self.assertRaises(FIRMWARE.FirmwarePackageError):
            FIRMWARE.inspect_firmware_package(truncated)


if __name__ == "__main__":
    unittest.main()
