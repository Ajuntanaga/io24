# CP34 runtime-storage and placement — progress checkpoint

Saved: 2026-09-01T02:01:23-07:00
Status: active, offline-only static analysis; image emission and all hardware
actions remain blocked.

## Completed since the prior handoff

- Revalidated the complete UC 4.7.2 io24 package in memory from the retained
  local `dspusbdevice.dll`: package SHA-256
  `790f668608448b7c9f244c360ad72e3c51f71b4e8a3d828eab0e08cd03b35de1`;
  application SHA-256
  `65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.
- Hardened `re/cp34_lane_control_firmware_static.py` so its proposed
  parent-owned sidecar is checked against decoded bytes, not merely reported
  as offsets. The firmware embeds the parent at `device+0x11e0`, starts the
  next sibling at `device+0x3a70`, and therefore bounds the parent at
  `0x2890` bytes. The stock constructor and reset each zero the existing byte
  at `+0x2884`; the proposed sidecar occupies only `+0x2885..+0x288f`.
- Corrected a false placement lead: raw `0x10d948..0x10d9e3` is 156 zero
  bytes, not an all-FF code cave. Only `0x10d9e4..0x10da3f` is all FF (92
  bytes), and it remains `UNPROVEN_NOT_EXECUTABLE_HOME`. The 36-byte ITCM FF
  span remains trampoline-only.
- Replaced the unverified model-5 label with a decoded selector proof: model
  IDs 0 through 5 remain stock-dispatchable and model 5 is not reclaimable.

## Verification

- Focused static analyzer contract: `12` tests, exit `0`.
- Broad hardware-free suite: `157` tests in `132.626s`, exit `0`, one expected
  skipped local-artifact test. It emitted the pre-existing temporary-WAV
  `ResourceWarning` from `re/cp34_current_slot_survey.py:260`.

## Current boundary

This checkpoint proves the storage layout and rejects two unsafe placement
shortcuts. It does not recover a structured-`Stat` parser interception or a
safe executable extension-body home. The correct current conclusion is
`NO_SAFE_HOME`; no patch bytes, modified image, extraction output, staging,
DFU, USB, audio, Wine, network, or live device action occurred.

## Next safe work

1. Keep investigating a source-bound parser interception and executable home
   only with the local pinned artifact in memory.
2. If either remains unresolved, close this pass with that evidence rather
   than inventing a code cave or repurposing live state.
3. Refresh this file and the task-root `RESUME.md` after each bounded evidence
   or verification stage, before starting another long-running action.

## 2026-09-01T01:39:02-07:00 — recovery mirror and bounded recheck

- Re-read the pinned application in memory only and independently rechecked
  the already recovered structured-state entry: primary Voice FX vtable raw
  `0x10c6e4 -> 0x5545c`; secondary state-interface vtable raw
  `0x10c704 -> 0x555b8`; the adjustor is `sub.w r0, r0, #4` followed by a
  branch to `0x5545c`.
- This establishes a top-level structured-state *entry* but does not establish
  optional-field lookup, default initialization, or an executable extension
  body. Keep `parser_status` unresolved and `extension_body=NO_SAFE_HOME`.
- Created `OBSIDIAN.md` alongside this progress record as a concise dashboard
  mirror. The project root `RESUME.md`, this file, and `CHECKPOINT.sha256`
  remain authoritative for recovery; the vault copy is deliberately secondary.

## Checkpoint cadence

1. Before a long static sweep or full-suite test, verify `CHECKPOINT.sha256`,
   then record the exact planned bounded action here.
2. Immediately after a code change, evidence result, or test result, update
   this file and the task-root `RESUME.md`, then refresh the manifest.
3. Mirror the current summary to `OBSIDIAN.md` and the Obsidian vault note.
4. On resume, read this file and root `RESUME.md` first, verify the manifest,
   then perform only the recorded next safe action.

## 2026-09-01T01:40:19-07:00 — Obsidian vault mirror verified

- Direct-Markdown mirror created at
  `Documents/Obsidian/ResearchOS/Projects/PreSonus Revelator io24 — CP34 custom-firmware recovery.md`.
- Its SHA-256 equals the task-local `OBSIDIAN.md`:
  `010a8e040848e5bd25d8803a770c5168214fa77094e3bb6fcca59d870d9fc683`.
- Obsidian CLI remains unavailable because the GUI app is not running. This is
  not a blocker: direct Markdown is the intended dashboard path for this note.

