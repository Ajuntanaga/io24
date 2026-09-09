# Task 9 R137 mandatory review

## Candidate and verified integrity

The accepted evidence is the unchanged 3/3 `task-9-r136-head.sha256`
candidate at manifest SHA-256
`f1f81159399034bf492f419c6e3fda61fadc2305251cd2833b9710ad0ec98298`,
the prior 54/54 R136 bundle at manifest SHA-256
`ca111ccab7208d44704bee1ab411e1d5c3d636c31bcd709abca4fea1e4aa4148`,
and the additive 56/56 R137 package at manifest SHA-256
`5d273ba5347f12783e227580da2c56d20f59c66b1d14769504d9342b842b4513`.

Both reviewers independently verified the immutable inputs and replayed the
additive package. The controller then reverified the three manifests, all
fourteen frozen paths, live R136 equality, and the replay. Admission two and
completion two each remained 203 failures with retained count zero in control
and 204 failures with retained count one in corrected R136, with exact
normalized comparisons and no direct, helper-accounting, or bad marker.

## Mandatory verdicts

Targeted review: PASS with no Critical, Important, or material Minor finding.

Holistic review: PASS with no Critical, Important, or material Minor finding.

Both reviews accepted ordinal-two arm placement, two-allocation/two-free helper
balance, the original 4/4 retirement journal, preserved outcomes, fair
hookless controls, replayability, immutable lineage, and the Tasks 11-13
boundary.

## Controller adjudication

Before their final verdicts, both reviewers independently examined a possible
ambiguity in the hook-bypass binding's local diff. The concern does not survive
the immutable-byte standard. The review request explicitly supplies the prior
54-file bundle; its `completion/bypass` case declares the hookless control.
The R137 binding is byte-identical to that sealed prior control and the R136
base at SHA-256
`dd9f1f86ffa6ce35e00715fbead4f971678caa6890faa20d3b97c657b36eb25a`.
The local diff records the new second-completion mutation and the complete
inherited binding is separately copied and sealed. No bad candidate can omit
the second interval or alter the control while keeping the immutable manifests
and the required 203/204 replay results.

## R138 decision

Accept the unchanged R136 candidate plus the additive R137 package. Preserve
both bundles, every test/support/wrapper/RANGE path, and all prior evidence
byte-for-byte.

The review gate reopens only the R125 Task-9 production boundary as already
widened by R130 to include `winusb.sys/session.c`, solely for the concrete
R129-R131 corrections:

- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/transfer.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/Makefile.in`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h`
- `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/wineusb.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb/main.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb/io.c`

Implementation must retain the R125 original-IRP ownership rule, implement
per-interface accounting and the locked conservative lower target scan, reuse
the canonical RANGE helper, restore `next_handle_token` to base seed 1, and
add no Tasks 11-13 lifetime behavior. Focused, retained, sanitizer, mutant,
freeze, and fresh independent production-review gates remain mandatory before
Task 9 can seal.

This review records the unlock only. No production edit or Task-9 completion
claim is made here.
