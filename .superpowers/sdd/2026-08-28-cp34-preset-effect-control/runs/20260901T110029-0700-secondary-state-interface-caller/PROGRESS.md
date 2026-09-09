# CP34 secondary state-interface caller boundary — progress

Opened: 2026-09-01T11:00:29-07:00
Status: sealed, offline-only static analysis.

## Starting boundary

The sealed predecessor proved two primary owner tables share `0x5545c`, but
neither owner installation materializes the independent `r1` state receiver.
The dynamic target at model-0 `0x54730` remains unresolved and is excluded.

## Planned bounded action

Verify the Voice FX parent’s embedded secondary state-interface field and only
its direct static dispatch/caller chain. Record whether the caller materially
constructs or constrains the separate `r1` record argument; stop before any
model-state dispatch.

## 2026-09-01T11:08:13-07:00 — secondary-interface caller boundary sealed

- The Voice FX owner construction loads the primary table from literal
  `0x418fc` at `0x41888`, forms the embedded owner at `r4+0x11e0`, and stores
  the primary vtable at `0x4189a`.
- It separately forms `+0x11e4` at `0x4188e`, derives secondary vtable
  `0x10c700` as primary `0x10c6bc + 0x44` at `0x41896`, and stores it at
  `0x418a0`. The secondary slot `0x10c704` (`+0x4`) targets adjustor
  `0x555b8`, which subtracts four from `r0` and branches to `0x5545c`.
- This source-binds the embedded-owner `r0` route into top-level apply, but no
  direct static caller was source-bound in this scope and no construction or
  concrete type of the independent `r1` record was materialized. The sealed
  result is `SECONDARY_INTERFACE_ROUTE_SOURCE_BOUND_CALLER_AND_R1_UNRESOLVED`.
- TDD RED was the missing
  `voicefx_secondary_state_interface_caller_boundary` report key; its focused
  hardware-free contract passed 1/1 after the minimal verifier. The complete
  hardware-free suite passed 165 tests with one expected local-artifact skip
  in 193.787 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This bounded stage is sealed. Any further caller investigation must start with
a separate exact scope and checkpoint that identifies a concrete dispatcher or
record-construction boundary. It must not infer `r1` type from the secondary
table, follow a model-state indirect call, invent a parser hook/code cave, or
emit an image.
