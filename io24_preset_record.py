#!/usr/bin/env python3
"""Pure codec for Universal Control's preset-record archive.

UC's ``.scene`` JSON and its ``MemP/Stat`` payload represent the same nested
preset object. The wire record uses a compact tagged archive: dictionaries are
braced, keys and strings are length-prefixed, integers use signed 8-, 16-, or
32-bit forms, and real values are big-endian IEEE-754 binary32. This module
performs only that local conversion; it has no device or transport code.

The format is independently visible in the factory records embedded in
``dspusbdevice.dll`` and in the UC 4.7.2 component serializer.
"""
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import struct
import tempfile


DOUBLER_CLASS_ID = "{66A10093-D461-4CAC-A80C-91F6A1BB37E5}"
DEVICE_SLOT_PAIRS = {1: (0, 1), 2: (2, 3)}
DEVICE_SLOT_REGISTRY_SCHEMA = "io24-device-slot-registry-v2"
DEVICE_SLOT_REGISTRY_PROVENANCE = \
    "HOST_WRITTEN_DEVICE_READBACK_UNAVAILABLE"
DEVICE_PRESET_LIBRARY_REGISTRY_SCHEMA = \
    "io24-device-preset-library-registry-v1"
DEVICE_PRESET_LIBRARY_REGISTRY_PROVENANCE = \
    "HOST_SENT_UC_PRSM_DEVICE_READBACK_UNAVAILABLE"

# A Stat update replaces a complete channel preset; accepting a tiny mapping
# containing only ``voicefx`` would silently erase the rest of that preset.
# These sections occur in every complete factory record recovered from UC.
REQUIRED_DEVICE_SLOT_SECTIONS = frozenset({
    "preset_name", "opt", "filter", "gate", "limit", "eq", "comp",
})


def complete_device_slot_record(record):
    """Validate and copy one explicit, complete ``MemP/Stat`` base record.

    A Stat save replaces the selected device block.  Consequently this helper
    accepts only a complete record supplied by the caller; it never attempts
    to infer the current device state or merge an incomplete host preset.
    ``_offset`` is extraction-only metadata used by the recovered factory JSON
    and is removed before the record is returned.

    The returned copy is also checked against the local archive codec.  That
    catches unsupported JSON values before any caller builds a wire frame.
    """
    if not isinstance(record, Mapping):
        raise TypeError("complete device slot record must be a mapping")
    missing = sorted(REQUIRED_DEVICE_SLOT_SECTIONS.difference(record))
    if missing:
        raise ValueError("complete device slot record is incomplete; missing %s" %
                         ", ".join(missing))
    result = deepcopy(dict(record))
    result.pop("_offset", None)
    if not isinstance(result.get("preset_name"), str):
        raise TypeError("complete device slot record preset_name must be text")
    # Check the actual recovered archive surface, rather than merely trusting
    # that it came from a JSON file.
    encode_preset_record(result)
    return result


