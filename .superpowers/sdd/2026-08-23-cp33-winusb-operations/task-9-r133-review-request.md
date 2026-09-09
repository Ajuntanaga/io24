# CP33 Task 9 R133 successor — independent re-review request

## Decision requested

Re-review the corrected immutable successor after the first R132 candidate was
rejected. Return `PASS` only if all four R133 review findings are closed without
introducing a Critical, Important, or material Minor regression or new
false-green. Otherwise give severity, exact file and line, a concrete mutant or
failure schedule, and the smallest correction.

Passing this review does not complete Task 9. It only permits the controller to
reopen the separately frozen production correction.

## Authority and lineage

- R132 and R133 at the end of `task-9-report.md` and in the ruling table of
  `progress.md`.
- Original bounded contract: `task-9-r132-brief.md`.
- First review: `task-9-r132-review-1.md`, SHA-256
  `c37d2c3db80dde8d7c3eb3473f483d75c4d07397fed780e98d0e69cbc126f3f7`.
- Rejected predecessor: `task-9-r132-head.sha256`, 2/2 immutable.
- Corrected candidate: `task-9-r133-head.sha256`, 2/2 verified, manifest
  SHA-256 `2d1ad6b0da1cf9d39b059e13e4a9953c83b4fcbd79a3b6df26f0825a56228ba1`.
- Exact rejected-to-corrected delta: `task-9-r133.diff`, 474 lines, SHA-256
  `911055793772ff16995cecf334de7fa863f9345bb27e1c25551ef199339831ef`.
- Full R132-base-to-corrected patch: `task-9-r132-base-to-r133.diff`, 952
  lines, SHA-256
  `ab04535484ecee684558587b37d8f15b34753695cd3b5b104deec0d05488f0e9`.
- Implementer report, including both rounds and mutants:
  `task-9-r132-implementer-report.md`, SHA-256
  `28246b99db572fe6a065161e1b04a7b9d1dad8aa8a9e4c81d746c0b711dd05c7`.
- All other Task-9 paths remain exact under `task-9-r132-frozen.sha256`.
- Live files were byte-equal to the corrected frozen head at controller freeze.

The workspace is intentionally non-Git. These task-local hashes, snapshots,
and patches replace commits and SHAs.

## Controller replay

`task-9-r133-controller-logs.sha256` verifies 12/12 generated outputs and has
SHA-256 `e62677d303e6fde9b3b3e5c1bfd6a23b56921a32c7ec59fc66cd1708da5b7af6`.

- Function focused: feature exit 1, 35 dispatches, 29 mode IOCTLs, 203
  failures, zero harness/crash markers.
- Function lifecycle: exit 0, zero failures.
- Actual-lower focused: feature exit 1, exactly 12 cross-interface permit
  failures, zero harness/crash markers.
- Actual-lower retained `--red`: exit 0.
- Manual ASan/UBSan/alignment compile: exit 0; focused execution exit 1 with
  the same 203 failures and zero sanitizer/harness markers.
- BAT0 was 90 and Discharging before both controller phases, above the stop
  threshold.

Implementer deletion/bypass evidence after restoration:

- swapped context/URB pairs: function 203 -> 213;
- reused context/URB pair: function 203 -> 206;
- post-unlock classification: lower 12 -> 13;
- transient busy SELECT insertion: lower 12 -> 26, one for each of 14 busy
  schedules;
- last-entry-only classifier: lower 12 -> 20, failing only both mirror
  schedules with four assertions each.

## Findings that must be closed

1. Per-request identity and retirement: two pending IRPs must retain distinct
   live completion contexts and URBs, distinct stored outcomes must return to
   the matching original IRP, and pair one alone must retire at completion one
   before pair two retires at completion two. Aggregate count/list/reference
   checks remain necessary but insufficient.
2. Locked classification: the injected IRP may remain alive after lock exit,
   but its classification fields must become a known nonconflict before an
   unlocked dereference could decide busy, then be restored after dispatch.
3. Busy SELECT ownership: every actual included-production `InsertTailList`
   attempt for the armed busy SELECT entry must be observed and rejected, so
   transient enqueue/dequeue cannot hide behind final list equality.
4. Complete-list scanning: later-conflict schedules must catch first-entry-only
   logic and mirror first-conflict/nonconflicting-tail schedules must catch
   last-entry-only logic in both root-5/interface-6 orders.

Also verify that the correction preserves all accepted R131/R132 witnesses,
uses the actual production boundaries rather than source scans, does not
redefine expectations from observed output, remains bounded and memory-safe,
retires only fixture-owned lower entries, and makes no Tasks 11-13 or production
completion claim.

## Safety

Review is read-only and offline. Do not edit/create files, initialize Git,
dispatch subagents, run Wine, touch any prefix, access USB/sysfs device paths,
stage/build/select a Wine candidate, use firmware, or access the network. Do
not rerun tests unless a specific named doubt cannot be resolved from the
sealed evidence; check battery first if execution is necessary.
