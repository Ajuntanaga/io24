# CP34 alternate equal-branch slot-two dispatch boundary — progress

Opened: 2026-09-01T13:11:49-07:00
Status: active, offline-only static analysis.

## Starting boundary

The sealed alternate key-comparison stage reaches its equal branch at `0x5345a`
but intentionally stops before the later component call. The same function
retains table offset `0x5e88` from the alternate setup.

## Planned bounded action

Verify the direct table object load and `+0x4` interface call only, link it to
the constructor's `device+0x5090` slot-two store, and prove it is not Voice FX
slot one. Do not traverse a dynamic target.

## 2026-09-01T13:19:22-07:00 — alternate slot-two dispatch boundary sealed

- The alternate setup retains `fp = 0x5e88`; on normal callee-saved flow, the
  equal branch loads `device + fp` and dispatches its object's vtable `+0x4`
  slot at `0x53470..0x5347c` with the existing record receiver in `r1`.
- Constructor code stores `device + 0x5090` at `device + 0x5e88`, which is
  component-table slot two. Voice FX is separately at slot one,
  `device + 0x5e80`. The equal branch is therefore source-bound to slot two,
  not the Voice FX route.
- The slot-two interface target and semantics remain dynamic/unresolved. This
  does not identify parser behavior, component 201, top-level apply `r1`
  provenance, `godv` linkage, executable placement, or a firmware
  implementation.
- TDD RED was the missing `alternate_slot_two_dispatch_boundary` report key.
  The focused hardware-free contract passed 1/1 in 15.063 seconds; the
  firmware-static module passed 31/31 in 15.947 seconds. The complete
  hardware-free suite passed 176 tests with one expected local-artifact skip
  in 286.710 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. A separate exact static scope may identify the vtable
installed at device `+0x5090` only if its direct constructor binding is found.
It may not infer semantics from that binding, follow an indirect target, or
emit an image.
