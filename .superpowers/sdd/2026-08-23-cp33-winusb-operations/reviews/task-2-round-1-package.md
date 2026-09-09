# Task 2 fix round 1 scoped re-review package

- Task brief: `../task-2-brief.md`.
- Initial review: `task-2-review-round-0.md`.
- Implementer report with round-1 evidence: `../task-2-report.md`.
- Fix base: `task-2-head`.
- Fix head: `task-2-round-1-head`.
- Fix diff: `task-2-round-1.diff` (419 lines).
- Fix-head manifest: `task-2-round-1-head.sha256` (11 entries).
- Fix-head manifest-file SHA-256:
  `63e1af3f913a2f38a87075623d4dd94e3805b87f91e01cef76a2a1f1d5d2fede`.
- Fix-diff SHA-256:
  `11daf7636ddabb29b55370bfe9d79ee8199366a68f03904611f50acc5abd1bc7`.

## Findings under re-review

1. The surface wrapper classified some unavailable/broken tools, unreadable
   required inputs, missing standard headers, and abnormal compiler failures as
   feature exit 1 instead of harness exit 2.
2. Compatible-type `_Generic` assertions could not distinguish the required
   `UINT*` declaration tokens from forbidden compatible aliases such as
   `ULONG`.

Verdict each finding as ADDRESSED or NOT ADDRESSED. Also flag only new Critical
or Important breakage introduced by the 419-line fix diff. The two initial
Minor observations are ledgered for the final review and are not open findings
in this round.

## Fresh controller verification

```text
16/16 focused checks classified correctly
normal surface-only: 0
historical surface RED, current public RED, policy RED, function RED: 1
retained CP32 checks: 3/3 at 0
missing cc, broken cc, broken grep, broken awk: 2 with HARNESS
abnormal candidate compiler: 2 with HARNESS
non-regular and unreadable required inputs: 2 with HARNESS
compatible ULONG alias mutation: 1 with FEATURE and no HARNESS
task-02-abi.sha256: 4/4 OK
production patch SHA-256 unchanged: 049afb59966dd679dab6270b99ee5437b9a04775319a3d86c33d6f71ea14fc82
production delta remains exactly five authorized paths
controller_failures=0
```

Review is read-only. Do not rerun the full suite, edit files, use Git, run
Wine, touch a prefix/device/sysfs USB path, build/stage/select/load a driver,
start applications, install tools, perform a physical operation, or retry
CP24.
