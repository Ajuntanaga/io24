# Native version-2 component states: what is decoded so far

Source: the four records embedded in firmware 1.28 at `0x69230`, `0x69670`,
`0x69AB0`, `0x69EB4` (`~/.cache/io24/re/io24_fw.bin`), read through
`io24_native_stat.decode_native_stat_record` and its `opt ` chunk group.
Offline only; no device was touched.

## The structural finding: these records are per sample rate

Every filter-bearing component stores its coefficients **four times**, once for
44100, 48000, 88200 and 96000 Hz, each labelled with the rate as a float. That
is how one stored preset stays correct at any clock, and it means a writer must
emit all four sets, not one. `gate` and `lim ` carry a single set.

## `filt` (120 bytes) — layout and UC arithmetic route exact

    [u32 count=4]
    4 x ( [u32 0 (the count word takes this slot in the first unit)]
          [5 x f32 biquad coefficients]
          [u8 flag = 1]
          [f32 rate] )
    [u32 0]                                   4 + 4*29 + 4 = 120

Unit stride is 29 bytes; rate labels land at offsets 25, 54, 83, 112. The
coefficient order matches the wire form this Host already builds, b0 == b2 for
the high-pass. Slot 2's units are `1, 0, 0, 0, 0` — an identity filter, i.e. a
bypassed HPF.

Slot 0, 44.1 kHz: `0.996304, 1.9926, -1.99261, -0.992622, 0.996304`
Slot 0, 48 kHz:   `0.997987, 1.99597, -1.99597, -0.995978, 0.997987`

Firmware slot 0 corresponds semantically to `Piano Accomany.scene` Channel 2,
including its 40 Hz HPF, but its four coefficient sets are not one canonical
UC 4.7.2 recompute. Static DLL recovery binds `FilterComponent` to designer
selector 3 and its binary64 bilinear high-pass branch. The imported UCRT
small-angle `tan` polynomial agrees with Python/glibc for these inputs. By
contrast, 17 of the firmware fixture's 20 words match an all-binary32 route,
while its 96 kHz set matches the binary64 UC route. The embedded values are
therefore preserved historical results, not an oracle for changing the
source-bound UC builder.

`ComponentState.filter_coefficients()` exposes all four stored biquads, and
`set_filter_coefficients()` replaces them atomically while retaining every
non-coefficient byte from the complete native base. Partial clock sets and
non-finite or non-binary32 values are refused before mutation.

## `lim ` (28 bytes) — exact

    [u32 24][u32 on][f32 inverse threshold][f32 release coefficient]
    [f32 0][f32 1.33352][f32 0]

`1.1885` in slots 0 and 1 is bit-for-bit `io24_dsp.limiter_inv_threshold(-1.5)`
(1.1885021924972534); slots 2 and 3 hold `1.0`, i.e. 0 dB. The release
coefficient `0.999644` has the form `exp(-2*pi/(t*fs))` the Host already uses.

## `gate` (128 bytes) — exact two-state live-payload mapping

    [u32 0][u32 payload_bytes=120]
    2 x ( [5 x f32 key-filter biquad]
          [f32 range linear][f32 inverse threshold]
          [f32 attack s][f32 release s]
          [f32 attack coefficient][f32 release coefficient]
          [u32 hold][u32 on][u32 expander][u32 keylisten] )

Each 60-byte state is exactly the payload after the 12-byte header of a live
`gate` blob. Prefixing the live tag, size `0x48`, and state index reconstructs
the complete wire blob byte-for-byte. Firmware slot 0 state 0 exactly matches
`io24_dsp.gate_blob()` built from `Piano Accomany.scene` Channel 2 at 44.1 kHz:
-47.5 dB threshold, -60 dB range, 25 ms attack, 700 ms release, 730 Hz key
filter, expander on. State 1 in the observed record is the power-on form.

## `comp` (228 bytes) — exact rate filters and two live-payload states

Rate labels at the same 25/54/83/112, so the first 116 bytes are four 29-byte
units of the same shape as `filt` — the compressor's side-chain filter. They
are followed by `[u32 0][u32 payload_bytes=104]` and two 52-byte states. Each
state is exactly the payload after the header of a live `cpxt` blob:

    [5 x f32 key-filter biquad]
    [f32 attack][f32 release][f32 slope][f32 knee]
    [f32 threshold dB][f32 makeup linear][u32 on][u32 keylisten]

Firmware slot 0 state 0 and all four stored rate biquads exactly match
`io24_dsp.cpxt_fet()` built from `Piano Accomany.scene` Channel 2. Prefixing
the live `cpxt` tag, size `0x40`, and state index reconstructs the complete
wire blob byte-for-byte. State 1 in the observed record remains power-on.

## `eq  ` (432 bytes) — complete coefficient layout; no parameter region

Eight rate labels: four at stride 69 (units of 15 floats, three biquads each)
and four at stride 37 (units of 7 floats). An unused band is stored as
`1, 0, 0, 0, 0`.

That shape is now explained rather than just observed. UC's EQ recompute calls
four band designers that each write an adjacent piece of one buffer — the low
band **seven** floats, the other three **five** each, 22 floats with no gap and
no overlap. A stored unit holds 22 floats per rate. The record is a copy of
that buffer, so nothing converts coefficients on the way to the device, and the
wide unit exists because one band is third order. Slot 2 proves the wide form
is really used: its trailing two floats are non-zero. `VINTAGE-EQ-TABLE.md` in
this run carries the measurements.

The band order in the main unit is low-mid, hi-mid, high, with the low band in
the wide unit — every firmware default then reads back in ascending frequency.

There is no hidden semantic-parameter region in these 432 bytes. The accounting
is exact: 22 floats x 4 rates = 352 coefficient bytes, eight rate labels = 32,
eight one-byte flags = 8, and ten structural u32 words = 40; total 432. The
native body stores coefficients, not gains, Q values, or switch indexes.

The retained UC 4.7.2 DLL now supplies all four exact Vintage designers through
`re/uc472_vintage_eq.py`. A complete tagged Vintage EQ can therefore be
designed for all four clocks and overlaid on a validated native base while all
non-EQ bytes remain unchanged. This is an offline executable analysis path; it
is not yet a self-contained dependency of the running Host.

## What this means for the writer

`gate`, `comp`, and `lim ` now have exact payload seams, and the EQ codec
preserves all 22 coefficients at every clock. `build_native_stat_record()` in
`re/uc472_vintage_eq.py` produces a complete validated native record by
replacing only the EQ coefficients in a complete base.

That is deliberately not called a general semantic preset writer yet. The UC
HPF route and all three Standard paths are now source-bound: peaking selector
6, low-shelf selector 8, and high-shelf selector 9. `design_standard_eq()`
maps scene bands 2/3/4/1 to native `low-mid`/`hi-mid`/`high`/`wide` at all four
rates; Standard's two extra `wide` coefficients are zero. The record builder
overlays that complete EQ leaf without changing another component. Passive EQ
and a self-contained running-Host Vintage dependency remain open. No device
operation was performed.
