# Task 1 fix round 5 scoped review package

- Task brief: `../task-1-brief.md`.
- Round-4 review finding: `task-1-review-round-4.md`.
- Implementer report with round-5 evidence: `../task-1-report.md`.
- Fix base label: `task-1-round-4-head`.
- Fix head label: `task-1-round-5-head`.
- Fix diff: `task-1-round-5.diff` (170 lines; full round-5 delta).
- Fix-head manifest: `task-1-round-5-head.sha256` (15 entries).
- Fix-head manifest-file SHA-256: `b919101918aea3a76ff90d4770dd4e4a2af27d194ea2e430da18fa876ba4cd49`.
- Fix-diff SHA-256: `9035f45f7ce4f80d8dbd4d792028e4584e14447389095f6fcf74d990d610b831`.

## Finding under verification

The round-4 focused `WinUsb_GetPipePolicy` caller supplied capacity 4 and
expected returned length 4. An implementation that copied the returned policy
value but omitted writing `*ValueLength` could therefore pass.

The re-review must determine whether round 5 now proves the complete returned
length path through the actual production API:

1. the focused caller supplies valid capacity 8 with independently guarded and
   sentinel-filled eight-byte storage;
2. the fake boundary receives only the typed request and returns exact actual
   length 4 plus value `0x13579bdf` through the typed response channel;
3. the caller observes `ValueLength == 4`, the exact value, unchanged tail
   bytes 4 through 7, and intact outer guards; and
4. the frozen vendor policy-8 call still supplies exact input capacity 4.

It must also check that every prior Task 1 correction remains preserved.

## Fresh controller verification

```text
aggregate feature REDs: 5/5 returned 1 with no HARNESS diagnostic
mode executions: 24/24 returned 1 with no HARNESS diagnostic
harness/usage/tool/input/read probes: 13/13 returned 2
CP32 seal: 72/72 OK
development clone diff status: 0
patch-check clone diff status: 0
Task 1 checkpoint: 11/11 OK
controller_failures=0
```

## Binding constraints

- The fake boundary must not receive or directly mutate the public caller's
  `ValueLength` pointer. Returned length and value must traverse the actual
  dlsym-resolved production API and typed IOCTL response.
- Input capacity 8 and returned actual length 4 must be separately asserted at
  both boundary and caller-visible layers. Tail sentinels and guards must make
  over-copy observable.
- Preserve the frozen vendor policy-8 input length 4 and its boundary-authored
  trace.
- Preserve typed requests, exact response propagation, mode-specific masks and
  IOCTLs, initialization-returned handles, real production execution, Python
  harness remapping, lower/cancel behavior, and feature-1 versus harness-2
  separation.
- CP32 and both CP33 production clones remain immutable throughout Task 1.
- Review is read-only. Never run Wine, touch a prefix/device/sysfs USB path,
  stage/select/load anything, start applications, perform physical USB
  operations, retry CP24, initialize Git, or mutate files.
