# Task 1 fix round 4 scoped review package

- Task brief: `../task-1-brief.md`.
- Round-3 review finding: `task-1-review-round-3.md`.
- Implementer report with round-4 evidence: `../task-1-report.md`.
- Fix base label: `task-1-round-3-head`.
- Fix head label: `task-1-round-4-head`.
- Fix diff: `task-1-round-4.diff` (335 lines; full round-4 delta).
- Fix-head manifest: `task-1-round-4-head.sha256` (15 entries).
- Fix-head manifest-file SHA-256: `5f87641e9c28c260aec16e33a4b7914f20ac47366070a994e0a51bc43c51ae99`.
- Fix-diff SHA-256: `3e12b5ba3b9630b5dc201246fcb58e4d0ff04cada418eff40f5e94d8f94e12cd`.

## Finding under verification

Public typed request submission was checked, but caller-visible response propagation was false-GREEN-capable: the caller did not assert returned descriptor bytes/length or `GetPipePolicy` value/value-length, and the same omission could affect speed, cached descriptor, transfer lengths/payload, or overlapped-result length.

The re-review must determine whether round 4 now separately proves both sides of the contract:

1. the fake boundary injects independently defined exact response data and returned-byte values through the real output channels; and
2. the caller initializes independent sentinels/guards and asserts the exact post-API bytes, values, and lengths.

It must also check that no prior Task 1 fix regressed.

## Fresh controller verification

```text
seal status=0 lines=72 ok=72 failed=0
public --descriptors/--policy/--vendor/--red: exit 1, no HARNESS
aggregate feature REDs: public=1 function=1 lower=1 cancel=1 vendor=1
mode executions: 24/24 returned 1 with no HARNESS diagnostic
harness/usage/tool/input/read probes: 13/13 returned 2
postcheck modes=24 probes=13 dev_diff=0 patch_diff=0 checkpoint_status=0 checkpoint_lines=11 checkpoint_ok=11
controller_failures=0
```

## Binding constraints

- Exact returned data must traverse the actual production API from the fake boundary to caller-visible buffers/length/value fields. Checking only fake output or only caller success is insufficient.
- Response fixtures and caller sentinels must be independently defined and exact. Policy `ValueLength` begins as its valid four-byte capacity and must remain exactly four after return; the policy value carries the distinct sentinel.
- Preserve typed request assertions, boundary-authored trace, mode-specific masks/IOCTLs, initialization-returned handles, real production execution, Python harness remapping, lower/cancel behavior, and feature-1 versus harness-2 separation.
- CP32 and both CP33 production clones remain immutable throughout Task 1.
- Review is read-only. Never run Wine, touch a prefix/device/sysfs USB path, stage/select/load anything, start applications, perform physical USB operations, retry CP24, initialize Git, or mutate files.
