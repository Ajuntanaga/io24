# CP33 Task 9 R132 successor candidate — independent review request

## Decision requested

Review the frozen two-file R132 successor as RED evidence only. Return `PASS`
only if there is no Critical, Important, or material Minor correctness,
false-green, concurrency, ownership, cleanup, or scope issue. Otherwise report
each finding with severity, exact file and line, a concrete failure schedule or
counterexample, and the smallest required correction.

This is not a Task-9 completion review. Every production path remains frozen;
passing this review can only reopen the later production-correction gate.

## Authority and exact candidate

- Controller authority: R132 at the end of `task-9-report.md` and row R132 in
  `progress.md`.
- Bounded implementation contract: `task-9-r132-brief.md`.
- Plan/spec: Task 9 in
  `docs/superpowers/plans/2026-08-23-cp33-winusb-operations.md` and the
  control/descriptor plus transfer-ownership sections of the companion design
  spec.
- Immutable predecessor: `task-9-r132-base.sha256`, 2/2 verified, manifest
  SHA-256 `1f465399f426409b8c0963d09962d605e3edd7c8d162e50061f69e3920dae162`.
- Frozen candidate: `task-9-r132-head.sha256`, 2/2 verified, manifest SHA-256
  `2bf2c60c9f0c250051c09ddb6f1e9eb49ba6f149562360cdab585b374fcd0cc1`.
- Exact base-to-head patch: `task-9-r132.diff`, 703 lines, SHA-256
  `906270b295d0776cd4ac0722f79ca323ac2e4a34f90a058d3bdf2213cd23e977`.
- Live files were byte-equal to the frozen candidate at controller freeze.
- The other fourteen Task-9 production/support/wrapper paths verify under
  `task-9-r132-frozen.sha256`, whose SHA-256 is
  `343e2929b6f03cd9af0b2f957e2edfbfef4dc3fd0c86126906c75c6882d08a53`.
- Implementer evidence: `task-9-r132-implementer-report.md`, SHA-256
  `a7ffe61fa32d2516991cb7b48717e60c3b60f248b2e401dc9988fc8138297225`.

The workspace is intentionally non-Git. Task-local snapshots, manifests, and
the exact patch substitute for commits and SHAs. Review the frozen head files,
not a later mutable workspace state.

## Controller replay

Generated outputs verify 12/12 under `task-9-r132-controller-logs.sha256`,
manifest SHA-256
`ce14f287a2a31270c30c8b9ec0c791e3b5afe8673dc41c3b0637715fe1aff3bb`.

- Function focused: exit 1, 35 dispatches, 29 mode IOCTLs, 203 feature
  failures, zero harness/crash markers.
- Function lifecycle: exit 0, zero failures.
- Actual-lower focused: exit 1, exactly 12 expected cross-interface permit
  failures, zero harness/crash markers.
- Actual-lower retained `--red`: exit 0.
- Manual function ASan/UBSan/alignment compile: exit 0; execution exit 1 with
  the same 203 failures and zero sanitizer or harness markers.
- BAT0 was 100 and Full before both controller verification phases.

The focused exits are intentional genuine feature RED against frozen
production. They are valid only if the added assertions reach actual production
through the fake WDM/lower boundary and cannot be satisfied by the named
defects.

## Required review conclusions

For `winusb_function_io_contract.c`, verify all accepted R131 evidence remains
sound and that the successor specifically proves:

1. two simultaneous same-interface pending original IRPs, with alternate
   selection still blocked after only one completion and permitted only after
   the second;
2. endpoint-recipient lookup after acquisition of the exact session mutex,
   using a real selected pipe map and a safe post-lock mutation schedule;
3. terminal handling of create/join failure before any worker-owned read;
4. correct FIFO completion identity, per-request record/URB/file-reference
   retirement, and no assertion redefinition that hides existing defects.

For `wineusb_winusb_busif_contract.c`, verify:

1. valid root-5 and interface-6 children are queued through actual production
   in both orders, with a conflicting later entry decisive;
2. every busy SELECT preserves exact prior order/membership and never queues
   itself, while every permitted pending SELECT appears exactly once after all
   prior entries before local retirement;
3. the one-shot conflict exists only while the exact `wineusb_cs` is held and
   catches a pre-lock or unlocked classifier behaviorally;
4. cleanup removes only fixture-owned entries and makes no Tasks 11-13
   cancellation, cleanup, teardown, or removal claim.

Across both files, look actively for false-green mutants, unsafe failure-path
continuation, shared-state races, assertion coupling, bounded-list corruption,
use-after-scope, hidden cleanup that masks ownership defects, and any production
or scope drift. Source inspection can support review but cannot replace the
executable real-boundary evidence.

## Safety

Review is read-only and offline. Do not edit files, initialize Git, run Wine,
touch any prefix, access USB/sysfs device paths, stage/build/select a Wine
candidate, issue a physical transfer, use firmware, or access the network.
