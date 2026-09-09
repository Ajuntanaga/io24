# CP33 Task 5 independent review rubric

Review only the bounded Task-5 delta from frozen `task-5-base` across the
three paths in `task-5-paths.txt`. The accepted test-first source SHA is
`7547c6f2292c3a8650bb18b0610959eee30927418e1d6b279a5bf6f6e8751fca`;
production implementation must not change it. Controller rulings R64-R74 and
the authoritative Task-5 plan/specification control.

## Scope and executable boundary

- Exactly `dlls/winusb/main.c`, `dlls/winusb/winusb_private.h`, and the already
  accepted user contract may differ from `task-5-base`.
- The wrapper stays at SHA
  `f601c75e890afb48771f77e976041139ee33e3ce4331cb380c1e601af9bf4ebc`.
- Both authoritative corrected RED logs must retain hashes recorded in
  `task-5-base-state.txt`; superseded and harness-error attempts are history,
  not Gate-1 inputs.
- Focused GREEN must compile and execute actual production. A source scan,
  fabricated opaque object, test-only production hook, skipped source, or
  harness exit is a blocker.

## Pointer admission and ownership

- Every public handle path scans the locked registry by pointer equality
  before dereferencing caller-provided memory. Null, arbitrary, and stale
  values return `FALSE`/`ERROR_INVALID_HANDLE` with exact output mutation.
- Admission increments the handle API reference while registry-locked and the
  root reference before unlocking. Every exit balances both.
- Lock order is always registry then root. No path acquires registry while
  holding root, waits with either lock held, or submits RELEASE under a lock.
- A retired handle remains allocated until all its admitted API calls leave.
  The root remains allocated until all live-handle and API references drain.
- The public handle is a process-global monotonic opaque token, never the heap
  record address. Tokens are nonzero, never `INVALID_HANDLE_VALUE`, never
  reused or wrapped, and exhaust cleanly. A zero-reference retired record is
  reclaimed without waiting for an otherwise long-lived root.
- The last live Free is the unique finalizer: it marks retiring atomically,
  waits in a condition loop, submits one synchronous RELEASE, frees slots and
  snapshot, deletes the root lock, and frees root. It returns TRUE and frees
  user memory even if RELEASE fails. No path closes or duplicates caller
  device ownership.

## Initialize and associated interfaces

- Preserve every sealed Task-4 two-stage request, snapshot parser, transport
  error, postcommit rollback, event balance, and meaningful-last-error rule.
- Postcommit ownership allocates root, exact checked slot array, and default
  handle; allocation failures at positions 2, 3, and 4 publish NULL, release
  exactly once, and balance all completed allocations.
- Default publication installs slot zero, one live/root reference, a complete
  registry entry, and caller output last.
- Associated accepts only a live default handle, nulls nonnull output first,
  treats `UCHAR_MAX` as overflow/`ERROR_INVALID_PARAMETER`, maps `n` to slot
  `n+1`, distinguishes no-more-items/duplicate/allocation errors, and
  atomically publishes one complete object. Allocation/race/retiring losers
  leave no slot, entry, reference, or output.
- Both root-first and associated-first free orders, reissue of both associated
  slots, and the deterministic acquire-before-final-Free schedule are sound.
  Carry R71's actual lower interface-index observation to Task 7.

## Cached operations

- Device `(1,0,0)` and configuration `(2,0,0)` reads are default-handle-only,
  checked against immutable snapshot bounds, copy only the exact cached bytes,
  report exact length, and preserve output tails.
- Short cache buffers return `ERROR_INSUFFICIENT_BUFFER`, copy nothing, and
  report zero bytes. Null buffer/length, associated handle, or selector mismatch
  returns `ERROR_INVALID_PARAMETER` with R68 mutation behavior.
- String/other descriptors return `ERROR_NOT_SUPPORTED`, report zero, and issue
  no IOCTL; Task 9 owns fallback.
- Speed accepts only `DEVICE_SPEED` on a live default handle. Zero capacity
  returns required length one without output write; sufficient capacity writes
  one byte and preserves tail; high-or-higher maps `0x03`, full-or-lower maps
  `0x01`. Invalid handle is `ERROR_INVALID_HANDLE`; all other invalid arguments
  use R69 and preserve the input length/output.
- Cleanup cannot overwrite the selected public error.

## Review evidence

Require focused handle/descriptor GREEN, retained user initialize/surface,
function lifecycle/initialize, metadata bus, and binding GREEN before PASS.
Inspect at least these executable mutation lenses: pre-registry dereference,
missing root retain/final wait, associated target without `+1`, partial short
descriptor copy, speed length/tail overrun, missing retired-record reclaim,
token reuse, invalid-token wrap, and token reset after final root teardown. Do
not run Wine, contained builds, a full matrix, live/device/prefix/install, or
physical operations.
