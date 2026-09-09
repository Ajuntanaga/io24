#!/usr/bin/env python3
"""Audit the offline MI05/MI06 WinUSB discovery and API boundary."""

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path


IO24_VENDOR = 0x194F
IO24_PRODUCT = 0x0422
IO24_DEVICE_ANCHOR = bytes.fromhex("12010002000000404f1922042801")
IO24_MODEL_WINDOW = 0x900
MS_OS_1_SIGNATURE = b"\x03" + "MSFT100".encode("utf-16le")
MS_COMPATIBLE_ID = r"USB\MS_COMP_WINUSB"

REQUIRED_WINUSB_IMPORTS = (
    "WinUsb_AbortPipe",
    "WinUsb_ControlTransfer",
    "WinUsb_Free",
    "WinUsb_GetAssociatedInterface",
    "WinUsb_GetDescriptor",
    "WinUsb_GetOverlappedResult",
    "WinUsb_GetPipePolicy",
    "WinUsb_Initialize",
    "WinUsb_QueryDeviceInformation",
    "WinUsb_ReadPipe",
    "WinUsb_ResetPipe",
    "WinUsb_SetCurrentAlternateSetting",
    "WinUsb_SetPipePolicy",
    "WinUsb_WritePipe",
)

EXPECTED_CLASS_IDS = {
    5: [
        r"USB\Class_ff&SubClass_00&Prot_00",
        r"USB\Class_ff&SubClass_00",
        r"USB\Class_ff",
    ],
    6: [
        r"USB\Class_fe&SubClass_01&Prot_01",
        r"USB\Class_fe&SubClass_01",
        r"USB\Class_fe",
    ],
}


class AuditError(Exception):
    """Raised when an input cannot support the requested audit."""


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _contains_ms_compatible_id(text):
    return MS_COMPATIBLE_ID.lower() in text.replace("\\\\", "\\").lower()


def _u16(data, offset):
    if offset < 0 or offset + 2 > len(data):
        raise AuditError("truncated PE field at offset %#x" % offset)
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        raise AuditError("truncated PE field at offset %#x" % offset)
    return struct.unpack_from("<I", data, offset)[0]


def _u64(data, offset):
    if offset < 0 or offset + 8 > len(data):
        raise AuditError("truncated PE field at offset %#x" % offset)
    return struct.unpack_from("<Q", data, offset)[0]


def _c_string(data, offset):
    if offset < 0 or offset >= len(data):
        raise AuditError("invalid PE string offset %#x" % offset)
    end = data.find(b"\0", offset)
    if end == -1:
        raise AuditError("unterminated PE string at offset %#x" % offset)
    try:
        return data[offset:end].decode("ascii")
    except UnicodeDecodeError as error:
        raise AuditError("non-ASCII PE import string at offset %#x" % offset) from error


def _pe_imports(data):
    """Return {DLL: [symbol, ...]} from a PE32 or PE32+ import directory."""
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise AuditError("hardware-access module is not a PE image")
    pe_offset = _u32(data, 0x3C)
    if pe_offset + 24 > len(data) or data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise AuditError("invalid PE signature")

    coff = pe_offset + 4
    section_count = _u16(data, coff + 2)
    optional_size = _u16(data, coff + 16)
    optional = coff + 20
    magic = _u16(data, optional)
    if magic == 0x20B:
        directory_base = optional + 112
        thunk_size = 8
        ordinal_mask = 1 << 63
    elif magic == 0x10B:
        directory_base = optional + 96
        thunk_size = 4
        ordinal_mask = 1 << 31
    else:
        raise AuditError("unsupported PE optional-header magic %#x" % magic)
    if directory_base + 16 > optional + optional_size:
        raise AuditError("PE optional header has no import directory")

    sections = []
    section_table = optional + optional_size
    for index in range(section_count):
        header = section_table + index * 40
        if header + 40 > len(data):
            raise AuditError("truncated PE section table")
        sections.append({
            "virtual_size": _u32(data, header + 8),
            "virtual_address": _u32(data, header + 12),
            "raw_size": _u32(data, header + 16),
            "raw_offset": _u32(data, header + 20),
        })

    def rva_to_offset(rva):
        for section in sections:
            start = section["virtual_address"]
            span = max(section["virtual_size"], section["raw_size"])
            if start <= rva < start + span:
                offset = section["raw_offset"] + (rva - start)
                if offset >= len(data):
                    break
                return offset
        if rva < len(data):
            return rva
        raise AuditError("unmapped PE RVA %#x" % rva)

    import_rva = _u32(data, directory_base + 8)
    if not import_rva:
        return {}
    descriptor = rva_to_offset(import_rva)
    imports = {}
    while True:
        if descriptor + 20 > len(data):
            raise AuditError("truncated PE import descriptor")
        original_thunk = _u32(data, descriptor)
        name_rva = _u32(data, descriptor + 12)
        first_thunk = _u32(data, descriptor + 16)
        if not any(data[descriptor:descriptor + 20]):
            break
        if not name_rva or not (original_thunk or first_thunk):
            raise AuditError("malformed PE import descriptor")

        dll_name = _c_string(data, rva_to_offset(name_rva)).upper()
        thunk = rva_to_offset(original_thunk or first_thunk)
        symbols = []
        while True:
            value = _u64(data, thunk) if thunk_size == 8 else _u32(data, thunk)
            if not value:
                break
            if not value & ordinal_mask:
                symbols.append(_c_string(data, rva_to_offset(value) + 2))
            thunk += thunk_size
        imports[dll_name] = symbols
        descriptor += 20
    return imports


