#!/usr/bin/env python3
"""Recover USB function ownership and endpoint topology from a sealed usbmon pcap."""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PCAP_PARSER_PATH = HERE / "io24_usbmon_range_extract.py"
SPEC = importlib.util.spec_from_file_location("io24_usbmon_range_extract", PCAP_PARSER_PATH)
PCAP_PARSER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PCAP_PARSER)

USBMON_CONTROL = 2
USB_REQUEST_GET_DESCRIPTOR = 0x06
USB_DESCRIPTOR_DEVICE = 0x01
USB_DESCRIPTOR_CONFIGURATION = 0x02
USB_DESCRIPTOR_INTERFACE = 0x04
USB_DESCRIPTOR_ENDPOINT = 0x05
USB_DESCRIPTOR_INTERFACE_ASSOCIATION = 0x0B
USB_DESCRIPTOR_CS_INTERFACE = 0x24
USB_CLASS_AUDIO = 0x01
USB_SUBCLASS_AUDIOCONTROL = 0x01
USB_PROTOCOL_UAC1 = 0x00


def _paired_control_transfers(packets):
    pending = {}
    for packet in packets:
        if (
            packet["event_type"] == "S"
            and packet["transfer_type"] == USBMON_CONTROL
            and packet["setup"] is not None
        ):
            pending[packet["urb_id"]] = packet
            continue
        if packet["event_type"] not in ("C", "E"):
            continue
        submit = pending.pop(packet["urb_id"], None)
        if submit is not None:
            yield submit, packet


def _descriptor_request(submit, descriptor_type):
    setup = submit["setup"]
    return (
        setup["bm_request_type"] == 0x80
        and setup["request"] == USB_REQUEST_GET_DESCRIPTOR
        and setup["value"] >> 8 == descriptor_type
    )


def _parse_device_descriptor(payload):
    if len(payload) < 18 or payload[0] != 18 or payload[1] != USB_DESCRIPTOR_DEVICE:
        raise PCAP_PARSER.CaptureError("invalid USB device descriptor")
    return {
        "bcd_usb": int.from_bytes(payload[2:4], "little"),
        "class": payload[4],
        "subclass": payload[5],
        "protocol": payload[6],
        "vendor": int.from_bytes(payload[8:10], "little"),
        "product": int.from_bytes(payload[10:12], "little"),
        "bcd_device": int.from_bytes(payload[12:14], "little"),
        "num_configurations": payload[17],
        "raw_hex": payload[:18].hex(),
    }


def _build_functions(interface_numbers, associations, audio_collections):
    functions = []
    occupied = set()

    for association in associations:
        members = list(
            range(
                association["first_interface"],
                association["first_interface"] + association["interface_count"],
            )
        )
        members = [number for number in members if number in interface_numbers]
        if not members:
            continue
        functions.append({"root": members[0], "interfaces": members, "source": "iad"})
        occupied.update(members)

    for collection in audio_collections:
        members = [collection["root"]] + collection["interfaces"]
        members = list(dict.fromkeys(number for number in members if number in interface_numbers))
        if not members or any(number in occupied for number in members):
            continue
        functions.append({
            "root": collection["root"],
            "interfaces": members,
            "source": "audio_control_collection",
        })
        occupied.update(members)

    for number in sorted(interface_numbers - occupied):
        functions.append({"root": number, "interfaces": [number], "source": "ungrouped"})

    return sorted(functions, key=lambda entry: entry["root"])


