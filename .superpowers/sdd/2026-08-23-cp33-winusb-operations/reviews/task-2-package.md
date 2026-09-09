# Task 2 scoped review package

- Task brief: `../task-2-brief.md`.
- Task review rubric: `../task-2-review-rubric.md`.
- Implementer report: `../task-2-report.md`.
- Controller rulings: `../progress.md` R7, R8, and R11 through R14.
- Base label: `task-2-base`.
- Head label: `task-2-head`.
- Base manifest: `task-2-base.sha256` (6 present-file entries; absence state
  is in `../task-2-base-state.txt`).
- Head manifest: `task-2-head.sha256` (11 entries).
- Full scoped diff: `task-2.diff` (1,227 lines).
- Head-manifest-file SHA-256:
  `c3657e9411d2af98f7e4cee162cf193cf16e19b25d83c12ffd34b589e72ec38d`.
- Diff SHA-256:
  `fbccc6019f223dff322e47298ff779a6146808da5ebe025daec851d45afab039`.

## Required review scope

Read the brief, rubric, report, and diff once. Return independent verdicts for
spec compliance and task quality. Review all production ABI declarations,
public headers, export signatures, test changes, and retained evidence in the
diff. R11's carried pointer non-alias assertion and R12's narrow wrapper mode
are part of this task. R13 fixes the production count at the five named paths;
R14 fixes the previously unnamed auxiliary record fields.

## Fresh controller verification

```text
surface-only: exit 0, no HARNESS
public default RED: exit 1, no HARNESS
public policy RED: exit 1, no HARNESS
function default RED: exit 1, no HARNESS
retained CP32 bus-interface/binding/INF checks: 3/3 exit 0
usage and invalid-mode probes: both exit 2
task-02-abi.sha256: 4/4 OK
task-02-abi.patch reproduction: byte-identical
patch dry-run against immutable CP32 source: exit 0
production source delta: exactly five authorized paths
controller_failures=0
```

The optional `-m32` capability probe reports unavailable on this host; no tool
installation is authorized or required.

## Safety and immutability

Review is read-only. Do not edit files, use or initialize Git, run Wine, touch
a Wine prefix, access a device or sysfs USB path, stage/select/load/build a
driver, start applications, perform a physical USB operation, install tools,
or retry CP24. CP32 and the CP33 patch-check source are immutable. Task 2 makes
no runtime or live-device completion claim.
