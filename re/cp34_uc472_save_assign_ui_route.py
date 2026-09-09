#!/usr/bin/env python3
"""Source-bind UC 4.7.2 preset UI actions to its existing DSP routes.

This analyzer is deliberately exact-version and static.  It parses the
embedded DEFAULT.SKIN package, checks the action registrations and dispatch
edges in ``studiolivepanel.dll``, verifies the UCNet import topology, and
binds the panel's high-level ``StorePreset`` message to the matching receiver
and existing ``MemP/PrsM`` and ``MemP/Stat`` builders in the exact
``dspusbdevice.dll``.

Vendor code is never loaded or executed.  Wine, USB, audio, firmware hardware,
and the network are never accessed.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ElementTree
import zlib

from capstone.x86_const import X86_INS_CALL, X86_INS_LEA


RE_DIR = Path(__file__).resolve().parent
if str(RE_DIR) not in sys.path:
    sys.path.insert(0, str(RE_DIR))

import cp34_uc5_serializer_comparison as pe_helpers  # noqa: E402
import cp34_uc472_record_writer_sink as writer_sink  # noqa: E402


class AnalysisError(ValueError):
    """An input differs from the exact source or expected static route."""


SOURCES = {
    "panel": {
        "size": 41_828_312,
        "sha256": "52e48cb1453b815abc4b55fd0232131e11115d1aceb2eb0ed899750db6c08dd8",
        "image_base": 0x180000000,
    },
    "service": {
        "size": 456_152,
        "sha256": "b8e97749f44a610aa621b3325303ce992096c7046cbb635694c115d3fcd8ee71",
        "image_base": 0x140000000,
    },
    "universal_control": {
        "size": 22_172_120,
        "sha256": "27f9fe550b466c9d783e3432d6663bb02af9aa001b23165985a56c96005e1a96",
        "image_base": 0x140000000,
    },
    "ucnet": {
        "size": 209_368,
        "sha256": "61aeda721584b7111a5ae5c296ac6ab824d0cd3d1f4306b9fcb8d796fdda32de",
        "image_base": 0x180000000,
    },
    "dsp": {
        "size": 4_979_672,
        "sha256": "de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28",
        "image_base": 0x180000000,
    },
}

PANEL_VTABLE = 0x1803B25A8
PANEL_STORE_PRESET = 0x18006EF10
PANEL_RESTORE_PRESET = 0x18006F310
PANEL_SEND_TO_MIXER = 0x1800FE080
PANEL_TRANSFER = 0x180113BA0
PANEL_STORE_NAMED_REMOTE = 0x180103BA0

DSP_REQUEST_RECEIVER = 0x18003AEF0
DSP_SERIALIZER = 0x18002E270
DSP_LIBRARY_SEND = 0x180037250
DSP_MEMP_FRAGMENTER = 0x180050F10
DSP_SENDER_VTABLE = 0x1804393E0

DEFAULT_SKIN_SIZE = 21_371_451
DEFAULT_SKIN_RVA = 0x1320348
DEFAULT_SKIN_FILE_OFFSET = 0x1305F48
PACKAGE_TOC_OFFSET = 0x145BD7A
PACKAGE_TOC_CONSUMED = 23_681
PACKAGE_FOOTER_SIZE = 64
UCEASY_OFFSET = 0x14579B5
UCEASY_COMPRESSED_SIZE = 5_918
UCEASY_RAW_SIZE = 39_057
UCEASY_SHA256 = "a710cf06425a48ff1bb0e9ae72ad74d15613b939e675d134b27f4441074d5dfa"


PANEL_EXACT_BYTES = {
    # Action registrations.
    0x1800F60B0: "488d0579452c00",       # sendToMixer
    0x1800F60BF: "41b852040000",         # id 0x452
    0x1800F66D5: "488d0524402c00",       # storeRemotePresetName
    0x1800F66EB: "41b85e040000",         # id 0x45e
    0x1800F670A: "488d0547402c00",       # storeNamedRemotePreset
    0x1800F6720: "41b85f040000",         # id 0x45f

    # The generic transfer obtains the source through virtual +0x88, swaps the
    # remote owner's +0x298 dispatcher temporarily, and creates ZStr items.
    0x180113BCA: "ff9088000000",
    0x180113D0C: "4d8bafe8010000",
    0x180113D13: "4981c598020000",
    0x180113D2A: "49897500",
    0x18011417A: "ba7274535a",
    0x18011423E: "ba7274535a",

    # High-level message dispatch through object+0x298, vtable+0x80.
    0x18006F28D: "488b8e98020000",
    0x18006F294: "488b01",
    0x18006F29F: "ff9080000000",

    # Jackson's four-value slot property registration.
    0x1800CA4E3: "c7442420ec030000",
    0x1800CA4F2: "41b804000000",
}

DSP_EXACT_BYTES = {
    # The StorePreset branch serializes the selected component, updates its
    # library record, then invokes the existing PrsM sender.
    0x18003B5AB: "498bd7",
    0x18003B5AE: "488d4c2420",
    0x18003B5B8: "488d1cf6",
    0x18003B5BC: "48c1e305",
    0x18003B5D7: "8bd6",
    0x18003B5D9: "498bcd",

    # The library sender constructs PrsM plus Appl and dispatches through the
    # same sender vtable used by the active-slot Stat route.
    0x180037293: "c74424304d737250",
    0x18003729B: "48c74424406c707041",
    0x1800372A4: "488d14c0",
    0x1800372AB: "48c1e205",
    0x1800372B7: "ff5010",
}


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _identity(name, data):
    expected = SOURCES[name]
    _require(
        len(data) == expected["size"],
        "%s size differs: %d" % (name, len(data)),
    )
    digest = hashlib.sha256(data).hexdigest()
    _require(
        digest == expected["sha256"],
        "%s SHA-256 differs: %s" % (name, digest),
    )
    return {
        "image_base": hex(expected["image_base"]),
        "sha256": digest,
        "size": len(data),
    }


def _parse_pe(name, data):
    try:
        image_base, sections = pe_helpers._parse_pe(data)
    except pe_helpers.PeAnalysisError as error:
        raise AnalysisError("%s: %s" % (name, error)) from error
    _require(
        image_base == SOURCES[name]["image_base"],
        "%s image base differs: %#x" % (name, image_base),
    )
    return image_base, sections


def _section_bytes(image_base, sections, address, size):
    try:
        return pe_helpers._section_bytes(image_base, sections, address, size)
    except pe_helpers.AnalysisError as error:
        raise AnalysisError(str(error)) from error


def _require_bytes(image_base, sections, address, expected_hex):
    try:
        pe_helpers._require_bytes(image_base, sections, address, expected_hex)
    except pe_helpers.AnalysisError as error:
        raise AnalysisError(str(error)) from error


def _require_direct_target(image_base, sections, address, target):
    try:
        pe_helpers._require_direct_target(image_base, sections, address, target)
    except pe_helpers.AnalysisError as error:
        raise AnalysisError(str(error)) from error


def _rip_target(image_base, sections, address, instruction_id):
    try:
        return pe_helpers._rip_memory_target(
            image_base, sections, address, instruction_id)
    except pe_helpers.AnalysisError as error:
        raise AnalysisError(str(error)) from error


def _read_u64(image_base, sections, address):
    return struct.unpack("<Q", _section_bytes(image_base, sections, address, 8))[0]


def _require_ascii(image_base, sections, address, expected):
    raw = _section_bytes(image_base, sections, address, len(expected) + 1)
    _require(
        raw == expected.encode("ascii") + b"\0",
        "ASCII literal differs at %#x" % address,
    )


def _rva_file_offset(data, sections, rva):
    try:
        return pe_helpers._rva_file_offset(data, sections, rva)
    except pe_helpers.AnalysisError as error:
        raise AnalysisError(str(error)) from error


def _pe_data_directory(data, index):
    _require(len(data) >= 0x40, "truncated PE image")
    pe_offset, = struct.unpack_from("<I", data, 0x3C)
    _require(pe_offset + 24 <= len(data), "truncated PE header")
    optional = pe_offset + 24
    magic, = struct.unpack_from("<H", data, optional)
    if magic == 0x20B:
        directory_count_offset = optional + 108
        directory_offset = optional + 112
    elif magic == 0x10B:
        directory_count_offset = optional + 92
        directory_offset = optional + 96
    else:
        raise AnalysisError("unsupported PE optional-header magic %#x" % magic)
    directory_count, = struct.unpack_from("<I", data, directory_count_offset)
    _require(index < directory_count, "PE data directory %d is absent" % index)
    entry = directory_offset + index * 8
    _require(entry + 8 <= len(data), "truncated PE data-directory table")
    return struct.unpack_from("<II", data, entry)


def _resource_name(data, sections, resource_rva, field):
    if not (field & 0x80000000):
        return field
    string_rva = resource_rva + (field & 0x7FFFFFFF)
    offset = _rva_file_offset(data, sections, string_rva)
    _require(offset + 2 <= len(data), "truncated resource name")
    length, = struct.unpack_from("<H", data, offset)
    end = offset + 2 + length * 2
    _require(end <= len(data), "truncated resource name text")
    try:
        return data[offset + 2:end].decode("utf-16le")
    except UnicodeDecodeError as error:
        raise AnalysisError("invalid UTF-16 resource name") from error


def _resource_leaves(data, sections):
    resource_rva, resource_size = _pe_data_directory(data, 2)
    _require(resource_rva and resource_size >= 16, "PE resource directory is absent")
    leaves = []

    def walk(relative, path, depth):
        _require(depth <= 8, "resource directory nesting is excessive")
        directory_rva = resource_rva + relative
        directory_offset = _rva_file_offset(data, sections, directory_rva)
        _require(directory_offset + 16 <= len(data), "truncated resource directory")
        named, ids = struct.unpack_from("<HH", data, directory_offset + 12)
        count = named + ids
        _require(count <= 4096, "resource directory has excessive entries")
        for index in range(count):
            entry_offset = directory_offset + 16 + index * 8
            _require(entry_offset + 8 <= len(data), "truncated resource entry")
            name_field, child_field = struct.unpack_from("<II", data, entry_offset)
            name = _resource_name(data, sections, resource_rva, name_field)
            child_relative = child_field & 0x7FFFFFFF
            if child_field & 0x80000000:
                walk(child_relative, path + (name,), depth + 1)
                continue
            leaf_rva = resource_rva + child_relative
            leaf_offset = _rva_file_offset(data, sections, leaf_rva)
            _require(leaf_offset + 16 <= len(data), "truncated resource leaf")
            data_rva, size, codepage, reserved = struct.unpack_from(
                "<IIII", data, leaf_offset)
            _require(reserved == 0, "resource leaf reserved field differs")
            raw_offset = _rva_file_offset(data, sections, data_rva)
            _require(raw_offset + size <= len(data), "resource data exceeds input")
            leaves.append({
                "path": path + (name,),
                "rva": data_rva,
                "size": size,
                "codepage": codepage,
                "file_offset": raw_offset,
                "data": data[raw_offset:raw_offset + size],
            })

    walk(0, (), 0)
    return leaves


def _read_utf16z(blob, cursor, limit):
    start = cursor
    while cursor + 2 <= limit and blob[cursor:cursor + 2] != b"\0\0":
        cursor += 2
    _require(cursor + 2 <= limit, "unterminated PACKAGEF UTF-16 name")
    try:
        value = blob[start:cursor].decode("utf-16le")
    except UnicodeDecodeError as error:
        raise AnalysisError("invalid PACKAGEF UTF-16 name") from error
    return value, cursor + 2


def _parse_package(package):
    _require(len(package) == DEFAULT_SKIN_SIZE, "DEFAULT.SKIN size differs")
    _require(package[:8] == b"PACKAGEF", "DEFAULT.SKIN PACKAGEF header differs")
    signature = b"Root\x01\x00\x00\x00"
    toc_offset = package.rfind(signature)
    _require(toc_offset == PACKAGE_TOC_OFFSET, "PACKAGEF TOC offset differs")

    cursor = toc_offset + 4
    root_version, root_count = struct.unpack_from("<II", package, cursor)
    cursor += 8
    _require(root_version == 1, "PACKAGEF root version differs")
    _require(root_count == 13, "PACKAGEF root entry count differs")
    files = []

    def parse_nodes(count, parent, depth):
        nonlocal cursor
        _require(depth <= 16, "PACKAGEF folder nesting is excessive")
        for _ in range(count):
            _require(cursor + 8 <= len(package), "truncated PACKAGEF node")
            tag = package[cursor:cursor + 4]
            version, = struct.unpack_from("<I", package, cursor + 4)
            cursor += 8
            _require(version == 2, "PACKAGEF node version differs")
            name, cursor = _read_utf16z(package, cursor, len(package))
            if tag == b"Fold":
                _require(cursor + 4 <= len(package), "truncated PACKAGEF folder")
                children, = struct.unpack_from("<I", package, cursor)
                cursor += 4
                _require(children <= 4096, "PACKAGEF folder child count is excessive")
                parse_nodes(children, parent + (name,), depth + 1)
            elif tag == b"File":
                _require(cursor + 33 <= len(package), "truncated PACKAGEF file")
                timestamp = package[cursor:cursor + 9]
                cursor += 9
                offset, compressed_size, raw_size = struct.unpack_from(
                    "<QQQ", package, cursor)
                cursor += 24
                files.append({
                    "path": "/".join(parent + (name,)),
                    "timestamp_hex": timestamp.hex(),
                    "offset": offset,
                    "compressed_size": compressed_size,
                    "raw_size": raw_size,
                })
            else:
                raise AnalysisError("unknown PACKAGEF node tag %r" % tag)

    parse_nodes(root_count, (), 0)
    _require(len(files) == 275, "PACKAGEF file count differs")
    _require(cursor - toc_offset == PACKAGE_TOC_CONSUMED,
             "PACKAGEF TOC consumed length differs")
    _require(len(package) - cursor == PACKAGE_FOOTER_SIZE,
             "PACKAGEF footer size differs")

    ordered = sorted(files, key=lambda item: item["offset"])
    next_offset = 8
    for item in ordered:
        _require(item["offset"] == next_offset,
                 "PACKAGEF compressed members are not contiguous")
        end = item["offset"] + item["compressed_size"]
        _require(end <= toc_offset, "PACKAGEF member overlaps its TOC")
        _require(package[item["offset"]:item["offset"] + 1] == b"x",
                 "PACKAGEF member is not a zlib stream")
        next_offset = end
    _require(next_offset == toc_offset, "PACKAGEF member area does not end at TOC")

    matches = [item for item in files if item["path"] == "uceasy/uceasy.xml"]
    _require(len(matches) == 1, "uceasy/uceasy.xml PACKAGEF member differs")
    target = matches[0]
    _require(target["offset"] == UCEASY_OFFSET, "uceasy.xml offset differs")
    _require(target["compressed_size"] == UCEASY_COMPRESSED_SIZE,
             "uceasy.xml compressed size differs")
    _require(target["raw_size"] == UCEASY_RAW_SIZE,
             "uceasy.xml raw size differs")
    compressed = package[
        target["offset"]:target["offset"] + target["compressed_size"]]
    try:
        xml = zlib.decompress(compressed)
    except zlib.error as error:
        raise AnalysisError("uceasy.xml zlib stream differs") from error
    _require(len(xml) == target["raw_size"], "uceasy.xml decoded size differs")
    _require(hashlib.sha256(xml).hexdigest() == UCEASY_SHA256,
             "uceasy.xml SHA-256 differs")
    return files, xml


def _validate_ui_xml(xml):
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise AnalysisError("uceasy.xml is not well formed") from error

    slot_values = sorted({
        int(node.attrib["value"])
        for node in root.iter("RadioButton")
        if node.attrib.get("name") == "presetSlot"
    })
    _require(slot_values == [1, 2, 3, 4], "presetSlot values differ")
    _require(any(
        node.attrib.get("name") == "remoteList"
        and node.attrib.get("tooltip") == "Device Presets"
        for node in root.iter("ListView")
    ), "Device Presets remoteList differs")
    _require(any(
        node.attrib.get("name") == "localList"
        for node in root.iter("ListView")
    ), "Local Presets localList differs")
    _require(any(
        node.attrib.get("title") == "Device Presets"
        for node in root.iter("Label")
    ), "Device Presets label differs")
    _require(any(
        node.attrib.get("title") == "Local Presets"
        for node in root.iter("Label")
    ), "Local Presets label differs")
    _require(any(
        node.attrib.get("name") == "sendToMixer"
        for node in root.iter("Button")
    ), "sendToMixer UI binding differs")
    _require(any(
        node.attrib.get("name") == "storeNamedRemotePreset"
        and node.attrib.get("title") == "Store"
        for node in root.iter("Button")
    ), "storeNamedRemotePreset UI binding differs")
    _require(any(
        node.attrib.get("name") == "storeRemotePresetName"
        for node in root.iter("EditBox")
    ), "storeRemotePresetName UI binding differs")
    return slot_values


def _export_names(data, sections):
    export_rva, export_size = _pe_data_directory(data, 0)
    _require(export_rva and export_size >= 40, "PE export directory is absent")
    offset = _rva_file_offset(data, sections, export_rva)
    _require(offset + 40 <= len(data), "truncated export directory")
    number_of_names, = struct.unpack_from("<I", data, offset + 24)
    names_rva, = struct.unpack_from("<I", data, offset + 32)
    _require(number_of_names <= 65536, "PE export name count is excessive")
    names = set()
    for index in range(number_of_names):
        pointer_offset = _rva_file_offset(data, sections, names_rva + index * 4)
        name_rva, = struct.unpack_from("<I", data, pointer_offset)
        name_offset = _rva_file_offset(data, sections, name_rva)
        end = data.find(b"\0", name_offset, min(len(data), name_offset + 4096))
        _require(end >= 0, "unterminated export name")
        try:
            names.add(data[name_offset:end].decode("ascii"))
        except UnicodeDecodeError as error:
            raise AnalysisError("non-ASCII export name") from error
    return names


def _import_names(data, image_base, sections):
    try:
        return pe_helpers._import_names_by_iat(data, image_base, sections)
    except pe_helpers.AnalysisError as error:
        raise AnalysisError(str(error)) from error


def _require_imports(label, imported_by_iat, required):
    actual = set(imported_by_iat.values())
    missing = sorted(set(required) - actual)
    _require(not missing, "%s UCNet imports differ: %s" % (label, missing))


def _tag_inventory(images):
    tags = ("MemP", "Stat", "PrsM", "SetP", "Appl", "ZStr")
    return {
        name: {tag: data.count(tag.encode("ascii")[::-1]) for tag in tags}
        for name, data in images.items()
    }


def analyze(panel, service, universal_control, ucnet, dsp):
    """Return the exact, hardware-free Save/Assign route report."""
    images = {
        "panel": panel,
        "service": service,
        "universal_control": universal_control,
        "ucnet": ucnet,
        "dsp": dsp,
    }
    sources = {name: _identity(name, data) for name, data in images.items()}
    parsed = {name: _parse_pe(name, data) for name, data in images.items()}

    panel_base, panel_sections = parsed["panel"]
    service_base, service_sections = parsed["service"]
    uc_base, uc_sections = parsed["universal_control"]
    ucnet_base, ucnet_sections = parsed["ucnet"]
    dsp_base, dsp_sections = parsed["dsp"]

    # Parse the actual embedded UI rather than relying on printable strings.
    skin = [
        leaf for leaf in _resource_leaves(panel, panel_sections)
        if leaf["path"] == (10, "DEFAULT.SKIN", 0x409)
    ]
    _require(len(skin) == 1, "DEFAULT.SKIN resource identity differs")
    skin = skin[0]
    _require(skin["rva"] == DEFAULT_SKIN_RVA, "DEFAULT.SKIN RVA differs")
    _require(skin["file_offset"] == DEFAULT_SKIN_FILE_OFFSET,
             "DEFAULT.SKIN file offset differs")
    package_files, ui_xml = _parse_package(skin["data"])
    slot_values = _validate_ui_xml(ui_xml)

    # Action names, ids, and event-handler edges.
    for address, expected in PANEL_EXACT_BYTES.items():
        _require_bytes(panel_base, panel_sections, address, expected)
    panel_direct_edges = {
        0x1800D0ED0: 0x1800F5750,
        0x1800F917F: PANEL_SEND_TO_MIXER,
        0x1800F92EC: 0x1801031F0,
        0x1800F94AA: PANEL_STORE_NAMED_REMOTE,
        0x1800FE8BB: PANEL_TRANSFER,
    }
    for address, target in panel_direct_edges.items():
        _require_direct_target(panel_base, panel_sections, address, target)

    panel_rip_edges = {
        0x1800D0ED6: PANEL_VTABLE,
        0x1800F60B0: 0x1803BA630,
        0x1800F66D5: 0x1803BA700,
        0x1800F670A: 0x1803BA758,
        0x1800CA4C7: 0x1803AF6D0,
        0x18006EFF8: 0x180399748,
        0x18006F091: 0x180399708,
        0x18006F13C: 0x180399758,
        0x18006F1C7: 0x180399710,
    }
    for address, target in panel_rip_edges.items():
        _require(
            _rip_target(panel_base, panel_sections, address, X86_INS_LEA) == target,
            "panel RIP-relative target differs at %#x" % address,
        )

    panel_literals = {
        0x1803BA630: "sendToMixer",
        0x1803BA700: "storeRemotePresetName",
        0x1803BA758: "storeNamedRemotePreset",
        0x1803AF6D0: "presetSlot",
        0x180399708: "presets",
        0x180399710: "presetFile",
        0x180399748: "StorePreset",
        0x180399758: "presetTarget",
    }
    for address, literal in panel_literals.items():
        _require_ascii(panel_base, panel_sections, address, literal)

    _require(_read_u64(panel_base, panel_sections, PANEL_VTABLE + 0x220)
             == PANEL_STORE_PRESET,
             "Jackson panel StorePreset vtable slot differs")
    _require(_read_u64(panel_base, panel_sections, PANEL_VTABLE + 0x228)
             == PANEL_RESTORE_PRESET,
             "Jackson panel RestorePreset vtable slot differs")

    # Source-bind the manager calls to the exact UCNet import slots.
    panel_imports = _import_names(panel, panel_base, panel_sections)
    service_imports = _import_names(service, service_base, service_sections)
    uc_imports = _import_names(universal_control, uc_base, uc_sections)
    dsp_imports = _import_names(dsp, dsp_base, dsp_sections)
    _require_imports("panel", panel_imports, {
        "UCSetReportFunction", "UCGetFileTransferManager", "UCGetNetworkManager"})
    _require_imports("service", service_imports, {
        "UCReportMessage", "UCGetFileTransferManager", "UCSetReportFunction",
        "UCGetNetworkManager", "UCGetMIDINetworkManager"})
    _require_imports("Universal Control", uc_imports, {
        "UCGetNetworkManager", "UCSetReportFunction", "UCGetFileTransferManager"})
    _require_imports("dsp", dsp_imports, {
        "UCGetNetworkManager", "UCReportMessage", "UCGetFileTransferManager"})
    _require(panel_imports.get(
        _rip_target(panel_base, panel_sections, 0x180103E77, X86_INS_CALL))
        == "UCGetNetworkManager",
        "storeNamedRemotePreset network-manager call differs")
    _require(panel_imports.get(
        _rip_target(panel_base, panel_sections, 0x180103E82, X86_INS_CALL))
        == "UCGetFileTransferManager",
        "storeNamedRemotePreset file-transfer-manager call differs")

    exports = _export_names(ucnet, ucnet_sections)
    _require({
        "UCGetFileTransferManager", "UCGetMIDINetworkManager",
        "UCGetNetworkManager", "UCReportMessage", "UCSetReportFunction",
    }.issubset(exports), "ucnet export set differs")

    # Bind the high-level message to the exact DSP receiver and its existing
    # PrsM sender.  The exact Stat writer analyzer independently proves the
    # active-slot record begins at 0x7b and has no native-u32-two prefix.
    for address, expected in DSP_EXACT_BYTES.items():
        _require_bytes(dsp_base, dsp_sections, address, expected)
    dsp_rip_edges = {
        0x18003AF68: 0x180435B60,
        0x18003B3CC: 0x180435B70,
        0x18003B3F7: 0x180435B80,
    }
    for address, target in dsp_rip_edges.items():
        _require(
            _rip_target(dsp_base, dsp_sections, address, X86_INS_LEA) == target,
            "DSP receiver literal target differs at %#x" % address,
        )
    for address, literal in {
        0x180435B60: "RestorePreset",
        0x180435B70: "StorePreset",
        0x180435B80: "presetTarget",
    }.items():
        _require_ascii(dsp_base, dsp_sections, address, literal)
    _require_direct_target(dsp_base, dsp_sections, 0x18003B5B3, DSP_SERIALIZER)
    _require_direct_target(dsp_base, dsp_sections, 0x18003B5DC, DSP_LIBRARY_SEND)
    _require(_read_u64(dsp_base, dsp_sections, DSP_SENDER_VTABLE + 0x10)
             == DSP_MEMP_FRAGMENTER,
             "DSP sender vtable +0x10 differs")

    try:
        writer_report = writer_sink.analyze(dsp)
    except (writer_sink.AnalysisError, pe_helpers.AnalysisError) as error:
        raise AnalysisError("UC 4.7.2 record writer: %s" % error) from error
    _require(writer_report["first_write"]["physical_prefix_hex"] == "7b",
             "UC 4.7.2 Stat record first byte differs")
    _require(not writer_report["first_write"]["native_u32_two_prefix_inserted"],
             "UC 4.7.2 Stat writer unexpectedly inserts native u32 two")

    inventory = _tag_inventory(images)
    expected_inventory = {
        "panel": {"MemP": 0, "Stat": 0, "PrsM": 0, "SetP": 0, "Appl": 0, "ZStr": 7},
        "service": {"MemP": 0, "Stat": 0, "PrsM": 0, "SetP": 0, "Appl": 0, "ZStr": 0},
        "universal_control": {"MemP": 0, "Stat": 0, "PrsM": 0, "SetP": 0, "Appl": 3, "ZStr": 0},
        "ucnet": {"MemP": 0, "Stat": 0, "PrsM": 0, "SetP": 0, "Appl": 0, "ZStr": 0},
        "dsp": {"MemP": 16, "Stat": 36, "PrsM": 16, "SetP": 13, "Appl": 44, "ZStr": 6},
    }
    _require(inventory == expected_inventory, "conceptual FourCC inventory differs")

    return {
        "boundary": (
            "STATIC_UI_AND_HOST_MESSAGE_ROUTE_RESOLVED_RUNTIME_UCNET_"
            "DELIVERY_FORMAT_TRANSFORMATION_PHYSICAL_COMMIT_RECALL_AND_"
            "AUDIBILITY_UNOBSERVED"
        ),
        "dsp_receiver": {
            "function": hex(DSP_REQUEST_RECEIVER),
            "messages": ["RestorePreset", "StorePreset"],
            "store_serializer_call": "0x18003b5b3 -> 0x18002e270",
            "store_send_call": "0x18003b5dc -> 0x180037250",
            "device_library_route": "MemP/PrsM indexes 16..27",
            "active_slot_route": "MemP/Stat indexes 0..3",
            "stat_record_first_byte": "0x7b",
        },
        "embedded_ui": {
            "container": "DEFAULT.SKIN/PACKAGEF",
            "member": "uceasy/uceasy.xml",
            "member_count": len(package_files),
            "preset_slot_values": slot_values,
            "remote_list_label": "Device Presets",
            "send_to_mixer_binding": "sendToMixer",
            "store_binding": "storeNamedRemotePreset",
        },
        "high_level_store_proxy": {
            "function": hex(PANEL_STORE_PRESET),
            "message": "StorePreset",
            "keys": ["presets", "presetFile", "presetTarget"],
            "dispatch": "object+0x298 vtable+0x80",
            "builds_low_level_memp_stat_bytes": False,
        },
        "module_topology": {
            "panel_ucnet_iat": {
                "UCSetReportFunction": "0x180384510",
                "UCGetFileTransferManager": "0x180384518",
                "UCGetNetworkManager": "0x180384520",
            },
            "runtime_panel_to_dsp_delivery_observed": False,
            "tag_inventory_reversed_file_bytes": inventory,
        },
        "reconciliation": {
            "device_library_and_fast_access_slot_are_distinct": True,
            "explicit_assign_frame_located": False,
            "native_u32_two_producer_located": False,
            "simple_wine_syscall_or_dll_workaround_source_bound": False,
            "linux_native_direction": (
                "reproduce the high-level preset/state-machine route after "
                "resolving the remaining runtime format boundary"
            ),
        },
        "slot_control": {
            "property": "presetSlot",
            "property_id": "0x3ec",
            "registered_values": 4,
            "store_policy": "active slot is maintained by the existing settled-state Stat path",
            "separate_assign_action_located": False,
        },
        "sources": sources,
        "status": (
            "UC472_SAVE_ASSIGN_UI_ROUTE_SOURCE_BOUND_TO_EXISTING_"
            "DEVICE_LIBRARY_AND_SLOT_STATE_PATHS"
        ),
        "ui_actions": {
            "send_to_mixer": {
                "action_id": "0x452",
                "event_target": "0x1800f9178",
                "helper": hex(PANEL_SEND_TO_MIXER),
                "transfer_helper": hex(PANEL_TRANSFER),
                "direction": "Local Presets -> Device Presets",
                "serialized_item_tag": "ZStr",
            },
            "store_named_remote_preset": {
                "action_id": "0x45f",
                "event_target": "0x1800f94a3",
                "helper": hex(PANEL_STORE_NAMED_REMOTE),
                "network_manager_import": "UCGetNetworkManager",
                "file_transfer_manager_import": "UCGetFileTransferManager",
            },
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("panel", type=Path)
    parser.add_argument("service", type=Path)
    parser.add_argument("universal_control", type=Path)
    parser.add_argument("ucnet", type=Path)
    parser.add_argument("dsp", type=Path)
    arguments = parser.parse_args(argv)
    try:
        report = analyze(
            panel=arguments.panel.read_bytes(),
            service=arguments.service.read_bytes(),
            universal_control=arguments.universal_control.read_bytes(),
            ucnet=arguments.ucnet.read_bytes(),
            dsp=arguments.dsp.read_bytes(),
        )
    except (OSError, AnalysisError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
