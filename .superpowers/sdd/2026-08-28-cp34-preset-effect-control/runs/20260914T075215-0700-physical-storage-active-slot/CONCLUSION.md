# CP34 active-slot native gate conclusion

Timestamp: 2026-09-14T08:04:58-07:00
Status: `NO_NATIVE_ACTIVE_SLOT_GATE_EFFECT_DETECTED`

With the user's explicit acknowledgement that the original slot body is
unreadable, the probe wrote native gate off / on / off bodies to global slot 3
while that slot was selected before every `MemP/Stat(3)` write. Each candidate
then received a forced 2 -> 3 recall edge. All three writes sent one exact-
length fragment and no readable storage reply.

The simultaneous `JaSt` Input-2/Main measurement was stable. Gate-on changed
the median Main/Input-2 ratio by only -0.068913 dB. The off-to-off drift was
+0.112856 dB and the maximum window MAD was 0.349676 dB. This is a null, not a
detected gate effect.

The `finally` path selected slot 3, rewrote the pinned native Piano body while
active, and restored all readable controls. The before/after state matches
exactly: Input 2 returned to slot 2 and 24.287769 dB gain; main returned to
0.7599996; headphones returned to 0.5100005; both phantom supplies stayed off;
input assignments and processing enable match. Slot-body restoration remains
write-sent rather than read-back proven. Battery was 99% before and after, and
postflight USB identity remained `194f:0422`, firmware `0x0128`.

This rejects inactive-slot timing as the explanation for the two earlier native
nulls. The known `MemP/Stat` writer must remain an exact transport primitive,
not a working preset-save feature. Do not continue record-body variants. The
next writer investigation should follow Universal Control's distinct explicit
Store/assignment route (`PrsM`) or a newly captured known command.

Evidence:

- `live-attempt-1/live-report.json`
- report SHA-256:
  `be5e19f27c703368a52ca3a0e460872fb3ae80b9baba1dff07040de22cc6d46d`

## 2026-09-14 positive control: this null is confirmed decisive

The null above was published without a positive control, so on its own it could
not distinguish a failed native write from a meter that cannot see Channel-2
DSP. That control has now been run, holding device, channel, meter, window size
and gate values constant and changing only the write route to the already
hardware-verified direct `SetP`/`gate` setter.

The direct route moved the same Main/Input-2 ratio by **-28.0871 dB** against a
2.6915 dB detection threshold, with baseline drift -0.1193 dB. That is roughly
400 times the native probe's -0.0689 dB delta. Input 2's own level held steady
while Main collapsed and recovered.

The blind-meter explanation is therefore excluded and the native active-slot
null stands as a genuine negative about the `MemP/Stat` write route. As a
by-product this also establishes that Channel 2's processing is in the Main
path on the current routing, which this run had not confirmed.

Evidence: `../20260914T083208-0700-direct-gate-positive-control/control-report.json`
