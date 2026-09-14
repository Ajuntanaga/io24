# Native Standard slot live acceptance

Timestamp: 2026-09-14T06:56:02-07:00
Status: measured negative; restoration complete

## Result

The connected io24 accepted exact-length native version-2 `MemP/Stat(3)`
transport and Channel 2 reported slot 3 after every selector transition, but
the stored Standard-EQ body did not become measurable DSP state.

Classification: `NO_NATIVE_SLOT_RECALL_EFFECT_DETECTED`.

- flat-before Main/Input-2 median: 0.929 dB
- +15 dB/1 kHz shelf median: 0.759 dB
- flat-after median: 0.949 dB
- boost delta against the two flats: -0.180 dB
- flat drift: 0.021 dB
- maximum window MAD: 0.304 dB

The same objective self-noise method previously measured about 6.66 dB from a
direct live +15 dB/1 kHz shelf, so the null is discriminating. This is stronger
than the prior tagged-record negative: a native u32-version-2 body was used.

## Exact bounded sequence

Target was inactive physical Channel-2 slot 3. Output controls were temporarily
lowered to 0.01 and Input-2 gain raised to 60 dB. The probe wrote and recalled:

1. native flat Standard EQ;
2. native +15 dB/1 kHz high shelf;
3. native flat Standard EQ;
4. pinned native Piano channel-strip restore.

The candidate and control differed only in the complete native `eq  ` leaf.
Every body was a validated 1028-byte native record. No playback or mixer-route
change was used.

## Restoration

Readable state before and after matched exactly: flags 385, Channel-1/2 slots
0/2, gains 30.0/24.287769 dB, main 0.7599996, headphones 0.5100005,
processing permutation 0/1, phantom off, and link off. The native Piano strip
restore SHA-256 was
`4976d6e597c6caafb25c85b9011b59cb9faa23e671d56a191c4bb460a62673f8`.
It was sent successfully but cannot be read back. Battery was 99% before and
after. Mixer routes, DSP Amount, and `processingChannel` were untouched.

No firmware, flash, DFU, reset, Wine, network, unknown tag, or destructive
slot exploration occurred.

## Verification and evidence

- focused probe tests: 5 passed, 3 subtests;
- neighboring native/Stat/slot/meter tests: 43 passed, 51 subtests;
- dry run: passed;
- `live-report.json` SHA-256:
  `e3ee09ba3a968b16f869455e21908d9cbe3111e124417386026365c00f6b5d32`;
- runner SHA-256:
  `269e9687c618feeddc2036951e160da2de0e3034bedc82d5846dcccc29840b6d`;
- test SHA-256:
  `32f657894ee33c9400796423f9079046d756756f2bb62119cb3e66896acf6b7e`.

## Next discriminator

Avoid the Standard-EQ composer as the next variable. Use the already decoded
native limiter leaf for a limiter-off / severe-limiter-on / limiter-off A/B/A
under the same guards and restoration. If that also produces a stable null,
the evidence points to a missing commit/apply edge in the known
`MemP/Stat`-plus-selector sequence rather than to EQ coefficient construction.
