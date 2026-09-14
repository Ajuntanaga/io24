"""Field-level access to the channel-strip components of a native slot record.

`io24_native_stat` reaches the `opt ` chunk group and hands back each
component's state as opaque bytes. This module knows what is inside them, so
the Host can write a preset the firmware will actually load.

Everything here was decoded from the four records embedded in firmware 1.28
(`0x69230`, `0x69670`, `0x69AB0`, `0x69EB4`); `DECODE-NOTES.md` in the
2026-09-14 native-slot-builder run carries the evidence.

The structural fact that shapes all of it: a filter's coefficients are stored
**once per sample rate**, for 44100, 48000, 88200 and 96000 Hz, each labelled
with its rate. One stored preset is therefore correct at any clock, and a
writer has to produce all four sets.

    filt   [u32][5 f32 biquad][u8 flag][f32 rate] x 4, then [u32]
    eq     the same shape with three bands per unit, then [u32], then four
           more units carrying the remaining band with two spare floats
    comp   four side-chain filter units, then the dynamics parameters:
           attack, release, slope, knee, threshold dB, makeup - the same six
           values in the same order as the live `cpxt` blob
    gate   one set: key biquad, range and threshold as linear gains, key Hz,
           Q, and the attack/release coefficients
    lim    [u32 24][u32 on][f32 inverse threshold][f32 release coefficient]...

Every component is held as its original bytes plus the offsets of the fields
that are understood. Unknown bytes are never rebuilt, only carried, so
encoding what was decoded returns the original byte-for-byte and an edit
touches nothing it does not name.
"""

import struct

RATES = (44100.0, 48000.0, 88200.0, 96000.0)
BIQUAD = 5                                    # b0, -a1, b1, -a2, b2

FILT_UNIT = 29
EQ_MAIN_UNIT = 69                             # three bands
EQ_MAIN_BANDS = 3
EQ_EXTRA_UNIT = 37                            # the remaining band
EQ_EXTRA_AT = 280
EQ_EXTRA_PAD = 8                              # two spare floats
COMP_UNIT = 29
COMP_PARAMS_AT = 124                          # after the four filter units
GATE_KEY_AT = 8
GATE_PARAMS_AT = 28
LIM_AT = 8


class NativeStripError(ValueError):
    """A component state is not the shape firmware 1.28 stores."""


def _f32(data, offset):
    return struct.unpack_from("<f", data, offset)[0]


def _put_f32(data, offset, value):
    struct.pack_into("<f", data, offset, float(value))


class RateBlock:
    """One sample rate's coefficients inside a component state."""

    def __init__(self, state, offset, bands, rate_offset):
        self._state, self._offset = state, offset
        self.bands, self._rate_offset = bands, rate_offset

    @property
    def rate(self):
        return _f32(self._state.data, self._rate_offset)

    def biquad(self, band=0):
        at = self._offset + band * BIQUAD * 4
        return struct.unpack_from("<%df" % BIQUAD, self._state.data, at)

    def set_biquad(self, band, coefficients):
        coefficients = tuple(float(c) for c in coefficients)
        if len(coefficients) != BIQUAD:
            raise NativeStripError("a biquad is five coefficients")
        at = self._offset + band * BIQUAD * 4
        struct.pack_into("<%df" % BIQUAD, self._state.data, at, *coefficients)


class ComponentState:
    """One channel-strip component, editable field by field."""

    def __init__(self, key, data):
        self.key = key
        self.data = bytearray(data)
        self.blocks = []
        self._map()

    def encode(self):
        return bytes(self.data)

    def _units(self, start, stride, bands, count=4, pad=0):
        """`pad` is the spare bytes some units keep between their last
        coefficient and the flag; the extra EQ band has two spare floats."""
        for index in range(count):
            offset = start + index * stride
            rate_at = offset + 4 + bands * BIQUAD * 4 + pad + 1
            self.blocks.append(
                RateBlock(self, offset + 4, bands, rate_at))

    def _map(self):
        if self.key == b"filt":
            self._units(0, FILT_UNIT, 1)
        elif self.key == b"eq  ":
            self._units(0, EQ_MAIN_UNIT, EQ_MAIN_BANDS)
            self._units(EQ_EXTRA_AT, EQ_EXTRA_UNIT, 1, pad=EQ_EXTRA_PAD)
        elif self.key == b"comp":
            self._units(0, COMP_UNIT, 1)
        elif self.key not in (b"gate", b"lim "):
            raise NativeStripError("unknown component %r" % self.key)
        for block in self.blocks:
            if block.rate not in RATES:
                raise NativeStripError(
                    "%r: expected a sample rate at %d, found %r"
                    % (self.key, block._rate_offset, block.rate))

    # -- comp -------------------------------------------------------------
    COMP_FIELDS = ("attack", "release", "slope", "knee", "threshold_db",
                   "makeup")

    def comp_parameters(self):
        values = struct.unpack_from("<6f", self.data, COMP_PARAMS_AT + 20)
        return dict(zip(self.COMP_FIELDS, values))

    def set_comp_parameters(self, **values):
        for name, value in values.items():
            if name not in self.COMP_FIELDS:
                raise NativeStripError("unknown compressor field %r" % name)
            _put_f32(self.data,
                     COMP_PARAMS_AT + 20 + self.COMP_FIELDS.index(name) * 4,
                     value)

    def comp_biquad(self):
        return struct.unpack_from("<%df" % BIQUAD, self.data, COMP_PARAMS_AT)

    def set_comp_biquad(self, coefficients):
        struct.pack_into("<%df" % BIQUAD, self.data, COMP_PARAMS_AT,
                         *(float(c) for c in coefficients))

    # -- gate -------------------------------------------------------------
    GATE_FIELDS = ("range", "key_hz", "threshold", "q",
                   "attack_coefficient", "release_coefficient")

    def gate_parameters(self):
        values = struct.unpack_from("<6f", self.data, GATE_PARAMS_AT)
        return dict(zip(self.GATE_FIELDS, values))

    def set_gate_parameters(self, **values):
        for name, value in values.items():
            if name not in self.GATE_FIELDS:
                raise NativeStripError("unknown gate field %r" % name)
            _put_f32(self.data,
                     GATE_PARAMS_AT + self.GATE_FIELDS.index(name) * 4, value)

    def gate_key_biquad(self):
        return struct.unpack_from("<%df" % BIQUAD, self.data, GATE_KEY_AT)

    def set_gate_key_biquad(self, coefficients):
        struct.pack_into("<%df" % BIQUAD, self.data, GATE_KEY_AT,
                         *(float(c) for c in coefficients))

    # -- lim --------------------------------------------------------------
    def limiter(self):
        on, = struct.unpack_from("<I", self.data, 4)
        threshold, release = struct.unpack_from("<2f", self.data, LIM_AT)
        return {"on": bool(on), "inverse_threshold": threshold,
                "release_coefficient": release}

    def set_limiter(self, on=None, inverse_threshold=None,
                    release_coefficient=None):
        if on is not None:
            struct.pack_into("<I", self.data, 4, 1 if on else 0)
        if inverse_threshold is not None:
            _put_f32(self.data, LIM_AT, inverse_threshold)
        if release_coefficient is not None:
            _put_f32(self.data, LIM_AT + 4, release_coefficient)


def decode_components(chunks):
    """{key: ComponentState} for one record's `opt ` chunk group."""
    return {chunk.key: ComponentState(chunk.key, chunk.payload)
            for chunk in chunks}
