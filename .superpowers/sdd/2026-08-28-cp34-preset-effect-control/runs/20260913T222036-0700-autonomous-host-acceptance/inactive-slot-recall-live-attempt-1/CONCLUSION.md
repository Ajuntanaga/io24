# Inactive device-slot save/recall conclusion

The authorized no-cable A/B/A test completed on serial `AB7C22200355` at
96 kHz / 512 frames. Input 1 remained assigned to slot 0 while inactive slot 1
was written and selected in this order: flat, +15 dB/1 kHz high shelf, flat.
The readable selector changed to slot 1 after every recall, but the normalized
Main/Input-1 response changed only +0.143 dB for the boosted body; flat-state
drift was -0.085 dB. Classification:
`NO_SAVED_BODY_RECALL_EFFECT_DETECTED`.

This is a clean negative for the current tagged `MemP`/`Stat` writer/framing:
slot selection works, but a known saved body did not become active on recall.
It does not prove that the device has no preset storage or that the native
control path behaves the same way.

The complete original slot-1 `B A S E` record was Host-known before the run
(canonical SHA-256
`135a93f1e6b0b63cd8102cf1309eb2ffb6e627cd21490fecd4481ef884fb2384`)
and was resent afterward. The device returned no reply to that one-fragment
write, consistent with the registry's pre-existing
`WRITE_SENT_UNVERIFIED` status. The registry itself remained read-only.

Readable state restored exactly: flags 385, Input 1 slot 0, Input 2 slot 2,
gains 30.0/24.287769 dB, Main 0.7599996, headphones 0.5100005,
phantom/link off, and processing order 0/1. Routes, DSP Amount, and
`processingChannel` were untouched; battery was 100 percent before and after.
Controlling report SHA-256:
`8db972783d0ce15d799c1fc8b1f6ff7422faee4f13c8fefdac8b962822363299`.
