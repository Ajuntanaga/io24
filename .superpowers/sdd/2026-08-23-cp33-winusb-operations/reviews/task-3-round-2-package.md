# Task 3 fix round 2 scoped re-review package

- Task rubric: `../task-3-review-rubric.md`.
- Initial review: `task-3-review-round-0.md`.
- Round-1 review: `task-3-review-round-1.md`.
- Implementer report with round-2 evidence: `../task-3-report.md`.
- Fix base: `task-3-round-1-head`.
- Fix head: `task-3-round-2-head`.
- Fix diff: `task-3-round-2.diff` (46 lines).
- Fix-head manifest: `task-3-round-2-head.sha256` (10 entries).
- Fix-head manifest-file SHA-256:
  `01a3300d6e290a98807bbbae4a2c5d8200e27d03abee93bf628d2cbeb0c17f55`.
- Fix-diff SHA-256:
  `d19c0e3e1329d4dc6e948a14ef18f3909cbdf8cf7a073fef9462195f6f4ac160`.

## Sole finding under re-review

The actual lower callback contract lacked executable invalid-input cases for
`GetDeviceSpeed(valid_context, NULL)` and
`GetDeviceSpeed(NULL, &sentinel)`. The fix must call the actual callback
obtained through the included production `wineusb.c` v2 query, require
`STATUS_INVALID_PARAMETER`, preserve the sentinel on null context, and avoid
unrelated state/guard mutation.

Verdict this finding as ADDRESSED or NOT ADDRESSED. Flag only new Critical or
Important breakage introduced by the 46-line diff. All five production paths,
the wrapper, and the other two contract sources are frozen and byte-identical
to the reviewed round-1 head. The only changed functional source is the bus
contract; the lifecycle seal changes solely to record its new hash.

## Fresh controller verification

```text
actual-lower metadata bus-interface: exit 0, pass
function lifecycle: exit 0, failures=0
retained CP32 function binding: exit 0, unchanged terminal pass line
task-03-lifecycle.sha256: exactly 9 entries, 9/9 OK, no self-hash
task-3-round-2-head.sha256: 10/10 snapshot entries OK
scope comparison: only wineusb_winusb_busif_contract.c and the lifecycle seal
  differ from task-3-round-1-head
working paths match the frozen round-2 head
controller_failures=0
```

Review is read-only. Do not rerun the full suite, edit files, use Git, run
Wine, touch a prefix/device/sysfs USB path, build/stage/select/load a driver,
start applications, install tools, perform a physical operation, or retry
CP24.
