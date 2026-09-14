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

## `filt` (120 bytes) — exact

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

## `lim ` (28 bytes) — exact

    [u32 24][u32 on][f32 inverse threshold][f32 release coefficient]
    [f32 0][f32 1.33352][f32 0]

`1.1885` in slots 0 and 1 is bit-for-bit `io24_dsp.limiter_inv_threshold(-1.5)`
(1.1885021924972534); slots 2 and 3 hold `1.0`, i.e. 0 dB. The release
coefficient `0.999644` has the form `exp(-2*pi/(t*fs))` the Host already uses.

## `gate` (128 bytes) — mostly mapped, single rate

    [u32 0][u32 120][5 x f32 key-filter biquad]
    [f32 attack s][f32 key Hz][f32 release s][f32 Q]
    [f32 attack coefficient][f32 release coefficient]
    [u32 ?][u32 on][u32 1][u32 0][u32 1] ... [u32 3000] ...

Slot 0: attack 0.001 s, key 237.137 Hz, release 0.025 s, Q 0.7. The stored
release coefficient 0.999186 is within 2e-5 of `exp(-1/(0.025*48000))`, so the
Host's own formulas reproduce it. The on flag at float index 14 reads 1, 1, 0,
0 across the four records. Threshold and range are not yet placed.

## `comp` (228 bytes) — partly mapped

Rate labels at the same 25/54/83/112, so the first 116 bytes are four 29-byte
units of the same shape as `filt` — the compressor's side-chain filter. Slot 2
carries real coefficients (`0.864306, -0.441905, 0.220952, ...`); the other
three are identity, i.e. compressor off. The remaining 108 bytes hold the
dynamics parameters and are not yet placed.

## `eq  ` (432 bytes) — partly mapped

Eight rate labels: four at stride 69 (units of 15 floats, three biquads each)
and four at stride 37 (units of 7 floats). The leading array is four bands of
five coefficients, with `1, 0, 0, 0, 0` for each unused band — which is how an
"off" band is stored.

## What this means for the writer

`filt` and `lim ` can be written exactly today. `gate` needs threshold and
range placed; `comp` and `eq  ` need their parameter regions placed. Every one
of them needs coefficients for all four sample rates, which the Host's builders
can produce because they already take `fs`.

The self-check that makes this safe: recomputing a stored coefficient set from
the stored parameters with `io24_dsp`'s formulas must reproduce the firmware's
bytes. It already does for the limiter threshold and the gate release.
