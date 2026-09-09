#!/usr/bin/env python3
"""Semantic INF/build contract for CP32's generic WinUSB function binding.

This intentionally reads the candidate Wine source tree.  It does not build,
load, or otherwise exercise Wine; the contract is suitable for the pre-build
CP32 RED and for both later clean source trees.
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parent / ".io24-build/wineusb-ms-os-10-v1/patch-check-source"
TARGET_ID = r"USB\MS_COMP_WINUSB"
USBDEVICE_GUID = "{88bae032-5a81-49f0-bc3d-a4ff138216d6}"


class ContractError(AssertionError):
    pass


def fail(message):
    raise ContractError(message)


def csv_fields(value):
    return [field.strip().strip('"') for field in next(csv.reader([value], skipinitialspace=True))]


def parse_inf(path):
    """Return an ordered, case-insensitive INF section map.

    The parser retains key/value pairs instead of relying on a particular
    spelling, whitespace layout, or model/install section names.
    """
    sections = defaultdict(list)
    section = None
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r"\[([^\]]+)\]", line)
        if match:
            section = match.group(1).strip().lower()
            continue
        if section is None:
            fail(f"{path}: line {line_number}: entry outside an INF section")
        if "=" in line:
            key, value = line.split("=", 1)
        elif "," in line:
            # wine.inf.in has list-style sections such as [InfFiles], whose
            # entries are key,value rather than key=value.
            key, value = line.split(",", 1)
        else:
            # Other list sections (for example [NlsFiles]) are irrelevant to
            # this contract, but must not make [InfFiles] unparsable.
            key, value = "", line
        sections[section].append((key.strip(), value.strip(), line_number))
    return sections


def entries(sections, name):
    return sections.get(name.lower(), [])


def one_value(sections, section, key):
    values = [value for entry_key, value, _ in entries(sections, section) if entry_key.lower() == key.lower()]
    if len(values) != 1:
        fail(f"winusb.inf: [{section}] must contain exactly one {key}= entry (found {len(values)})")
    return values[0]


def model_sections(sections):
    models = []
    manufacturer = entries(sections, "Manufacturer")
    if not manufacturer:
        fail("winusb.inf: missing [Manufacturer] section")
    for _, value, _ in manufacturer:
        fields = csv_fields(value)
        if len(fields) < 1 or not fields[0]:
            fail("winusb.inf: malformed [Manufacturer] model reference")
        # Remaining fields are TargetOSVersion decorations, not further model
        # section names.  The selected model section itself may be decorated
        # by the INF author, so preserve its declared spelling.
        models.append(fields[0])
    missing = [name for name in models if name.lower() not in sections]
    if missing:
        fail("winusb.inf: [Manufacturer] references missing model section(s): " + ", ".join(missing))
    return models


def parse_model_rows(sections):
    rows = []
    for section in model_sections(sections):
        for description, value, _ in entries(sections, section):
            fields = csv_fields(value)
            if len(fields) < 2 or not fields[0] or not fields[1]:
                fail(f"winusb.inf: [{section}] model {description!r} lacks an install section and hardware ID")
            rows.append((fields[0], fields[1:]))
    if not rows:
        fail("winusb.inf: no model rows selected by [Manufacturer]")
    return rows


def check_inf(source):
    directory = source / "dlls/winusb.sys"
    inf = directory / "winusb.inf"
    if not directory.is_dir():
        fail(f"CP32 function-driver directory missing: {directory}")
    if not inf.is_file():
        fail(f"CP32 function-driver INF missing: {inf}")
    if not (directory / "Makefile.in").is_file():
        fail(f"CP32 function-driver build input missing: {directory / 'Makefile.in'}")

    sections = parse_inf(inf)
    if one_value(sections, "Version", "Class").casefold() != "usbdevice":
        fail("winusb.inf: Class must be USBDevice")
    if one_value(sections, "Version", "ClassGuid").casefold() != USBDEVICE_GUID:
        fail(f"winusb.inf: ClassGuid must be {USBDEVICE_GUID}")

    rows = parse_model_rows(sections)
    matches = [hardware_id for _, hardware_ids in rows for hardware_id in hardware_ids]
    forbidden = re.compile(r"(?:\bVID_[0-9a-f]+|\bPID_[0-9a-f]+|&MI_[0-9a-f]+|USB\\Class_|PaeDSPUSB|\broot\\)", re.I)
    bad_matches = [hardware_id for hardware_id in matches if forbidden.search(hardware_id)]
    if bad_matches:
        fail("winusb.inf: prohibited VID/PID/MI/class/PaeDSPUSB/root model match(es): " + repr(bad_matches))
    normalized = [hardware_id.casefold() for hardware_id in matches]
    if normalized.count(TARGET_ID.casefold()) != 1 or len(matches) != 1:
        fail("winusb.inf: the sole model hardware match must be USB\\MS_COMP_WINUSB; found " + repr(matches))

    install_sections = {install for install, _ in rows}
    services = []
    for install in install_sections:
        service_entries = entries(sections, install + ".Services")
        if not service_entries:
            fail(f"winusb.inf: model install section [{install}] has no [.Services] section")
        for key, value, _ in service_entries:
            if key.casefold() == "addservice":
                fields = csv_fields(value)
                if len(fields) < 3:
                    fail(f"winusb.inf: [{install}.Services] has malformed AddService entry")
                services.append((fields[0], fields[2]))
    if len(services) != 1 or services[0][0].casefold() != "winusb" or not services[0][1]:
        fail("winusb.inf: selected model must install only service winusb; found " + repr(services))

    service_section = services[0][1]
    if one_value(sections, service_section, "ServiceBinary").strip().strip('"').replace(" ", "").casefold() != "%12%\\winusb.sys":
        fail("winusb.inf: winusb service binary must be %12%\\winusb.sys")
    if one_value(sections, service_section, "ServiceType").strip() != "1":
        fail("winusb.inf: winusb service must be a kernel driver (ServiceType=1)")
    if one_value(sections, service_section, "StartType").strip() != "3":
        fail("winusb.inf: winusb service must be demand-start (StartType=3)")
    if one_value(sections, service_section, "LoadOrderGroup").strip().strip('"').casefold() != "wineplugplay":
        fail("winusb.inf: winusb service must use WinePlugPlay load-order group")


def check_publication(source):
    configure = source / "configure.ac"
    loader = source / "loader/wine.inf.in"
    resource = source / "dlls/winusb.sys/winusb.rc"
    for path in (configure, loader, resource):
        if not path.is_file():
            fail(f"CP32 build/publication input missing: {path}")

    configured = re.findall(r"\bWINE_CONFIG_MAKEFILE\s*\(\s*([^\s)]+)\s*\)", configure.read_text(encoding="utf-8"))
    if "dlls/winusb.sys" not in configured:
        fail("configure.ac: no WINE_CONFIG_MAKEFILE declaration for dlls/winusb.sys")

    loader_sections = parse_inf(loader)
    inf_files = {key.casefold(): csv_fields(value) for key, value, _ in entries(loader_sections, "InfFiles")}
    published = inf_files.get("winusb.inf")
    if not published or ",".join(published).casefold() != "@%12%\\winusb.sys,-1":
        fail("loader/wine.inf.in: [InfFiles] must publish winusb.inf from @%12%\\winusb.sys,-1")

    resource_text = resource.read_text(encoding="utf-8")
    resource_match = re.search(r"^\s*\d+\s+WINE_DATA_FILE\s+winusb\.inf\s*$", resource_text, re.M | re.I)
    if not resource_match:
        fail("dlls/winusb.sys/winusb.rc: no WINE_DATA_FILE resource for winusb.inf")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wine-source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    source = args.wine_source.resolve()
    try:
        check_inf(source)
        check_publication(source)
    except ContractError as error:
        print("CP32 WinUSB function-binding INF contract: FAIL: " + str(error), file=sys.stderr)
        return 1
    print("CP32 WinUSB function-binding INF contract: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
