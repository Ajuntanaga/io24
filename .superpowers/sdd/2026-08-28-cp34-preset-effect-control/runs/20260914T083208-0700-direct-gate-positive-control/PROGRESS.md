# Positive control for the native active-slot gate null

Status: `DIRECT_GATE_EFFECT_DETECTED` — the native null is confirmed decisive.

## Why this was run

The active-slot probe reported `NO_NATIVE_ACTIVE_SLOT_GATE_EFFECT_DETECTED` and
the peer inbox escalated it to a "decisive negative" that closes off record-body
variants. The run had no positive control, so its null was equally consistent
with two worlds: the native write not taking effect, or the Main/Input-2 meter
being unable to see Channel-2 DSP at all. `mixer_routes` and `processing_channel`
were both `UNTOUCHED` and the ratio sat near unity in all three windows, which
is what a blind meter would also look like. PROTOCOL.md §12Y records a published
null being voided for exactly this omission.

## Result

Everything held constant except the write route. Direct `SetP`/`gate` blob,
same channel, same meter, same 40-sample windows, same gate values
(-40 dB threshold, -84 dB range, 5 ms attack, 50 ms release, 20 Hz key filter).

| window | median Input 2 | median Main | ratio dB | MAD dB |
|---|---|---|---|---|
| direct_gate_off_before | 0.00083805 | 0.00146451 | +4.8940 | 0.3494 |
| direct_gate_on | 0.00085539 | 0.00005833 | **-23.2528** | 0.4486 |
| direct_gate_off_after | 0.00087134 | 0.00150742 | +4.7747 | 0.3001 |

Effect delta **-28.0871 dB** against a detection threshold of 2.6915 dB
(6 x max window MAD). Baseline drift -0.1193 dB, inside the 0.75 dB stability
limit. Classification `DIRECT_GATE_EFFECT_DETECTED`.

Input 2's own level was unchanged across all three windows while Main collapsed
and recovered, so the movement is Channel-2 processing and not a source drift.
The residual Main level under a closed gate is consistent with Channel 1 still
feeding the bus.

## Consequence

The meter observes a Channel-2 gate change at roughly 400 times the size of the
native probe's measured delta (-28.09 dB versus -0.0689 dB). The blind-meter
explanation is excluded. The native active-slot null is therefore a genuine
negative about the `MemP/Stat` write route, and the inbox's instruction to stop
varying record bodies is now supported by evidence rather than assumed.

This also establishes, as a by-product, that Channel 2's processing is in the
Main path on the current routing — which the native probe never confirmed.

## Boundary

Direct live setters only; no native record, `PrsM`, slot, routing, or firmware
operation. Identity verified before any write: serial `AB7C22200355`,
`194f:0422`, firmware `0x0128`. Battery 98% before and after. All disturbed
controls restored exactly: Input-2 gain returned to 24.287769317626953 dB and
main volume to 0.7599995732307434. The gate was left in its byte-exact firmware
power-on state, which is a defined landing point rather than a guess at the
channel's prior contents; recall a preset on Channel 2 to reprogram it.

Evidence: `control-report.json`.
