# Task 9 R134 successor review request

## Authority and decision boundary

Review R134 at the end of `task-9-report.md` and the exact rejected review in
`task-9-r133-review.md`.  Production remains frozen.  This review may accept
only the Task-9 RED evidence needed for a later, separately scoped production
correction.  It cannot claim Task 9, CP33, firmware, preset/effect capture, or
hardware behavior complete.

## Immutable candidate and lineage

- R133 rejected candidate: `task-9-r133-head.sha256`, manifest SHA-256
  `2d1ad6b0da1cf9d39b059e13e4a9953c83b4fcbd79a3b6df26f0825a56228ba1`.
- R134 successor: `task-9-r134-head.sha256`, 2/2, manifest SHA-256
  `7af721f59ec7d9b50ae47ebfee6c18aa8f9abcc1b72ce88490abcca6c4c56fd4`.
- Exact R133-to-R134 function-only delta: `task-9-r134.diff`, 74 lines,
  SHA-256 `39187e38e5a98c2c0f2b0c77ab9428e03bdfe38a2c75b80546f8bfc39ee43e5f`.
- R134 function SHA-256:
  `ad139419c758fe5b9aacd9c612bbb865f3baf96edc66aed42071f32df8b531f2`.
- Frozen lower-contract SHA-256:
  `9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348`.
- Frozen fourteen-path manifest: `task-9-r132-frozen.sha256`.
- Implementer evidence: `task-9-r134-implementer-report.md`, SHA-256
  `5013406e3602796a2a0ef623f3e8d064fb5c4a7d9d24827e82a43af7b0f01a33`.
- Controller logs: `task-9-r134-controller-logs.sha256`, 12/12, manifest
  SHA-256 `6bda954a9bf793780ea31746c4417da8d6ae9c6d77618a99b918993c3836a092`.

Verify each manifest and diff and require the two live contracts to equal the
R134 snapshot before relying on them.

## Fresh controller replay

- Function focused: exit 1, 35 dispatches, 29 mode IOCTLs, exactly 203 named
  feature failures; no compiler/linker/harness/crash marker.
- Function lifecycle: exit 0, 12 dispatches, zero failures.
- Actual-lower focused: exit 1, exactly 12 named permit failures.
- Actual-lower retained: exit 0.
- Manual function ASan/UBSan/alignment: compile exit 0; focused exit 1 with the
  same 203 failures; zero sanitizer, leak, crash, or harness marker.

## Required adversarial review

The only R134 code change is an allocation-attempt observer independent of the
paused admission journal.  It is armed immediately before, and checked and
disarmed immediately after, each of the two exact
`complete_pending_task9_irp()` calls.  It is disarmed during the intervening
alternate-selection calls.  Reset clears it.

The implementer's bounded disposable recreation mutant allocated replacement
context/URB pairs at completion, copied and used the replacements, let
production free them, explicitly retired the four admission-journaled
originals in the expected pairwise order, and preserved outcomes, list state,
references, and global allocation balance.  Against immutable pre-observer
R133 it remained at 203 failures; against R134 it produced 204, with exactly
`control_completion_allocation_attempts == 0` added.  Both executions compiled
and reached the feature boundary without crash or harness failure.

Independently determine whether this closes the Important R133 false-green:
all completion-time allocation attempts, including failed ones and all
production allocation routes relevant to context/URB recreation, must be
observable; alternate allocations must remain excluded; the admission and
free journals, two distinct stored outcomes, exact pairwise retirement, and
all prior R132/R133 lower fixes must stay intact.  Hunt for false greens,
observer self-dependence, reset leakage, expectation weakening, mutant
confounding, unsafe cleanup, or a Tasks 11-13 ownership claim.

Return `PASS` only with no Critical, Important, or material Minor finding.
Otherwise return `REQUEST CHANGES` with severity, exact file/line evidence,
the passing bad implementation, and the smallest correction.  Do not edit any
file.  Do not use a source-text scan as feature evidence.  No Wine, prefix,
USB/sysfs device path, driver/build/staging, network, firmware, preset/effect,
or live hardware action is authorized.
