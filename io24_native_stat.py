#!/usr/bin/env python3
"""Pure parser and encoder for firmware 1.28 native ``Stat`` records.

The io24 firmware keeps its four device-slot defaults in a version-2 chunk
container.  This is distinct from Universal Control's tagged ``{...}`` preset
archive used by the adjacent factory/library collection.  This module is
local-only: it has no transport, USB, audio, or device access.
"""

from dataclasses import dataclass
import math
import struct


NATIVE_STAT_VERSION = 2
CHANNEL_STRIP_KEY = b"opt "
VOICEFX_COMPONENT_ID = 201
VOICEFX_COMPONENT_KEY = VOICEFX_COMPONENT_ID.to_bytes(4, "big")
VOICEFX_PARENT_VERSION = 6
VOICEFX_MODEL0 = 0
CHANNEL_COMPONENT_KEYS = (b"filt", b"gate", b"comp", b"eq  ", b"lim ")

# All four firmware 1.28 defaults use these fixed stock component-state sizes.
# They are validation facts, not claimed storage maxima.
CHANNEL_COMPONENT_SIZES = {
    b"filt": 120,
    b"gate": 128,
    b"comp": 228,
    b"eq  ": 432,
    b"lim ": 28,
}


class NativeStatFormatError(ValueError):
    """A byte string is not a structurally eligible native ``Stat`` record."""


@dataclass(frozen=True)
class NativeChunk:
    """One four-byte-keyed payload in a native chunk group."""

    key: bytes
    payload: bytes


@dataclass(frozen=True)
class NativeStatRecord:
    """Decoded top-level native device-slot record."""

    version: int
    chunks: tuple[NativeChunk, ...]


def _as_bytes(name, value):
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise TypeError("%s must be bytes-like" % name)
    return bytes(value)


def _checked_chunks(chunks):
    checked = []
    for chunk in chunks:
        if isinstance(chunk, NativeChunk):
            key, payload = chunk.key, chunk.payload
        else:
            try:
                key, payload = chunk
            except (TypeError, ValueError) as error:
                raise TypeError(
                    "each native chunk must be NativeChunk or a key/payload pair"
                ) from error
        key = _as_bytes("native chunk key", key)
        payload = _as_bytes("native chunk payload", payload)
        if len(key) != 4:
            raise NativeStatFormatError("native chunk keys must be four bytes")
        checked.append(NativeChunk(key, payload))
    return tuple(checked)


def encode_chunk_group(chunks):
    """Encode one directory followed by its ordered payloads."""
    chunks = _checked_chunks(chunks)
    body_size = sum(12 + len(chunk.payload) for chunk in chunks)
    directory = b"".join(
        chunk.key + struct.pack("<Q", len(chunk.payload)) for chunk in chunks
    )
    return (struct.pack("<Q", body_size) + directory +
            b"".join(chunk.payload for chunk in chunks))


