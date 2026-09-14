# Native Channel-2 gate slot discriminator

Timestamp: 2026-09-14T07:05:47-07:00
Status: measured negative; current writer route closed; restoration complete

## Result

The second native-slot acceptance test independently returned
`NO_NATIVE_SLOT_RECALL_EFFECT_DETECTED`.

- gate-off-before Main/Input-2 median: 0.989 dB
- gate-on median: 0.766 dB
- gate-off-after median: 0.903 dB
- gate-on delta against the two off windows: -0.181 dB
- off-baseline drift: -0.086 dB
- maximum window MAD: 0.374 dB

The test used firmware's own Channel-2-shaped native slot-2 record as the
1028-byte candidate base. A and B differed only in the complete native `gate`
leaf. Both stored gate states were disabled for A and enabled for B at -40 dB
threshold, -84 dB range, 5 ms attack, and 50 ms release. This removes the
Standard-EQ composer and use of a Channel-1-shaped native base as explanations
for the preceding null.

## Sequence and restoration

Inactive physical Channel-2 slot 3 received gate off, gate on, gate off, then
the pinned native Piano channel-strip restore. Every exact-length
`MemP/Stat(3)` write completed and Channel 2 reported slot 3 during every
window. Stored bodies are not readable, so transport and selector readback do
not prove commit or application.

Readable state before and after matched exactly: flags 385, Channel-1/2 slots
0/2, gains 30.0/24.287769 dB, main 0.7599996, headphones 0.5100005,
processing permutation 0/1, phantom off, and link off. The pinned native Piano
restore SHA-256 was
`4976d6e597c6caafb25c85b9011b59cb9faa23e671d56a191c4bb460a62673f8`.
Battery was 100% before/after and charging. Postflight enumeration remained
`194f:0422`.

Mixer routes, DSP Amount, and `processingChannel` were untouched. No playback,
firmware, flash, DFU, reset, Wine, network, unknown tag, or destructive slot
exploration occurred.

## Verification and evidence

- new gate-probe plus Standard-probe tests: 9 passed, 7 subtests;
- neighboring native/Stat/slot/meter tests: 43 passed, 51 subtests;
- dry run: passed;
- `live-report.json` SHA-256:
  `be97285a71f562bae959bc56cef1f5c4041b5c09aa9ed4561401ae825c4b2734`;
- runner SHA-256:
  `b60a7f2278df2eaea3b40961b42e80231cf975decaab3f358284335ec9079e32`;
- test SHA-256:
  `a23a14681854fa9f03bf90cf18c4083e1657dc157b4af28a27df2258988a696f`.

## Decision

Stop varying native record bodies through the current writer. The known
`MemP/Stat` store followed by slot-selector recall is not a viable Host writer
on current device evidence. Reopen only if a distinct commit/apply operation is
captured or source-bound. Passive EQ can continue as offline codec coverage,
but it is not a remedy for this writer failure.
