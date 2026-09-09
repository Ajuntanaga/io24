# CP34 adjacent pre-slot-two receiver boundary — progress

Opened: 2026-09-01T23:45:19-07:00
Status: active, offline-only static analysis.

## Starting boundary

The sealed base-initializer map excludes slot two from the entry prologue. A
later direct call at `0x5df3e` loads its receiver from a caller-local stack slot
and adds `0x18`; its source offset has not yet been bound.

## Planned bounded action

Verify the stack-local provenance, direct call target, and exact arithmetic.
Report adjacency to slot two only if the source path is intact; do not enter the
callee or infer object identity from the offset relationship.

## 2026-09-01T23:52:54-07:00 — adjacent pre-slot-two receiver sealed

- The base initializer allocates its `0x24`-byte caller-local stack frame at
  `0x5d9ba`; the `sp+0x4` slot has one source-bound store at `0x5dc2e` and
  two loads (`0x5dc50`, `0x5df36`) before release at `0x5df64`.
- The stored value is constructed as `device +0x5074`; the named later call
  reloads it at `0x5df36`, adds `0x18` at `0x5df3c`, and directly calls
  `0x5d2cc` at `0x5df3e` with receiver `device +0x508c`.
- `+0x508c` precedes unresolved slot-two `+0x5090` by four bytes. This is
  source-bound adjacency only, not object identity, an interface adjustment,
  a vtable binding, target semantics, or parser behavior. The target was not
  entered.
- TDD RED was the missing `adjacent_pre_slot_two_receiver_boundary` report key.
  The focused hardware-free contract passed 1/1 in 19.844 seconds; the
  firmware-static module passed 36/36 in 17.417 seconds. The complete
  hardware-free suite passed 181 tests with one expected local-artifact skip
  in 239.985 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. A separate exact static scope may inspect direct target
`0x5d2cc` only to recover its receiver adjustment or initial static store, if
any. It may not follow further calls or virtual targets, infer semantics,
parser behavior, component identity, executable placement, or a firmware
implementation.