def _device_slot_index(name, value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 4:
        raise ValueError("%s must be a device slot in the range 0..3" % name)
    return value


def _device_preset_library_index(name, value):
    if isinstance(value, bool) or not isinstance(value, int) or \
            not 16 <= value <= 27:
        raise ValueError("%s must be a Device Presets index in the range "
                         "16..27" % name)
    return value


def _json_pointer_part(value):
    return value.replace("~", "~0").replace("/", "~1")


def _record_differences(expected, observed, path=""):
    """Return stable JSON-pointer-like paths where complete records differ."""
    if isinstance(expected, Mapping) and isinstance(observed, Mapping):
        differences = []
        for key in sorted(set(expected).union(observed)):
            child_path = "%s/%s" % (path, _json_pointer_part(key))
            if key not in expected or key not in observed:
                differences.append(child_path)
            else:
                differences.extend(
                    _record_differences(expected[key], observed[key], child_path))
        return differences
    if isinstance(expected, list) and isinstance(observed, list):
        differences = []
        for index in range(max(len(expected), len(observed))):
            child_path = "%s/%d" % (path, index)
            if index >= len(expected) or index >= len(observed):
                differences.append(child_path)
            else:
                differences.extend(
                    _record_differences(expected[index], observed[index], child_path))
        return differences
    if type(expected) is not type(observed) or expected != observed:
        return [path or "/"]
    return []


def _canonical_record_sha256(record):
    encoded = json.dumps(record, allow_nan=False, ensure_ascii=False,
                         separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validated_device_identity(value):
    fields = {"serial", "vendor_id", "product_id", "bcd_device"}
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(
            "device slot registry identity must contain serial, vendor_id, "
            "product_id, and bcd_device")
    identity = dict(value)
    serial = identity["serial"]
    if not isinstance(serial, str) or not serial.strip() or serial != serial.strip():
        raise ValueError("device slot registry serial must be non-empty text")
    for name in ("vendor_id", "product_id", "bcd_device"):
        encoded = identity[name]
        if not isinstance(encoded, str) or len(encoded) != 4 or \
                encoded != encoded.lower() or \
                any(char not in "0123456789abcdef" for char in encoded):
            raise ValueError(
                "device slot registry %s must be four lowercase hex digits" %
                name)
    return identity


class DeviceSlotRegistry:
    """Local evidence for complete slot bodies the Host actually sent.

    The device exposes its selected slot but not the stored body.  This file is
    therefore deliberately one-way provenance: it never adopts an unknown
    device slot, never auto-replays a body, and never labels a sent record as
    device readback or nonvolatile commit.
    """

    def __init__(self, path):
        try:
            self.path = os.fspath(path)
        except TypeError as exc:
            raise TypeError("device slot registry path must be path-like") from exc

    @staticmethod
    def _blank():
        return {"schema": DEVICE_SLOT_REGISTRY_SCHEMA, "slots": {}}

    def _read(self):
        if not os.path.exists(self.path):
            return self._blank()

        def reject_nonstandard_json(value):
            raise ValueError("non-finite registry value %s is not allowed" % value)

        with open(self.path, encoding="utf-8") as source:
            document = json.load(source, parse_constant=reject_nonstandard_json)
        if not isinstance(document, dict) or \
                document.get("schema") != DEVICE_SLOT_REGISTRY_SCHEMA or \
                not isinstance(document.get("slots"), dict):
            raise ValueError("invalid device slot registry schema")
        for key, entry in document["slots"].items():
            try:
                slot = int(key)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid device slot registry key") from exc
            _device_slot_index("registry slot", slot)
            if not isinstance(entry, dict) or entry.get("slot") != slot:
                raise ValueError("invalid device slot registry entry")
            record = complete_device_slot_record(entry.get("record"))
            if entry.get("canonical_sha256") != _canonical_record_sha256(record):
                raise ValueError("device slot registry record hash differs")
            if entry.get("physical_channel") != (1 if slot < 2 else 2):
                raise ValueError("device slot registry channel differs")
            if entry.get("device_identity") != _validated_device_identity(
                    entry.get("device_identity")):
                raise ValueError("device slot registry identity differs")
            if entry.get("provenance") != DEVICE_SLOT_REGISTRY_PROVENANCE:
                raise ValueError("device slot registry provenance differs")
            if entry.get("status") != "WRITE_SENT_UNVERIFIED":
                raise ValueError("device slot registry status differs")
            transport = entry.get("transport")
            if not isinstance(transport, dict):
                raise ValueError("device slot registry transport is invalid")
            fragments = transport.get("fragments_sent")
            replies = transport.get("replies_received")
            if isinstance(fragments, bool) or not isinstance(fragments, int) or \
                    fragments < 1 or isinstance(replies, bool) or \
                    not isinstance(replies, int) or not 0 <= replies <= fragments:
                raise ValueError("device slot registry transport counts are invalid")
        return document

    def get(self, slot_index, *, device_identity):
        """Return one entry only when it belongs to the current device."""
        slot = _device_slot_index("slot_index", slot_index)
        identity = _validated_device_identity(device_identity)
        entry = self._read()["slots"].get(str(slot))
        if entry is None or entry.get("device_identity") != identity:
            return None
        return deepcopy(entry)

    def entries(self, *, device_identity=None):
        """Return Host-known sent-write receipts in global slot order.

        This is a local Host list, not device readback.  Supplying an identity
        limits the result to that exact unit; omitting it is useful while the
        Host is opening offline and still preserves each entry's identity.
        """
        identity = None if device_identity is None else \
            _validated_device_identity(device_identity)
        entries = []
        for key, entry in self._read()["slots"].items():
            if identity is None or entry.get("device_identity") == identity:
                entries.append(deepcopy(entry))
        return sorted(entries, key=lambda entry: entry["slot"])

    def prepare_write(self, slot_index, record, source, written_at=None, *,
                      device_identity, native_record=None):
        """Validate local state and one complete body before any device write."""
        slot = _device_slot_index("slot_index", slot_index)
        complete = complete_device_slot_record(record)
        identity = _validated_device_identity(device_identity)
        if not isinstance(source, str) or not source.strip():
            raise ValueError("device slot registry source must be non-empty text")
        if written_at is None:
            written_at = datetime.now(timezone.utc).isoformat()
        if not isinstance(written_at, str) or not written_at:
            raise ValueError("device slot registry timestamp must be text")
        entry = {
            "slot": slot,
            "physical_channel": 1 if slot < 2 else 2,
            "device_identity": identity,
            "record": complete,
            "canonical_sha256": _canonical_record_sha256(complete),
            "source": source.strip(),
            "written_at": written_at,
            "provenance": DEVICE_SLOT_REGISTRY_PROVENANCE,
            "status": "WRITE_SENT_UNVERIFIED",
        }
        if native_record is not None:
            try:
                native_record = bytes(native_record)
            except (TypeError, ValueError):
                raise TypeError("native device slot body must be bytes-like")
            entry.update({
                "body_format": "firmware-native-v2",
                "native_sha256": hashlib.sha256(native_record).hexdigest(),
            })
        return {"document": self._read(), "entry": entry}

    def commit_sent(self, prepared, transport_report):
        """Persist a prepared entry after its transport call returned."""
        if not isinstance(prepared, dict) or \
                not isinstance(prepared.get("document"), dict) or \
                not isinstance(prepared.get("entry"), dict):
            raise ValueError("invalid prepared device slot write")
        entry = deepcopy(prepared["entry"])
        slot = _device_slot_index("prepared slot", entry.get("slot"))
        if not isinstance(transport_report, dict) or \
                transport_report.get("slot") != slot:
            raise ValueError("transport slot does not match prepared slot")
        fragments = transport_report.get("fragments_sent")
        replies = transport_report.get("replies_received")
        if isinstance(fragments, bool) or not isinstance(fragments, int) or \
                fragments < 1 or isinstance(replies, bool) or \
                not isinstance(replies, int) or not 0 <= replies <= fragments:
            raise ValueError("transport counts are invalid")
        entry["transport"] = {
            "fragments_sent": fragments,
            "replies_received": replies,
        }
        document = deepcopy(prepared["document"])
        if document.get("schema") != DEVICE_SLOT_REGISTRY_SCHEMA or \
                not isinstance(document.get("slots"), dict):
            raise ValueError("invalid prepared registry document")
        document["slots"][str(slot)] = entry
        self._write_atomic(document)
        return deepcopy(entry)

    def _write_atomic(self, document):
        parent = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(parent, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=parent,
            prefix=".%s." % os.path.basename(self.path), suffix=".tmp",
            delete=False)
        temporary = handle.name
        try:
            with handle:
                json.dump(document, handle, allow_nan=False, ensure_ascii=False,
                          indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            try:
                directory_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
            except (AttributeError, OSError):
                directory_fd = None
            if directory_fd is not None:
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise


class DevicePresetLibraryRegistry:
    """Local receipts for UC's twelve-entry ``MemP/PrsM`` library.

    Indexes 16..21 belong to physical input 1 and 22..27 to input 2.  The
    device does not expose a read command for these bodies, so a successful
    SetP exchange is recorded accurately as ``WRITE_SENT_UNVERIFIED``.  This
    registry never turns a transport receipt into a persistence or audibility
    claim.
    """

    def __init__(self, path):
        try:
            self.path = os.fspath(path)
        except TypeError as exc:
            raise TypeError(
                "device preset library registry path must be path-like") from exc

    @staticmethod
    def _blank():
        return {
            "schema": DEVICE_PRESET_LIBRARY_REGISTRY_SCHEMA,
            "presets": {},
        }

    @staticmethod
    def _location(user_index):
        user_index = _device_preset_library_index("user_index", user_index)
        if user_index <= 21:
            return 1, user_index - 16
        return 2, user_index - 22

    def _read(self):
        if not os.path.exists(self.path):
            return self._blank()

        def reject_nonstandard_json(value):
            raise ValueError(
                "non-finite registry value %s is not allowed" % value)

        with open(self.path, encoding="utf-8") as source:
            document = json.load(source, parse_constant=reject_nonstandard_json)
        if not isinstance(document, dict) or \
                document.get("schema") != \
                DEVICE_PRESET_LIBRARY_REGISTRY_SCHEMA or \
                not isinstance(document.get("presets"), dict):
            raise ValueError("invalid device preset library registry schema")
        for key, entry in document["presets"].items():
            try:
                user_index = int(key)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "invalid device preset library registry key") from exc
            user_index = _device_preset_library_index(
                "registry user index", user_index)
            if not isinstance(entry, dict) or \
                    entry.get("user_index") != user_index:
                raise ValueError("invalid device preset library registry entry")
            physical_channel, channel_slot = self._location(user_index)
            if entry.get("physical_channel") != physical_channel or \
                    entry.get("channel_slot") != channel_slot:
                raise ValueError("device preset library location differs")
            record = complete_device_slot_record(entry.get("record"))
            if entry.get("canonical_sha256") != \
                    _canonical_record_sha256(record):
                raise ValueError("device preset library record hash differs")
            if entry.get("device_identity") != _validated_device_identity(
                    entry.get("device_identity")):
                raise ValueError("device preset library identity differs")
            if entry.get("provenance") != \
                    DEVICE_PRESET_LIBRARY_REGISTRY_PROVENANCE:
                raise ValueError("device preset library provenance differs")
            if entry.get("status") != "WRITE_SENT_UNVERIFIED":
                raise ValueError("device preset library status differs")
            transport = entry.get("transport")
            if not isinstance(transport, dict) or \
                    transport.get("user_index") != user_index:
                raise ValueError("device preset library transport is invalid")
            fragments = transport.get("fragments_sent")
            replies = transport.get("replies_received")
            if isinstance(fragments, bool) or not isinstance(fragments, int) or \
                    fragments < 1 or isinstance(replies, bool) or \
                    not isinstance(replies, int) or \
                    not 0 <= replies <= fragments:
                raise ValueError(
                    "device preset library transport counts are invalid")
        return document

    def get(self, user_index, *, device_identity):
        user_index = _device_preset_library_index("user_index", user_index)
        identity = _validated_device_identity(device_identity)
        entry = self._read()["presets"].get(str(user_index))
        if entry is None or entry.get("device_identity") != identity:
            return None
        return deepcopy(entry)

    def entries(self, *, device_identity=None):
        identity = None if device_identity is None else \
            _validated_device_identity(device_identity)
        entries = []
        for entry in self._read()["presets"].values():
            if identity is None or entry.get("device_identity") == identity:
                entries.append(deepcopy(entry))
        return sorted(entries, key=lambda entry: entry["user_index"])

    def prepare_write(self, user_index, record, source, written_at=None, *,
                      device_identity):
        user_index = _device_preset_library_index("user_index", user_index)
        complete = complete_device_slot_record(record)
        identity = _validated_device_identity(device_identity)
        if not isinstance(source, str) or not source.strip():
            raise ValueError(
                "device preset library source must be non-empty text")
        if written_at is None:
            written_at = datetime.now(timezone.utc).isoformat()
        if not isinstance(written_at, str) or not written_at:
            raise ValueError("device preset library timestamp must be text")
        physical_channel, channel_slot = self._location(user_index)
        entry = {
            "user_index": user_index,
            "physical_channel": physical_channel,
            "channel_slot": channel_slot,
            "device_identity": identity,
            "record": complete,
            "canonical_sha256": _canonical_record_sha256(complete),
            "source": source.strip(),
            "written_at": written_at,
            "provenance": DEVICE_PRESET_LIBRARY_REGISTRY_PROVENANCE,
            "status": "WRITE_SENT_UNVERIFIED",
            "body_format": "uc-tagged-preset-record",
        }
        return {"document": self._read(), "entry": entry}

    def commit_sent(self, prepared, transport_report):
        if not isinstance(prepared, dict) or \
                not isinstance(prepared.get("document"), dict) or \
                not isinstance(prepared.get("entry"), dict):
            raise ValueError("invalid prepared device preset library write")
        entry = deepcopy(prepared["entry"])
        user_index = _device_preset_library_index(
            "prepared user index", entry.get("user_index"))
        if not isinstance(transport_report, dict) or \
                transport_report.get("user_index") != user_index:
            raise ValueError(
                "transport user index does not match prepared preset")
        fragments = transport_report.get("fragments_sent")
        replies = transport_report.get("replies_received")
        if isinstance(fragments, bool) or not isinstance(fragments, int) or \
                fragments < 1 or isinstance(replies, bool) or \
                not isinstance(replies, int) or \
                not 0 <= replies <= fragments:
            raise ValueError("transport counts are invalid")
        entry["transport"] = {
            "user_index": user_index,
            "fragments_sent": fragments,
            "replies_received": replies,
        }
        document = deepcopy(prepared["document"])
        if document.get("schema") != \
                DEVICE_PRESET_LIBRARY_REGISTRY_SCHEMA or \
                not isinstance(document.get("presets"), dict):
            raise ValueError("invalid prepared registry document")
        document["presets"][str(user_index)] = entry
        self._write_atomic(document)
        return deepcopy(entry)

    def _write_atomic(self, document):
        parent = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(parent, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=parent,
            prefix=".%s." % os.path.basename(self.path), suffix=".tmp",
            delete=False)
        temporary = handle.name
        try:
            with handle:
                json.dump(document, handle, allow_nan=False,
                          ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            try:
                directory_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
            except (AttributeError, OSError):
                directory_fd = None
            if directory_fd is not None:
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise


def compare_device_slot_records(expected_slot, expected_record,
                                observed_slot=None, observed_record=None):
    """Compare a prepared ``Stat`` record with an independently decoded readback.

    The function is deliberately local-only.  A matching slot index, a USB
    reply, or a host-side cached record is not an ``observed_record`` and yields
    ``READBACK_UNAVAILABLE``.  ``RECORD_EQUAL`` means only that two complete
    decoded records are semantically equal; it never proves nonvolatile commit,
    front-panel recall, or audible Voice FX.
    """
    expected_slot = _device_slot_index("expected_slot", expected_slot)
    expected = complete_device_slot_record(expected_record)
    result = {
        "schema": "cp34-device-slot-record-comparison-v1",
        "status": "READBACK_UNAVAILABLE",
        "expected_slot": expected_slot,
        "observed_slot": None,
        "expected_canonical_sha256": _canonical_record_sha256(expected),
        "observed_canonical_sha256": None,
        "differences": [],
        "physical_commit": "UNPROVED",
        "front_panel_recall": "UNPROVED",
        "audibility": "UNPROVED",
    }
    if observed_slot is not None:
        result["observed_slot"] = _device_slot_index(
            "observed_slot", observed_slot)
    if observed_record is None:
        return result

    try:
        observed = complete_device_slot_record(observed_record)
    except (TypeError, ValueError) as error:
        result["status"] = "INVALID_READBACK"
        result["readback_error"] = "%s: %s" % (type(error).__name__, error)
        return result

    result["observed_canonical_sha256"] = _canonical_record_sha256(observed)
    if result["observed_slot"] != expected_slot:
        result["differences"].append("/slot")
    result["differences"].extend(_record_differences(expected, observed))
    result["status"] = "RECORD_EQUAL" if not result["differences"] \
        else "RECORD_MISMATCH"
    return result


def load_complete_device_slot_record(path):
    """Load one caller-selected complete channel base from local JSON.

    ``path`` must name a JSON object representing exactly one complete channel
    record.  This is deliberately a local-file import: it neither opens nor
    reads the interface and cannot claim that the file matches a current slot.
    """
    try:
        path = os.fspath(path)
    except TypeError as exc:
        raise TypeError("complete device slot record path must be path-like") from exc

    def reject_nonstandard_json(value):
        raise ValueError("non-finite JSON value %s is not allowed" % value)

    with open(path, encoding="utf-8") as source:
        record = json.load(source, parse_constant=reject_nonstandard_json)
    return complete_device_slot_record(record)


def load_paired_device_slot_bases(channel1_path, channel2_path):
    """Load independent local bases for channel 1 and channel 2.

    This convenience function intentionally takes two paths.  Supplying the
    same file is allowed, but no implicit factory fallback or device read is
    performed when either path is absent.
    """
    return (load_complete_device_slot_record(channel1_path),
            load_complete_device_slot_record(channel2_path))


def _unit_value(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("%s must be a real number" % name)
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("%s must be finite and in the range 0..1" % name)
    return value


def _clamped_unit_value(name, value):
    """Return a finite gain clamped to the firmware's normalized range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("%s must be a real number" % name)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % name)
    return max(0.0, min(1.0, value))


def _boolean_value(name, value):
    if not isinstance(value, bool):
        raise TypeError("%s must be boolean" % name)
    return value


def _archive_boolean_value(name, value):
    """Parse a boolean from JSON or the archive's integer representation."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise TypeError("%s must be boolean" % name)


def normalized_doubler_lane_controls(voicefx):
    """Read custom model-0 lane controls from a current or legacy record.

    Old Universal Control records do not contain these keys.  Their retained
    behavior is full wet signal and no lane bypass, which is deliberately the
    default here.  This helper is local schema handling only; it never implies
    that stock firmware understands the custom fields.
    """
    if not isinstance(voicefx, Mapping):
        raise TypeError("voicefx must be a mapping")
    return {
        "wet_ch1": _clamped_unit_value("wet_ch1", voicefx.get("wet_ch1", 1.0)),
        "wet_ch2": _clamped_unit_value("wet_ch2", voicefx.get("wet_ch2", 1.0)),
        "bypass_ch1": _archive_boolean_value(
            "bypass_ch1", voicefx.get("bypass_ch1", False)),
        "bypass_ch2": _archive_boolean_value(
            "bypass_ch2", voicefx.get("bypass_ch2", False)),
    }


def doubler_private_reverb_state(enabled=True, lows=0.06, width=0.405,
                                  mix=0.295, wet_ch1=1.0, wet_ch2=1.0,
                                  bypass_ch1=False, bypass_ch2=False,
                                  custom_firmware_lane_controls=False):
    """Return the exact storable state for Doubler's private reverb core.

    This is Voice FX model 0's record surface, not shared reverb block 202.
    Stock UC exposes one shared parameter set and assigns Voice FX to one input
    at a time; independently parameterised per-channel copies do not exist.
    """
    _boolean_value("enabled", enabled)
    _boolean_value("bypass_ch1", bypass_ch1)
    _boolean_value("bypass_ch2", bypass_ch2)
    _boolean_value("custom_firmware_lane_controls",
                   custom_firmware_lane_controls)
    result = {
        "__classid": DOUBLER_CLASS_ID,
        "on": int(enabled),
        "lows": _unit_value("lows", lows),
        "width": _unit_value("width", width),
        "mix": _unit_value("mix", mix),
    }
    requested_lanes = normalized_doubler_lane_controls({
        "wet_ch1": wet_ch1, "wet_ch2": wet_ch2,
        "bypass_ch1": bypass_ch1, "bypass_ch2": bypass_ch2,
    })
    if custom_firmware_lane_controls:
        result.update(requested_lanes)
    elif requested_lanes != {
            "wet_ch1": 1.0, "wet_ch2": 1.0,
            "bypass_ch1": False, "bypass_ch2": False}:
        raise ValueError("per-lane controls require explicit custom firmware "
                         "capability")
    return result


def with_doubler_private_reverb(slot_record, enabled=True, lows=0.06,
                                width=0.405, mix=0.295,
                                preset_name=None, wet_ch1=1.0, wet_ch2=1.0,
                                bypass_ch1=False, bypass_ch2=False,
                                custom_firmware_lane_controls=False):
    """Copy one complete channel record and install model-0 private reverb."""
    result = complete_device_slot_record(slot_record)
    if preset_name is not None and not isinstance(preset_name, str):
        raise TypeError("preset_name must be text")

    if preset_name is not None:
        result["preset_name"] = preset_name
    result["voicefx"] = doubler_private_reverb_state(
        enabled=enabled, lows=lows, width=width, mix=mix,
        wet_ch1=wet_ch1, wet_ch2=wet_ch2,
        bypass_ch1=bypass_ch1, bypass_ch2=bypass_ch2,
        custom_firmware_lane_controls=custom_firmware_lane_controls)
    return result


def paired_doubler_private_reverb_slots(channel1_slot, channel1_base,
                                         channel2_slot, channel2_base,
                                         enabled=True, lows=0.06,
                                         width=0.405, mix=0.295,
                                         preset_name=None, wet_ch1=1.0,
                                         wet_ch2=1.0, bypass_ch1=False,
                                         bypass_ch2=False,
                                         custom_firmware_lane_controls=False):
    """Build the superseded paired fixture for offline firmware design.

    Global slots 0/1 belong to channel 1 and 2/3 to channel 2. Both records
    intentionally receive byte-equivalent ``voicefx`` mappings. Stock UC does
    not save Voice FX this way; it assigns the shared engine to one channel and
    saves that channel's selected slot. No caller should treat this helper as a
    live stock workflow.
    """
    if isinstance(channel1_slot, bool) or channel1_slot not in (0, 1):
        raise ValueError("channel 1 device slot must be 0 or 1")
    if isinstance(channel2_slot, bool) or channel2_slot not in (2, 3):
        raise ValueError("channel 2 device slot must be 2 or 3")

    values = dict(enabled=enabled, lows=lows, width=width, mix=mix,
                  preset_name=preset_name, wet_ch1=wet_ch1, wet_ch2=wet_ch2,
                  bypass_ch1=bypass_ch1, bypass_ch2=bypass_ch2,
                  custom_firmware_lane_controls=custom_firmware_lane_controls)
    records = {
        channel1_slot: with_doubler_private_reverb(channel1_base, **values),
        channel2_slot: with_doubler_private_reverb(channel2_base, **values),
    }
    if records[channel1_slot]["voicefx"] != records[channel2_slot]["voicefx"]:
        raise AssertionError("paired private-reverb state diverged")
    return records


def _encode_name(value):
    if not isinstance(value, str):
        raise TypeError("preset record keys and strings must be text")
    raw = value.encode("utf-8")
    if len(raw) > 0x7F:
        raise ValueError("preset record text exceeds the recovered short form")
    return b"i" + bytes((len(raw),)) + raw


def _encode_value(value):
    if isinstance(value, Mapping):
        return encode_preset_record(value)
    if isinstance(value, str):
        return b"S" + _encode_name(value)
    if isinstance(value, bool):
        return b"i" + struct.pack("b", int(value))
    if isinstance(value, int):
        if -128 <= value <= 127:
            return b"i" + struct.pack("b", value)
        if -32768 <= value <= 32767:
            return b"I" + struct.pack(">h", value)
        if -2147483648 <= value <= 2147483647:
            return b"l" + struct.pack(">i", value)
        raise ValueError("preset record integer must fit 32 signed bits")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("preset record real value must be finite")
        return b"d" + struct.pack(">f", value)
    raise TypeError("unsupported preset record value type: %s" %
                    type(value).__name__)


def encode_preset_record(record):
    """Encode one insertion-ordered scene slot or factory preset mapping."""
    if not isinstance(record, Mapping):
        raise TypeError("preset record must be a mapping")
    out = bytearray(b"{")
    for key, value in record.items():
        if key == "_offset":
            raise ValueError("remove extractor-only _offset before encoding")
        out.extend(_encode_name(key))
        out.extend(_encode_value(value))
    out.extend(b"}")
    return bytes(out)


class _Reader:
    def __init__(self, data):
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("preset record must be bytes-like")
        self.data = bytes(data)
        self.offset = 0

    def take(self, size):
        end = self.offset + size
        if end > len(self.data):
            raise ValueError("truncated preset record at byte %d" % self.offset)
        value = self.data[self.offset:end]
        self.offset = end
        return value

    def name(self):
        if self.take(1) != b"i":
            raise ValueError("unsupported preset-record name encoding")
        size = self.take(1)[0]
        try:
            return self.take(size).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("invalid UTF-8 in preset record") from exc

    def value(self):
        tag = self.take(1)
        if tag == b"{":
            return self.mapping(opened=True)
        if tag == b"S":
            return self.name()
        if tag == b"i":
            return struct.unpack("b", self.take(1))[0]
        if tag == b"I":
            return struct.unpack(">h", self.take(2))[0]
        if tag == b"l":
            return struct.unpack(">i", self.take(4))[0]
        if tag == b"d":
            return struct.unpack(">f", self.take(4))[0]
        raise ValueError("unsupported preset-record value tag %r" % tag)

    def mapping(self, opened=False):
        if not opened and self.take(1) != b"{":
            raise ValueError("preset record does not start with a dictionary")
        result = {}
        while True:
            if self.offset >= len(self.data):
                raise ValueError("unterminated preset record")
            if self.data[self.offset:self.offset + 1] == b"}":
                self.offset += 1
                return result
            key = self.name()
            if key in result:
                raise ValueError("duplicate preset record key %r" % key)
            result[key] = self.value()


def decode_preset_record_prefix(data):
    """Decode the first preset archive and return ``(record, byte_count)``.

    Firmware factory records live inside a larger image, so callers need the
    consumed length without treating the following firmware bytes as part of
    the record.  Complete-record callers should use :func:`decode_preset_record`.
    """
    reader = _Reader(data)
    result = reader.mapping()
    return result, reader.offset


def decode_preset_record(data):
    """Decode one complete recovered preset archive into an ordered ``dict``."""
    result, consumed = decode_preset_record_prefix(data)
    if consumed != len(data):
        raise ValueError("trailing bytes after preset record")
    return result
