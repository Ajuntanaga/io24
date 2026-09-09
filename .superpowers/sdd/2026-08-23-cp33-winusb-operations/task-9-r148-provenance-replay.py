#!/usr/bin/env python3
"""Generate source-bound R148 mutation evidence without touching live sources."""

from __future__ import annotations

import argparse
import dataclasses
import difflib
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
from typing import Iterable


BASE_SHA256 = "ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1"
PATCH_SHA256 = "23333adc2918a72e2f1b32c53713533620f1be782373d1fcd389f4c598f2d08a"
ARCHIVE_SHA256 = "561da904b991e9fcf41c55f1c95230f7a8f90d5e24c228069e9f606b22dea4a1"
CANDIDATE_CONTRACT_SHA256 = "56a7aace5141dff885e4859659cc1e729031deeba76e371cbbcc1b64ebdf7cf5"
CANDIDATE_FAKE_SHA256 = "bd76d84e99227549eb587317971c33707457b56d93de3a90e1e5672b509bab15"
LIVE_UPPER_SHA256 = "eb3323df6df6fc40745e992263ada5ab2a83319e40851af55d58d2c46d359380"
LIVE_LOWER_SHA256 = "7dfe09e4dbc0d3463a2c407791c91771326f0c0037d33dd804e64c82ee0b0afa"
LIVE_FAKE_SHA256 = "c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb"

TASK_REL = Path(".superpowers/sdd/2026-08-23-cp33-winusb-operations")
PATCH_REL = TASK_REL / "task-9-r148-proposed-unified-rejection-state.patch"
ARCHIVE_REL = TASK_REL / "task-9-r148-isolated-evidence.tar.gz"
SOURCE_REL = Path(".io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c")


@dataclasses.dataclass(frozen=True)
class Mutation:
    row: int
    slug: str
    description: str
    expected_failures: int
    edits: tuple[tuple[str, str], ...]
    expected_marker_count: int = 1


RANGE_LINE = "            range_supported = wineusb_io24_control_range_supported(req);\n"
RANGE_RETURN = """            if (range_supported)
                return complete_io24_clock_source_range(&req->Hdr,
                        &req->TransferBufferLength, params->transfer_buffer);
"""
INTERFACE_REJECT = """            if (recipient == LIBUSB_RECIPIENT_INTERFACE && !range_supported &&
                    !device_has_interface(params->device, req->SetupPacket[4]))
            {
                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
                return STATUS_INVALID_PARAMETER;
            }
"""
GENERIC_REJECT = """            if (req->Hdr.Length != sizeof(*req) || length != req->TransferBufferLength ||
                    length > WINE_WINUSB_MAX_CONTROL_TRANSFER || (length && !params->transfer_buffer) ||
                    (type != LIBUSB_REQUEST_TYPE_STANDARD && type != LIBUSB_REQUEST_TYPE_CLASS &&
                    type != LIBUSB_REQUEST_TYPE_VENDOR) || recipient > LIBUSB_RECIPIENT_OTHER ||
                    (recipient == LIBUSB_RECIPIENT_ENDPOINT &&
                    (!control_endpoint_is_current(params->device, req->SetupPacket[4]) ||
                    ((req->SetupPacket[4] ^ request_type) & LIBUSB_ENDPOINT_IN))))
            {
                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
                return STATUS_INVALID_PARAMETER;
            }
"""
PIPE_ACTIVE_LINE = "    if (libusb_get_active_config_descriptor(libusb_get_device(device->handle), &config)) return false;\n"


