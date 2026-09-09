# CP34 model-0 decoder first-helper boundary — progress

Status: sealed, offline-only static analysis.

## Starting boundary

The stock model-0 structured decoder at `0x5e0ec` was hash-pinned but did not
yet have a source-bound first direct-helper argument boundary. The parser gate
remained `OPTIONAL_FIELD_LOOKUP_UNRESOLVED`.

## 2026-09-02T00:17:23-07:00 — first-helper boundary sealed

- Decoder `0x5e0ec` captures its receiver in `sl` at `0x5e0f6`, its incoming
  pointer in `r6` at `0x5e0f8`, and checks the incoming count at `0x5e0ec`.
- Its first direct call at `0x5e192` targets `0x5e094`. Immediately before the
  call, `r0` and `r1` are addresses of decoder-local descriptors at `sp+0x2c`
  and `sp+0x4`; they are not direct serialized-field pointers.
- Those local descriptors are initialized with heads at `sp+0x34` and
  `sp+0xc`; the count source is set to zero at `0x5e156` and remains unchanged
  through the local setup.
- The helper first checks `[r0,+4]` against one, and separately branches from a
  zero-or-less `[r1,+4]` count to the `r0 = 1` success return. The over-limit
  branch reaches the `r0 = 0` return. This is descriptor/count evidence only.
- TDD RED was the absent `doubler_decoder_first_helper_boundary` report key.
  The focused contract passed 1/1 in 16.607 seconds; the firmware-static module
  passed 38/38 in 17.237 seconds. The complete hardware-free suite passed 183
  tests with one expected local-artifact skip in 256.479 seconds. The only
  warning was the pre-existing temporary-WAV `ResourceWarning` at
  `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Result and retained boundary

`DOUBLER_DECODER_FIRST_HELPER_LOCAL_DESCRIPTORS_SOURCE_BOUND_OPTIONAL_FIELD_LOOKUP_UNRESOLVED`.

The first helper's local descriptor mechanics do not recover serialized record
field names, model-0 optional fields, defaults, a parser bridge, safe
executable placement, or an image implementation.

## Next safe action

Any continuation needs a separate exact static scope. It may inspect one named
decoder operation that consumes the captured incoming pointer, but may not
follow a later call, assign record/field semantics, or weaken any image or
hardware gate.
