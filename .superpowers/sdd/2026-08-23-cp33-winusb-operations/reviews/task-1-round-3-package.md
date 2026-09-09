# Task 1 fix round 3 scoped review package

- Task brief: `../task-1-brief.md`.
- Round-2 review findings: `task-1-review-round-2.md`.
- Implementer report with round-3 evidence: `../task-1-report.md`.
- Fix base label: `task-1-round-2-head`.
- Fix head label: `task-1-round-3-head`.
- Fix diff: `task-1-round-3.diff` (571 lines; full round-3 delta).
- Fix-head manifest: `task-1-round-3-head.sha256` (15 entries).
- Fix-head manifest-file SHA-256: `73f188f4f036124880c055c27deded4edb2db4b829c26b02c03b26b93bbe4b2a`.
- Fix-diff SHA-256: `063fe4dc3029052fe754c1c71def05e18dc10b1e2fbc733a0eaf4a3b7fcf1727`.

## Findings under verification

1. Public event validation was false-GREEN-capable because it searched for expected integers at arbitrary byte offsets instead of parsing and checking exact semantic fields.
2. Public modes collapsed on missing initialization with zero events, and function session/alternate/policy/transfer modes collapsed on prerequisites rather than exposing distinct CP32 feature boundaries.

The re-review must also check that round 3 preserved every previously addressed finding: real production translation-unit execution, boundary-authored vendor observation, Python harness-error remapping, initialization-returned handles, control-only setup subtraction, exact pre/post fake deltas, distinct lower/cancel modes, and exit-code separation.

## Fresh controller verification

```text
seal status=0 lines=72 ok=72 failed=0
aggregate feature REDs: public=1 function=1 lower=1 cancel=1 vendor=1
mode executions: 24/24 returned 1 with no HARNESS diagnostic
public masks: initialize missing=0x80; handles=0x88; descriptors=0x190; policy=0x18c0; transfer=0x22a2; cancel=0x481; vendor/red=0x3ffb
function last IOCTLs: session=0x222002; alternate=0x22200c; policy=0x222014; transfer=0x222022; each status=0xc00000bb
harness/usage/tool/input/read probes: 13/13 returned 2
postcheck modes=24 probes=13 dev_diff=0 patch_diff=0 checkpoint_status=0 checkpoint_lines=11 checkpoint_ok=11
controller_failures=0
```

## Binding constraints

- Typed public observations must be captured at the fake boundary and checked by exact named field/offset derived independently of production helpers; arbitrary byte search is not semantic proof.
- Missing exports may be genuine RED but each public mode must interrogate its own target set in the actual loaded module, report a distinct target/present/missing mask, and safely continue into its typed behavior once initialization becomes available. Never fabricate a private handle.
- Function modes must execute and record their exact distinct actual IOCTL dispatch/rejection without fabricating private file state, while retaining the full prerequisite path for later GREEN.
- Feature failures return `1`; every harness, usage, compiler, linker, loader, crash, input, file-read, or tool fault returns `2` or another non-`1` value.
- CP32 and both CP33 production clones remain immutable throughout Task 1.
- Review is read-only. Never run Wine, touch a prefix/device/sysfs USB path, stage/select/load anything, start applications, perform physical USB operations, retry CP24, initialize Git, or mutate files.
