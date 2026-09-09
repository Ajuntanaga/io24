# Task 9 R148 isolated proof

Timestamp: 2026-08-26T02:45:04-07:00

## Result

Controller preflight is PASS for independent preauthorization review. R148 is
not applied.

## Exact identities

```text
23333adc2918a72e2f1b32c53713533620f1be782373d1fcd389f4c598f2d08a  direct patch
56a7aace5141dff885e4859659cc1e729031deeba76e371cbbcc1b64ebdf7cf5  candidate lower contract
bd76d84e99227549eb587317971c33707457b56d93de3a90e1e5672b509bab15  candidate fake
ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1  restored production
561da904b991e9fcf41c55f1c95230f7a8f90d5e24c228069e9f606b22dea4a1  isolated evidence archive
```

## Executable gates

- focused baseline and final: exit 0, `completions=1 failures=0`;
- retained baseline and final: exit 0, `completions=3 failures=0`;
- reconstructed focused candidate: exit 0, `failures=0`;
- rows 1-28: fake marker, exit 1, nonzero feature failures;
- row 29: retained `test_descriptor_backed_pipe_lookup` failures, normal lower
  execution summary, exit 1, 96 failures, no fake pass marker and no harness or
  crash substitution;
- 29/29 log/exit pairs exist and all 29 logs have unique hashes; and
- usage, loader, symbol, and unsupported-mode probes remain exit 2.

## Structural gates

- 32 compiled fake exports and 33 source witness references;
- 32/32 first compiled `counts` accesses use the global witness offset;
- three immediate dedicated increments and compiled offsets `0x44`, `0x48`,
  and `0x4c`;
- identical normalized count and record layouts with complete-object resets;
- executable mutable configuration-view poison/refresh probe passes;
- twelve-hunk, two-file direct patch reconstructs both candidate hashes;
- bounded two-file delta remains contained to the test harness; and
- live upper, lower, fake, and production hashes remain frozen exactly.

The pointer-safe comparator returns before deep comparison whenever the live
pipe-table pointer differs from the captured pointer. Row 26 proves a null
replacement is an assertion RED rather than a dereference crash; row 28 proves
same-pointer deep mutation is observed. Rows 25 and 27 prove the formerly
partial scope and null-buffer fixtures now detect exact handle corruption.

No live application or device-facing action occurred.
