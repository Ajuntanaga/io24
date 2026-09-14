#!/usr/bin/env python3
"""Hardware-free contracts for firmware-native io24 ``Stat`` records."""

import importlib.util
from pathlib import Path
import struct
import unittest

import io24
import io24_fx
from io24_native_stat import (
    CHANNEL_COMPONENT_SIZES,
    NativeChunk,
    NativeStatFormatError,
    NativeStatRecord,
    build_native_model0_stat_record,
    decode_chunk_group,
    decode_native_stat_record,
    encode_chunk_group,
    encode_native_model0_state,
    encode_native_stat_record,
    native_stat_summary,
    validate_native_stat_record,
)
from io24_preset_record import encode_preset_record


ROOT = Path(__file__).resolve().parents[1]
UC472_DLL = (
    ROOT / ".superpowers" / "sdd" /
    "2026-08-28-cp34-preset-effect-control" / "runs" /
    "20260906T001130-0700-uc472-official-reacquisition" / "extracted" /
    "hwaccess" / "dspusbdevice.dll"
)


def _native_record(include_voicefx=True):
    channel = encode_chunk_group([
        (key, bytes([index + 1]) * size)
        for index, (key, size) in enumerate(CHANNEL_COMPONENT_SIZES.items())
    ])
    chunks = [NativeChunk(b"opt ", channel)]
    if include_voicefx:
        voicefx = (
            struct.pack("<II", 6, 5) +
            encode_chunk_group([(
                b"\x00\x00\x00\x05",
                struct.pack("<I", 16) + bytes(range(16)),
            )])
        )
        chunks.append(NativeChunk(b"\x00\x00\x00\xc9", voicefx))
    return encode_native_stat_record(NativeStatRecord(2, tuple(chunks)))


def _tagged_record():
    return {
        "preset_name": "Reverb",
        "opt": {"swapcompeq": 0},
        "filter": {"hpf": 40.0},
        "gate": {"on": 0},
        "limit": {"limiteron": 0},
        "eq": {"eqallon": 0},
        "comp": {"on": 0},
        "voicefx": {"on": 1, "mix": 0.295},
    }


class _WireFake(io24.Io24):
    def __init__(self):
        self.payloads = []

    def _exec(self, payload, wait=1.5):
        self.payloads.append(bytes(payload))
        return struct.pack("<I", io24.RPLY)


