# CP33 Task 9 R132 brief — successor evidence correction

## Purpose and authority

Close only the successor-evidence gaps identified by controller ruling R132 in
`task-9-report.md` and `progress.md`. This is a test-only RED correction after
the first R131 candidate was rejected. It does not authorize a production
change or claim Task 9 complete.

Binding authorities, in descending order for this bounded correction:

1. R132 at the end of `task-9-report.md` and row R132 in `progress.md`.
2. Task 9 in `docs/superpowers/plans/2026-08-23-cp33-winusb-operations.md`.
3. The control/descriptor and transfer-ownership sections of
   `docs/superpowers/specs/2026-08-23-cp33-winusb-operations-design.md`.

The immutable rejected-candidate base is `task-9-r132-base.sha256`, which must
verify 2/2 before and after the edit against the copied snapshot paths.

## Exclusive write ownership

You may modify exactly these two live files:

1. `tests/winusb_function_io_contract.c`
2. `tests/wineusb_winusb_busif_contract.c`

You may create or append only your own evidence report at
`task-9-r132-implementer-report.md`. Do not edit `task-9-report.md`,
`progress.md`, any snapshot or manifest, any wrapper/support/RANGE file, or any
production file. Do not dispatch subagents. This workspace is intentionally
non-Git, so do not initialize Git or create commits.

## Function-contract requirements

In `tests/winusb_function_io_contract.c`, keep all accepted R131 witnesses and
add executable behavior that catches each remaining false-green:

1. Keep two caller-owned generic-control requests for the same interface
   pending simultaneously. Complete only one and require the target alternate
   to remain blocked. Complete the second and require that alternate to become
   permitted. This must distinguish a real per-interface count from a Boolean.
2. Extend the exact FAST_MUTEX rendezvous to endpoint lookup. Establish a real
   current pipe map first, then dispatch an endpoint-recipient request that
   blocks on the exact session mutex. While retaining that mutex, change the
   target endpoint/map state; after release the request must reject before a
   lower submission. This proves endpoint lookup happens after the lock is
   acquired, not from a stale pre-lock observation.
3. A failed thread creation or join is a terminal harness path. In particular,
   after a failed join do not inspect the worker result, schedule effect, or
   any other worker-owned state. Preserve safe cleanup without inventing a
   production claim.

Name the production defects these tests catch in comments: Boolean accounting,
pre-lock endpoint lookup, and post-failed-join shared-state access. Expectations
must be independently derived and must execute actual production through the
existing fake WDM/lower boundary.

## Actual-lower contract requirements

In `tests/wineusb_winusb_busif_contract.c`, retain the root-5/interface-6 model
and executable actual-`wineusb.c` boundary, then add:

1. Queue valid root-5 and interface-6 pending children in both list orders.
   A conflicting later entry must block its target, proving complete-list
   classification rather than first-entry-only behavior.
2. For every busy SELECT, assert the exact prior list order and membership is
   unchanged. For every permitted pending SELECT, assert it appears exactly
   once after all prior entries before the fixture retires only its own entries.
3. Add a one-shot fake observation that inserts a conflicting caller-owned
   entry only while the exact `wineusb_cs` critical section is held. The
   resulting SELECT must observe the conflict. This must prove locked-list
   classification behaviorally, without a source-text scan.
4. Preserve the Tasks 11-13 boundary: no cancellation, cleanup, teardown,
   removal, or production-owned retirement claim.

## Required evidence

Before editing, run the focused modes once and record the current genuine
feature RED. After editing, rerun:

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --lifecycle
tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source --red
```

The two focused modes must compile and execute actual production and remain
feature exit 1 for the missing/corrected behavior, with no usage, prerequisite,
compiler, linker, crash, or harness exit 2. The retained modes must exit 0.
Run the function focused mode under the established manual ASan/UBSan recipe
and require zero sanitizer markers. Do not count the documented GCC C11-thread
TSan exit 66 as feature or race evidence.

Perform bounded deletion/bypass mutants for the newly added lenses when
practical, remove them afterward, and restore the exact intended live head.
Write commands, exit codes, relevant failure counts, sanitizer result, files
changed, mutant results, and self-review to the implementer report.

## Safety boundary

Offline host contracts only. Do not run Wine, access or create any Wine prefix,
open a USB node or sysfs USB device path, stage/select/build a Wine candidate,
load a driver, claim/detach/change an interface, issue a physical transfer, run
Universal Control or Voice FX, access firmware, use the network, or touch the
protected prefix. Check `/sys/class/power_supply/BAT0/capacity` before each
meaningful verification phase and stop at 10 or lower.
