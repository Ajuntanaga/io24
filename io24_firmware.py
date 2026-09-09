#!/usr/bin/env python3
"""Offline inspector/extractor for the Revelator io24 vendor firmware package.

This module is deliberately not a device tool.  It can inspect or extract the
complete, pinned UC 4.7.2 package and it refuses every firmware-write request.
It has no USB enumeration, defaults restore, reset, detach, or staging command.

The complete vendor package is a recovery prerequisite, not a flashable image:
the vendor compatibility/update transport has not been reproduced here.
"""

import hashlib
import struct
import sys
import zlib

VID = 0x194F
PID_RUN = 0x0422           # Revelator io24, application mode
PID_DFU = 0x0405           # ...the same unit in bootloader mode

# Where the firmware image lives inside PreSonus's own DLL. Recovered in this
# project (see re/README.txt); kept here so the extraction is reproducible
# rather than a magic file someone has to be handed.
DLL_FW_START = 0x216030
# UC 4.7.2 registers this entire package, not merely the Cortex-M application
# span.  The old value (0x323a70) produced a 0x10da40-byte truncation and must
# never be accepted as an update image.
VENDOR_PACKAGE_LENGTH = 0x12A694
DLL_FW_END = DLL_FW_START + VENDOR_PACKAGE_LENGTH
IO24_PACKAGE_TARGET = 0x194F0407
IO24_PACKAGE_IMAGE_ID = 1
UC472_IO24_PACKAGE_SHA256 = (
    "790f668608448b7c9f244c360ad72e3c51f71b4e8a3d828eab0e08cd03b35de1")

TL_METADATA_MAGIC = 0xE1BEADDE
TL_METADATA_TAG = b"TL#IMG#METADATA#"
TL_METADATA_HEADER_SIZE = 0x3C
TL_METADATA_TRAILER_SIZE = 7  # three reserved bytes followed by CRC32
TL_METADATA_MIN_SIZE = 0x3C
CRC32_SIZE = 4


class FirmwarePackageError(ValueError):
    """A file is not a complete, self-consistent Thesycon firmware package."""


def _u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def _metadata_offsets(data):
    """Yield offsets of valid TL image-metadata headers in *data*.

    The marker is retained in the vendor package and is a more stable anchor
    than a DLL offset.  Its first eight bytes also make accidental string
    matches unsuitable as headers.
    """
    start = 0
    while True:
        tag = data.find(TL_METADATA_TAG, start)
        if tag < 0:
            return
        header = tag - 8
        start = tag + 1
        if header < 0 or header + TL_METADATA_MIN_SIZE > len(data):
            continue
        if _u16(data, header) != TL_METADATA_HEADER_SIZE:
            continue
        if _u32(data, header + 4) != TL_METADATA_MAGIC:
            continue
        yield header


def parse_package_metadata(package):
    """Return the TL metadata needed to validate an offline vendor package.

    The image-size field is the byte count protected by the package CRC; the
    package has seven additional bytes (three reserved bytes and the CRC32).
    This function intentionally describes only fields that are independently
    anchored in the UC 4.7.2 payload, rather than guessing undocumented TLV
    semantics.
    """
    headers = list(_metadata_offsets(package))
    if len(headers) != 1:
        raise FirmwarePackageError(
            "expected exactly one TL image-metadata header, found %d" % len(headers))
    offset = headers[0]
    metadata_size = _u32(package, offset + 0x18)
    if metadata_size < TL_METADATA_MIN_SIZE or offset + metadata_size > len(package):
        raise FirmwarePackageError("TL metadata size is outside package bounds")
    protected_length = _u32(package, offset + 0x30)
    expected_length = protected_length + TL_METADATA_TRAILER_SIZE
    if expected_length != len(package):
        raise FirmwarePackageError(
            "incomplete or trailing data: metadata requires 0x%x bytes, got 0x%x"
            % (expected_length, len(package)))
    reserved = package[protected_length:protected_length + 3]
    if reserved != b"\0\0\0":
        raise FirmwarePackageError("unexpected nonzero bytes before package CRC32")
    return {
        "metadata_offset": offset,
        "metadata_size": metadata_size,
        "format_version": _u16(package, offset + 2),
        "target": _u32(package, offset + 0x20),
        "image_id": _u32(package, offset + 0x24),
        "protected_length": protected_length,
        "package_length": expected_length,
    }


