#!/usr/bin/env python3
"""Inventory exact io24 class-IN responses and UAC2 terminal controls in usbmon."""

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
TARGETS = {
    "clock_source_5_sampling_frequency_cur": (0xA1, 0x01, 0x0100, 0x0500, 4),
    "terminal_2_latency_cur": (0xA1, 0x01, 0x0700, 0x0200, 4),
    "terminal_3_latency_cur": (0xA1, 0x01, 0x0700, 0x0300, 4),
}
LATENCY_ACCESS = {
    0: "not_present",
    1: "read_only",
    2: "reserved",
    3: "read_write",
}


def _setup_tuple(setup):
    if setup is None:
        return None
    return (
        setup["bm_request_type"],
        setup["request"],
        setup["value"],
        setup["index"],
        setup["length"],
    )


def _paired_control_transfers(packets):
    pending = {}
    pairs = []
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
            pairs.append((submit, packet))
    return pairs


def _is_complete_configuration(payload):
    if len(payload) < 9 or payload[0] != 9 or payload[1] != 2:
        return False
    total_length = int.from_bytes(payload[2:4], "little")
    return total_length >= 9 and len(payload) >= total_length


def _uac2_terminals(payload):
    terminals = []
    offset = 0
    audio_control_interface = False
    while offset + 2 <= len(payload):
        length = payload[offset]
        descriptor_type = payload[offset + 1]
        if length < 2 or offset + length > len(payload):
            break
        descriptor = payload[offset:offset + length]
        if descriptor_type == 4 and length >= 9:
            audio_control_interface = (
                descriptor[5] == 0x01
                and descriptor[6] == 0x01
                and descriptor[7] == 0x20
            )
        elif descriptor_type == 0x24 and audio_control_interface and length >= 3:
            subtype = descriptor[2]
            if subtype == 0x02 and length >= 17:
                kind = "input_terminal"
                entity_id = descriptor[3]
                bm_controls = int.from_bytes(descriptor[14:16], "little")
            elif subtype == 0x03 and length >= 12:
                kind = "output_terminal"
                entity_id = descriptor[3]
                bm_controls = int.from_bytes(descriptor[9:11], "little")
            else:
                offset += length
                continue
            latency_code = (bm_controls >> 12) & 0x03
            terminals.append({
                "bm_controls": bm_controls,
                "entity_id": entity_id,
                "kind": kind,
                "latency_access": LATENCY_ACCESS[latency_code],
                "latency_readable": latency_code in (1, 3),
            })
        offset += length
    return terminals


def analyze_capture(path):
    path = Path(path)
    capture = PCAP_PARSER.parse_pcap(path)
    pairs = _paired_control_transfers(capture["packets"])
    target_by_tuple = {value: key for key, value in TARGETS.items()}
    targets = {
        name: {
            "request_count": 0,
            "successful_response_count": 0,
            "responses": [],
            "unique_values_u32": [],
        }
        for name in TARGETS
    }
    target_devices = set()

    for submit, completion in pairs:
        name = target_by_tuple.get(_setup_tuple(submit["setup"]))
        if name is None:
            continue
        target_devices.add((submit["bus"], submit["device"]))
        result = targets[name]
        result["request_count"] += 1
        response = {
            "bus": submit["bus"],
            "device": submit["device"],
            "event_type": completion["event_type"],
            "response_hex": completion["payload"].hex(),
            "status": completion["status"],
            "urb_id": "%016x" % submit["urb_id"],
            "value_u32": None,
        }
        if completion["status"] == 0 and len(completion["payload"]) >= 4:
            response["value_u32"] = int.from_bytes(
                completion["payload"][:4], "little"
            )
            result["successful_response_count"] += 1
        result["responses"].append(response)

    for result in targets.values():
        result["unique_values_u32"] = sorted({
            response["value_u32"]
            for response in result["responses"]
            if response["value_u32"] is not None
        })

    complete_configurations = []
    terminals_by_identity = {}
    for submit, completion in pairs:
        setup = submit["setup"]
        if (
            (submit["bus"], submit["device"]) not in target_devices
            or setup["bm_request_type"] != 0x80
            or setup["request"] != 0x06
            or setup["value"] != 0x0200
            or completion["status"] != 0
            or not _is_complete_configuration(completion["payload"])
        ):
            continue
        complete_configurations.append(completion["payload"])
        for terminal in _uac2_terminals(completion["payload"]):
            identity = (terminal["kind"], terminal["entity_id"])
            previous = terminals_by_identity.setdefault(identity, terminal)
            if previous != terminal:
                raise PCAP_PARSER.CaptureError(
                    "conflicting UAC2 terminal descriptors for entity %d"
                    % terminal["entity_id"]
                )

    return {
        "pcap": str(path.resolve()),
        "pcap_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "linktype": capture["linktype"],
        "snaplen": capture["snaplen"],
        "packet_count": len(capture["packets"]),
        "complete_uac2_configuration_count": len(complete_configurations),
        "targets": targets,
        "uac2_terminals": sorted(
            terminals_by_identity.values(),
            key=lambda entry: (entry["entity_id"], entry["kind"]),
        ),
    }


def _has_required_evidence(result):
    clock = result["targets"]["clock_source_5_sampling_frequency_cur"]
    entity_ids = {entry["entity_id"] for entry in result["uac2_terminals"]}
    return (
        clock["successful_response_count"] > 0
        and result["complete_uac2_configuration_count"] > 0
        and {2, 3}.issubset(entity_ids)
    )


def print_human(result):
    print("pcap=%s" % result["pcap"])
    print("pcap_sha256=%s" % result["pcap_sha256"])
    print("packet_count=%s" % result["packet_count"])
    print(
        "complete_uac2_configuration_count=%s"
        % result["complete_uac2_configuration_count"]
    )
    for name, target in result["targets"].items():
        print(
            "%s requests=%s successful=%s values_u32=%s"
            % (
                name,
                target["request_count"],
                target["successful_response_count"],
                ",".join(str(value) for value in target["unique_values_u32"])
                or "none",
            )
        )
    for terminal in result["uac2_terminals"]:
        print(
            "terminal entity=%s kind=%s bm_controls=0x%04x latency_access=%s"
            % (
                terminal["entity_id"],
                terminal["kind"],
                terminal["bm_controls"],
                terminal["latency_access"],
            )
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--require-evidence", action="store_true")
    parser.add_argument("pcap")
    args = parser.parse_args(argv)
    try:
        result = analyze_capture(args.pcap)
    except (OSError, PCAP_PARSER.CaptureError) as error:
        print("io24 class-IN evidence: %s" % error, file=sys.stderr)
        return 1
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_human(result)
    if args.require_evidence and not _has_required_evidence(result):
        print("io24 class-IN evidence: required evidence is incomplete", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
