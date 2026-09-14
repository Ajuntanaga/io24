# Active-slot pre-authorization record

Superseded 2026-09-14T08:04:58-07:00: the user explicitly accepted the risk,
the live probe completed, and its result is in `CONCLUSION.md` and
`live-attempt-1/live-report.json`. This file is retained to show that the
earlier request did not launch or mutate the device.

The bounded command was submitted for the required device-operation approval,
but execution was rejected before process launch. The reason was the exact
remaining restoration limit: global slot 3 contents are unreadable, so a write
to the active slot cannot be restored with readback proof. No `MemP`, selector,
gain, volume, routing, DSP Amount, `processingChannel`, firmware, reset/DFU,
Wine, or other device command was sent by this attempt.

The prepared runner and its failure restoration tests remain at
`re/io24_native_gate_active_slot_probe.py` and
`tests/test_io24_native_gate_active_slot_probe.py`.