def mutation_rows() -> tuple[Mutation, ...]:
    rows = (
        Mutation(1, "broad-range", "broad RANGE admission", 427, ((
            RANGE_LINE,
            RANGE_LINE + "            range_supported = true;\n",
        ),)),
        Mutation(2, "function-direction-widen", "function-conditioned direction widening", 50, ((
            RANGE_LINE,
            RANGE_LINE + """            if (params->device->function && req->SetupPacket[1] == 2 &&
                    req->SetupPacket[2] == 0 && req->SetupPacket[3] == 1 &&
                    req->SetupPacket[4] == 0 && req->SetupPacket[5] == 5 &&
                    length == 256)
                range_supported = true;
""",
        ),)),
        Mutation(3, "scope-backend-activity", "allocate and free before scope rejection", 8, ((
            INTERFACE_REJECT,
            INTERFACE_REJECT.replace(
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
                "                transfer = libusb_alloc_transfer(0);\n"
                "                libusb_free_transfer(transfer);\n"
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
            ),
        ),)),
        Mutation(4, "nonfunction-tail-corrupt", "non-function exact RANGE tail corruption", 1, ((
            RANGE_RETURN,
            """            if (range_supported && !params->device->function)
            {
                NTSTATUS status = complete_io24_clock_source_range(&req->Hdr,
                        &req->TransferBufferLength, params->transfer_buffer);
                ((unsigned char *)params->transfer_buffer)
                        [sizeof(io24_clock_source_range) - 1] ^= 1;
                return status;
            }
""" + RANGE_RETURN,
        ),)),
        Mutation(5, "nonfunction-suppress", "suppress local RANGE for non-function device", 5, ((
            RANGE_RETURN,
            RANGE_RETURN.replace("if (range_supported)", "if (range_supported && params->device->function)"),
        ),)),
        Mutation(6, "sync-control-local-range", "synchronous backend control then local RANGE", 3, ((
            RANGE_RETURN,
            """            if (range_supported)
            {
                libusb_control_transfer(handle, request_type, req->SetupPacket[1],
                        req->SetupPacket[2] | (req->SetupPacket[3] << 8),
                        req->SetupPacket[4] | (req->SetupPacket[5] << 8),
                        params->transfer_buffer, length, 0);
                return complete_io24_clock_source_range(&req->Hdr,
                        &req->TransferBufferLength, params->transfer_buffer);
            }
""",
        ),)),
        Mutation(7, "accept-direction-mismatch", "accept endpoint direction mismatch", 10, ((
            """                    type != LIBUSB_REQUEST_TYPE_VENDOR) || recipient > LIBUSB_RECIPIENT_OTHER ||
                    (recipient == LIBUSB_RECIPIENT_ENDPOINT &&
                    (!control_endpoint_is_current(params->device, req->SetupPacket[4]) ||
                    ((req->SetupPacket[4] ^ request_type) & LIBUSB_ENDPOINT_IN))))
""",
            """                    type != LIBUSB_REQUEST_TYPE_VENDOR) || recipient > LIBUSB_RECIPIENT_OTHER ||
                    (recipient == LIBUSB_RECIPIENT_ENDPOINT &&
                    !control_endpoint_is_current(params->device, req->SetupPacket[4])))
""",
        ),)),
        Mutation(8, "endpoint-membership-widen", "widen endpoint function membership", 5, ((
            """    return device_has_interface(device, pipe->interface_number) &&
            (!device->function || interface_in_set(device->claimed_interfaces,
            pipe->interface_number)) && device->pipe_table &&
""",
            """    return (!device->function || interface_in_set(device->claimed_interfaces,
            pipe->interface_number)) && device->pipe_table &&
""",
        ),)),
        Mutation(9, "omit-range-status", "omit exact RANGE success status", 3, ((
            """    memcpy(buffer, io24_clock_source_range, sizeof(io24_clock_source_range));
    *length = sizeof(io24_clock_source_range);
    header->Status = USBD_STATUS_SUCCESS;
    return STATUS_SUCCESS;
""",
            """    memcpy(buffer, io24_clock_source_range, sizeof(io24_clock_source_range));
    *length = sizeof(io24_clock_source_range);
    return STATUS_SUCCESS;
""",
        ),)),
        Mutation(10, "range-config-probe", "exact RANGE device and configuration probe", 3, ((
            RANGE_RETURN,
            """            if (range_supported)
            {
                struct libusb_config_descriptor *config;
                libusb_device *device = libusb_get_device(handle);
                if (!libusb_get_active_config_descriptor(device, &config))
                    libusb_free_config_descriptor(config);
                return complete_io24_clock_source_range(&req->Hdr,
                        &req->TransferBufferLength, params->transfer_buffer);
            }
""",
        ),)),
        Mutation(11, "scope-config-probe", "scope rejection device and configuration probe", 8, ((
            INTERFACE_REJECT,
            INTERFACE_REJECT.replace(
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
                """                {
                    struct libusb_config_descriptor *config;
                    libusb_device *device = libusb_get_device(params->device->handle);
                    if (!libusb_get_active_config_descriptor(device, &config))
                        libusb_free_config_descriptor(config);
                }
                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
""",
            ),
        ),)),
        Mutation(12, "malformed-config-probe", "malformed header device and configuration probe", 1, ((
            GENERIC_REJECT,
            GENERIC_REJECT.replace(
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
                """                if (req->Hdr.Length != sizeof(*req))
                {
                    struct libusb_config_descriptor *config;
                    libusb_device *device = libusb_get_device(params->device->handle);
                    if (!libusb_get_active_config_descriptor(device, &config))
                        libusb_free_config_descriptor(config);
                }
                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
""",
            ),
        ),)),
        Mutation(13, "null-buffer-config-probe", "exact null buffer device and configuration probe", 1, ((
            GENERIC_REJECT,
            GENERIC_REJECT.replace(
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
                """                if (!params->transfer_buffer &&
                        request_type == (LIBUSB_REQUEST_TYPE_CLASS |
                        LIBUSB_RECIPIENT_INTERFACE | LIBUSB_ENDPOINT_IN) &&
                        req->SetupPacket[1] == 2 && length == 256)
                {
                    struct libusb_config_descriptor *config;
                    libusb_device *device = libusb_get_device(params->device->handle);
                    if (!libusb_get_active_config_descriptor(device, &config))
                        libusb_free_config_descriptor(config);
                }
                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
""",
            ),
        ),)),
        Mutation(14, "oversized-config-probe", "oversized generic rejection configuration probe", 1, ((
            GENERIC_REJECT,
            GENERIC_REJECT.replace(
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
                """                if (length > WINE_WINUSB_MAX_CONTROL_TRANSFER)
                {
                    struct libusb_config_descriptor *config;
                    libusb_device *device = libusb_get_device(params->device->handle);
                    if (!libusb_get_active_config_descriptor(device, &config))
                        libusb_free_config_descriptor(config);
                }
                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
""",
            ),
        ),)),
        Mutation(15, "extra-direction-probe", "extra endpoint direction validation probe", 8, ((
            """            struct transfer_ctx *transfer_ctx;
            unsigned char *buffer;

            if (req->Hdr.Length != sizeof(*req) || length != req->TransferBufferLength ||
""",
            """            struct transfer_ctx *transfer_ctx;
            unsigned char *buffer;

            if (recipient == LIBUSB_RECIPIENT_ENDPOINT &&
                    ((req->SetupPacket[4] ^ request_type) & LIBUSB_ENDPOINT_IN))
                control_endpoint_is_current(params->device, req->SetupPacket[4]);
            if (req->Hdr.Length != sizeof(*req) || length != req->TransferBufferLength ||
""",
        ),)),
        Mutation(16, "skip-direction-validator", "direction rejection skips endpoint validator", 8, ((
            """                    (recipient == LIBUSB_RECIPIENT_ENDPOINT &&
                    (!control_endpoint_is_current(params->device, req->SetupPacket[4]) ||
                    ((req->SetupPacket[4] ^ request_type) & LIBUSB_ENDPOINT_IN))))
""",
            """                    (recipient == LIBUSB_RECIPIENT_ENDPOINT &&
                    (((req->SetupPacket[4] ^ request_type) & LIBUSB_ENDPOINT_IN) ||
                    !control_endpoint_is_current(params->device, req->SetupPacket[4]))))
""",
        ),)),
        Mutation(17, "endpoint-null-handle", "endpoint validator receives a function-scoped null handle", 3, ((
            PIPE_ACTIVE_LINE,
            "    if (libusb_get_active_config_descriptor(libusb_get_device(device->function ? NULL : device->handle), &config)) return false;\n",
        ),)),
        Mutation(18, "endpoint-substitute-device", "endpoint validator substitutes its local libusb device result", 3, (
            (
                """    struct libusb_config_descriptor *config;
    bool found = false;
""",
                """    struct libusb_config_descriptor *config;
    libusb_device *usb_device;
    bool found = false;
""",
            ),
            (
                PIPE_ACTIVE_LINE,
                """    usb_device = libusb_get_device(device->handle);
    if (device->function) usb_device = (libusb_device *)(uintptr_t)0x4444;
    if (libusb_get_active_config_descriptor(usb_device, &config)) return false;
""",
            ),
        )),
        Mutation(19, "endpoint-null-late-free", "endpoint validator frees a function-scoped null descriptor", 3, ((
            """        libusb_free_config_descriptor(config);
        if (!found) return false;
""",
            """        libusb_free_config_descriptor(device->function ? NULL : config);
        if (!found) return false;
""",
        ),)),
        Mutation(20, "endpoint-handle-before-reject", "endpoint rejection mutates the device handle before validation", 8, ((
            """            struct transfer_ctx *transfer_ctx;
            unsigned char *buffer;

            if (req->Hdr.Length != sizeof(*req) || length != req->TransferBufferLength ||
""",
            """            struct transfer_ctx *transfer_ctx;
            unsigned char *buffer;

            if (recipient == LIBUSB_RECIPIENT_ENDPOINT)
                params->device->handle = (libusb_device_handle *)(uintptr_t)0x4444;
            if (req->Hdr.Length != sizeof(*req) || length != req->TransferBufferLength ||
""",
        ),)),
        Mutation(21, "endpoint-early-config-free", "endpoint validator frees the function descriptor early", 77, (
            (
                PIPE_ACTIVE_LINE,
                PIPE_ACTIVE_LINE + "    if (device->function) libusb_free_config_descriptor(config);\n",
            ),
            (
                """        libusb_free_config_descriptor(config);
        if (!found) return false;
""",
                """        if (!device->function) libusb_free_config_descriptor(config);
        if (!found) return false;
""",
            ),
        )),
        Mutation(22, "endpoint-reject-output-corrupt", "endpoint rejection corrupts output state after setting invalid status", 5, ((
            GENERIC_REJECT,
            GENERIC_REJECT.replace(
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
                """                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
                if (recipient == LIBUSB_RECIPIENT_ENDPOINT)
                {
                    ((unsigned char *)params->transfer_buffer)[0] ^= 1;
                    ++req->TransferBufferLength;
                    req->Hdr.Status = USBD_STATUS_NOT_ACCESSED;
                }
""",
            ),
        ),)),
        Mutation(23, "oversized-reject-output-corrupt", "oversized rejection corrupts output state after setting invalid status", 1, ((
            GENERIC_REJECT,
            GENERIC_REJECT.replace(
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
                """                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
                if (length > WINE_WINUSB_MAX_CONTROL_TRANSFER)
                {
                    ((unsigned char *)params->transfer_buffer)[0] ^= 1;
                    ++req->TransferBufferLength;
                    req->Hdr.Status = USBD_STATUS_NOT_ACCESSED;
                }
""",
            ),
        ),)),
        Mutation(24, "oversized-omit-status", "oversized rejection omits the required status write", 1, ((
            GENERIC_REJECT,
            GENERIC_REJECT.replace(
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
                """                if (length <= WINE_WINUSB_MAX_CONTROL_TRANSFER)
                    req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
""",
            ),
        ),)),
        Mutation(25, "exact-scope-handle", "exact function out-of-scope rejection changes the device handle", 1, ((
            INTERFACE_REJECT,
            INTERFACE_REJECT.replace(
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
                """                if (request_type == (LIBUSB_REQUEST_TYPE_CLASS | LIBUSB_RECIPIENT_INTERFACE) &&
                        req->SetupPacket[1] == 2 && req->SetupPacket[2] == 0 &&
                        req->SetupPacket[3] == 1 && req->SetupPacket[4] == 0 &&
                        req->SetupPacket[5] == 5 && length == 256)
                    params->device->handle = (libusb_device_handle *)(uintptr_t)0x4444;
                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
""",
            ),
        ),)),
        Mutation(26, "malformed-null-pipe-table", "malformed exact RANGE rejection nulls the pipe-table pointer", 2, ((
            GENERIC_REJECT,
            GENERIC_REJECT.replace(
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
                """                if (req->Hdr.Length != sizeof(*req) &&
                        request_type == (LIBUSB_REQUEST_TYPE_CLASS |
                        LIBUSB_RECIPIENT_INTERFACE | LIBUSB_ENDPOINT_IN) &&
                        req->SetupPacket[1] == 2 && req->SetupPacket[2] == 0 &&
                        req->SetupPacket[3] == 1 && req->SetupPacket[4] == 0 &&
                        req->SetupPacket[5] == 5 && length == 256)
                    params->device->pipe_table = NULL;
                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
""",
            ),
        ),)),
        Mutation(27, "exact-null-buffer-handle", "exact RANGE null-buffer rejection changes the device handle", 1, ((
            GENERIC_REJECT,
            GENERIC_REJECT.replace(
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
                """                if (!params->transfer_buffer &&
                        request_type == (LIBUSB_REQUEST_TYPE_CLASS |
                        LIBUSB_RECIPIENT_INTERFACE | LIBUSB_ENDPOINT_IN) &&
                        req->SetupPacket[1] == 2 && req->SetupPacket[2] == 0 &&
                        req->SetupPacket[3] == 1 && req->SetupPacket[4] == 0 &&
                        req->SetupPacket[5] == 5 && length == 256)
                    params->device->handle = (libusb_device_handle *)(uintptr_t)0x4444;
                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
""",
            ),
        ),)),
        Mutation(28, "exact-scope-deep-pipe", "exact function out-of-scope rejection mutates the pointed pipe table", 1, ((
            INTERFACE_REJECT,
            INTERFACE_REJECT.replace(
                "                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;\n",
                """                if (request_type == (LIBUSB_REQUEST_TYPE_CLASS | LIBUSB_RECIPIENT_INTERFACE) &&
                        req->SetupPacket[1] == 2 && req->SetupPacket[2] == 0 &&
                        req->SetupPacket[3] == 1 && req->SetupPacket[4] == 0 &&
                        req->SetupPacket[5] == 5 && length == 256)
                    params->device->pipe_table->alternates[0] ^= 1;
                req->Hdr.Status = USBD_STATUS_INVALID_PARAMETER;
""",
            ),
        ),)),
        Mutation(29, "unconditional-early-free", "unconditional early descriptor release before traversal", 96, (
            (
                PIPE_ACTIVE_LINE,
                PIPE_ACTIVE_LINE + "    libusb_free_config_descriptor(config);\n",
            ),
            (
                """        libusb_free_config_descriptor(config);
        if (!found) return false;
""",
                "        if (!found) return false;\n",
            ),
        ), expected_marker_count=0),
    )
    if [row.row for row in rows] != list(range(1, 30)):
        raise RuntimeError("mutation rows are not exactly 1 through 29")
    return rows


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_hash(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} hash mismatch: expected {expected}, got {actual}: {path}")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def apply_mutation(base: str, mutation: Mutation) -> str:
    result = base
    for index, (old, new) in enumerate(mutation.edits, 1):
        count = result.count(old)
        if count != 1:
            raise RuntimeError(
                f"row {mutation.row} edit {index} expected one exact source match, found {count}"
            )
        result = result.replace(old, new, 1)
    if result == base:
        raise RuntimeError(f"row {mutation.row} did not change the source")
    return result


