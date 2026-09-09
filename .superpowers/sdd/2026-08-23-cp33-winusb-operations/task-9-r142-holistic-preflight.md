# Task 9 R142 holistic preauthorization review

Timestamp: 2026-08-25

## Verdict

`REQUEST CHANGES`

Critical findings: none.

Important findings: one.

Material Minor findings: none.

## Finding: exact-success status assertion is self-fulfilling

`reset_control()` zeroes the complete URB, and `USBD_STATUS_SUCCESS` is zero.
R142 therefore enters each exact positive with status already equal to the
expected postcondition. `expect_exact_range_success()` checks success afterward
but never seeds a non-success sentinel first.

A production mutant that omits `header->Status = USBD_STATUS_SUCCESS` from
`complete_io24_clock_source_range()` passes all three exact positives: payload,
length, tail, backend state, and `DriverContext` are correct while the fixture's
preexisting zero status satisfies the assertion. A caller entering with
`USBD_STATUS_NOT_ACCESSED` would instead receive `STATUS_SUCCESS` with stale URB
status.

## Required correction

Seed a defined non-success USBD status immediately before each exact production
call, then require the existing success result and postcondition. Add an
executable omit-status-write mutant.

## Strengths

The reviewer verified the 6/6 R142 manifest, live 2/2 R139 head, patch hash,
one-file dry-run, and byte-exact disposable candidate. The coherent
three-scope truth table, backend state comparisons currently exposed by the
fake, full caller-buffer preservation, bounds, status/length rejection, pending
routing, and retained witnesses are otherwise sound.

## Boundary

Read-only offline review. No workspace byte was changed. R142 was never
applied.
