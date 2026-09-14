#!/usr/bin/env python3
"""Field-level contracts for the channel-strip components of a slot record.

Firmware 1.28 loads only native version-2 records, so writing a preset the
unit will actually apply means writing these component states. The layout was
decoded from the four records embedded in the firmware; the evidence is in
`runs/20260914T031459-0700-native-slot-builder/DECODE-NOTES.md`.

The strongest check here is that decoding and re-encoding every component of
every embedded record returns the original bytes exactly: the codec carries
what it does not understand instead of rebuilding it.

Nothing here opens USB, audio or a display.
"""

import math
import os
import struct
import unittest

import io24_dsp
import io24_native_stat
import io24_native_strip as strip

FIRMWARE = os.path.expanduser("~/.cache/io24/re/io24_fw.bin")
OFFSETS = (0x69230, 0x69670, 0x69AB0, 0x69EB4)
LENGTHS = (0x440, 0x440, 0x404, 0x404)


def _records():
    image = open(FIRMWARE, "rb").read()
    for offset, length in zip(OFFSETS, LENGTHS):
        record = io24_native_stat.decode_native_stat_record(
            image[offset:offset + length])
        group = [c for c in record.chunks if c.key == b"opt "][0].payload
        yield io24_native_stat.decode_chunk_group(group)


@unittest.skipUnless(os.path.exists(FIRMWARE), "firmware image not retained")
class NativeStripTests(unittest.TestCase):
    def setUp(self):
        self.records = list(_records())

    def test_every_component_round_trips_byte_for_byte(self):
        for index, chunks in enumerate(self.records):
            original = {chunk.key: bytes(chunk.payload) for chunk in chunks}
            for key, component in strip.decode_components(chunks).items():
                with self.subTest(record=index, component=key):
                    self.assertEqual(component.encode(), original[key])

    def test_the_filters_carry_one_set_per_clock(self):
        for index, chunks in enumerate(self.records):
            components = strip.decode_components(chunks)
            with self.subTest(record=index):
                self.assertEqual(
                    tuple(block.rate for block in components[b"filt"].blocks),
                    strip.RATES)
                # three bands, then the remaining band, each at four clocks
                self.assertEqual(
                    tuple(block.rate for block in components[b"eq  "].blocks),
                    strip.RATES + strip.RATES)

    def test_the_compressor_parameters_are_the_live_blob_order(self):
        # record 3 is a plain 2:1 at -30 dB: values a misread could not invent
        components = strip.decode_components(self.records[3])
        values = components[b"comp"].comp_parameters()
        self.assertAlmostEqual(values["threshold_db"], -30.0, places=4)
        self.assertAlmostEqual(values["knee"], 3.0, places=4)
        self.assertAlmostEqual(values["attack"], 0.01, places=5)
        self.assertAlmostEqual(values["release"], 0.15, places=5)
        # the stored slope is 0.49525, i.e. 1.98:1 - a 2:1 compressor as
        # the firmware rounds it, not a coincidence of misalignment
        self.assertAlmostEqual(
            1.0 / (1.0 - values["slope"]), 2.0, delta=0.05)
        self.assertAlmostEqual(
            20 * math.log10(values["makeup"]), 3.0, places=2)

    def test_the_limiter_threshold_is_the_hosts_own_formula(self):
        first = strip.decode_components(self.records[0])[b"lim "].limiter()
        self.assertTrue(first["on"])
        self.assertAlmostEqual(first["inverse_threshold"],
                               io24_dsp.limiter_inv_threshold(-1.5), places=6)
        quiet = strip.decode_components(self.records[2])[b"lim "].limiter()
        self.assertAlmostEqual(quiet["inverse_threshold"], 1.0, places=6)

    def test_the_gate_keeps_threshold_and_range_as_linear_gains(self):
        values = strip.decode_components(self.records[0])[b"gate"]
        gate = values.gate_parameters()
        self.assertAlmostEqual(20 * math.log10(gate["range"]), -60.0, places=3)
        self.assertAlmostEqual(20 * math.log10(gate["threshold"]),
                               -32.04, places=1)
        self.assertAlmostEqual(gate["key_hz"], 237.13737, places=3)
        self.assertAlmostEqual(gate["q"], 0.7, places=5)

    def test_an_edit_changes_only_the_bytes_it_names(self):
        components = strip.decode_components(self.records[0])
        component = components[b"comp"]
        before = component.encode()
        component.set_comp_parameters(threshold_db=-24.0)
        after = component.encode()
        differing = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
        field = strip.COMP_PARAMS_AT + 20 + \
            component.COMP_FIELDS.index("threshold_db") * 4
        self.assertTrue(differing)
        self.assertTrue(set(differing) <= set(range(field, field + 4)),
                        "an edit reached outside its own field: %s" % differing)
        self.assertEqual(len(before), len(after))
        self.assertAlmostEqual(
            component.comp_parameters()["threshold_db"], -24.0, places=5)

    def test_a_state_that_is_not_that_shape_is_refused(self):
        chunks = self.records[0]
        filt = [c for c in chunks if c.key == b"filt"][0]
        broken = bytearray(filt.payload)
        struct.pack_into("<f", broken, 25, 12345.0)     # not a sample rate
        with self.assertRaises(strip.NativeStripError):
            strip.ComponentState(b"filt", bytes(broken))


if __name__ == "__main__":
    unittest.main()
