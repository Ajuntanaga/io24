# CP34 channel-2 slot-3 173 ms Echo trial

## Authority

The operator granted full CP34 access on 2026-09-03, then explicitly limited
preset-block editing, changing, and testing to channel 2 while directing that
channel 1 remain untouched. The target unit is Revelator io24 serial
`AB7C22200355`.

## Exact bounded operation

1. Confirm host battery remains above 10 percent and verify the exact serial.
2. Claim interface 5, alternate setting 1, and take a `GetP/Appl/JaSt`
   baseline.
3. Write only the complete `MemP/Stat` record in `channel2-slot3-173ms.json`
   to global slot 3, which is channel 2's inactive block at baseline.
4. Send only the known `Pari` preset-selector write with channel index 1 and
   value 3, then take a second `JaSt` state read.
5. Release the interface and record frame hashes, state, and boundaries.

No operation may target slots 0 or 1, a channel-1 selector, gain, phantom,
mute, routing, output level, or effect block. The run will not flash/reset/DFU,
access Wine, access the network, install/stage software, detach USB, or make a
custom-firmware change.

## Record and acceptance boundary

The record is a complete stock-compatible Slap Echo base with a deliberately
distinct 173 ms delay and compressor threshold -22 dB. It retains `voicefx.on`
and a stock Delay class identifier. A successful transport write plus selected
slot 3 establishes only `WRITE_SENT_AND_SELECTED`; it does not establish a
physical nonvolatile commit, front-panel recall, decoded-record equality, or
audibility.

The device offers no full current-slot readback, so the pre-write content of
slot 3 cannot be restored from host evidence. The operator explicitly permits
channel-2 block changes; channel 1 is preserved by an enforced transport guard
and before/after state comparison.
