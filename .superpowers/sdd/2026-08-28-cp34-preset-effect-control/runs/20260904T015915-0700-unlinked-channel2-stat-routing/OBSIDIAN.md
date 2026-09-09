# io24 CP34 - Channel-2 Stat routing resolved

Updated: 2026-09-04T02:11:16-07:00

Current live state: battery 98%, io24 `AB7C22200355` firmware descriptor 1.28,
flags `0x1a1`, stereo link off, Channel 1 slot 0 disabled, Channel 2 slot 3
enabled. Two read-only `JaSt` replies were identical.

Current result: unlinked Channel-2 slots 2/3 dispatch the second channel-strip
state apply (`filt`, `gate`, `comp`, `eq`, `lim`), not Voice FX. This explains
the dry custom Delay and factory Slap Echo observations but does not prove or
disprove physical `Stat` storage.

Linked candidate: with bit 12 set and a positive slot, firmware runs the normal
indexed table first, where Voice FX slot 1 is eligible, then the second channel
strip. Actual Voice FX selection remains record-driven.

Verification: read-only preflight 4/4; firmware-static 44/44; complete
hardware-free suite 205 passed with one expected skip in 482.698 seconds,
exit 0. No firmware image or live mutation beyond the bounded reads was
produced.

Next gate: explicitly lift the Channel-1-untouched restriction and accept that
full Channel-1 strip restoration cannot be guaranteed before a temporary link
plus slot-3 recall trial.

Authoritative recovery: `../../RESUME.md`; detailed checkpoint:
`PROGRESS.md`, `LIVE-PREFLIGHT.json`, `ROUTING-RESULT.json`, and
`CHECKPOINT.sha256` in this directory.