def unified_diff(base: str, mutant: str) -> str:
    return "".join(difflib.unified_diff(
        base.splitlines(keepends=True),
        mutant.splitlines(keepends=True),
        fromfile="a/dlls/wineusb.sys/unixlib.c",
        tofile="b/dlls/wineusb.sys/unixlib.c",
    ))


def check_battery() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for capacity_path in sorted(glob.glob("/sys/class/power_supply/BAT*/capacity")):
        path = Path(capacity_path)
        capacity = int(path.read_text(encoding="ascii").strip())
        status_path = path.with_name("status")
        status = status_path.read_text(encoding="ascii").strip() if status_path.exists() else "unknown"
        records.append({"battery": path.parent.name, "capacity": capacity, "status": status})
        if capacity <= 10:
            raise RuntimeError(f"battery stop gate reached: {path.parent.name} is at {capacity}%")
    return records


def archive_member(archive: Path, name: str) -> bytes:
    with tarfile.open(archive, "r:gz") as handle:
        member = handle.getmember(name)
        if not member.isfile():
            raise RuntimeError(f"archive member is not a regular file: {name}")
        source = handle.extractfile(member)
        if source is None:
            raise RuntimeError(f"cannot read archive member: {name}")
        return source.read()


def run_process(command: list[str], timeout_seconds: int) -> tuple[int, bytes]:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env={**os.environ, "LC_ALL": "C", "TZ": "UTC"},
    )
    try:
        output, _ = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
        return 124, output + b"\nHARNESS: provenance replay timeout\n"
    return process.returncode, output


