# CP34 pre-slot-two direct-target prologue boundary — progress

Opened: 2026-09-01T23:54:53-07:00
Status: active, offline-only static analysis.

## Starting boundary

The sealed caller path reaches direct target `0x5d2cc` with `device +0x508c`.
That receiver is adjacent to but not identified with slot two at `+0x5090`.

## Planned bounded action

Decode only the target's prologue through its first call or control transfer,
then record any receiver adjustment or static store. Do not enter later calls
or infer type/semantics from the prologue.

## 2026-09-02T00:02:35-07:00 — pre-slot-two target prologue sealed

- Direct target `0x5d2cc` begins with a `push`, local stack allocation, and
  captures caller-provided `r0` unchanged into `r4` at `0x5d2d6`.
- Before its first control transfer at `0x5d2da`, the target makes no receiver
  adjustment and no receiver-relative store. Its only early store writes `r1`
  to its local stack frame. The first conditional branch targets `0x5d3b0`.
- The caller-supplied receiver remains source-bound `device +0x508c`, four
  bytes before unresolved slot two `+0x5090`. This still does not establish an
  object/interface identity, vtable, later target behavior, parser behavior, or
  semantics. No subsequent target block, call, or virtual entry was followed.
- TDD RED was the missing `pre_slot_two_target_prologue_boundary` report key.
  The focused hardware-free contract passed 1/1 in 18.783 seconds; the
  firmware-static module passed 37/37 in 25.095 seconds. The complete
  hardware-free suite passed 182 tests with one expected local-artifact skip
  in 240.250 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. A separate exact static scope may inspect one specified
post-branch basic block only if the branch condition and incoming receiver can
be source-bound. It may not follow a call or virtual target, infer semantics,
parser behavior, component identity, executable placement, or a firmware
implementation.
