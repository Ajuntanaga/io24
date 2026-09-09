# Task 8 test-first RED review — round 0

## Critical

None.

## Important

1. The function contract requires an invalid private GET shape to succeed.
   `output_length` remains zero at `tests/winusb_function_io_contract.c:1767`,
   yet GET expects success and 40 returned bytes at line 1797. This conflicts
   with the exact 40-byte buffered response boundary and would pressure
   production into accepting malformed GET requests. It also never validates
   the returned default value.

2. The public RED result is symbol-driven, not behavior-driven. When Get/Set
   symbols are absent, `tests/winusb_user_api_contract.c:861-869` runs real
   initialize/alternate/free but returns before any policy assertion. Thus the
   required policy assertions do not execute in the reported exit-1 run,
   contrary to the test-first RED acceptance rule.

3. The public contract has substantial false-GREEN paths. SET cases at
   `tests/winusb_user_api_contract.c:872-885` generally assert only the Boolean
   result, without binding exact request header, interface, PipeID, policy ID,
   value length/value, or single-submission behavior. The fake returns
   arbitrary GET data `0x13579bdf` at line 452, while the normal GET test at
   lines 879-881 never checks the required 4 MiB maximum. Short-GET guard words
   are neither initialized nor checked, and invalid post-alternate calls do not
   consistently assert value/length/guard and submission preservation. No
   GET/SET transport-failure case is exercised.

4. Major policy/state families are absent from both deltas. The compact
   function sequence at `tests/winusb_function_io_contract.c:1782-1808` checks
   selected statuses but not:

   - all authoritative defaults and direction/applicability combinations;
   - both supported values for IN allow-partial and RAW_IO;
   - every prohibited enabled setting;
   - undersized and oversized lengths;
   - successful state readback and failure non-mutation;
   - successful alternate target-only reset;
   - failed-alternate complete preservation;
   - unrelated interface/associated-handle preservation;
   - absence of lower transport calls after policy operations.

   The public sequence at `tests/winusb_user_api_contract.c:872-885` has the
   same state/reset/preservation omissions.

5. The required bounded negative source variants are absent. With only the two
   contract files changed, there is no evidence that plausible bypasses such as
   ignored arguments, constant defaults, storing prohibited values, global
   reset, rollback loss, or transport submission are rejected.

## Minor

None.

## Verdict

**TEST GAPS REMAIN.**

The function mode invokes the real production translation unit, and the
public mode reaches real initialize/alternate logic through the fake boundary,
but the current RED delta is not yet a complete or honest Task 8/R95 policy
contract.