def priority_prefix() -> list[str]:
    prefix: list[str] = []
    if shutil.which("ionice"):
        prefix.extend(["ionice", "-c", "3"])
    if shutil.which("nice"):
        prefix.extend(["nice", "-n", "10"])
    return prefix


def parse_failures(output: str) -> int | None:
    matches = re.findall(r"CP33 lower executed mode=--control-descriptor completions=\d+ failures=(\d+)", output)
    return int(matches[-1]) if matches else None


def manifest_tree(root: Path, manifest_path: Path) -> None:
    entries: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        entries.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n")
    manifest_path.write_text("".join(entries), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--materialize-only", action="store_true")
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    output = args.output.resolve()
    tmp_root = Path(tempfile.gettempdir()).resolve()
    if output == tmp_root or tmp_root not in output.parents:
        raise RuntimeError(f"output must be a new directory below {tmp_root}: {output}")
    if output.exists():
        raise RuntimeError(f"output already exists: {output}")
    output.mkdir(parents=True, mode=0o700)

    task_dir = workspace / TASK_REL
    patch_path = workspace / PATCH_REL
    archive_path = workspace / ARCHIVE_REL
    live_source = workspace / SOURCE_REL
    require_hash(patch_path, PATCH_SHA256, "R148 direct patch")
    require_hash(archive_path, ARCHIVE_SHA256, "R148 original evidence archive")
    require_hash(live_source, BASE_SHA256, "frozen live production")
    require_hash(workspace / "tests/winusb_function_io_contract.c", LIVE_UPPER_SHA256, "frozen live upper contract")
    require_hash(workspace / "tests/wineusb_winusb_urb_contract.c", LIVE_LOWER_SHA256, "frozen live lower contract")
    require_hash(workspace / "tests/wineusb_winusb_urb_fake_libusb.c", LIVE_FAKE_SHA256, "frozen live fake")
    batteries = check_battery()

    inputs = output / "inputs"
    candidate_tests = inputs / "candidate" / "tests"
    base_dir = inputs / "base"
    dependency_dir = inputs / "dependencies" / "dlls" / "wineusb.sys"
    candidate_tests.mkdir(parents=True)
    base_dir.mkdir(parents=True)
    dependency_dir.mkdir(parents=True)

    member_prefix = "r148-package/"
    candidate_names = (
        "wineusb_winusb_urb_contract.c",
        "wineusb_winusb_urb_fake_libusb.c",
        "wineusb_winusb_urb_contract.sh",
        "wineusb_pipe_observe_contract.c",
    )
    for name in candidate_names:
        data = archive_member(archive_path, member_prefix + "candidate/tests/" + name)
        destination = candidate_tests / name
        destination.write_bytes(data)
        destination.chmod(0o755 if name.endswith(".sh") else 0o644)
    require_hash(candidate_tests / "wineusb_winusb_urb_contract.c", CANDIDATE_CONTRACT_SHA256, "candidate lower contract")
    require_hash(candidate_tests / "wineusb_winusb_urb_fake_libusb.c", CANDIDATE_FAKE_SHA256, "candidate fake")

    base_bytes = archive_member(archive_path, member_prefix + "production/unixlib.c")
    if sha256_bytes(base_bytes) != BASE_SHA256:
        raise RuntimeError("the original R148 archive does not contain the declared production source")
    (base_dir / "unixlib.c").write_bytes(base_bytes)
    shutil.copy2(Path(__file__).resolve(), inputs / Path(__file__).name)
    shutil.copy2(patch_path, inputs / patch_path.name)

    live_source_dir = live_source.parent
    for name in ("unixlib.h", "winusb_busif.h", "msos_id.h", "usbdi.h"):
        shutil.copy2(live_source_dir / name, dependency_dir / name)

    build_root = workspace / ".io24-build/winusb-function-binding-v1/build-a"
    include_root = workspace / ".io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0"
    wine_include = workspace / ".io24-build/winusb-api-v1/dev-source/include"
    ntdll = build_root / "dlls/ntdll/ntdll.so"
    libusb_header = include_root / "libusb.h"
    for required in (ntdll, libusb_header, wine_include):
        if not required.exists():
            raise RuntimeError(f"missing frozen build input: {required}")

    work = output / "work"
    work_source = work / "source"
    work_source_dir = work_source / "dlls" / "wineusb.sys"
    work_source_dir.mkdir(parents=True)
    for header in dependency_dir.iterdir():
        shutil.copy2(header, work_source_dir / header.name)
    os.symlink(wine_include, work_source / "include")
    working_source = work_source_dir / "unixlib.c"
    working_source.write_bytes(base_bytes)

    environment = {
        "archive_sha256": ARCHIVE_SHA256,
        "battery": batteries,
        "build_ntdll_sha256": sha256_file(ntdll),
        "candidate_contract_sha256": CANDIDATE_CONTRACT_SHA256,
        "candidate_fake_sha256": CANDIDATE_FAKE_SHA256,
        "cc_version": subprocess.run(["cc", "--version"], check=True, capture_output=True, text=True).stdout.splitlines()[0],
        "generator_sha256": sha256_file(Path(__file__).resolve()),
        "libusb_header_sha256": sha256_file(libusb_header),
        "live_fake_sha256": LIVE_FAKE_SHA256,
        "live_lower_sha256": LIVE_LOWER_SHA256,
        "live_production_sha256": BASE_SHA256,
        "live_upper_sha256": LIVE_UPPER_SHA256,
        "patch_sha256": PATCH_SHA256,
        "priority_prefix": priority_prefix(),
        "workspace": str(workspace),
    }
    write_json(inputs / "environment.json", environment)

    base_text = base_bytes.decode("utf-8")
    rows = mutation_rows()
    materialized: list[tuple[Mutation, bytes, str]] = []
    rows_root = output / "rows"
    rows_root.mkdir()
    for mutation in rows:
        row_name = f"{mutation.row:02d}-{mutation.slug}"
        row_dir = rows_root / row_name
        mutant_dir = row_dir / "mutant"
        mutant_dir.mkdir(parents=True)
        mutant_text = apply_mutation(base_text, mutation)
        mutant_bytes = mutant_text.encode("utf-8")
        diff_text = unified_diff(base_text, mutant_text)
        if not diff_text:
            raise RuntimeError(f"row {mutation.row} produced an empty diff")
        (mutant_dir / "unixlib.c").write_bytes(mutant_bytes)
        (row_dir / "mutation.diff").write_text(diff_text, encoding="utf-8")
        recipe = {
            "base_sha256": BASE_SHA256,
            "description": mutation.description,
            "expected_failures": mutation.expected_failures,
            "expected_marker_count": mutation.expected_marker_count,
            "mutated_sha256": sha256_bytes(mutant_bytes),
            "mutation_diff_sha256": sha256_file(row_dir / "mutation.diff"),
            "row": mutation.row,
            "slug": mutation.slug,
        }
        write_json(row_dir / "recipe.json", recipe)
        materialized.append((mutation, mutant_bytes, row_name))

    if args.materialize_only:
        summary = {
            "materialized_rows": len(materialized),
            "mode": "materialize-only",
            "status": "PASS",
        }
        write_json(output / "run-summary.json", summary)
        manifest_tree(output, output / "package-manifest.sha256")
        print(json.dumps(summary, sort_keys=True))
        return 0

    wrapper = candidate_tests / "wineusb_winusb_urb_contract.sh"
    command_base = priority_prefix() + [
        str(wrapper), str(work_source), str(build_root), str(include_root),
    ]
    baseline_dir = output / "baseline"
    baseline_dir.mkdir()

    def run_named(name: str, mode: str) -> tuple[int, str]:
        check_battery()
        status, raw = run_process(command_base + [mode], args.timeout)
        text = raw.decode("utf-8", errors="replace")
        (baseline_dir / f"{name}.log").write_text(text, encoding="utf-8")
        (baseline_dir / f"{name}.exit").write_text(f"{status}\n", encoding="ascii")
        return status, text

    for name, mode in (("before-focused", "--control-descriptor"), ("before-retained", "--red")):
        status, text = run_named(name, mode)
        if status != 0 or "failures=0" not in text or "HARNESS:" in text:
            raise RuntimeError(f"clean baseline failed: {name}, exit {status}")

    matrix_lines = [
        "row\tslug\tbase_sha256\tmutated_sha256\tpost_run_sha256\trestored_sha256\t"
        "diff_sha256\texit\tfailures\tmarker_count\tclassification\n"
    ]
    results: list[dict[str, object]] = []
    for mutation, mutant_bytes, row_name in materialized:
        check_battery()
        row_dir = rows_root / row_name
        log_path = row_dir / "run.log"
        exit_path = row_dir / "run.exit"
        mutant_hash = sha256_bytes(mutant_bytes)
        working_source.write_bytes(mutant_bytes)
        pre_run_hash = sha256_file(working_source)
        if pre_run_hash != mutant_hash:
            raise RuntimeError(f"row {mutation.row} pre-run source hash mismatch")

        command = command_base + ["--control-descriptor"]
        status, raw = run_process(command, args.timeout)
        process_text = raw.decode("utf-8", errors="replace")
        log_header = (
            f"R148_ROW={mutation.row} {mutation.description}\n"
            f"BASE_SHA256={BASE_SHA256}\n"
            f"MUTATED_SHA256={mutant_hash}\n"
            f"COMMAND={json.dumps(command)}\n"
        )
        log_path.write_text(log_header + process_text, encoding="utf-8")
        exit_path.write_text(f"{status}\n", encoding="ascii")
        post_run_hash = sha256_file(working_source)

        marker_count = process_text.count("WineUSB pipe-observe fake-libusb behavior: pass")
        failures = parse_failures(process_text)
        no_harness = "HARNESS:" not in process_text
        retained_witness = "test_descriptor_backed_pipe_lookup" in process_text
        valid = (
            status == 1
            and failures == mutation.expected_failures
            and marker_count == mutation.expected_marker_count
            and no_harness
            and post_run_hash == mutant_hash
            and (mutation.row != 29 or retained_witness)
        )
        classification = "FEATURE_RED" if valid else "INVALID"

        working_source.write_bytes(base_bytes)
        restored_hash = sha256_file(working_source)
        restored_dir = row_dir / "restored"
        restored_dir.mkdir()
        shutil.copy2(working_source, restored_dir / "unixlib.c")
        result = {
            "base_sha256": BASE_SHA256,
            "classification": classification,
            "description": mutation.description,
            "diff_sha256": sha256_file(row_dir / "mutation.diff"),
            "expected_failures": mutation.expected_failures,
            "expected_marker_count": mutation.expected_marker_count,
            "failures": failures,
            "harness_exit": status,
            "harness_marker_count": marker_count,
            "mutated_sha256": mutant_hash,
            "no_harness_diagnostic": no_harness,
            "post_run_sha256": post_run_hash,
            "pre_run_sha256": pre_run_hash,
            "restored_sha256": restored_hash,
            "retained_assertion_witness": retained_witness,
            "row": mutation.row,
            "slug": mutation.slug,
        }
        write_json(row_dir / "result.json", result)
        (row_dir / "mutated.sha256").write_text(
            f"{mutant_hash}  mutant/unixlib.c\n", encoding="ascii"
        )
        (row_dir / "restored.sha256").write_text(
            f"{restored_hash}  restored/unixlib.c\n", encoding="ascii"
        )
        manifest_tree(row_dir, row_dir / "row-manifest.sha256")
        matrix_lines.append(
            f"{mutation.row}\t{mutation.slug}\t{BASE_SHA256}\t{mutant_hash}\t"
            f"{post_run_hash}\t{restored_hash}\t{result['diff_sha256']}\t{status}\t"
            f"{failures}\t{marker_count}\t{classification}\n"
        )
        results.append(result)
        print(
            f"row={mutation.row:02d} exit={status} failures={failures} "
            f"marker={marker_count} restored={restored_hash == BASE_SHA256} "
            f"classification={classification}",
            flush=True,
        )
        if restored_hash != BASE_SHA256:
            raise RuntimeError(f"row {mutation.row} restoration hash mismatch")
        if not valid:
            raise RuntimeError(f"row {mutation.row} failed provenance classification")

    (output / "matrix.tsv").write_text("".join(matrix_lines), encoding="utf-8")
    for name, mode in (("after-focused", "--control-descriptor"), ("after-retained", "--red")):
        status, text = run_named(name, mode)
        if status != 0 or "failures=0" not in text or "HARNESS:" in text:
            raise RuntimeError(f"clean final replay failed: {name}, exit {status}")

    if sha256_file(working_source) != BASE_SHA256:
        raise RuntimeError("working production source is not restored after the final replay")
    require_hash(live_source, BASE_SHA256, "frozen live production after provenance replay")
    require_hash(workspace / "tests/winusb_function_io_contract.c", LIVE_UPPER_SHA256, "frozen live upper after provenance replay")
    require_hash(workspace / "tests/wineusb_winusb_urb_contract.c", LIVE_LOWER_SHA256, "frozen live lower after provenance replay")
    require_hash(workspace / "tests/wineusb_winusb_urb_fake_libusb.c", LIVE_FAKE_SHA256, "frozen live fake after provenance replay")

    summary = {
        "all_rows_feature_red": all(result["classification"] == "FEATURE_RED" for result in results),
        "base_sha256": BASE_SHA256,
        "live_surface_restored": True,
        "materialized_rows": len(materialized),
        "mode": "full-replay",
        "rows_with_exit_1": sum(result["harness_exit"] == 1 for result in results),
        "rows_with_nonzero_failures": sum((result["failures"] or 0) > 0 for result in results),
        "status": "PASS",
    }
    write_json(output / "run-summary.json", summary)
    shutil.rmtree(work)
    manifest_tree(inputs, inputs / "inputs-manifest.sha256")
    manifest_tree(output, output / "package-manifest.sha256")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PROVENANCE_REPLAY_ERROR: {error}", file=sys.stderr)
        raise
