# The Vintage and Passive EQ switch tables, recovered

PROTOCOL.md §12N formerly recorded the Vintage model as a Neve 1073 with only
switch indices known, and the Host's old `--vintage-eq` path applied 1073
values as a labelled guess. The table is now read out of the vendor's own
binary and that approximate direct-live path remains disabled.

Source: the pinned UC 4.7.2 `dspusbdevice.dll`, 4,979,672 bytes, SHA-256
`de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`, at
`runs/20260906T001130-0700-uc472-official-reacquisition/extracted/hwaccess/`.
Offline static reading only.

## Current result

The switch tables and all four Vintage designers are recovered. The designers
write 22 floats per clock: low-mid, hi-mid, and high are five-float sections;
the low shelf is a seven-float third-order section. That is exactly the native
`eq  ` coefficient capacity. `re/uc472_vintage_eq.py` executes the pinned
vendor routines for 44.1, 48, 88.2, and 96 kHz and can replace only the EQ
coefficients in a complete validated native record. The running Host still
keeps direct Vintage editing paused because this executable analysis depends on
the separately retained UC DLL. No device operation was performed.

## Where it is

The position labels are 8-byte inline strings in `.rdata` from file `0x4327d8`
(VA `0x1804335d8`; the section's file-to-VA delta is `0xE00`). Lists of
pointers to them sit in `.data` at file `0x49ba50` onward, which is what binds
each list to a parameter, in order.

## Vintage 1970s (Neve 1073)

| Parameter | Enum max | Positions |
|---|---|---|
| `lowfreq` | 3 | **35, 60, 110, 220 Hz** |
| `lowmidfreq` | 2 | **360, 700, 1600 Hz** |
| `himidfreq` | 2 | **3200, 4800, 7200 Hz** |
| `lowgain`, `himidgain`, `lowmidgain`, `higain` | +-16 dB | continuous |

The counts match the descriptor maxima exactly (4, 3, 3), which is what makes
the grouping unambiguous rather than a plausible reading: a 1073's four-position
LF shelf and its six mids split three and three.

## Passive Program (Pultec EQP-1A)

The three pointer lists are now bound to the descriptors and designers:

| Parameter | Positions |
|---|---|
| `bfreq` | **20, 30, 60, 100 Hz** |
| `mfreq` | **3, 4, 5, 8, 10, 12, 16 kHz** |
| `hsfreq` | **5, 10, 20 kHz** |

The pinned binary literally reuses the string `20kHz` for `bfreq` index 0 and
`hsfreq` index 2. The low designer's circuit branch and the physical EQP-1A
control identify the former as 20 Hz; this is a vendor label reuse/bug, not a
20 kHz low-band setting.

Passive also does appear in the retained UC factory collection: **Big Vocal**
has class `{C0730CBB-5135-4558-9222-C40BDBA036ED}` with boost 3.9 at low
position 3, high boost 1.8 at position 6, bandwidth 4.55, and both attenuation
controls at zero. That is an authentic semantic fixture.

`0x18001a610` writes the seven-float combined high boost/attenuation section;
`0x18001adb0` writes the five-float combined low boost/attenuation section.
The recompute sends them as `Lfdf` index 0 and `Bqdf` index 1, with indexes 2
and 3 identity. Firmware native slot 2 has exactly that structural shape: one
non-identity main biquad, two identity main biquads, and one non-identity
seven-float wide section. `re/uc472_passive_eq.py` executes both routines at
all four stored clocks and overlays only the EQ coefficient bytes in a
validated native record. This is offline executable analysis and still
depends on the retained pinned DLL; it is not a running-Host dependency.

## What it decodes on this unit

`MAIN` and `B A S E` both carry `lowfreq 0`, `lowmidfreq 0`, `himidfreq 1`:

    low shelf   35 Hz    +1.76 dB
    low-mid    360 Hz    -3.84 dB
    hi-mid    4800 Hz    +1.60 dB
    high        fixed    +0.96 dB

## Initial gap (closed later in this record)

The coefficient designer was the next missing piece after the tables. The
sections below retain the analysis sequence: first the routine was located,
then its seven-float output was interpreted correctly, and finally all four
adjacent output regions were bound to the native record layout.

## The designer, located

Walking the code from the label lists:

- `0x18001b660..0x18001ba00` registers the Vintage parameters and proves the
  grouping from the code side: `lowfreq` id 2 with **4** positions,
  `lowmidfreq` id 4 with **3**, `himidfreq` id 6 with **3**.
- The class vtable is `0x180434608`, referenced at `0x18001bc1e`. It has no
  selector-mapper slot at `+0xC0`, so Vintage does not use the Standard EQ's
  selector machinery that `re/uc472_standard_highshelf.py` recovered.
- `0x18001bf80` / `0x18001c0b0` are the parameter set/get switches over ids
  0..7. They store each frequency as an **index** (`+0x60`, `+0x88`, `+0x9c`)
  with its gain beside it (`+0x64`, `+0x8c`, `+0xa0`, `+0x78`) and raise dirty
  flags at `+0xb4..+0xbb`.
- `0x18001bdd0` is the sample-rate handler; it recomputes the per-band
  smoothing from 1/rate.
- `0x18001c140` is the recompute. At `0x18001c270` it loads the low-frequency
  index into `edx`, points `rcx` at the band's coefficient buffer, and calls
  the designer; it then packs the result into an `fdfL`-tagged blob for the
  device.

**The designer is `0x18001d470`.** It takes the coefficient buffer, the
smoothed gain, and the frequency index.

It is not a textbook shelf. It is an analog model: the corner frequency and Q
are polynomial fits in the absolute gain, with one branch for index < 2 and
another for index >= 2, and the result clamped to 5 .. 20000 Hz. Constants seen
in the first branch include 21.68, 2.455, 0.02589, 0.002083, 0.1237, 0.07143,
1.006 and 0.01143; the second uses 37.96 among others, and index 0 scales by
0.53.

That is what a Neve 1073 does - its corner and Q move with the gain control -
and it is why the Host's "apply 1073 values as a labelled guess" was never
going to match. Reproducing it exactly means transcribing this function and its
callees faithfully; it is bounded work, a few hundred instructions across the
branches, not a guess.

**Ground truth for an acceptance test:** any firmware default record whose EQ
is a Vintage preset stores the designer's exact output as coefficients, so a
transcription can be checked against those bytes rather than against opinion.

## Intermediate transcription result (superseded below)

`re/uc472_vintage_eq.py` executes the vendor's designer rather than
re-implementing it: a small x86-64/SSE interpreter runs `0x18001d470` and its
callees (`0x18001b270`, `0x18001b110`, and the `tanf`/`powf` stage
`0x180010610`) straight out of the pinned DLL, so the arithmetic and its
float32 rounding are the vendor's by construction. The chain uses no
double-precision instructions, so single precision throughout is correct.

It runs clean: 333 instructions for one band, no unmodelled opcode, the
expected switch capacitor selected per index (index 0 takes 2e-7 F).

The initial response calculation was wrong because it read a seven-float
third-order section as a five-float biquad. Under that incorrect reading it
appeared nearly flat:

    gain -16 dB -> 0.999844  2.705977 -2.706195 -2.430948  2.430982   DC -0.002 dB
    gain   0 dB -> 1.000000  2.897441 -2.897441 -2.796924  2.796924   DC  0.000 dB
    gain +16 dB -> 1.000157  2.706618 -2.706401 -2.431362  2.431328   DC +0.002 dB

The coefficients do move with gain, and at 0 dB the numerator and the negated
denominator match exactly, which is a correct identity filter. So the routine
is being driven, but either an input is still wrong or these seven floats are
an intermediate rather than the band's final response - the engine may apply
the shelf gain around this filter rather than inside it.

Known and unknown inputs at the call site (`0x18001c344`): `rcx` is the scratch
buffer at object `+0xc4`, `edx` the switch index from `+0x60`, `xmm2` the gain
from `+0x70`, and the fifth argument is either -1 or an inverse sample rate.
Nothing else in the buffer is read except the rate at `+0x58`.

Next moves, in order of expected value:

1. Follow what the recompute does with the seven floats after the call
   (`0x18001c27b` onward) and how the `fdfL` blob is consumed, to learn whether
   the gain is applied outside this filter.
2. Compare against `0x18001cf30`, the gain-only high band, which takes a gain
   and no index; its output shape should reveal the convention.
3. Only then wire anything into the Host.

At this point in the analysis the Host correctly remained fail-closed. The next
step resolved the apparent flat result without changing any device state.

## Intermediate interpretation (superseded by the measured write regions)

Following the seven floats proved that `fdfL` carries a real higher-order
section, while `Bqdf` carries an ordinary biquad. The first record-layout pass
still mislabeled the two trailing wide-section floats as padding and therefore
incorrectly concluded that stored slots held only biquads. Measuring every byte
written by all four designers resolved that mistake in the next section: the
native record holds the same 7 + 5 + 5 + 5 output buffer.

## What produces the stored biquads - answered

The open question was whether UC converts a Vintage EQ into biquads before
storing it, or the device derives them when it saves. Neither. **The record is
a copy of the designer's output buffer.**

The recompute at `0x18001c140` calls four designers, each writing its own
adjacent piece of one buffer at `+0xc4`. The widths below were measured by
recording which bytes each designer actually wrote, not assumed:

| Band | Designer | Index field | Gain in | Bytes | Floats |
|---|---|---|---|---|---|
| low | `0x18001d470` | `+0x60` | xmm2 | `0x00..0x1b` | **7** |
| high | `0x18001cf30` | none (fixed) | xmm1 | `0x1c..0x2f` | 5 |
| hi-mid | `0x18001cc20` | `+0x88` | xmm2 | `0x30..0x43` | 5 |
| low-mid | `0x18001c910` | `+0x9c` | xmm2 | `0x44..0x57` | 5 |

7 + 5 + 5 + 5 = **22 floats, 88 bytes**, with no gap and no overlap.

A stored `eq  ` unit holds **22 floats per sample rate**: three five-float
bands in the 69-byte main unit plus one seven-float band in the 37-byte wide
unit. The counts match exactly, and the seven-float band is the reason the
wide unit exists - a third-order section cannot be folded into a biquad, so a
converter targeting biquads could not have produced it.

### The band order in the record

Reading the firmware defaults back as filters places the main unit's three
bands as low-mid, hi-mid, high, with the low band in the wide unit:

| Slot | low-mid | hi-mid | high | wide |
|---|---|---|---|---|
| 0 | -1.00 dB @ 275 Hz | -3.00 dB @ 6233 Hz | off | -1.90 dB @ 31 Hz, biquad-shaped |
| 1 | +1.50 dB @ 260 Hz | -3.00 dB @ 1205 Hz | +1.29 dB @ 8853 Hz | +2.14 dB @ 52 Hz, biquad-shaped |
| 3 | off | +1.50 dB @ 4002 Hz | +2.15 dB @ 18878 Hz | -1.50 dB @ 201 Hz, biquad-shaped |

Every one is in ascending frequency order, which is what makes the assignment
a reading rather than a fit. An unused band stores `1, 0, 0, 0, 0`.

Slot 2 does **not** fit that order: its low content sits in the first main band
(+8.97 dB @ 15 Hz) and its wide unit carries a genuine **third-order** section
(+0.68 dB @ 5952 Hz, trailing floats `-0.156978, +0.142112`). So slot 2 is a
different EQ type, and the wide unit holds whichever band that type designs at
third order. That one record is the direct proof the seven-float form is
stored and recalled by real firmware, not a spare field.

### The low band is a real Neve shelf

Read in the device's interleaved convention carried to third order
(`b0, -a1, b1, -a2, b2, -a3, b3`), the low designer at +6 dB gives:

| Switch | 10 Hz | 20 Hz | at the switch | 1 kHz | 15 kHz |
|---|---|---|---|---|---|
| 35 Hz | +4.56 | +3.35 | +1.71 | -0.01 | -0.00 |
| 60 Hz | +5.00 | +4.55 | +2.06 | -0.06 | -0.00 |
| 110 Hz | +5.16 | +5.01 | +2.10 | -0.23 | -0.00 |
| 220 Hz | +5.19 | +5.15 | +2.22 | -0.53 | -0.00 |

The half-gain point tracks each switch position, the response returns to unity
above 5 kHz, and boost and cut are slightly asymmetric at 35 Hz (+4.56 against
-4.87) - all of which is what a 1073 LF shelf does. Factoring the section gives
three real poles and three real zeros, all on the positive real axis inside the
unit circle: three cascaded one-pole shelving stages, no resonance.

One caution for anyone measuring this: the section's poles sit as close as
0.997 to z = 1, so `num(1)` and `den(1)` are both around 5e-6. True DC is
therefore dominated by float32 rounding of coefficients near 2.897 and is not a
meaningful measurement point. Measure at 10-20 Hz instead.

Executable: `re/uc472_vintage_eq.py` (`design(image, band, index, gain, rate)`),
contracts in `tests/test_uc472_vintage_eq.py`.