## 2026-09-01T01:42:53-07:00 — state-apply entry contract

- TDD RED: added the live pinned-image contract for both Voice FX vtable paths;
  it failed with the expected missing `parser_patch.state_apply_entry` key.
- TDD GREEN: the static analyzer now verifies raw vtable slots
  `0x10c6e4 -> 0x5545c` and `0x10c704 -> 0x555b8`, decodes the adjustor as
  `sub.w r0, r0, #4`, and verifies its immediate branch returns to `0x5545c`.
- Focused hardware-free result: 13 tests, exit 0.
- Report status is now `TOP_LEVEL_STATE_APPLY_SOURCE_BOUND; OPTIONAL_FIELD_LOOKUP_UNRESOLVED`.
  It still does not identify code that reads `wet_ch1`, `wet_ch2`,
  `bypass_ch1`, or `bypass_ch2`, initializes their defaults, or supplies an
  executable extension-body home.

## Next bounded action

Run the hardware-free full suite from this clean checkpoint. Then save the
exact result before any further static analysis. No device, firmware image,
Wine, or network action is part of that verification.

## 2026-09-01T01:46:04-07:00 — full regression verification

- Full hardware-free suite: 158 tests passed, one expected skipped
  local-artifact test, exit 0, 132.191 seconds.
- It emitted the same pre-existing temporary-WAV `ResourceWarning` at
  `re/cp34_current_slot_survey.py:260`; no new warning or failure occurred.
- The run performed no device, USB, audio, Wine, network, firmware-image, or
  other live action.

## Next bounded action

Continue static-only recovery of how the structured-state loader reaches model
0's nested `godv` state. Preserve the distinction between the now source-bound
top-level entry and the still-unresolved optional-field lookup/default logic.
Save a new checkpoint before any subsequent long sweep or test run.

## 2026-09-01T01:49:59-07:00 — model-zero state-apply ABI contract

- TDD RED: the new pinned-image model-zero route contract failed with the
  expected missing `parser_patch.model_zero_state_apply` key.
- TDD GREEN: the parent indirect call at raw `0x5559a` is now tied to the
  model's secondary interface (`model+4`, vtable slot `+4`). Model-0
  construction binds that interface to static vtable `0x10c8d0`; its slot at
  `0x10c8d4` points to adjustor `0x548dc`, which subtracts four from `this`
  then branches to `0x546ec`.
- Focused hardware-free result: 14 tests, exit 0.
- This is a model-state apply route, not proof that `0x546ec` decodes the
  `godv` tagged payload or any of the new optional fields. Parser status stays
  `OPTIONAL_FIELD_LOOKUP_UNRESOLVED`; placement stays `NO_SAFE_HOME`.

## Next bounded action

Run the full hardware-free suite from this checkpoint. Afterward, reconcile the
model-zero state-apply route with the separately source-bound stock `godv`
event handler, without assuming they are the same parser.

## 2026-09-01T01:53:36-07:00 — model-zero full regression verification

- Full hardware-free suite: 159 tests passed, one expected skipped
  local-artifact test, exit 0, 148.614 seconds.
- The same pre-existing temporary-WAV `ResourceWarning` at
  `re/cp34_current_slot_survey.py:260` was the only warning.
- No device, USB, audio, Wine, network, firmware-image, or other live action
  occurred.

## Next bounded action

Perform a short static-only trace of the stock `godv` event handler's tag
comparison and its relationship, if any, to the model-zero state-apply target
`0x546ec`. Do not equate a shared model object with a shared parser without
decoded control flow evidence.

## 2026-09-01T01:55:28-07:00 — stock `godv` callback boundary

- TDD RED: the pinned-image report lacked a `stock_godv_tagged_handler` entry.
- TDD GREEN: model-0 primary vtable `0x10c890 -> 0x5bb6c`, tag literal
  `0x5bd38 = godv`, comparison at `0x5bc06`, five stock state stores at
  `+0x340/+0x344/+0x348/+0x34c/+0x350`, and the derived mix at `+0x358` are
  now checked against the pinned image.
- Focused hardware-free result: 15 tests, exit 0.
- `0x5bb6c` and model state-apply target `0x546ec` are distinct entries. The
  evidence does not claim an ordering or call relationship between them; that
  relationship remains `UNRESOLVED`.

## Next bounded action

