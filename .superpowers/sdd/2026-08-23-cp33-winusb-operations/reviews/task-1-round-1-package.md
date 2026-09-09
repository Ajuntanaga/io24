# Task 1 fix round 1 scoped review package

- Task brief: `../task-1-brief.md`.
- Initial review findings: `task-1-review-round-0.md`.
- Implementer report with round-1 evidence: `../task-1-report.md`.
- Fix base label: `task-1-head` (the exact 15-file snapshot reviewed in round 0).
- Fix head label: `task-1-round-1-head` (the exact current 15-file snapshot).
- Fix diff: `task-1-round-1.diff` (1,088 lines; full base-to-head delta).
- Fix-head manifest: `task-1-round-1-head.sha256` (15 entries).
- Fix-head manifest-file SHA-256: `1e64cb87fa205f8f4877514deb88c7cfb090d72939d31425e60c21d9c47d48b4`.
- Fix-diff SHA-256: `485342b0969188103b5f9a915def4c30c150362c30f5a16070693645ebfdbefc`.

The base and head snapshots include the ten owned contracts/fakes, four owned evidence files, and the implementer report. The 1.56 MB static call-site log is present in both snapshots and unchanged, so it adds no content to the fix diff.

## Findings under verification

1. The four C families compiled production objects without executing their behavior: public/function discarded objects, lower built an unused module, and cancellation did not compile `wineusb.c`.
2. Complete, controllable, observable Win32, WDM/lower-stack, and libusb fakes/assertions were missing or inert.
3. The vendor-profile contract had frozen static evidence but no synthetic call sequence through the public boundary.
4. Focused modes were accepted but ignored.
5. Compiler/linker/tool failures could return `1` and collide with feature RED; harness faults must diagnose and return `2` or another non-`1` status.

The initial review accepted the CP32 seal, clone equality, static vendor evidence, MI05 fixture bytes, usage status, fresh temporary directories, and Task 1 scope. The re-review should verdict the five findings above and inspect only the round-1 fix diff for new breakage.

## Fresh controller verification after the pause

The controller independently ran the corrected matrix against the untouched CP32-derived development tree. It did not rewrite retained evidence.

```text
seal status=0 lines=72 ok=72 failed=0
aggregate feature REDs: public=1 function=1 lower=1 cancel=1 vendor=1
mode executions: 24/24 returned 1 with no HARNESS diagnostic
harness/usage probes: 12/12 returned 2
postcheck modes=24 probes=12 dev_diff=0 patch_diff=0 checkpoint_status=0 checkpoint_lines=11 checkpoint_ok=11
controller_failures=0
```

The exact 24 mode diagnostics and 12 negative-probe diagnostics are also retained in `re/winusb-api-v1/logs/cp33-red.log` and described in the report.

## Binding global constraints

- CP32 is immutable. The two CP33 roots must remain exact CP32-derived clones throughout Task 1.
- All verification is offline. Do not run Wine, create or access a Wine prefix, stage or select a build, load a driver, start Universal Control or Voice FX, open a USB node, inspect a sysfs USB path, claim or detach a physical interface, change a physical alternate/configuration, issue a physical transfer, or retry CP24.
- CP24 authorization is consumed. A connected io24 is state evidence only and is not authorization.
- A missing fake, malformed harness, unrelated compile failure, crash, or retained-test failure is not an acceptable feature RED.
- Every wrapper must self-check its inputs, use a fresh temporary directory, compile actual production translation units with the required strict warning flags, exit `2` on usage/harness errors, and reserve exit `1` for executed missing-feature failures.
- The function fixture encodes MI05 alternate 0 with zero endpoints and alternate 1 with bulk endpoints `0x81` and `0x01`, maximum packet size 512.
- Fake libusb must expose counters for claim, release, detach, auto-detach, set-configuration, set-alternate, control, bulk, interrupt, cancel, clear-halt, transfer-free, and close.
- No automatic detach, libusb auto-detach, `libusb_set_configuration`, selector, firmware, live candidate, raw USB, prefix, or device path may be used.
- This workspace is not a Git repository. Review the supplied non-Git snapshots, manifest, and unified diff; do not initialize Git or mutate files.