def _parse_configuration(payload):
    if len(payload) < 9 or payload[0] != 9 or payload[1] != USB_DESCRIPTOR_CONFIGURATION:
        raise PCAP_PARSER.CaptureError("invalid USB configuration descriptor")
    total_length = int.from_bytes(payload[2:4], "little")
    if total_length < 9 or len(payload) < total_length:
        raise PCAP_PARSER.CaptureError("truncated USB configuration descriptor")
    payload = payload[:total_length]

    associations = []
    audio_collections = []
    interfaces = []
    current_interface = None
    offset = 0
    while offset < len(payload):
        if len(payload) - offset < 2:
            raise PCAP_PARSER.CaptureError("truncated descriptor header")
        length = payload[offset]
        descriptor_type = payload[offset + 1]
        if length < 2 or offset + length > len(payload):
            raise PCAP_PARSER.CaptureError("invalid descriptor length at offset %d" % offset)
        descriptor = payload[offset:offset + length]

        if descriptor_type == USB_DESCRIPTOR_INTERFACE_ASSOCIATION:
            if length < 8:
                raise PCAP_PARSER.CaptureError("short interface association descriptor")
            associations.append({
                "first_interface": descriptor[2],
                "interface_count": descriptor[3],
                "class": descriptor[4],
                "subclass": descriptor[5],
                "protocol": descriptor[6],
                "string": descriptor[7],
            })
        elif descriptor_type == USB_DESCRIPTOR_INTERFACE:
            if length < 9:
                raise PCAP_PARSER.CaptureError("short interface descriptor")
            current_interface = {
                "number": descriptor[2],
                "alternate": descriptor[3],
                "declared_endpoints": descriptor[4],
                "class": descriptor[5],
                "subclass": descriptor[6],
                "protocol": descriptor[7],
                "string": descriptor[8],
                "endpoints": [],
            }
            interfaces.append(current_interface)
        elif descriptor_type == USB_DESCRIPTOR_ENDPOINT:
            if current_interface is None or length < 7:
                raise PCAP_PARSER.CaptureError("orphan or short endpoint descriptor")
            current_interface["endpoints"].append({
                "address": descriptor[2],
                "attributes": descriptor[3],
                "max_packet": int.from_bytes(descriptor[4:6], "little"),
                "interval": descriptor[6],
            })
        elif (
            descriptor_type == USB_DESCRIPTOR_CS_INTERFACE
            and current_interface is not None
            and current_interface["class"] == USB_CLASS_AUDIO
            and current_interface["subclass"] == USB_SUBCLASS_AUDIOCONTROL
            and current_interface["protocol"] == USB_PROTOCOL_UAC1
            and length >= 8
            and descriptor[2] == 0x01
        ):
            collection_count = descriptor[7]
            if length < 8 + collection_count:
                raise PCAP_PARSER.CaptureError("short UAC1 AudioControl collection")
            audio_collections.append({
                "root": current_interface["number"],
                "interfaces": list(descriptor[8:8 + collection_count]),
            })

        offset += length

    for interface in interfaces:
        if interface["declared_endpoints"] != len(interface["endpoints"]):
            raise PCAP_PARSER.CaptureError(
                "endpoint count mismatch for interface %d alternate %d"
                % (interface["number"], interface["alternate"])
            )

    interface_numbers = {entry["number"] for entry in interfaces}
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "configuration": {
            "total_length": total_length,
            "num_interfaces": payload[4],
            "value": payload[5],
            "attributes": payload[7],
            "max_power": payload[8],
        },
        "interface_associations": associations,
        "audio_control_collections": audio_collections,
        "functions": _build_functions(interface_numbers, associations, audio_collections),
        "interfaces": interfaces,
    }


def analyze_capture(path, vendor=0x194F, product=0x0422):
    path = Path(path)
    capture = PCAP_PARSER.parse_pcap(path)
    pairs = list(_paired_control_transfers(capture["packets"]))
    target_devices = {}

    for submit, completion in pairs:
        if (
            not _descriptor_request(submit, USB_DESCRIPTOR_DEVICE)
            or completion["status"] != 0
        ):
            continue
        descriptor = _parse_device_descriptor(completion["payload"])
        if descriptor["vendor"] == vendor and descriptor["product"] == product:
            target_devices[(submit["bus"], submit["device"])] = descriptor

    configurations = []
    seen_configurations = set()
    incomplete_configurations = 0
    for submit, completion in pairs:
        if (
            (submit["bus"], submit["device"]) not in target_devices
            or not _descriptor_request(submit, USB_DESCRIPTOR_CONFIGURATION)
            or completion["status"] != 0
        ):
            continue
        payload = completion["payload"]
        if (
            len(payload) < 9
            or payload[0] != 9
            or payload[1] != USB_DESCRIPTOR_CONFIGURATION
            or len(payload) < int.from_bytes(payload[2:4], "little")
        ):
            incomplete_configurations += 1
            continue
        topology = _parse_configuration(payload)
        if topology["sha256"] in seen_configurations:
            continue
        seen_configurations.add(topology["sha256"])
        topology["bus"] = submit["bus"]
        topology["device"] = submit["device"]
        configurations.append(topology)

    return {
        "pcap": str(path.resolve()),
        "pcap_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "packet_count": len(capture["packets"]),
        "target_vendor": vendor,
        "target_product": product,
        "target_device_count": len(target_devices),
        "target_devices": [
            {"bus": bus, "device": device, "descriptor": descriptor}
            for (bus, device), descriptor in sorted(target_devices.items())
        ],
        "incomplete_configuration_response_count": incomplete_configurations,
        "configuration_count": len(configurations),
        "configurations": configurations,
    }


