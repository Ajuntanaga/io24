# CP33 Task 5 handle/cache implementation brief

This is approved Task 5 only. The authoritative plan/specification and
controller rulings R64-R70 apply. The frozen base is `task-5-base`, derived
exactly from sealed `task-4-round-2-head`. Keep every live, Wine, prefix,
contained-build, install, physical-device, and CP24 boundary closed.

## Owned paths

- `.io24-build/winusb-api-v1/dev-source/dlls/winusb/main.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb/winusb_private.h`
- `tests/winusb_user_api_contract.c`

Do not edit the wrapper, kernel/lower sources, plan, specification, ledger,
evidence, snapshots, or another task's files. The controller owns checkpoint,
logs, review packaging, and seals.

## Test-first boundary

Expand the real compiled-production contract before editing production. Both
focused modes must exit 1 for missing Task-5 behavior rather than harness or
tool failure:

```bash
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --handles
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --descriptors
```

Cover null, non-readable arbitrary, and stale public handles without ever
requiring a caller-pointer dereference; exact associated mapping/default-only,
out-of-range, duplicate, allocation-failure, and output-null behavior; both
valid free orders; exactly one final RELEASE; balanced storage; no caller
device close; and a deterministic real-thread schedule in which an API acquire
is admitted before the final Free retires the handle and the Free waits until
that API reference leaves.

Descriptor coverage must execute actual cache reads for device and projected
configuration descriptors, exact selector/language rules, default-only access,
null and short buffers, copied length, guard/tail preservation, and Task-5
string/other `ERROR_NOT_SUPPORTED` with zero private IOCTLs. Speed coverage
must exercise invalid/default/associated handles, unknown type, null and zero
length cases, high and low fixtures, output length mutation, and tail guards.

Use only host contract fakes for Win32 synchronization. No source-text
substitute or production-only hook counts. A child process may safely classify
an arbitrary non-readable handle crash as a feature failure. C11 threads may
drive the concurrency schedule; if the unchanged wrapper cannot honestly
compile/link it, stop and report that exact boundary instead of editing the
wrapper.

## Production invariants

- Use a locked global registry and compare opaque pointer values before any
  object dereference. Every admitted API call holds both handle and root
  references until its final exit.
- Free unlinks one live handle, clears its interface slot, and defers its
  storage until acquired references drain. Final retirement blocks new
  publication, waits without holding registry/root locks, submits exactly one
  synchronous RELEASE, and frees all user-mode ownership even if release
  fails. Never duplicate or close the caller device.
- Associated index zero means root interface index one. Publish a completely
  initialized object exactly once; roll back every allocation/race failure.
- Cache reads use the independently validated Task-4 snapshot offsets/lengths.
  Device/configuration selectors are exact and default-handle-only. Short
  buffers receive no partial descriptor. Task 9, not Task 5, owns descriptor
  IOCTL fallback.
- Speed is cache-only and one byte: high-or-higher `0x03`, full-or-lower
  `0x01`. Preserve exact input/output mutation rules from R69.
- Preserve every sealed Task-4 initialization parser, transport-error,
  rollback, allocation, and release invariant.

## Required green gates

Run the two focused modes plus Task 4 initialization, public surface,
function lifecycle/initialize, metadata bus, and binding contracts. Do not run
Wine, a contained build, a full matrix, or any live-device operation.
