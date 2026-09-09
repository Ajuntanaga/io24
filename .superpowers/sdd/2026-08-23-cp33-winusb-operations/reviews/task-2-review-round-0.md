# Task 2 initial scoped review

## Spec compliance

Verdict: **FAIL**. The production declarations match the requested surface,
but R12's feature-1 versus harness-2 separation remains incomplete.

The reviewer could not verify test-first chronology or the absence of external
actions from the diff alone. The controller resolves those two warnings from
the task-local report, sealed pre-task snapshot, observed dispatch sequence,
exact ten-path changed-surface check, and current safety/tool history: the
test-only RED evidence preceded the five production deltas, and no forbidden
external action is present or authorized. These warnings do not join the fix
loop.

## Strengths

- Exact public constants, 8-byte setup packet, fourteen prototypes, fourteen
  `stdcall` exports, eight stubs, and `int64` control setup are present.
- Public installation and private-header exclusion are correct in the current
  source.
- The private ABI has exact sizes, IOCTLs, methods, and R14 field order.
- R11 records the internal byte-count pointer and asserts non-aliasing while
  preserving focused capacity 8 and vendor capacity 4.
- The four-entry evidence seal and exact five-path production patch are
  reproducible; retained CP32 checks pass.

## Important findings

1. `tests/winusb_user_api_contract.sh:43-50` maps `awk`, `grep`, native
   compiler, and `-m32` compiler/tool failures into feature exit 1. The wrapper
   also omits `include/Makefile.in` from its required-input preflight. A broken
   or missing compiler/tool, unreadable input, unavailable standard headers, or
   abnormal compiler termination can therefore masquerade as accepted RED.
   Add explicit tool/readability/baseline-compiler probes and distinguish tool
   failure from an actual surface-contract mismatch.
2. `tests/winusb_user_api_contract.c:14-15` uses `_Generic` compatible-type
   matching, which cannot distinguish required `UINT32` tokens from compatible
   forbidden aliases such as `ULONG`. Add an independent token-level schema or
   declaration allowlist that enforces the exact fixed-width typedef spellings
   for every private ABI member, and prove it rejects a disposable alias
   mutation.

## Deferred minors

- `tests/winusb_user_api_contract.sh:46` does not negatively assert that the
  private `wine/winusb.h` is absent from the public install list.
- `tests/winusb_user_api_contract.c:106-119` checks named IOCTL values but does
  not source-enforce exactly one definition each or reject an added
  `METHOD_NEITHER` definition. The current reviewed header is correct.

## Assessment

Task quality: **Needs fixes**. No Critical finding was reported; the two
Important false-GREEN risks enter fix round 1.
