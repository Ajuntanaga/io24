# Task 9 R141 targeted preauthorization review

Timestamp: 2026-08-25

## Verdict

`REQUEST CHANGES`

Critical findings: none.

Important findings: one.

Material Minor findings: none.

## Finding

`expect_control_generic_no_range()` does not prove that the caller buffer is
unchanged before natural completion. It only proves that the complete captured
50-byte RANGE answer is not present. Production can therefore copy the first
49 captured bytes into the caller buffer after submitting the generic transfer,
leave the final byte different, and still satisfy R141's `memcmp(...) != 0`
assertion.

The reviewer reproduced that counterexample in a disposable production copy,
conditioned on the function/in-scope direction-negative cell. The actual lower
wrapper compiled and executed the mutant at exit 0 with `failures=0` against
the proposed R141 candidate. This is an executable false green, not a source
scan.

## Required correction

Snapshot the complete caller storage before production submission and require
it to remain byte-for-byte unchanged until the pending generic transfer is
discarded or completed. Preserve the full scope matrix and the existing pending
backend assertions.

## Boundary

Read-only, offline preauthorization review. R141 was never applied. No live
test, production, support, wrapper, prior evidence, Wine/prefix, USB/device,
driver build/staging, network, firmware, preset/effect, or hardware path was
changed or invoked.
