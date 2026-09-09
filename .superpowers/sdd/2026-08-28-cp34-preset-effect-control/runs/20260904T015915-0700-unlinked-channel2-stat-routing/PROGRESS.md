# CP34 unlinked Channel-2 Stat routing progress

Timestamp: 2026-09-04T02:11:16-07:00
Status: routing resolved and hardware-free checkpoint green; next live state
change gated.

## Result

The current device is unlinked (`flags=0x1a1`) with Channel 2 enabled on slot 3.
Pinned firmware proves that this exact state routes Channel-2 `Stat` slots 2/3
to the second channel strip, not the Voice FX table entry. This explains the
repeated dry custom Delay and factory Slap Echo recalls without treating the
result as proof of failed record storage.

Slot two is now source-bound through the two-instance channel-strip constructor,
its secondary vtable, adjustor, and five-key state table. It is not an unknown
dynamic target and does not contain component 201.

The linked positive-slot branch is also bounded. It invokes the normal indexed
component table first and the second channel strip second. Voice FX is present
in the first table, but the selected table index remains data-dependent. This
makes a linked trial discriminating but not guaranteed to produce Voice FX.

## TDD and verification

- The preflight test first failed because `flags_word` and `channel_linked` were
  absent. The implementation now reports the raw word and bit-12 decode; its
  module passes 4/4.
- The unlinked-dispatch test first failed with a missing report key, then bound
  the bit test, pair collapse, callee diversion, and Channel-2 slot-two route.
- The slot-two identity test first failed with a missing report key, then bound
  the constructor loop, vtable target, adjustor, and five channel-strip keys.
- The linked-positive test first failed with a missing report key, then bound
  the positive-slot gate and both handoffs. Its focused GREEN ran in 52.676s.
- The unlinked report was then made self-consistent with the slot-two result;
  its expectation failed before implementation and the two routing contracts
  passed together in 42.799s.
- The complete firmware-static module passes 44/44 in 53.332s.
- An earlier full discovery run reached its 420-second wrapper timeout while
  observed tests were green and one expected historical artifact was skipped.
  Because it did not finish, it remains `INCOMPLETE_TIMEOUT`, not PASS.
- The final longer hardware-free discovery run passed 205 tests with one
  expected historical-artifact skip in 482.698 seconds, exit 0. Its only
  diagnostic was the pre-existing unclosed-WAV `ResourceWarning` at
  `re/cp34_current_slot_survey.py:260`.

## Files changed

- `re/cp34_readonly_preflight.py`
- `tests/test_cp34_readonly_preflight.py`
- `re/cp34_lane_control_firmware_static.py`
- `tests/test_cp34_lane_control_firmware_static.py`
- `README.md`
- `PROTOCOL.md`
- task-local `RESUME.md` and `EVIDENCE.md`
- this checkpoint directory

## Predecessor reconciliation

The predecessor's `CHECKPOINT.sha256` was written at 00:39:42. Its aggregate
`RESULT.json` and `FACTORY-SLAP-ECHO-RESULT.json` were then updated at 00:46:51
to retain the later headphone-cause attestation and final fault-boundary text;
`RECALL-EDGE-RESULT.json` predates the manifest and still matches its recorded
hash. The older manifest is therefore intentionally stale for the two later
reports, not evidence that this checkpoint lost its predecessor. This new
manifest pins their current bytes without rewriting any predecessor file.

## Safety and next gate

No further device command followed the two read-only `JaSt` requests. No link,
Channel-1, output, routing, audio, firmware, Wine, network, or install action
occurred in this checkpoint.

The next useful live experiment is a temporary stereo-link enable followed by
a positive-slot Channel-2 recall and immediate audible observation. It is not
eligible under the retained instruction to leave Channel 1 untouched: linking
changes the channel relationship and the normal indexed application can affect
shared/first-path state. Full Channel-1 `Stat` content is not readable, so exact
restoration cannot be guaranteed. Proceed only after the user explicitly
accepts that limitation and lifts the Channel-1 boundary.