def decode_chunk_group(data):
    """Decode one exact native chunk group without interpreting leaf payloads.

    The format has no explicit directory-entry count.  The unique count is the
    one for which ``directory bytes + declared payload sizes`` consumes the
    group's declared extent exactly.
    """
    data = _as_bytes("native chunk group", data)
    if len(data) < 8:
        raise NativeStatFormatError("native chunk group is shorter than its header")
    declared_size, = struct.unpack_from("<Q", data)
    if declared_size != len(data) - 8:
        raise NativeStatFormatError(
            "native chunk group declares %d bytes, has %d" %
            (declared_size, len(data) - 8))

    candidates = []
    maximum = min(64, (len(data) - 8) // 12)
    for count in range(maximum + 1):
        directory_end = 8 + 12 * count
        sizes = [
            struct.unpack_from("<Q", data, 8 + 12 * index + 4)[0]
            for index in range(count)
        ]
        if directory_end + sum(sizes) == len(data):
            candidates.append((count, sizes))
    if len(candidates) != 1:
        raise NativeStatFormatError(
            "native chunk directory has %d possible entry counts" %
            len(candidates))

    count, sizes = candidates[0]
    payload_offset = 8 + 12 * count
    chunks = []
    for index, size in enumerate(sizes):
        key_offset = 8 + 12 * index
        key = data[key_offset:key_offset + 4]
        payload_end = payload_offset + size
        chunks.append(NativeChunk(key, data[payload_offset:payload_end]))
        payload_offset = payload_end
    return tuple(chunks)


def encode_native_stat_record(record):
    """Re-encode a decoded native record byte-for-byte."""
    if not isinstance(record, NativeStatRecord):
        raise TypeError("record must be a NativeStatRecord")
    if record.version != NATIVE_STAT_VERSION:
        raise NativeStatFormatError(
            "native Stat version must be %d" % NATIVE_STAT_VERSION)
    return struct.pack("<I", record.version) + encode_chunk_group(record.chunks)


def decode_native_stat_record(data):
    """Decode the version and top-level chunk directory of one record."""
    data = _as_bytes("native Stat record", data)
    if len(data) < 12:
        raise NativeStatFormatError("native Stat record is shorter than its header")
    version, = struct.unpack_from("<I", data)
    if version != NATIVE_STAT_VERSION:
        raise NativeStatFormatError(
            "native Stat record starts with version %d, expected %d" %
            (version, NATIVE_STAT_VERSION))
    return NativeStatRecord(version, decode_chunk_group(data[4:]))


def _unique_by_key(name, chunks):
    result = {}
    for chunk in chunks:
        if chunk.key in result:
            raise NativeStatFormatError(
                "%s repeats chunk key %s" % (name, chunk.key.hex()))
        result[chunk.key] = chunk.payload
    return result


def validate_native_stat_record(data, slot_index=None):
    """Return structurally valid firmware startup/default chunk bytes.

    Validation intentionally stops at the stock component-state boundary.  It
    proves the native version, chunk directories, component identities, and
    stock leaf sizes; it does not claim that the leaf values are safe, audible,
    accepted by a device, or nonvolatile.  ``slot_index`` checks only the
    four-slot index range.  The contents of four embedded defaults are
    observations, not a rule forbidding Voice FX in another channel's saved
    record.
    """
    if slot_index is not None:
        if (isinstance(slot_index, bool) or not isinstance(slot_index, int) or
                not 0 <= slot_index <= 3):
            raise ValueError("device slot index must be in the range 0..3")
    data = _as_bytes("native Stat record", data)
    record = decode_native_stat_record(data)
    top = _unique_by_key("native Stat top level", record.chunks)
    allowed = {CHANNEL_STRIP_KEY, VOICEFX_COMPONENT_KEY}
    unknown = sorted(set(top).difference(allowed))
    if unknown:
        raise NativeStatFormatError(
            "native Stat has unsupported top-level chunks: %s" %
            ", ".join(key.hex() for key in unknown))
    if CHANNEL_STRIP_KEY not in top:
        raise NativeStatFormatError("native Stat lacks the channel-strip chunk")

    channel_chunks = decode_chunk_group(top[CHANNEL_STRIP_KEY])
    channel = _unique_by_key("native channel strip", channel_chunks)
    missing = [key for key in CHANNEL_COMPONENT_KEYS if key not in channel]
    extra = sorted(set(channel).difference(CHANNEL_COMPONENT_KEYS))
    if missing or extra:
        details = []
        if missing:
            details.append("missing %s" % ",".join(
                key.decode("ascii") for key in missing))
        if extra:
            details.append("unsupported %s" % ",".join(
                key.hex() for key in extra))
        raise NativeStatFormatError(
            "native channel-strip chunks differ: %s" % "; ".join(details))
    for key, expected_size in CHANNEL_COMPONENT_SIZES.items():
        if len(channel[key]) != expected_size:
            raise NativeStatFormatError(
                "native %s chunk has %d bytes, expected %d" %
                (key.decode("ascii"), len(channel[key]), expected_size))

    if VOICEFX_COMPONENT_KEY in top:
        voicefx = top[VOICEFX_COMPONENT_KEY]
        if len(voicefx) < 16:
            raise NativeStatFormatError("native Voice FX chunk is truncated")
        # The first two words are the parent-state version and selected model.
        parent_version, selected_model = struct.unpack_from("<II", voicefx)
        if parent_version != VOICEFX_PARENT_VERSION:
            raise NativeStatFormatError(
                "native Voice FX parent version is %d, expected %d" %
                (parent_version, VOICEFX_PARENT_VERSION))
        if not 0 <= selected_model <= 5:
            raise NativeStatFormatError(
                "native Voice FX model %d is outside 0..5" % selected_model)
        model_chunks = _unique_by_key(
            "native Voice FX model", decode_chunk_group(voicefx[8:]))
        selected_key = selected_model.to_bytes(4, "big")
        if selected_key not in model_chunks:
            raise NativeStatFormatError(
                "native Voice FX selected model %d has no state chunk" %
                selected_model)
        if len(model_chunks) != 1:
            raise NativeStatFormatError(
                "native Voice FX must contain only its selected model state")
        model_state = model_chunks[selected_key]
        if len(model_state) < 4:
            raise NativeStatFormatError(
                "native Voice FX model state lacks its byte-count prefix")
        state_bytes, = struct.unpack_from("<I", model_state)
        if state_bytes != len(model_state) - 4:
            raise NativeStatFormatError(
                "native Voice FX model state declares %d bytes, has %d" %
                (state_bytes, len(model_state) - 4))

        if selected_model == VOICEFX_MODEL0:
            if state_bytes != 20:
                raise NativeStatFormatError(
                    "native Voice FX model 0 state must contain 20 bytes")
            enabled, lows, width, lows_mirror, mix = struct.unpack_from(
                "<Iffff", model_state, 4)
            if enabled not in (0, 1):
                raise NativeStatFormatError(
                    "native Voice FX model 0 enable is not boolean")
            if not all(math.isfinite(value) and 0.0 <= value <= 1.0
                       for value in (lows, width, lows_mirror, mix)):
                raise NativeStatFormatError(
                    "native Voice FX model 0 controls are outside 0..1")
            if struct.pack("<f", lows) != struct.pack("<f", lows_mirror):
                raise NativeStatFormatError(
                    "native Voice FX model 0 lows mirror differs")

    # Re-encoding at both levels makes the no-hidden-prefix claim executable.
    if encode_native_stat_record(record) != data:
        raise NativeStatFormatError("native Stat record does not round-trip")
    return data


def _unit_float(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("%s must be a real number" % name)
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("%s must be finite and in the range 0..1" % name)
    # Canonicalize now so the mirrored value is bit-identical on the wire.
    return struct.unpack("<f", struct.pack("<f", value))[0]


def encode_native_model0_state(enabled=True, lows=0.06, width=0.405,
                               mix=0.295):
    """Encode model 0's native leaf: byte count plus five stock dwords.

    Firmware serializer ``0x53680`` emits 20 bytes from ``model+0x340``.
    Those words are ``on, lows, width, lows-mirror, mix``—the same state words
    carried after the 12-byte header in the source-bound ``godv`` live-control
    message.  This function emits no transport framing and performs no I/O.
    """
    if not isinstance(enabled, bool):
        raise TypeError("enabled must be bool")
    lows = _unit_float("lows", lows)
    width = _unit_float("width", width)
    mix = _unit_float("mix", mix)
    return struct.pack(
        "<IIffff", 20, int(enabled), lows, width, lows, mix)


def build_native_model0_stat_record(base_record, slot_index, enabled=True,
                                    lows=0.06, width=0.405, mix=0.295):
    """Replace or add component 201 in a firmware chunk fixture.

    The complete Fat Channel state is retained byte-for-byte.  This is an
    offline firmware-structure helper, not UC's source-bound tagged host slot
    writer and not a live-write eligibility decision.
    """
    if isinstance(slot_index, bool) or not isinstance(slot_index, int) or \
            not 0 <= slot_index <= 3:
        raise ValueError("device slot index must be in the range 0..3")
    base_record = validate_native_stat_record(
        base_record, slot_index=slot_index)
    record = decode_native_stat_record(base_record)
    voicefx = (
        struct.pack("<II", VOICEFX_PARENT_VERSION, VOICEFX_MODEL0) +
        encode_chunk_group([(
            VOICEFX_MODEL0.to_bytes(4, "big"),
            encode_native_model0_state(enabled, lows, width, mix),
        )])
    )
    chunks = tuple(
        NativeChunk(chunk.key, voicefx)
        if chunk.key == VOICEFX_COMPONENT_KEY else chunk
        for chunk in record.chunks
    )
    if not any(chunk.key == VOICEFX_COMPONENT_KEY for chunk in record.chunks):
        chunks += (NativeChunk(VOICEFX_COMPONENT_KEY, voicefx),)
    result = encode_native_stat_record(NativeStatRecord(record.version, chunks))
    return validate_native_stat_record(result, slot_index=slot_index)


def native_stat_summary(data, slot_index=None):
    """Return a compact JSON-serializable structural summary."""
    data = validate_native_stat_record(data, slot_index=slot_index)
    record = decode_native_stat_record(data)
    top = _unique_by_key("native Stat top level", record.chunks)
    channel = decode_chunk_group(top[CHANNEL_STRIP_KEY])
    result = {
        "version": record.version,
        "bytes": len(data),
        "top_chunks": [
            {"key_hex": chunk.key.hex(), "bytes": len(chunk.payload)}
            for chunk in record.chunks
        ],
        "channel_chunks": [
            {"key": chunk.key.decode("ascii"), "bytes": len(chunk.payload)}
            for chunk in channel
        ],
        "voicefx": None,
    }
    if VOICEFX_COMPONENT_KEY in top:
        voicefx = top[VOICEFX_COMPONENT_KEY]
        parent_version, selected_model = struct.unpack_from("<II", voicefx)
        result["voicefx"] = {
            "component_id": VOICEFX_COMPONENT_ID,
            "parent_version": parent_version,
            "selected_model": selected_model,
            "bytes": len(voicefx),
        }
        model = decode_chunk_group(voicefx[8:])[0]
        state_bytes, = struct.unpack_from("<I", model.payload)
        result["voicefx"].update({
            "model_key_hex": model.key.hex(),
            "state_bytes": state_bytes,
            "state_hex": model.payload[4:].hex(),
        })
    return result
