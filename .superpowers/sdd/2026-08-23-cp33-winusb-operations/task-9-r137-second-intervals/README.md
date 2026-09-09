# Task 9 R137 second-ordinal retained-allocation evidence

This is an additive, offline, hardware-free replay package. It does not alter
the frozen R136 candidate, its 54-file evidence bundle, any live test or support
file, or any production source. The four cases are copied fixtures that target
only operation ordinal two, closing the evidence gap recorded by R137.

Run all cases from any directory with:

```text
sh .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r137-second-intervals/replay.sh
```

Each case stores the exact contract, binding support, production copies,
mutation diff, compiler log/exit, and complete execution log/exit used for the
recorded result. Successful compiler logs are intentionally empty. The replay
script recompiles only the copied fixtures into a validated `mktemp` directory,
runs `--control-descriptor`, checks the declared failure counts and markers,
and compares each control/corrected pair after normalizing source line numbers.

## Cases

| Case | Boundary | Required result |
| --- | --- | --- |
| `second-admission/r135-control` | Hookless R135 control; helper replacement pair is allocated during admission two. | compile 0, feature run 1, exactly 203 baseline failures |
| `second-admission/r136` | The same second-admission helper route under the unchanged R136 retained hook. | compile 0, feature run 1, exactly 204 failures; the sole normalized delta is one retained-latch failure |
| `second-completion/hook-bypass` | Hook-bypass control; helper replacement pair is allocated during completion two. | compile 0, feature run 1, exactly 203 baseline failures |
| `second-completion/r136` | The same second-completion helper route under the unchanged R136 retained hook. | compile 0, feature run 1, exactly 204 failures; the sole normalized delta is one retained-latch failure |

All cases require zero direct-lens, helper-accounting, harness, crash, or
sanitizer markers. The fixtures assert two helper allocations and two frees,
preserve the original four admitted allocations and 4/4 pairwise retirement
journal, and preserve the declared request outcomes. Pairwise normalized log
comparison proves that enabling the unchanged R136 hook adds only the intended
`control_retained_allocation_end` witness.

`manifest.sha256` seals every package file except itself. Task 9 production
remains frozen until two independent reviews accept both the unchanged R136
head and this sealed additive package.
