# CP34 linked Channel-2 slot-3 trial progress

Timestamp: 2026-09-04T02:41:59-07:00
Status: live routing sequence completed and restored; audible Voice FX remains
unproved because the passive capture contained no above-gate source.

## Result

The final discriminating caller condition was exercised on the target device.
Channel 2 moved from slot 3 to slot 2 while unlinked, stereo link was confirmed,
Channel-2 slot 3 was recalled once, and stereo link was cleared.  The action's
final readable Channel-1 guard matched its baseline.  A separate no-write
postflight confirmed flags `0x1a1`, Channel 1 disabled on slot 0, and Channel 2
enabled on slot 3.

The simultaneous six-channel capture proves that the link operation changed
the captured bus topology: during the linked window, channels 3-6 each became
a correlation-`0.99999668`, -3 dB copy of Input 2.  No 150 ms component was
measurable in those buses.  Input 2, however, contained only an open-cable noise
floor at -97.15 dBFS RMS and -83.66 dBFS peak.  The factory Slap Echo record's
gate is enabled at -47.5 dBFS, so the strongest sample was still 36.16 dB below
the gate.  The capture cannot answer whether a real transient would be echoed.

## Verification

- TDD RED: 3/3 focused contracts failed because the bounded action was absent.
- Focused GREEN: linked action 3/3; linked plus existing host actions 7/7.
- Syntax and paired preflight/action verification passed 7/7.
- Full hardware-free suite: 208 passed, one expected skip, 196.907 seconds.
- Raw capture: 14 seconds, six-channel S32_LE/48 kHz, exit 0, SHA-256
  `e587d9a7cbf78312eabcb4b2b4ee5e2f806d88335d3c812dd4d7372b1120aa14`.

## Safety and next boundary

No preset-record, gain, gate, routing, output, playback, firmware, reset, DFU,
install, Wine, or network operation occurred.  Live work stopped after the
postflight.  The only next audible discriminator is a separately prepared,
known safe source physically feeding Input 2, or separately authorized and
fully restorable gain/gate changes.  Device presence and this completed routing
trial do not authorize either.