def analyze_vendor_module(path):
    path = Path(path)
    data = path.read_bytes()
    imports = _pe_imports(data)
    imported_winusb = sorted(imports.get("WINUSB.DLL", []))
    required = set(REQUIRED_WINUSB_IMPORTS)

    models = []
    search_from = 0
    while True:
        offset = data.find(IO24_DEVICE_ANCHOR, search_from)
        if offset == -1:
            break
        window = data[offset:offset + IO24_MODEL_WINDOW]
        interfaces = []
        record_offsets = {}
        for interface in (5, 6):
            record = bytes([interface, 1]) + b"WINUSB"
            relative = window.find(record)
            if relative != -1:
                interfaces.append(interface)
                record_offsets[str(interface)] = "0x%x" % (offset + relative)

        signature_relative = window.find(MS_OS_1_SIGNATURE)
        vendor_code = None
        signature_offset = None
        if signature_relative != -1:
            signature_offset = offset + signature_relative
            code_offset = signature_offset + len(MS_OS_1_SIGNATURE)
            if code_offset < len(data):
                vendor_code = data[code_offset]

        property_relative = window.find(b"DeviceInterfaceGUID\0")
        models.append({
            "offset": "0x%x" % offset,
            "winusb_interfaces": interfaces,
            "winusb_record_offsets": record_offsets,
            "ms_os_1_signature": signature_relative != -1,
            "ms_os_1_signature_offset": (
                "0x%x" % signature_offset if signature_offset is not None else None
            ),
            "ms_os_1_vendor_code": vendor_code,
            "device_interface_guid_property": property_relative != -1,
            "device_interface_guid_property_offset": (
                "0x%x" % (offset + property_relative)
                if property_relative != -1 else None
            ),
        })
        search_from = offset + 1

    expected_models = [
        model for model in models
        if model["winusb_interfaces"] == [5, 6]
        and model["ms_os_1_signature"]
        and model["device_interface_guid_property"]
    ]
    missing_imports = sorted(required - set(imported_winusb))
    return {
        "path": str(path.resolve()),
        "sha256": _sha256(data),
        "winusb_import_count": len(imported_winusb),
        "winusb_imports": imported_winusb,
        "required_winusb_import_count": len(REQUIRED_WINUSB_IMPORTS),
        "missing_required_winusb_imports": missing_imports,
        "io24_model_count": len(models),
        "io24_models": models,
        "expected_model_count": len(expected_models),
        "expectation_complete": not missing_imports and len(expected_models) == 1,
    }


