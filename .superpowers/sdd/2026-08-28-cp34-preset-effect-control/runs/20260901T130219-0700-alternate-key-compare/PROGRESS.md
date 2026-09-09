# CP34 alternate-path static key-comparison boundary — progress

Opened: 2026-09-01T13:02:19-07:00
Status: active, offline-only static analysis.

## Starting boundary

The sealed cursor-adjust stage reaches an immediate four-byte reader and a
local equality comparison. The expected word originates at device `+0x5e8c`,
which the constructor initializes from the same `opt ` literal associated with
the table's third entry.

## Planned bounded action

Verify the exact expected-key store, reader output local, equality branch, and
constructor literal only. Do not follow the equal branch or name the key as a
parser field/component.

## 2026-09-01T13:10:01-07:00 — alternate static key-comparison boundary sealed

- The alternate path snapshots its current device word at `+0x5e8c` into
  `sp+0x18`. Construction initializes that location from literal `opt `
  (`0x6f707420`), but the verifier intentionally records the runtime
  comparison operand separately from its constructor default.
- A direct four-byte reader writes `sp+0x4c`; after its success check, the
  path compares that word with `sp+0x18` at `0x53434` and has a bounded equal
  branch to `0x5345a`. The reader word, key meaning, record order, and branch
  outcome remain semantically unresolved.
- This does not establish a parser field, component identity, Voice FX slot
  one, component 201, top-level apply `r1` provenance, `godv` linkage,
  executable placement, or a firmware implementation.
- TDD RED was the missing `alternate_key_compare_boundary` report key. The
  focused hardware-free contract passed 1/1 in 14.898 seconds; the
  firmware-static module passed 30/30 in 15.783 seconds. The complete
  hardware-free suite passed 175 tests with one expected local-artifact skip
  in 288.630 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. A separate exact static scope may inspect only the first
equal-branch block at `0x5345a..0x5347c`; it may not follow the dynamic
component interface call, infer component identity, or emit an image.
