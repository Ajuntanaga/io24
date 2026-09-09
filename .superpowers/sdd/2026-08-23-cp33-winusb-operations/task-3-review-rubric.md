# Task 3 independent review rubric

The reviewer is read-only and returns separate spec-compliance and task-quality
verdicts.

## Exact owned scope

- Production: `dlls/wineusb.sys/winusb_busif.h`,
  `dlls/wineusb.sys/winusb_busif.c`, `dlls/wineusb.sys/wineusb.c`,
  `dlls/winusb.sys/main.c`, and new `dlls/winusb.sys/winusb_private.h` in the
  CP33 development source only.
- Tests: `tests/wineusb_winusb_busif_contract.c`, the narrowly expanded
  `tests/wineusb_winusb_busif_contract.sh` compile/link boundary, and
  `tests/winusb_function_io_contract.c`, plus the narrowly additive
  `tests/winusb_function_binding_contract.c` fake update required for the
  upper FDO's exact metadata-v2 consumption.
- Evidence: `re/winusb-api-v1/logs/task-03-lifecycle.sha256`.
- No other wrapper, production/test/evidence path, plan, specification, ledger,
  snapshot, handoff, immutable CP32, or patch-check file may change.

## Required test-first evidence

- Before production edits, the extended bus-interface test retains genuine v1
  success but fails on missing v2 behavior, and the lifecycle mode fails on
  missing per-file behavior. Each is feature exit 1 after compiling/executing
  the intended boundary, not usage, missing-input, compiler/harness, crash, or
  unrelated RED.
- GREEN evidence covers the bus-interface contract, function lifecycle mode,
  and retained CP32 function-binding contract, with clean exit 0.
- The contract changes compile and exercise the real scoped production units;
  source-text checks may supplement but may not replace behavioral execution.
- The bus-interface GREEN executes the actual lower `wineusb.c` speed callback,
  including low/high mapping, enclosing-device recovery, removal failure, and
  failure-path output nonmutation. A synthetic duplicate callback or
  compilation-only check is insufficient.

## Additive metadata interface

- Every pre-existing v1 declaration remains textually unchanged and the exact
  v1 size/version query still returns the same field values, `BusContext`, and
  one successful reference. No v1 client is redirected to a different context
  representation.
- Version 2 is appended with the exact constant, callback typedef, field order,
  and layout from the approved task. It does not edit or embed the v1 type.
- An exact v2 size/version query succeeds and references exactly once. Its
  matching dereference balances that reference. Undersized, oversized, v1-size
  with v2-version, and unsupported-version requests fail without mutating any
  caller output byte or changing the reference balance.
- The v2 speed callback derives the enclosing USB device from the existing
  metadata-source `BusContext`, preserving v1 context semantics. It returns
  `HighSpeed` only from `device->high_speed`, `LowSpeed` otherwise, and
  `STATUS_DEVICE_NOT_CONNECTED` after removal. It does not inspect or request a
  descriptor to infer speed and does not write the output byte on failure.

## Per-file lifecycle

- The new private header contains the exact six-value `enum winusb_file_state`
  and every required `struct winusb_file` member, spelling, type, and order.
  Forward declarations/includes are sufficient for every consumer.
- `struct winusb_device` is shared through the private header and gains a spin
  lock, file list/count, removal event, metadata-interface version, and cached
  speed. Device creation initializes all of them before use.
- `IRP_MJ_CREATE` rejects every state except `WINUSB_DEVICE_STARTED`; after
  start it allocates exactly one distinct file context per file object,
  initializes its lock/state/session/reference/outstanding/event/transfer-list
  fields, and inserts it under the device lock. `FsContext` is published only
  after allocation and insertion succeed; failure leaves it unchanged.
- Cleanup is admitted only for the matching linked context, closes further
  admission, transitions toward release/closing, and starts the outstanding
  drain without freeing an in-use context.
- Close is safe and idempotent. It clears the file object's published context,
  unlinks at most once, decrements the device count at most once, and frees only
  after `outstanding == 0`; repeated close cannot double-unlink or double-free.
- The device removal ownership event/count cannot be released until the file
  context's outstanding work has drained and the context has reached final
  destruction. A deterministic nonzero-outstanding close/remove schedule must
  make premature signaling and premature free observable.
- Surprise removal closes admission and causes later creates to fail. Existing
  linked contexts are marked removed/drained consistently, and device removal
  cannot report completion while file ownership remains live.
- Existing PnP start/stop/remove behavior and the retained CP32 lifecycle line
  remain intact. The retained binding fake may add exact v2 query, speed, and
  balanced dereference behavior, but must keep its v1 regression coverage and
  terminal pass line unchanged.
- Every retained function-contract mode that creates a file context performs
  matching cleanup and close before REMOVE; a permissive host wait fake may not
  conceal live ownership.

## Evidence and preservation

- `task-03-lifecycle.sha256` has exactly nine entries: the five production
  paths and four contract paths owned by this task. Paths are project-root
  relative, the manifest does not hash itself, and `sha256sum -c` verifies all
  nine from the project root.
- Task 2 public/private ABI remains unchanged except where the new private
  header consumes it. CP32 and the patch-check clone remain immutable.
- No Wine, prefix, device, sysfs USB, driver, application, physical operation,
  build/stage/select action, CP24 retry, installation, or Git action occurred.

## Verdict

Return spec compliant only if every exact metadata, lifecycle, retained-PnP,
and checkpoint item is supported by the scoped diff and report. Return task
quality approved only if the tests independently reject context/version/state,
reference-balance, output-mutation, file-aliasing, double-close, and
post-removal regressions without accepting a harness failure as RED.