def _registry_sections(text):
    # Wine registry exports double their path separators. Normalize only those
    # pairs; keep value terminators such as \0 intact.
    text = text.replace("\\\\", "\\")
    sections = {}
    current = None
    for line in text.splitlines():
        if line.startswith("[") and "]" in line:
            current = line[1:line.index("]")]
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def analyze_registry(path):
    path = Path(path)
    data = path.read_bytes()
    text = data.decode("utf-8", errors="strict")
    instances = {5: [], 6: []}
    section_pattern = re.compile(
        r"^System\\ControlSet001\\Enum\\USB\\VID_194F&PID_0422&MI_(05|06)\\([^\\]+)$",
        re.IGNORECASE,
    )
    compatible_pattern = re.compile(
        r'^"CompatibleIDs"=str\(7\):"(.*)"$', re.IGNORECASE
    )
    driver_pattern = re.compile(r'^"Driver"=', re.IGNORECASE)
    service_pattern = re.compile(r'^"Service"=', re.IGNORECASE)

    for section, lines in _registry_sections(text).items():
        match = section_pattern.match(section)
        if not match:
            continue
        interface = int(match.group(1), 10)
        compatible_ids = []
        for line in lines:
            compatible = compatible_pattern.match(line)
            if compatible:
                compatible_ids = [
                    entry for entry in compatible.group(1).split(r"\0") if entry
                ]
        instances[interface].append({
            "section": section,
            "compatible_ids": compatible_ids,
            "has_ms_comp_winusb": any(
                entry.upper() == MS_COMPATIBLE_ID.upper()
                for entry in compatible_ids
            ),
            "has_driver": any(driver_pattern.match(line) for line in lines),
            "has_service": any(service_pattern.match(line) for line in lines),
        })

    exact_class_only = {}
    for interface, entries in instances.items():
        exact_class_only[str(interface)] = bool(entries) and all(
            entry["compatible_ids"] == EXPECTED_CLASS_IDS[interface]
            and not entry["has_driver"]
            and not entry["has_service"]
            for entry in entries
        )
    return {
        "path": str(path.resolve()),
        "sha256": _sha256(data),
        "instances": {str(key): value for key, value in instances.items()},
        "exact_class_only_without_driver": exact_class_only,
        "has_ms_comp_winusb": any(
            entry["has_ms_comp_winusb"]
            for entries in instances.values()
            for entry in entries
        ),
    }


def analyze_service_log(path):
    path = Path(path)
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    no_driver = {
        str(interface): bool(re.search(
            r"No compatible drivers were enumerated for device .*MI_%02d" % interface,
            text,
        ))
        for interface in (5, 6)
    }
    return {
        "path": str(path.resolve()),
        "sha256": _sha256(data),
        "no_compatible_driver": no_driver,
        "wineusb_inf_examined": "wineusb.inf" in text.lower(),
        "ms_comp_winusb_observed": _contains_ms_compatible_id(text),
    }


def analyze_wine_source(path):
    path = Path(path)
    bus_source = path / "dlls/wineusb.sys/wineusb.c"
    bus_inf = path / "dlls/wineusb.sys/wineusb.inf"
    api_spec = path / "dlls/winusb/winusb.spec"
    api_source = path / "dlls/winusb/main.c"
    required_files = (bus_source, bus_inf, api_spec, api_source)
    missing = [str(item) for item in required_files if not item.is_file()]
    if missing:
        raise AuditError("missing Wine source inputs: " + ", ".join(missing))

    bus_text = bus_source.read_text(encoding="utf-8")
    inf_text = bus_inf.read_text(encoding="utf-8")
    spec_text = api_spec.read_text(encoding="utf-8")
    api_text = api_source.read_text(encoding="utf-8")
    stub_exports = sorted(set(re.findall(
        r"^@\s+stub\s+(WinUsb_[A-Za-z0-9_]+)\s*$", spec_text, re.MULTILINE
    )))
    imported_required = set(REQUIRED_WINUSB_IMPORTS)
    required_spec_stubs = sorted(imported_required & set(stub_exports))
    free_is_semantic_stub = bool(re.search(
        r"BOOL\s+WINAPI\s+WinUsb_Free\s*\([^)]*\).*?FIXME\s*\(",
        api_text,
        re.DOTALL,
    ))
    unimplemented_required = set(required_spec_stubs)
    if free_is_semantic_stub:
        unimplemented_required.add("WinUsb_Free")

    ms_id_in_bus = _contains_ms_compatible_id(bus_text)
    ms_id_in_inf = _contains_ms_compatible_id(inf_text)
    return {
        "path": str(path.resolve()),
        "wineusb_bus_source_sha256": _sha256(bus_source.read_bytes()),
        "wineusb_bus_inf_sha256": _sha256(bus_inf.read_bytes()),
        "winusb_api_spec_sha256": _sha256(api_spec.read_bytes()),
        "winusb_api_source_sha256": _sha256(api_source.read_bytes()),
        "ms_comp_winusb_id_generation": ms_id_in_bus,
        "ms_comp_winusb_inf_match": ms_id_in_inf,
        "wineusb_inf_root_bus_match": "root\\wineusb" in inf_text.lower(),
        "all_winusb_spec_stub_count": len(stub_exports),
        "required_spec_stubs": required_spec_stubs,
        "winusb_free_semantic_stub": free_is_semantic_stub,
        "unimplemented_required_apis": sorted(unimplemented_required),
        "implemented_required_api_count": (
            len(REQUIRED_WINUSB_IMPORTS) - len(unimplemented_required)
        ),
    }