class NativeStatTests(unittest.TestCase):
    def test_native_container_round_trips_without_hidden_prefix(self):
        raw = _native_record()

        self.assertEqual(validate_native_stat_record(raw), raw)
        self.assertEqual(encode_native_stat_record(
            decode_native_stat_record(raw)), raw)
        summary = native_stat_summary(raw)
        self.assertEqual(summary["version"], 2)
        self.assertEqual(
            [chunk["key"] for chunk in summary["channel_chunks"]],
            ["filt", "gate", "comp", "eq  ", "lim "],
        )
        self.assertEqual(summary["voicefx"]["component_id"], 201)
        self.assertEqual(summary["voicefx"]["selected_model"], 5)

    def test_embedded_default_shapes_do_not_define_slot_ownership(self):
        with_voicefx = _native_record(include_voicefx=True)
        without_voicefx = _native_record(include_voicefx=False)

        for slot in range(4):
            self.assertEqual(
                validate_native_stat_record(with_voicefx, slot_index=slot),
                with_voicefx,
            )
            self.assertEqual(
                validate_native_stat_record(without_voicefx, slot_index=slot),
                without_voicefx,
            )

    def test_model0_native_state_matches_the_mapped_godv_state_words(self):
        native = encode_native_model0_state(
            True, lows=0.06, width=0.405, mix=0.295)
        godv = io24_fx.fx_transformer_blobs(
            True, lows=0.06, width=0.405, mix=0.295)[-1]

        self.assertEqual(struct.unpack_from("<I", native)[0], 20)
        self.assertEqual(native[4:], godv[12:])

    def test_model0_builder_changes_only_the_voicefx_component(self):
        base = _native_record(include_voicefx=True)
        before = {chunk.key: chunk.payload
                  for chunk in decode_native_stat_record(base).chunks}

        result = build_native_model0_stat_record(
            base, 1, enabled=True, lows=0.06, width=0.405, mix=0.295)

        after = {chunk.key: chunk.payload
                 for chunk in decode_native_stat_record(result).chunks}
        self.assertEqual(after[b"opt "], before[b"opt "])
        voicefx = after[b"\x00\x00\x00\xc9"]
        self.assertEqual(struct.unpack_from("<II", voicefx), (6, 0))
        model = decode_chunk_group(voicefx[8:])
        self.assertEqual(model[0].key, b"\x00\x00\x00\x00")
        self.assertEqual(model[0].payload,
                         encode_native_model0_state(
                             True, lows=0.06, width=0.405, mix=0.295))
        self.assertEqual(validate_native_stat_record(result, slot_index=1), result)

        channel2_base = _native_record(include_voicefx=False)
        channel2_result = build_native_model0_stat_record(channel2_base, 3)
        self.assertIsNotNone(native_stat_summary(
            channel2_result, slot_index=3)["voicefx"])

    def test_chunk_group_round_trips_binary_and_numeric_keys(self):
        raw = encode_chunk_group([
            (b"opt ", b"abc"),
            (b"\x00\x00\x00\xc9", b"\x00\xff"),
        ])

        self.assertEqual(
            decode_chunk_group(raw),
            (NativeChunk(b"opt ", b"abc"),
             NativeChunk(b"\x00\x00\x00\xc9", b"\x00\xff")),
        )
        self.assertEqual(encode_chunk_group(decode_chunk_group(raw)), raw)

    def test_tagged_library_archive_is_not_native_stat(self):
        archive = encode_preset_record({"preset_name": "Slap Echo"})

        with self.assertRaisesRegex(NativeStatFormatError, "version"):
            validate_native_stat_record(archive)

    def test_component_size_mutation_is_rejected(self):
        channel = encode_chunk_group([
            (key, bytes(size - (key == b"gate")))
            for key, size in CHANNEL_COMPONENT_SIZES.items()
        ])
        raw = encode_native_stat_record(
            NativeStatRecord(2, (NativeChunk(b"opt ", channel),)))

        with self.assertRaisesRegex(NativeStatFormatError, "gate.*expected"):
            validate_native_stat_record(raw)

    def test_native_slot_envelope_contains_the_exact_native_record(self):
        raw = _native_record(include_voicefx=False)

        frames = io24._build_native_slot_memp_frames(3, raw)

        self.assertEqual(len(frames), 1)
        frame = frames[0]
        self.assertEqual(struct.unpack_from("<IIIIII", frame),
                         (io24.SETP, io24.APPL, 0, io24.MEMP,
                          io24.STATE_BLOB_SIZE, io24.STAT))
        self.assertEqual(struct.unpack_from("<I", frame, 24)[0], 3)
        size = struct.unpack_from("<H", frame, 35)[0]
        self.assertEqual(frame[41:41 + size], raw)

    def test_live_api_rejects_tagged_archives_before_transport(self):
        fake = _WireFake()
        archive = encode_preset_record({"preset_name": "Slap Echo"})

        with self.assertRaises(NativeStatFormatError):
            fake.save_device_slot(3, archive)
        with self.assertRaises(TypeError):
            fake.save_device_slot(3, {"preset_name": "Slap Echo"})

        self.assertEqual(fake.payloads, [])

    def test_live_api_sends_complete_native_record(self):
        fake = _WireFake()
        record = _native_record(include_voicefx=False)

        report = fake.save_device_slot(3, record)

        self.assertEqual(report, {
            "slot": 3,
            "fragments_sent": 1,
            "replies_received": 1,
        })
        self.assertEqual(len(fake.payloads), 1)
        frame = fake.payloads[0]
        size = struct.unpack_from("<H", frame, 35)[0]
        self.assertEqual(frame[41:41 + size], record)

    def test_tagged_uc_slot_api_is_retired_before_transport(self):
        fake = _WireFake()

        with self.assertRaisesRegex(
                io24.HostActionError, "tagged UC Stat archives"):
            fake.save_uc_device_slot(3, _tagged_record())

        self.assertEqual(fake.payloads, [])

    def test_native_model0_live_api_is_retired_before_transport(self):
        fake = _WireFake()
        base = _native_record(include_voicefx=True)

        with self.assertRaisesRegex(
                io24.HostActionError, "unreadable current slot"):
            fake.save_native_model0_voicefx_slot(3, base)

        self.assertEqual(fake.payloads, [])


