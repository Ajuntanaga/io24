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
    eq     the same shape with three five-float bands per unit, then [u32],
           then four more units carrying one seven-float third-order section
    comp   four side-chain filter units, then two exact live `cpxt` payloads
    gate   [u32 120], then two exact live `gate` payloads
    lim    [u32 24][u32 on][f32 inverse threshold][f32 release coefficient]...

Every component is held as its original bytes plus the offsets of the fields
that are understood. Unknown bytes are never rebuilt, only carried, so
encoding what was decoded returns the original byte-for-byte and an edit
touches nothing it does not name.
"""

import math
import struct

RATES = (44100.0, 48000.0, 88200.0, 96000.0)
BIQUAD = 5                                    # b0, -a1, b1, -a2, b2

FILT_UNIT = 29
EQ_MAIN_UNIT = 69                             # three bands
EQ_MAIN_BANDS = 3
EQ_EXTRA_UNIT = 37                            # the remaining band
EQ_EXTRA_AT = 280
EQ_EXTRA_PAD = 8                              # part of the seven-float section
EQ_BAND_ORDER = ("low-mid", "hi-mid", "high", "wide")
STANDARD_EQ_CLASS_ID = "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}"
COMP_UNIT = 29
COMP_STATE_AT = 124                           # after the four filter units
COMP_STATE_SIZE = 52                          # live cpxt blob minus header
COMP_PARAMS_AT = COMP_STATE_AT                # compatibility name for state 0
GATE_STATE_AT = 8                             # after size + state-count words
GATE_STATE_SIZE = 60                          # live gate blob minus header
GATE_KEY_AT = 8
GATE_PARAMS_AT = 28
LIM_AT = 8

# The live protocol's integer tags are byte-reversed on the little-endian wire.
TAG_CPXT = 0x63707874                         # wire bytes: b"txpc"
TAG_GATE = 0x67617465                         # wire bytes: b"etag"


class NativeStripError(ValueError):
    """A component state is not the shape firmware 1.28 stores."""


def _f32(data, offset):
    return struct.unpack_from("<f", data, offset)[0]


def _put_f32(data, offset, value):
    struct.pack_into("<f", data, offset, float(value))


def _state_index(index):
    if isinstance(index, bool) or not isinstance(index, int) or index not in (0, 1):
        raise NativeStripError("state index must be 0 or 1")
    return index


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
        """Map repeated coefficient units, including any extra section width.

        ``pad`` is historical naming: for the EQ wide unit those eight bytes
        are two real coefficients extending a five-float biquad to third order.
        """
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

    # -- filt -------------------------------------------------------------
    def _filter_blocks(self):
        if self.key != b"filt":
            raise NativeStripError(
                "filter coefficients require a 'filt' component")
        blocks = {block.rate: block for block in self.blocks}
        if tuple(blocks) != RATES:
            raise NativeStripError("filter coefficient clocks are incomplete")
        return blocks

    def filter_coefficients(self):
        """Return the stored HPF biquad for each supported sample rate."""
        blocks = self._filter_blocks()
        return {
            rate: blocks[rate].biquad()
            for rate in RATES
        }

    def set_filter_coefficients(self, coefficients_by_rate):
        """Replace all four stored HPF biquads atomically.

        Count words, flags, sample-rate labels, and trailing bytes are retained
        from the complete native base. A partial clock set is refused because
        it would make recall depend on the device's current sample rate.
        """
        blocks = self._filter_blocks()
        if not isinstance(coefficients_by_rate, dict) or \
                set(coefficients_by_rate) != set(RATES):
            raise NativeStripError(
                "filter coefficients must contain 44100, 48000, 88200 and "
                "96000 Hz")
        checked = {}
        for rate in RATES:
            try:
                values = tuple(float(value)
                               for value in coefficients_by_rate[rate])
            except (TypeError, ValueError, OverflowError):
                raise NativeStripError(
                    "filter coefficients at %g Hz must be finite numbers" %
                    rate)
            if len(values) != BIQUAD or not all(
                    math.isfinite(value) for value in values):
                raise NativeStripError(
                    "filter coefficients at %g Hz must contain five finite "
                    "numbers" % rate)
            try:
                packed = struct.pack("<5f", *values)
            except (OverflowError, struct.error):
                raise NativeStripError(
                    "filter coefficients at %g Hz must fit binary32" % rate)
            checked[rate] = struct.unpack("<5f", packed)

        updated = bytearray(self.data)
        for rate in RATES:
            struct.pack_into("<5f", updated, blocks[rate]._offset,
                             *checked[rate])
        self.data = updated

    # -- eq ---------------------------------------------------------------
    def _eq_blocks(self):
        if self.key != b"eq  ":
            raise NativeStripError("EQ coefficients require an 'eq  ' component")
        main = {block.rate: block for block in self.blocks[:4]}
        wide = {block.rate: block for block in self.blocks[4:]}
        if tuple(main) != RATES or tuple(wide) != RATES:
            raise NativeStripError("EQ coefficient clocks are incomplete")
        return main, wide

    def eq_coefficients(self):
        """Return the four stored EQ sections for every supported clock.

        The first three sections are five-float biquads. ``wide`` is the
        seven-float third-order section Claude recovered from UC 4.7.2; two
        real coefficients used to be mislabelled as padding.
        """
        main, wide = self._eq_blocks()
        result = {}
        for rate in RATES:
            result[rate] = {
                "low-mid": main[rate].biquad(0),
                "hi-mid": main[rate].biquad(1),
                "high": main[rate].biquad(2),
                "wide": struct.unpack_from(
                    "<7f", self.data, wide[rate]._offset),
            }
        return result

    def set_eq_coefficients(self, coefficients_by_rate):
        """Replace all 22 coefficient floats per clock, atomically.

        Structural words, flags and rate labels are retained from the complete
        native base. The caller must supply all four rates and all four bands;
        a partial update would leave a preset clock-dependent.
        """
        self._eq_blocks()
        if not isinstance(coefficients_by_rate, dict) or \
                set(coefficients_by_rate) != set(RATES):
            raise NativeStripError(
                "EQ coefficients must contain 44100, 48000, 88200 and 96000 Hz")
        widths = {"low-mid": 5, "hi-mid": 5, "high": 5, "wide": 7}
        checked = {}
        for rate in RATES:
            bands = coefficients_by_rate[rate]
            if not isinstance(bands, dict) or set(bands) != set(EQ_BAND_ORDER):
                raise NativeStripError(
                    "EQ rate %g must contain low-mid, hi-mid, high and wide" % rate)
            checked[rate] = {}
            for name in EQ_BAND_ORDER:
                try:
                    values = tuple(float(value) for value in bands[name])
                except (TypeError, ValueError, OverflowError):
                    raise NativeStripError(
                        "EQ %s coefficients at %g Hz must be finite numbers" %
                        (name, rate))
                if len(values) != widths[name] or not all(
                        math.isfinite(value) for value in values):
                    raise NativeStripError(
                        "EQ %s at %g Hz must contain %d finite coefficients" %
                        (name, rate, widths[name]))
                try:
                    packed = struct.pack("<%df" % len(values), *values)
                except (OverflowError, struct.error):
                    raise NativeStripError(
                        "EQ %s coefficients at %g Hz must fit binary32" %
                        (name, rate))
                checked[rate][name] = struct.unpack(
                    "<%df" % len(values), packed)

        main, wide = self._eq_blocks()
        updated = bytearray(self.data)
        for rate in RATES:
            for band, name in enumerate(EQ_BAND_ORDER[:3]):
                struct.pack_into("<5f", updated,
                                 main[rate]._offset + band * BIQUAD * 4,
                                 *checked[rate][name])
            struct.pack_into("<7f", updated, wide[rate]._offset,
                             *checked[rate]["wide"])
        self.data = updated

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

    def compressor_blob(self, index):
        """Return one native compressor state as its exact live cpxt blob."""
        if self.key != b"comp":
            raise NativeStripError("compressor blobs require a 'comp' component")
        index = _state_index(index)
        at = COMP_STATE_AT + index * COMP_STATE_SIZE
        return struct.pack("<III", TAG_CPXT, 0x40, index) + \
            bytes(self.data[at:at + COMP_STATE_SIZE])

    def set_compressor_blob(self, blob):
        """Replace the state selected by a complete live cpxt blob."""
        if self.key != b"comp":
            raise NativeStripError("compressor blobs require a 'comp' component")
        try:
            blob = bytes(blob)
        except (TypeError, ValueError):
            raise NativeStripError("compressor blob must be bytes-like")
        if len(blob) != 0x40:
            raise NativeStripError("compressor blob must be 64 bytes")
        tag, size, index = struct.unpack_from("<III", blob)
        if tag != TAG_CPXT or size != 0x40:
            raise NativeStripError("compressor blob header is not cpxt/64")
        index = _state_index(index)
        at = COMP_STATE_AT + index * COMP_STATE_SIZE
        updated = bytearray(self.data)
        updated[at:at + COMP_STATE_SIZE] = blob[12:]
        self.data = updated

    # -- gate -------------------------------------------------------------
    GATE_FIELDS = ("range", "inverse_threshold", "attack_s", "release_s",
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

    def gate_blob(self, index):
        """Return one native gate state as its exact live gate blob."""
        if self.key != b"gate":
            raise NativeStripError("gate blobs require a 'gate' component")
        index = _state_index(index)
        at = GATE_STATE_AT + index * GATE_STATE_SIZE
        return struct.pack("<III", TAG_GATE, 0x48, index) + \
            bytes(self.data[at:at + GATE_STATE_SIZE])

    def set_gate_blob(self, blob):
        """Replace the state selected by a complete live gate blob."""
        if self.key != b"gate":
            raise NativeStripError("gate blobs require a 'gate' component")
        try:
            blob = bytes(blob)
        except (TypeError, ValueError):
            raise NativeStripError("gate blob must be bytes-like")
        if len(blob) != 0x48:
            raise NativeStripError("gate blob must be 72 bytes")
        tag, size, index = struct.unpack_from("<III", blob)
        if tag != TAG_GATE or size != 0x48:
            raise NativeStripError("gate blob header is not gate/72")
        index = _state_index(index)
        at = GATE_STATE_AT + index * GATE_STATE_SIZE
        updated = bytearray(self.data)
        updated[at:at + GATE_STATE_SIZE] = blob[12:]
        self.data = updated

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


def design_standard_eq(eq):
    """Design one complete native four-clock Standard EQ coefficient body.

    UC's Standard bands map to the native layout as band 2 ``low-mid``, band
    3 ``hi-mid``, band 4 ``high``, and band 1 ``wide``.  Standard's wide
    section is still a five-coefficient biquad; its two third-order fields are
    zero.  Disabled bands are written as identity sections.
    """
    if not isinstance(eq, dict):
        raise NativeStripError("Standard EQ state must be a mapping")

    # Keep model and complete-field validation aligned with the tagged-scene
    # reader, but do the coefficient work here without transport or device I/O.
    import io24
    import io24_presets
    try:
        if io24_presets.eq_model(eq) != "standard":
            raise NativeStripError("native Standard EQ builder requires Standard EQ")
        scene_bands = io24_presets._standard_eq_bands(eq)
    except ValueError as error:
        if isinstance(error, NativeStripError):
            raise
        raise NativeStripError(str(error)) from error

    identity = (1.0, 0.0, 0.0, 0.0, 0.0)

    def coefficients(band, rate):
        shape = band["shape"]
        if shape == "off":
            return identity
        designer = {
            "peaking": io24.biquad_peaking,
            "lowshelf": io24.biquad_lowshelf,
            "highshelf": io24.biquad_highshelf,
        }.get(shape)
        if designer is None:
            raise NativeStripError(
                "unsupported Standard EQ band shape %r" % shape)
        return tuple(designer(
            band["freq"], band["gain"], rate, band["q"]))

    result = {}
    for rate in RATES:
        band1, band2, band3, band4 = scene_bands
        result[rate] = {
            "low-mid": coefficients(band2, rate),
            "hi-mid": coefficients(band3, rate),
            "high": coefficients(band4, rate),
            "wide": coefficients(band1, rate) + (0.0, 0.0),
        }
    return result


def build_standard_eq_component(base_component, eq):
    """Overlay a semantic Standard EQ onto a complete native ``eq  `` leaf."""
    component = ComponentState(b"eq  ", base_component)
    component.set_eq_coefficients(design_standard_eq(eq))
    return component.encode()


def decode_components(chunks):
    """{key: ComponentState} for one record's `opt ` chunk group."""
    return {chunk.key: ComponentState(chunk.key, chunk.payload)
            for chunk in chunks}