def analyze(dspusb_dll, wine_source, system_reg, service_log):
    vendor = analyze_vendor_module(dspusb_dll)
    registry = analyze_registry(system_reg)
    log = analyze_service_log(service_log)
    wine = analyze_wine_source(wine_source)

    blockers = []
    if not wine["ms_comp_winusb_id_generation"]:
        blockers.append("os_1_compatible_id_translation_missing")
    if not wine["ms_comp_winusb_inf_match"]:
        blockers.append("generic_winusb_function_binding_missing")
    if wine["unimplemented_required_apis"]:
        blockers.append("required_winusb_api_surface_unimplemented")

    known_boundary = (
        vendor["expectation_complete"]
        and registry["exact_class_only_without_driver"] == {"5": True, "6": True}
        and not registry["has_ms_comp_winusb"]
        and log["no_compatible_driver"] == {"5": True, "6": True}
        and log["wineusb_inf_examined"]
        and not log["ms_comp_winusb_observed"]
        and blockers == [
            "os_1_compatible_id_translation_missing",
            "generic_winusb_function_binding_missing",
            "required_winusb_api_surface_unimplemented",
        ]
    )
    return {
        "vendor_module": vendor,
        "retained_registry": registry,
        "retained_service_log": log,
        "wine_source": wine,
        "blockers": blockers,
        "known_boundary_confirmed": known_boundary,
        "structural_preconditions_met": not blockers,
        # This audit can prove source surfaces are absent. It cannot prove a
        # future implementation's runtime semantics merely from source text.
        "behavioral_implementation_proven": False,
        "stageable": False,
    }


def _human_report(result):
    vendor = result["vendor_module"]
    wine = result["wine_source"]
    print("io24 MI05/MI06 WinUSB readiness")
    print("  vendor imports: %d/%d" % (
        vendor["winusb_import_count"], vendor["required_winusb_import_count"]
    ))
    print("  io24 MI05/MI06 WINUSB model: %s" % (
        "present" if vendor["expectation_complete"] else "incomplete"
    ))
    print("  compatible-ID translation: %s" % (
        "present" if wine["ms_comp_winusb_id_generation"] else "missing"
    ))
    print("  generic WinUSB INF match: %s" % (
        "present" if wine["ms_comp_winusb_inf_match"] else "missing"
    ))
    print("  required WinUSB APIs implemented: %d/%d" % (
        wine["implemented_required_api_count"], len(REQUIRED_WINUSB_IMPORTS)
    ))
    print("  known CP30 boundary: %s" % (
        "confirmed" if result["known_boundary_confirmed"] else "not confirmed"
    ))
    print("  structural readiness: %s" % (
        "READY" if result["structural_preconditions_met"] else "NOT READY"
    ))
    print("  stageable from this audit alone: NO")
    for blocker in result["blockers"]:
        print("    blocker: " + blocker)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dspusb-dll", required=True, type=Path)
    parser.add_argument("--wine-source", required=True, type=Path)
    parser.add_argument("--system-reg", required=True, type=Path)
    parser.add_argument("--service-log", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-known-boundary", action="store_true")
    parser.add_argument("--require-structural-ready", action="store_true")
    args = parser.parse_args()

    try:
        result = analyze(
            args.dspusb_dll,
            args.wine_source,
            args.system_reg,
            args.service_log,
        )
    except (AuditError, OSError, UnicodeError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _human_report(result)

    if args.require_known_boundary and not result["known_boundary_confirmed"]:
        print("FAIL: expected MI05/MI06 boundary was not confirmed", file=sys.stderr)
        return 1
    if args.require_structural_ready and not result["structural_preconditions_met"]:
        for blocker in result["blockers"]:
            print("STRUCTURALLY NOT READY: " + blocker, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
