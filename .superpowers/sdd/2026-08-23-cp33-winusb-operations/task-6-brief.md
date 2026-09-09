# CP33 Task 6 transactional function-claim implementation brief

Read this first. It is the requirements source for approved Task 6, including
controller ruling R76. The authoritative design's function-claim section,
plan Task 6, and ledger rulings R31, R46, R47, and R76 apply. The frozen base
is `task-6-base`, derived exactly from the sealed Task-5/Gate-1 state.

This task is hardware-free and offline. Never run Wine, access or create a
Wine prefix, inspect USB/sysfs, stage/select a build, load a driver, start UC
or Voice FX, claim a physical interface, or perform a live transfer. Do not
edit CP32 or `patch-check-source`.

## Owned paths

- `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/winusb_busif.h`
- `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/wineusb.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.h`
- `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c`
- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`
- `tests/wineusb_pipe_observe_contract.c`
- `tests/winusb_function_io_contract.c`
- `tests/wineusb_function_scope_fake_libusb.c` (R77 compatibility fix only)

Do not edit wrappers, Makefiles, public/user ABI, metadata v1/v2 behavior,
the retained function-scope contract C/wrapper, plan/spec/ledger, evidence,
snapshots, or another task's files. The controller owns logs, checkpoints,
review packages, and seals. Use `apply_patch` for edits.

R78 keeps `unixlib.h` in the owned audit set but requires it to remain
byte-for-byte at the recorded base hash. The selected private URB uses the
existing `unix_usb_submit_urb`; do not add an unused Unix-call declaration.

## Test-first boundary

First expand the actual compiled-production `--claims` contract and fake
libusb. Cover MI05-only claim; ascending multi-interface claims; idempotent
selection after commit; rejection of a second select while a transaction is
pending; second-claim failure with reverse rollback; `LIBUSB_ERROR_BUSY`
mapping to failed USBD status plus `STATUS_DEVICE_BUSY`; stale/wrong/finalized
transaction rejection without mutation; child-destruction release before the
parent/shared handle decrement; sibling isolation and parent lifetime; and
zero detach, auto-detach, and set-configuration calls. Record ordered claim
and release journals rather than only final counters.

Also add an actual `session.c` schedule to `--initialize`: after the real upper
submits a lower SELECT successfully but before the upper post-select commit
check, deterministically change the file or device state. Prove the upper
sends rollback for the exact returned transaction and that rollback finishes
before initialize returns failure, with no published session/snapshot/output
information and no lower claimed or selected state. The normal success path
must finalize commit exactly once. Tests must execute the real production
translation units through the existing fake boundaries; source-text checks or
copied production logic do not count.

R77 separately permits one narrow retained-fake compatibility correction:
the sealed CP32 `wineusb.so` imports `libusb_control_transfer`, while the
existing function-scope fake omits it and the retained command therefore dies
at `dlopen` before assertions. Add only a safe unsupported metadata-control
result so the pre-existing configuration/IAD projection remains under test.
Do not edit the retained contract or wrapper and do not count this harness
repair as Task-6 RED/GREEN feature evidence.

Run the focused commands after test edits and before production edits. Both
must be genuine feature RED exits of 1, never compiler/harness exit 2:

```bash
tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source \
  .io24-build/winusb-function-binding-v1/build-a \
  .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --claims
tests/winusb_function_io_contract.sh \
  .io24-build/winusb-api-v1/dev-source --initialize
```

## Production invariants

- Extend only the private in-kernel WineUSB boundary. Use one reserved private
  URB function and an exactly validated fixed request declared in the shared
  private header. The select output's `ConfigurationHandle` is an opaque
  transaction token; scan/compare registered pending state before any use and
  never dereference a caller-supplied token.
- Each function child stores a 256-bit committed claimed set and at most one
  pending transaction journal. Parent/non-function behavior remains unchanged.
- Validate the entire SELECT before side effects. Claim only function-owned,
  newly required interfaces, ascending by interface number. On any lower
  failure release only this transaction's successful claims in reverse order;
  leave the committed set and prior claims unchanged.
- A successful SELECT remains pending until the upper post-select state
  decision. Rollback reverses and clears only that transaction. Commit retains
  its interfaces and destroys only transaction state. Repeated selection after
  commit is idempotent and makes no duplicate libusb claim.
- Upper rejection must synchronously finalize rollback before freeing its
  temporary state or returning failure. Upper success atomically publishes its
  session decision and finalizes commit exactly once before returning.
- Child destruction releases every still-pending/committed claim exactly once
  before decrementing the parent/shared physical handle. Never detach an
  owner, enable auto-detach, or call `libusb_set_configuration`.
- Preserve exact `IRP_MN_QUERY_INTERFACE` metadata v1/v2 definitions and
  behavior; do not introduce metadata v3 for this task.

## Required GREEN gates

Run the focused claims and upper-initialize modes, then the retained
function-scope contract using the sealed CP32 lower artifact. Keep all wrapper
hashes frozen. Report exact exit codes, test-first RED evidence, changed-path
hashes, and any concern in `task-6-report.md`; do not create the controller's
checkpoint or seal.