def inspect_firmware_package(package):
    """Validate and describe a complete UC Thesycon firmware package.

    This is read-only and contains no device, DFU, or image-modification path.
    A successful result proves structural consistency only; it does *not*
    establish that an updater or a device will accept the package.
    """
    metadata = parse_package_metadata(package)
    protected_length = metadata["protected_length"]
    stored_crc32 = _u32(package, len(package) - CRC32_SIZE)
    calculated_crc32 = zlib.crc32(package[:protected_length]) & 0xffffffff
    if calculated_crc32 != stored_crc32:
        raise FirmwarePackageError(
            "CRC32 mismatch: stored 0x%08x, calculated 0x%08x"
            % (stored_crc32, calculated_crc32))
    metadata.update({
        "stored_crc32": stored_crc32,
        "firmware_version": image_version(package),
    })
    return metadata


def inspect_io24_recovery_package(package):
    """Validate the exact, known io24 UC 4.7.2 recovery package.

    ``inspect_firmware_package`` deliberately remains a structural parser for
    tests and forensic work.  Extraction, however, is a recovery boundary: it
    accepts only the known io24 target, image id, vector table, package length,
    and complete-package digest.  A merely self-consistent foreign or newer
    package must be reviewed before it can become a recovery source.
    """
    metadata = inspect_firmware_package(package)
    if metadata["target"] != IO24_PACKAGE_TARGET:
        raise FirmwarePackageError(
            "unexpected package target: 0x%08x" % metadata["target"])
    if metadata["image_id"] != IO24_PACKAGE_IMAGE_ID:
        raise FirmwarePackageError(
            "unexpected package image id: %d" % metadata["image_id"])
    if len(package) != VENDOR_PACKAGE_LENGTH:
        raise FirmwarePackageError(
            "unexpected io24 package length: 0x%x" % len(package))
    if not _looks_like_vector_table(package, 0):
        raise FirmwarePackageError("io24 package lacks the expected application vector")
    digest = hashlib.sha256(package).hexdigest()
    if digest != UC472_IO24_PACKAGE_SHA256:
        raise FirmwarePackageError(
            "unknown io24 package digest: %s" % digest)
    version = image_version(package)
    if version is None:
        raise FirmwarePackageError("io24 package lacks the expected USB descriptor")
    metadata.update({"firmware_version": version, "sha256": digest})
    return metadata


def _looks_like_vector_table(data, offset):
    """Conservative Cortex-M/XMOS application-vector check."""
    if offset < 0 or offset + 8 > len(data):
        return False
    stack, reset = struct.unpack_from("<II", data, offset)
    return (0x20000000 <= stack < 0x20080000 and
            0x60000001 <= reset < 0x60200000 and reset & 1)


# --------------------------------------------------------------------------
# Firmware packages (offline only)
# --------------------------------------------------------------------------
def locate_firmware(data):
    """Find one complete self-validating io24 package inside a UC DLL.

    This deliberately uses TL metadata plus the package CRC instead of trying
    to infer an end from padding.  The old padding heuristic cut the 4.7.2
    package at 0x10da40 and silently discarded valid package metadata.
    Returns ``(start, end, version)`` or ``(None, None, None)``.
    """
    candidates = []
    for metadata in _metadata_offsets(data):
        # The application vector table precedes metadata.  Bound the scan so a
        # malformed host DLL cannot make this routine unexpectedly expensive.
        lo = max(0, metadata - 0x400000)
        for base in range(metadata & ~3, lo - 1, -4):
            if not _looks_like_vector_table(data, base):
                continue
            try:
                info = inspect_firmware_package(
                    data[base:base + _u32(data, metadata + 0x30) +
                         TL_METADATA_TRAILER_SIZE])
            except FirmwarePackageError:
                continue
            if info["metadata_offset"] != metadata - base:
                continue
            if (info["target"] == IO24_PACKAGE_TARGET and
                    info["image_id"] == IO24_PACKAGE_IMAGE_ID and
                    image_version(data[base:base + info["package_length"]])):
                candidates.append((base, base + info["package_length"],
                                   info["firmware_version"]))
            break
    if len(candidates) == 1:
        return candidates[0]
    return None, None, None


