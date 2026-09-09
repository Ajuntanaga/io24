# CP34 model-0 decoder entry-route boundary — progress

Status: sealed, offline-only static analysis.

## Starting boundary

The decoder body and its local input mechanics were source-bound, but its own
model-0 entry ABI was not. No dynamic caller, record schema, or optional field
lookup had been recovered.

## 2026-09-02T00:38:36-07:00 — entry routes sealed

- Model-0 primary vtable `0x10c890` has decoder slot `+0x34` at `0x10c8c4`,
  which directly points to Thumb entry `0x5e0ec`.
- A separate vtable slot at `0x10c8e0` points to `0x5e268`; it subtracts
  `0x1c0` from `r0` and tail-branches at `0x5e26c` to the same decoder body.
- The decoder captures its post-entry receiver from `r0` into `sl` at
  `0x5e0f6`. This confirms static entry routes and ABI adjustment only; it does
  not identify a caller, interface name, input record, field, or model choice.
- TDD RED was the absent `model_zero_decoder_entry_routes_boundary` report key.
  The focused contract passed 1/1 in 29.857 seconds; the firmware-static module
  passed 40/40 in 34.132 seconds. The complete hardware-free suite passed 185
  tests with one expected local-artifact skip in 319.470 seconds. The only
  warning was the pre-existing temporary-WAV `ResourceWarning` at
  `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Result and retained boundary

`MODEL_ZERO_DECODER_PRIMARY_AND_ADJUSTOR_ENTRY_ROUTES_SOURCE_BOUND_OPTIONAL_FIELD_LOOKUP_UNRESOLVED`.

The two static entries do not recover caller provenance, serialized field
names/layout, optional fields/defaults, parser behavior, safe executable
placement, or an image implementation.

## Next safe action

Any continuation needs a separate exact static scope. It may inspect one named
direct decoder caller only if its receiver adjustment and all input arguments
are independently source-bound. It may not resolve a dynamic call by inference,
label a record field, or weaken any image or hardware gate.
