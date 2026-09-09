# Task 1 fix round 2 scoped review package

- Task brief: `../task-1-brief.md`.
- Round-1 review findings: `task-1-review-round-1.md`.
- Implementer report with round-2 evidence: `../task-1-report.md`.
- Fix base label: `task-1-round-1-head` (the exact 15-file snapshot reviewed after round 1).
- Fix head label: `task-1-round-2-head` (the exact current 15-file snapshot).
- Fix diff: `task-1-round-2.diff` (707 lines; full round-2 delta).
- Fix-head manifest: `task-1-round-2-head.sha256` (15 entries).
- Fix-head manifest-file SHA-256: `892c97dc751e72ae41bd00bd31d531631a9acb9a9a448ce1af66f19142f76dc8`.
- Fix-diff SHA-256: `541ee3e481475b23fe862d20883800c85489d2cada18ae6374bddf436ed2b7ff`.

## Findings under verification

1. Fake observations/assertions could false-GREEN: function setup polluted `lower_calls`; session/alternate inspected prefilled bytes; cancellation counted before the real lower call; public IOCTL records were not semantically asserted.
2. The vendor operation trace was authored by the caller after attempted API calls rather than emitted by the fake Win32 boundary, so incorrect translations could pass.
3. Python source/optional-file reads could raise uncaught `OSError` and collide with feature exit `1`.
4. Public focused modes handed fabricated private handle `0x2200` to production rather than using a handle returned by `WinUsb_Initialize`.
5. Fake libusb subtracted `LIBUSB_CONTROL_SETUP_SIZE` for bulk/interrupt completion, truncating payload and allowing an inconsistent actual length.

The re-review must also check that round 2 did not regress the already-addressed real-production-execution and distinct-mode findings.

## Fresh controller verification

The controller independently reran the amended evidence against untouched CP32 after the implementer returned:

```text
seal status=0 lines=72 ok=72 failed=0
aggregate feature REDs: public=1 function=1 lower=1 cancel=1 vendor=1
mode executions: 24/24 returned 1 with no HARNESS diagnostic
harness/usage/tool/input/read probes: 13/13 returned 2
vendor_unreadable_source: status=2, HARNESS Permission denied diagnostic
postcheck modes=24 probes=13 dev_diff=0 patch_diff=0 checkpoint_status=0 checkpoint_lines=11 checkpoint_ok=11
controller_failures=0
```

## Binding constraints

- Review is read-only and scoped to the five findings plus new Critical/Important breakage in the 707-line round-2 diff.
- CP32 and both CP33 production clones are immutable during Task 1.
- Feature RED is exit `1`; all usage, compiler, linker, loader, crash, input, read/stat, and external-tool failures must diagnose as harness failures and exit `2` or another non-`1` value.
- Tests must observe effects caused by actual production calls; setup state, caller-authored traces, or expected values copied into the observed channel cannot satisfy behavior assertions.
- Handle-dependent public calls must use only a valid handle returned by production initialization.
- Control setup-size adjustment applies only to control transfers; bulk and interrupt copied bytes and `actual_length` must agree.
- All work is offline and hardware-free. Never run Wine, access/create a Wine prefix, stage/select/load a build or driver, start Universal Control or Voice FX, open a USB node, inspect a sysfs USB path, claim/detach/change a physical interface/configuration/alternate, issue a physical transfer, or retry CP24.
- Do not initialize Git or mutate any file.
