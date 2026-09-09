# CP34 structured-state record-prefix gate - progress

Timestamp: 2026-09-05T18:16:19-07:00
Status: locally sealed, offline-only static evidence; independent review is
still open.

## Resume seal repair

The interrupted session had created `CHECKPOINT.sha256` as a zero-byte file
after all source, test, and documentation changes. Fresh reproduction passed
the focused contract 1/1 in 16.609 seconds, the firmware-static module 45/45 in
18.427 seconds, and the complete hardware-free suite 224 tests with one
expected skip in 158.624 seconds, exit 0. The checkpoint was rebuilt from the
exact current files and verified 6/6.

## Recovery and TDD

The interrupted run contained only `SCOPE.md` in its task-local directory, but
the live test and analyzer files had an unsealed partial addition. The test file
predated the analyzer file by about four milliseconds; no prior RED transcript
or checkpoint existed, so this run does not claim that earlier execution.

The recovered test first failed because it compared the complete 850-byte
embedded archive with a reconstructed JSON record. That was outside this
scope's four-byte comparison and failed before exercising the new analyzer.
The test was narrowed to independently require the literal prefix on both
inputs. It then produced the intended RED: the analyzer report lacked
`structured_state_record_prefix_gate_boundary`. Minimal source-bound
implementation made that focused contract pass.

## Source-bound result

- `0x531f6` constructs the stack record-stream wrapper at `sp+0x60` with its
  byte-reverse flag set to zero; `0x531fa..0x53202` installs specialized vtable
  `0x66b54` and stores the incoming stream at wrapper offset `+0x8`.
- The specialized slot targets `0x2cd20`, which forwards to the underlying
  stream's vtable slot `+0x8`. Reader `0x2ce10` requests exactly four bytes.
  Because the wrapper flag is zero, its `rev` path is skipped.
- `0x5320e` loads the native four-byte word and `0x53212` compares it with
  integer `2`. Only the equal branch at `0x53216` reaches `0x53222`, before the
  component-selector gates.
- The retained factory Slap Echo archive at raw `0x6b1c8` and the existing pure
  `MemP/Stat` encoder both begin with bytes `7b690b70`. Read natively without
  reversal, that is `0x700b697b`, not `2`.
- Result:
  `STRUCTURED_STATE_PREFIX_GATE_SOURCE_BOUND_RAW_FACTORY_ARCHIVE_NOT_DIRECTLY_ELIGIBLE`.

The raw archive therefore cannot be passed unchanged from byte zero into this
entry and satisfy the gate. No edge in this bounded scope proves whether the
storage/recall path strips framing, advances the stream, prepends a type word,
or otherwise transforms the record. Physical storage, stored-record equality,
the selected component index, Voice FX activation, and audible processing all
remain unresolved.

## Verification

- First recovered-test failure: wrong full-record premise, 1 failure in 0.007s.
- Correct contract RED: missing report key, 1 failure in 16.060s.
- Focused GREEN: 1/1 in 16.853s.
- Firmware-static module: 45/45 in 18.537s.
- Complete hardware-free suite: 224 tests passed, one expected historical-
  artifact skip, 233.126s, exit 0.
- The complete run's only diagnostic was the pre-existing unclosed-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.

## Safety and next boundary

No firmware image was built, modified, emitted, staged, signed, uploaded, or
executed. No USB/device, ALSA, preset/effect, Wine, network, reset, DFU, install,
or REAPER action occurred. Host battery was 86 percent and charging at resume.

The next safe scope is another named offline/static unit that traces the
incoming record stream or cursor at the `0x42266` handoff far enough to identify
the first word actually presented to `0x531e0`. It must preserve transformation,
physical storage, component selection, parser semantics, image placement, and
all hardware conclusions as unresolved until separately proved.