@unittest.skipUnless(UC472_DLL.is_file(), "retained exact UC 4.7.2 DLL unavailable")
class NativeStatFirmwareAttributionTests(unittest.TestCase):
    def test_exact_firmware_separates_four_native_slots_from_library(self):
        path = ROOT / "re" / "cp34_native_stat_layout.py"
        spec = importlib.util.spec_from_file_location(
            "cp34_native_stat_layout_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        report = module.analyze(UC472_DLL.read_bytes())

        self.assertEqual(
            report["status"],
            "FIRMWARE128_STAT_DEFAULTS_NATIVE_V2_SEPARATE_FROM_TAGGED_LIBRARY",
        )
        self.assertEqual(report["native_stat"]["lengths"],
                         [0x440, 0x440, 0x404, 0x404])
        self.assertEqual(report["native_stat"]["end_raw_offset"], "0x6a2b8")
        self.assertEqual(report["factory_library"]["first_raw_offset"],
                         "0x6a2b8")
        self.assertEqual(report["factory_library"]["first_prefix_hex"],
                         "7b690b70")
        self.assertEqual(
            report["correction"]["old_shared_tagged_record_model"],
            "RETRACTED",
        )
        records = report["native_stat"]["records"]
        self.assertEqual([record["version"] for record in records], [2] * 4)
        self.assertEqual([record["voicefx"] is not None for record in records],
                         [True, True, False, False])
        bridge = report["voicefx_native_bridge"]
        self.assertEqual(bridge["voicefx_storage_slot_indexes"], [0, 1])
        self.assertEqual(
            bridge["channel_strip_only_slot_indexes"], [2, 3])
        self.assertTrue(bridge["storage_owner_does_not_fix_runtime_input"])
        self.assertTrue(bridge["model5_matches_mapped_delay_state"])
        self.assertEqual(bridge["model0_serializer_raw_offset"], "0x53680")
        self.assertEqual(bridge["model0_state_bytes"], 20)

        candidate_report, artifacts = module.build_model0_candidates(
            UC472_DLL.read_bytes())
        candidates = candidate_report["model0_private_reverb_candidates"]
        self.assertEqual(candidates["physical_outcome"], "UNOBSERVED")
        self.assertEqual(
            candidates["restoration_basis"],
            "EXACT_FIRMWARE_DEFAULT_NOT_CURRENT_DEVICE_CONTENT",
        )
        self.assertEqual(len(candidates["records"]), 2)
        for slot_index in (0, 1):
            base = artifacts["slot%d-firmware-default.stat" % slot_index]
            candidate = artifacts[
                "slot%d-model0-private-reverb.stat" % slot_index]
            before = {
                chunk.key: chunk.payload
                for chunk in decode_native_stat_record(base).chunks
            }
            after = {
                chunk.key: chunk.payload
                for chunk in decode_native_stat_record(candidate).chunks
            }
            self.assertEqual(after[b"opt "], before[b"opt "])
            self.assertEqual(
                native_stat_summary(candidate, slot_index=slot_index)[
                    "voicefx"
                ]["selected_model"],
                0,
            )


if __name__ == "__main__":
    unittest.main()