Run the full hardware-free suite. Then either identify a source-bound bridge
between the two entries or document the bridge as unresolved; do not broaden a
tagged callback into a structured-`Stat` parser without direct evidence.

## 2026-09-01T01:59:11-07:00 — tagged-callback full regression verification

- Full hardware-free suite: 160 tests passed, one expected skipped
  local-artifact test, exit 0, 151.034 seconds.
- The existing temporary-WAV `ResourceWarning` at
  `re/cp34_current_slot_survey.py:260` was unchanged and was the only warning.
- No device, USB, audio, Wine, network, firmware-image, or other live action
  occurred.

## Next bounded action

Use only source-bound model-0 state-apply and tagged-handler code slices to
check for immediate `B`/`BL` edges between the two paths. A lack of such an
edge may be reported only as a narrow direct-edge result; it must not be
mistaken for a whole-program no-relationship proof.

## 2026-09-01T02:01:23-07:00 — bounded direct-edge contract

- TDD RED: the report lacked direct-edge evidence bounded to the two validated
  function slices.
- TDD GREEN: `0x546ec..0x548cb` has no immediate edge into
  `0x5bb6c..0x5bd2f`, and the converse has none either. The state-apply slice
  has six register-indirect `blx` sites at `0x54730`, `0x54776`, `0x54788`,
  `0x5479c`, `0x5480e`, and `0x548b4`; the tagged-handler slice has none.
- Focused hardware-free result: 16 tests, exit 0.
- The conclusion is explicitly
  `NO_IMMEDIATE_CROSS_EDGE_IN_VALIDATED_SLICES`, with
  `INDIRECT_OR_INTERPROCEDURAL_RELATIONSHIP_UNRESOLVED` retained as the
  boundary.

## Next bounded action

Run the full hardware-free suite. If further parser work continues, resolve at
most one named indirect call from the state-apply slice with source-bound
vtable evidence; otherwise close this static pass with the unresolved bridge.

## 2026-09-01T02:06:42-07:00 — direct-edge full regression verification

- Full hardware-free suite: 161 tests passed, one expected skipped
  local-artifact test, exit 0, 153.314 seconds.
- The only warning was the same pre-existing temporary-WAV `ResourceWarning`
  at `re/cp34_current_slot_survey.py:260`.
- The run performed no device, USB, audio, Wine, network, firmware-image, or
  other live action.

## Next bounded action

Resolve at most the state-apply indirect call at raw `0x54730`, starting from
the exact receiver/vtable loads (`r0` from stack, then `[r0]`, then `[vtable+8]`).
Do not assign parser semantics or a `godv` relationship unless the dynamic
target is source-bound. If it remains dynamic, record that boundary and stop.

## 2026-09-01T02:10:15-07:00 — state-apply indirect-call receiver boundary

- TDD RED: the new pinned-image contract failed with the expected missing
  `parser_patch.state_apply_indirect_call_0x54730` key.
- TDD GREEN: the top-level state receiver is captured at `0x55462`, forwarded
  to model-0 at `0x55592`, preserved through `0x546f0/0x54708/0x54726`, then
  dispatched through the caller-supplied receiver's vtable slot `+8` at
  `0x5472c/0x5472e/0x54730`. The call receives `model+0x340` in `r1` and its
  return is compared with raw immediate `0x14` at `0x54732`.
- Focused hardware-free result: 17 tests, exit 0.
- The receiver provenance is source-bound, but no concrete vtable or target is
  static in this evidence. Parser semantics and any relationship to tagged
  `godv` remain `UNRESOLVED`.

## Next bounded action

Run the full hardware-free suite from this saved checkpoint. Then retain this
dynamic-target boundary and close this static pass; do not trace a second
indirect call or invent a parser hook without a new bounded scope.

## 2026-09-01T02:14:16-07:00 — static-pass full regression verification

- Full hardware-free suite: 162 tests passed, one expected skipped
  local-artifact test, exit 0, 163.340 seconds.
- The only warning was the existing temporary-WAV `ResourceWarning` at
  `re/cp34_current_slot_survey.py:260`; it is unrelated to this change.
- No device, USB, audio, Wine, network, firmware-image, or other live action
  occurred.

## Next safe action

This bounded static pass is sealed. Preserve
`CALLER_SUPPLIED_RECEIVER_VTABLE_TARGET_UNRESOLVED` and do not trace another
indirect call, emit an image, or infer a parser hook without a new bounded
scope and its own saved checkpoint.