def extract_firmware(dll_path, out_path):
    """Pull the io24 image out of a Universal Control dspusbdevice.dll.

    Tries the registered UC 4.7.2 package extent first, then falls back to
    self-validating TL metadata discovery.  The output is a vendor package,
    not a raw application binary and not a flash authorization.
    """
    with open(dll_path, "rb") as source:
        data = source.read()
    if len(data) >= DLL_FW_END:
        img = data[DLL_FW_START:DLL_FW_END]
        try:
            info = inspect_io24_recovery_package(img)
        except FirmwarePackageError:
            info = None
        if info and info["firmware_version"]:
            with open(out_path, "wb") as destination:
                destination.write(img)
            return out_path, len(img), info["firmware_version"]
    start, end, v = locate_firmware(data)
    if start is None:
        raise ValueError("no io24 firmware image found in %s — is this the "
                         "right DLL? (expected hwaccess/dspusbdevice.dll)"
                         % dll_path)
    img = data[start:end]
    # Keep this explicit even after locate_firmware succeeded: extraction is a
    # security boundary and must never recreate the historical truncated file.
    info = inspect_io24_recovery_package(img)
    with open(out_path, "wb") as destination:
        destination.write(img)
    return out_path, len(img), v


def image_version(img):
    """bcdDevice from the USB device descriptor embedded in the image.

    This is how the firmware announces its own version, so it is the honest
    way to identify an image rather than trusting a filename.
    """
    needle = struct.pack("<HH", VID, PID_RUN)
    i = img.find(needle)
    if i < 0 or i + 6 > len(img):
        return None
    bcd = struct.unpack("<H", img[i + 4:i + 6])[0]
    return "%x.%02x" % (bcd >> 8, bcd & 0xFF)


def flash(image_path, alt=None):
    """Refuse raw DFU writes until the vendor update protocol is recovered.

    A correct package CRC is only an integrity check.  It is not evidence that
    a bare ``dfu-util -D`` write supplies the image-selection and compatibility
    negotiation performed by Universal Control.
    """
    return False, ("refusing raw DFU write: this tool is offline-only; "
                   "vendor compatibility/update transport is not implemented")


# --------------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "help"

    if cmd == "extract":
        if len(args) < 3:
            print("usage: io24_firmware.py extract <dspusbdevice.dll> <out.bin>")
            return 2
        path, n, ver = extract_firmware(args[1], args[2])
        print("wrote %s (%d bytes), image reports firmware %s" % (path, n, ver))
        return 0

    if cmd == "identify":
        if len(args) < 2:
            print("usage: io24_firmware.py identify <vendor-package.bin>")
            return 2
        try:
            info = inspect_io24_recovery_package(open(args[1], "rb").read())
        except (OSError, FirmwarePackageError) as e:
            print("invalid io24 recovery package: %s" % e)
            return 1
        print("%s: io24 firmware %s" % (args[1], info["firmware_version"]))
        return 0

    if cmd == "inspect":
        if len(args) < 2:
            print("usage: io24_firmware.py inspect <vendor-package.bin>")
            return 2
        try:
            info = inspect_firmware_package(open(args[1], "rb").read())
        except (OSError, FirmwarePackageError) as e:
            print("invalid firmware package: %s" % e)
            return 1
        print("%s: complete vendor package" % args[1])
        for key in ("firmware_version", "package_length", "protected_length",
                    "metadata_offset", "metadata_size", "format_version",
                    "target", "image_id", "stored_crc32"):
            value = info[key]
            if key.endswith("length") or key.endswith("offset") or key in ("target", "stored_crc32"):
                value = "0x%x" % value
            print("  %s: %s" % (key, value))
        return 0

    if cmd == "flash":
        ok, out = flash(None)
        print(out)
        return 2

    if cmd in ("status", "defaults", "detach"):
        print("%s is not available in this offline-only tool; a separately "
              "authorized live workflow is required" % cmd)
        return 2

    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
