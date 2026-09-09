# Channel-2 Reverb assignment correction scope

Timestamp: 2026-09-06T06:47:42-07:00
Status: **INVALID PHYSICAL CHANNEL CONTROL MAPPING; SUPERSEDED**

The retained attempt assigned VoiceFX to Input 2 but called the physical preset
APIs with channel 1. Its readback shows Channel 1 changed. It is not a
Channel-2 recall/audibility result; see `LIVE-ATTEMPT-2-CLASSIFICATION.md`.

This run corrects one over-broad inference and prepares one bounded acceptance
test:

- target only serial `AB7C22200355`, firmware descriptor `0x0128`;
- target global slot 3 for physical Channel 2; never target or write slot 0;
- reproduce UC's `Assign Voice FX = Ch2` state before the slot write;
- preserve the firmware's observed active-slot-value exchange while keeping
  physical preset-control calls on Channel 2;
- write the exact complete tagged factory `Reverb` record through
  `MemP/Stat(3)`;
- recall and enable slot 3 through Channel 2;
- stop for the user's disconnected, non-computer-powered cold-boot listening
  check.

The first authorized attempt stopped before any record write and is retained in
`LIVE-ATTEMPT-1.json`. The second sent `Stat(3)` but recalled through physical
Channel 1 and is retained unchanged in `LIVE-ATTEMPT-2.json`. A corrected
successor exists in the later materialization run and requires new exact live
authorization.
