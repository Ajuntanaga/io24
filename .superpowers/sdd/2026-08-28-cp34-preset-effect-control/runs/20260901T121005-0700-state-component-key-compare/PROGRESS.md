# CP34 structured-state component-key comparison boundary — progress

Opened: 2026-09-01T12:10:05-07:00
Status: active, offline-only static analysis.

## Starting boundary

The sealed indexed-component stage established the device-owned table and its
valid Voice FX slot-one state-interface route, but correctly left its selected
`r7` dynamic. The next exact bridge is the comparison at `0x53326`, where
locals at `sp+0x8` and `sp+0x4c` determine whether `r7` receives loop counter
`r6`.

## Planned bounded action

Bind the two local write paths, inspect only the direct four-byte reader
adapter at `0x2cf58`, and distinguish component-key layout from a selected
component. Do not extend into parser semantics or dynamic helper targets.

## 2026-09-01T12:10:05-07:00 — key-comparison boundary sealed

- A focused hardware-free contract first failed because
  `structured_state_component_key_compare_boundary` did not exist.
- The repaired verifier binds both operand paths at `0x53326`. The candidate
  key is indexed from the device key table rooted at `+0x5e7c` and written to
  `sp+0x8`; the other word is produced at `sp+0x4c` by direct helper `0x2cf58`.
  That helper requests exactly four bytes, accepts only a length-four result,
  byte-reverses the word, and stores it through the supplied output pointer.
- Constructor code source-binds slot-zero key literal `0x6f707420` (`opt `)
  and the distinct Voice FX slot-one companion literal `0xc9` at `+0x5e84`.
  The key table layout does not make the latter a selected slot.
- The compare at `0x53326` sends only a match to `r7 = r6`. The dynamic
  selection index remains unresolved: this does not establish `r7 == 1`,
  component 201, top-level apply `r1` provenance, parser/default semantics,
  `godv` linkage, executable placement, or a firmware implementation.
- TDD RED was the missing report key. The focused hardware-free contract
  passed 1/1 in 7.441 seconds after the minimal verifier; the firmware-static
  module passed 25/25 in 7.745 seconds. The complete hardware-free suite
  passed 170 tests with one expected local-artifact skip in 237.283 seconds.
  The only warning was the pre-existing temporary-WAV `ResourceWarning` at
  `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. Continue only under a separate exact static scope that
can identify the branch-control argument entering `0x531e0`, or prove that its
direct caller does not materialize it. Do not use the key-table mechanics to
invent parser semantics, record ordering, a Voice FX selection, or a firmware
image.