def _interface(topology, number, alternate):
    return next(
        (
            entry for entry in topology["interfaces"]
            if entry["number"] == number and entry["alternate"] == alternate
        ),
        None,
    )


def _has_required_io24_topology(result):
    required_functions = {
        (0, (0, 1, 2), "iad"),
        (3, (3, 4), "audio_control_collection"),
        (5, (5,), "ungrouped"),
        (6, (6,), "ungrouped"),
    }
    for topology in result["configurations"]:
        functions = {
            (entry["root"], tuple(entry["interfaces"]), entry["source"])
            for entry in topology["functions"]
        }
        interface4 = _interface(topology, 4, 0)
        interface5_alt0 = _interface(topology, 5, 0)
        interface5_alt1 = _interface(topology, 5, 1)
        interface6 = _interface(topology, 6, 0)
        if (
            required_functions.issubset(functions)
            and interface4 is not None
            and (interface4["class"], interface4["subclass"]) == (1, 3)
            and [entry["address"] for entry in interface4["endpoints"]] == [2, 130]
            and interface5_alt0 is not None
            and interface5_alt0["endpoints"] == []
            and interface5_alt1 is not None
            and [entry["address"] for entry in interface5_alt1["endpoints"]] == [129, 1]
            and interface6 is not None
            and (interface6["class"], interface6["subclass"]) == (0xFE, 1)
        ):
            return True
    return False


def print_human(result):
    print("pcap=%s" % result["pcap"])
    print("pcap_sha256=%s" % result["pcap_sha256"])
    print("packet_count=%s" % result["packet_count"])
    print("target_device_count=%s" % result["target_device_count"])
    print("configuration_count=%s" % result["configuration_count"])
    for topology in result["configurations"]:
        config = topology["configuration"]
        print(
            "configuration bus=%s device=%s sha256=%s total_length=%s interfaces=%s"
            % (
                topology["bus"],
                topology["device"],
                topology["sha256"],
                config["total_length"],
                config["num_interfaces"],
            )
        )
        for function in topology["functions"]:
            print(
                "function root=%s source=%s interfaces=%s"
                % (
                    function["root"],
                    function["source"],
                    ",".join(map(str, function["interfaces"])),
                )
            )
        for interface in topology["interfaces"]:
            endpoints = ",".join(
                "0x%02x" % endpoint["address"] for endpoint in interface["endpoints"]
            ) or "none"
            print(
                "interface number=%s alternate=%s class=0x%02x subclass=0x%02x "
                "protocol=0x%02x endpoints=%s"
                % (
                    interface["number"],
                    interface["alternate"],
                    interface["class"],
                    interface["subclass"],
                    interface["protocol"],
                    endpoints,
                )
            )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--require-io24-topology", action="store_true")
    parser.add_argument("--vendor", type=lambda value: int(value, 0), default=0x194F)
    parser.add_argument("--product", type=lambda value: int(value, 0), default=0x0422)
    parser.add_argument("pcap")
    args = parser.parse_args(argv)
    try:
        result = analyze_capture(args.pcap, args.vendor, args.product)
    except (OSError, PCAP_PARSER.CaptureError) as error:
        print("io24 function topology: %s" % error, file=sys.stderr)
        return 1
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_human(result)
    if args.require_io24_topology and not _has_required_io24_topology(result):
        print("io24 function topology: required topology is incomplete", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
