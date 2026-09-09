#!/usr/bin/env python3
"""Synthetic RED/GREEN contract for io24_winusb_readiness.py."""

import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ANALYZER = HERE / "io24_winusb_readiness.py"

REQUIRED_IMPORTS = (
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


def synthetic_pe():
    data = bytearray(0x4000)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    coff = 0x84
    struct.pack_into("<HHIIIHH", data, coff, 0x8664, 1, 0, 0, 0, 0xF0, 0)
    optional = coff + 20
    struct.pack_into("<H", data, optional, 0x20B)
    struct.pack_into("<I", data, optional + 108, 16)
    struct.pack_into("<II", data, optional + 120, 0x1000, 40)
    section = optional + 0xF0
    data[section:section + 8] = b".rdata\0\0"
    struct.pack_into("<IIII", data, section + 8, 0x3E00, 0x1000, 0x3E00, 0x200)

    def raw_offset(rva):
        return 0x200 + rva - 0x1000

    struct.pack_into("<IIIII", data, raw_offset(0x1000), 0x1040, 0, 0, 0x10C0, 0x1060)
    data[raw_offset(0x10C0):raw_offset(0x10C0) + 11] = b"WINUSB.DLL\0"
    thunk = raw_offset(0x1040)
    name_rva = 0x1100
    for index, name in enumerate(REQUIRED_IMPORTS):
        struct.pack_into("<Q", data, thunk + index * 8, name_rva)
        encoded = b"\0\0" + name.encode("ascii") + b"\0"
        offset = raw_offset(name_rva)
        data[offset:offset + len(encoded)] = encoded
        name_rva += len(encoded)

    model = 0x1200
    anchor = bytes.fromhex("12010002000000404f1922042801")
    data[model:model + len(anchor)] = anchor
    data[model + 0x100:model + 0x108] = b"\x05\x01WINUSB"
    data[model + 0x118:model + 0x120] = b"\x06\x01WINUSB"
    data[model + 0x200:model + 0x214] = b"DeviceInterfaceGUID\0"
    signature = b"\x03" + "MSFT100".encode("utf-16le") + b"\xa5"
    data[model + 0x300:model + 0x300 + len(signature)] = signature
    return bytes(data)


def write_wine_boundary(source):
    bus = source / "dlls/wineusb.sys"
    api = source / "dlls/winusb"
    bus.mkdir(parents=True)
    api.mkdir(parents=True)
    (bus / "wineusb.c").write_text(
        'append_id(buffer, L"USB\\\\Class_%02x");\n', encoding="utf-8"
    )
    (bus / "wineusb.inf").write_text(
        "Wine USB bus driver=device_section,root\\wineusb\n", encoding="utf-8"
    )
    spec_lines = []
    for name in REQUIRED_IMPORTS:
        if name == "WinUsb_Free":
            spec_lines.append("@ stdcall WinUsb_Free(ptr)")
        else:
            spec_lines.append("@ stub " + name)
    (api / "winusb.spec").write_text("\n".join(spec_lines) + "\n", encoding="utf-8")
    (api / "main.c").write_text(
        "BOOL WINAPI WinUsb_Free(void *handle)\n"
        "{\n"
        "    FIXME(\"stub\");\n"
        "    return TRUE;\n"
        "}\n",
        encoding="utf-8",
    )


def write_wine_ready(source):
    bus = source / "dlls/wineusb.sys"
    api = source / "dlls/winusb"
    (bus / "wineusb.c").write_text(
        'append_id(buffer, L"USB\\\\MS_COMP_WINUSB");\n', encoding="utf-8"
    )
    (bus / "wineusb.inf").write_text(
        "Wine WinUSB function=device_section,USB\\MS_COMP_WINUSB\n",
        encoding="utf-8",
    )
    (api / "winusb.spec").write_text(
        "\n".join("@ stdcall %s()" % name for name in REQUIRED_IMPORTS) + "\n",
        encoding="utf-8",
    )
    (api / "main.c").write_text(
        "BOOL WINAPI WinUsb_Free(void *handle) { return handle != 0; }\n",
        encoding="utf-8",
    )


def run_analyzer(arguments):
    return subprocess.run(
        [sys.executable, str(ANALYZER), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def main():
    with tempfile.TemporaryDirectory(prefix="io24-winusb-readiness-contract.") as directory:
        root = Path(directory)
        dll = root / "dspusbdevice.dll"
        source = root / "wine"
        registry = root / "system.reg"
        log = root / "service-install.log"
        dll.write_bytes(synthetic_pe())
        write_wine_boundary(source)
        registry.write_text(
            r'''[System\\ControlSet001\\Enum\\USB\\VID_194F&PID_0422&MI_05\\fixture]
"CompatibleIDs"=str(7):"USB\\Class_ff&SubClass_00&Prot_00\0USB\\Class_ff&SubClass_00\0USB\\Class_ff\0"

[System\\ControlSet001\\Enum\\USB\\VID_194F&PID_0422&MI_06\\fixture]
"CompatibleIDs"=str(7):"USB\\Class_fe&SubClass_01&Prot_01\0USB\\Class_fe&SubClass_01\0USB\\Class_fe\0"
''',
            encoding="utf-8",
        )
        log.write_text(
            'Examining C:/windows/inf/wineusb.inf\n'
            'No compatible drivers were enumerated for device L"USB\\\\VID_194F&PID_0422&MI_05\\\\fixture".\n'
            'No compatible drivers were enumerated for device L"USB\\\\VID_194F&PID_0422&MI_06\\\\fixture".\n',
            encoding="utf-8",
        )
        common = [
            "--dspusb-dll", str(dll),
            "--wine-source", str(source),
            "--system-reg", str(registry),
            "--service-log", str(log),
        ]

        boundary = run_analyzer(["--json", "--require-known-boundary", *common])
        assert boundary.returncode == 0, boundary.stderr
        result = json.loads(boundary.stdout)
        assert result["known_boundary_confirmed"] is True
        assert result["vendor_module"]["winusb_import_count"] == 14
        assert result["vendor_module"]["io24_models"][0]["winusb_interfaces"] == [5, 6]
        assert result["vendor_module"]["io24_models"][0]["ms_os_1_vendor_code"] == 0xA5
        assert result["wine_source"]["implemented_required_api_count"] == 0
        assert result["blockers"] == [
            "os_1_compatible_id_translation_missing",
            "generic_winusb_function_binding_missing",
            "required_winusb_api_surface_unimplemented",
        ]

        red = run_analyzer(["--require-structural-ready", *common])
        assert red.returncode == 1, red.stderr
        for blocker in result["blockers"]:
            assert "STRUCTURALLY NOT READY: " + blocker in red.stderr

        write_wine_ready(source)
        green = run_analyzer(["--json", "--require-structural-ready", *common])
        assert green.returncode == 0, green.stderr
        green_result = json.loads(green.stdout)
        assert green_result["structural_preconditions_met"] is True
        assert green_result["blockers"] == []
        assert green_result["wine_source"]["implemented_required_api_count"] == 14
        assert green_result["behavioral_implementation_proven"] is False
        assert green_result["stageable"] is False

    print("io24 WinUSB readiness contract: pass (known RED and synthetic structural GREEN)")


if __name__ == "__main__":
    main()
