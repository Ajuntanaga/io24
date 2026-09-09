# Channel 1 MAIN slot-0 progress

Status: `MAIN_ACTIVE_WRITE_SENT`

The test-first runner is `re/cp34_channel1_main_slot_stage.py`; its hardware-free
contract is `tests/test_cp34_channel1_main_slot_stage.py`. The initial test run
failed because the production module did not exist. After implementation, the
new four-test contract passed, then the focused new/Channel-2/persistence/Host
suite passed 61/61.

Live preflight found the exact Revelator io24 at USB ID `194f:0422`, battery 95
percent, and no active Linux Host/audio command. The runner validated serial
`AB7C22200355`, firmware `0x0128`, and stereo link off before mutation.

The live operation:

1. Preserved Channel 2 at gain `24.287769317626953`, slot 2, enabled,
   processing index 1.
2. Bypassed Channel 1 and moved its selector from active target slot 0 to
   alternate slot 1.
3. Sent the complete 851-byte `MAIN` record to `MemP/Stat(0)` in one fragment.
4. Selected slot 0, enabled Channel 1, and directly applied the identical
   compressor, EQ, limiter, gate-off, and 24 Hz DSP-bypass values.
5. Explicitly turned the separate preamp HPF switch off.
6. Verified the exposed Channel-1 selector/enable and all protected readable
   state. Channel 1 gain remained 30 dB and Channel 2 was unchanged.

The transport returned zero replies, as recorded by the existing API. No claim
of durable storage or audible quality follows from the write receipt. Await the
user's listening report; test durable slot recall separately before calling the
preset round trip complete.

After sealing the focused result, the complete hardware-free discovery suite
passed 396 tests with one expected skip in 238.801 seconds. It reproduced the
pre-existing `ResourceWarning` for an unclosed temporary WAV reader in
`re/cp34_current_slot_survey.py`; no test failed and no hardware action was
performed by the suite.
