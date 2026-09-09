# Task 3 fix round 1 scoped re-review package

- Task brief: `../task-3-brief.md`.
- Task review rubric: `../task-3-review-rubric.md`.
- Initial review: `task-3-review-round-0.md`.
- Implementer report with round-1 evidence: `../task-3-report.md`.
- Controller rulings: `../progress.md` R8, R15, R17, R23, and R24.
- Frozen fix base: `task-3-round-1-base` (the reviewed initial head plus the
  unmodified newly authorized wrapper).
- Frozen fix head: `task-3-round-1-head`.
- Fix-base manifest: `task-3-round-1-base.sha256` (10 entries).
- Fix-head manifest: `task-3-round-1-head.sha256` (10 entries).
- Fix diff: `task-3-round-1.diff` (605 lines).
- Fix-head manifest-file SHA-256:
  `0fe92a26b7d5a547242efb36f1d1d79354153974ad6961afdf4c88fdfc854b51`.
- Fix-diff SHA-256:
  `9a44683b35287a96006cf914dee57682adcbc883c31b34fcfa079dfe273686c5`.

## Findings under re-review

1. Removal ownership was released before outstanding drain and final context
   destruction, allowing REMOVE to pass its event while file-owned state was
   still live.
2. The initial contracts called a synthetic speed helper instead of the real
   lower `wineusb.c` callback and did not exercise a nonzero-outstanding
   lifecycle schedule, so incorrect containment/mapping/output mutation and
   premature removal signaling could false-GREEN.
3. The retained binding fake replaced successful metadata-v1 behavior rather
   than preserving an explicit successful v1 regression alongside v2.
4. Retained session/alternate/policy/transfer modes called REMOVE with a live
   `FsContext`, relying on a permissive host wait fake to conceal ownership.

Verdict each initial finding as ADDRESSED or NOT ADDRESSED. Also flag only new
Critical or Important breakage introduced by the 605-line fix diff. R24
authorizes the bus wrapper solely to execute actual lower `wineusb.c` behavior
while retaining feature-versus-harness classification. Historical base/head
and initial review artifacts are immutable.

## Required mutation/race lens

- At the zero-outstanding wait boundary, `file_count` remains one and the
  device removal event remains nonsignaled; only after drain, unlink, and final
  file-owned frees may the last-owner transition signal REMOVE.
- The executed v2 speed callback must come from the actual included
  `wineusb.c` query routine. Check low/high mapping, enclosing-source
  containment, both device/source removed cases, null outputs, and unchanged
  output on every failure.
- Successful v1 fake/query behavior remains explicit and additive; production
  upper-FDO v2 behavior and the retained terminal CP32 pass remain intact.
- Every retained mode that creates a file performs matching cleanup and close
  before REMOVE. Later unimplemented IOCTL assertions may remain feature RED,
  but teardown must contribute no wait, ownership, allocation/free, or hidden
  harness failure.
- The final lifecycle checkpoint has exactly nine project paths: five
  production and four contracts including the wrapper, with no self-hash.

## Fresh controller verification

```text
actual-lower metadata bus-interface: exit 0, pass
function lifecycle: exit 0, failures=0
retained CP32 function binding: exit 0, unchanged terminal pass line
retained session/alternate/policy/transfer: intended later-feature exit 1,
  failures=4 in each mode; cleanup/close/remove adds no extra failure
task-03-lifecycle.sha256: exactly 9 entries, 9/9 OK, no self-hash
task-3-round-1-base.sha256: 10/10 snapshot entries OK
task-3-round-1-head.sha256: 10/10 snapshot entries OK
fix scope: main.c, four authorized contracts, and lifecycle seal differ;
  the other four production paths are byte-identical to the frozen fix base
working paths match the frozen fix head
controller_failures=0
```

Review is read-only. Do not rerun the full suite, edit files, use Git, run
Wine, touch a prefix/device/sysfs USB path, build/stage/select/load a driver,
start applications, install tools, perform a physical operation, or retry
CP24.
