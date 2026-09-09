# CP33 Task 4 combined independent review rubric

Review the combined diff from frozen `task-4-base`, both half reports, exact
plan/spec Task 4 sections, and controller rulings R25–R63. Review is read-only.

## Scope and TDD

- Exactly eight production paths and six contract paths may change; the two
  new headers/modules match their declared ownership. Patch/checksum evidence
  is controller generated. Task 3 frozen snapshots remain immutable.
- Both prescribed initialize commands reach compiled production boundaries and
  have genuine feature RED followed by clean GREEN. Wrapper/compiler/missing
  input/crash failures remain harness exit 2. Retained lifecycle, binding, and
  public surface gates remain green.
- The user wrapper's R32 link change executes actual `winusb.dll/main.c`
  through the host fake Win32/NT boundary without a production seam or
  permissive unresolved-symbol fallback, and preserves every unrelated mode.
- The retained binding wrapper's R41 change requires and links the actual new
  `winusb.sys/session.c` beside `main.c`; it preserves the exact CP32 terminal
  pass line and adds no weak/fallback/test-only production behavior.
- The retained binding C contract's R42 change adds only the two missing WDM
  host fakes needed by real `session.c`; it neither weakens existing assertions
  nor treats their permissive behavior as Task-4 initialization evidence.

## Kernel initialization

- Exact 24-byte input validation precedes all mutation. Direct output uses
  only the mapped MDL; input and guard buffers remain untouched.
- Descriptor acquisition is exactly device, 9-byte configuration header, then
  validated `wTotalLength`. Parsing rejects every malformed sequence with
  checked arithmetic and no out-of-bounds read.
- Output under 72 is untouched/noncommitting. A 72-byte size query returns
  header/information 72, exact total 211, session zero, and no select/commit.
- Full success validates a sufficient mapped MDL before one lower select, then
  atomically commits exact MI05 arrays/snapshot, speed 0x03, and a nonzero
  monotonic cookie. Every allocation/select failure rolls back to coherent
  uninitialized state.
- Production explicitly supplies each lower URB through next-stack
  `Others.Argument1`; the fake builder does not help. NT and USB-header status
  channels are independently varied and both must succeed.
- Builder IRPs may be freed by synchronous completion: production consumes the
  supplied `IO_STATUS_BLOCK`, and an ASan fake frees the immediate IRP. URB
  status starts at a failure sentinel and must be overwritten independently;
  the real lower select backend writes success on its validated success path.
- No spin lock is held across allocation or lower waits. Cleanup/close/removal
  free committed ownership only after drain; Task 3 lifetime ordering remains.
- Exact live-session RELEASE frees committed Task 4 state, clears the cookie,
  returns to uninitialized, rejects stale/cross-file/malformed requests without
  mutation, and permits a new distinct monotonic session. DLL rollback must
  therefore be executable against real kernel behavior in later integration,
  not only accepted by a user-mode fake.
- No claim/detach/set-configuration mechanics are added or claimed.
- A post-select/precommit cleanup/removal race has no persistent lower effect
  in Task 4; R46 is an explicit Task-6 transactional-claim rollback carry.

## DLL initialization

- Output is nulled before validation. Error codes and `FileModeInformation`
  overlapped-only validation are exact; the caller handle is never duplicated
  or closed.
- Event, immediate IOCTL, wait, and pending-completion failures preserve their
  meaningful error after cleanup. Protocol inconsistency maps to
  `ERROR_BAD_DEVICE`, allocation to `ERROR_NOT_ENOUGH_MEMORY`, and mode failure
  to `ERROR_INVALID_HANDLE`.
- `WAIT_FAILED` preserves the wait API's exact last error across event cleanup;
  only other unexpected wait results may use a generic local error.
- The wait fake records and checks the exact private event handle and varies at
  least two errors; wrong-handle waits or a hardcoded error fail the contract.
- Cleanup helpers deliberately clobber last error in the fake; production
  saves/restores the primary error. Pending sizing TRUE is classified as local
  protocol failure, not stale `ERROR_IO_PENDING`.
- Exactly two successful-path initialize IOCTLs occur: 72-byte size query and
  exact 211-byte full request, both with 24-byte zero-session inputs and local
  synchronous OVERLAPPED/event handling.
- The full request output length and snapshot allocation are each exactly the
  `total_size` advertised by the sizing header; a `total_size + 1` production
  mutation fails the contract.
- Exact size and allocation/output pointer identity are checked for every valid
  fixture total, including 211, 181, and 163. A conditional non-211 `+1`
  mutation fails.
- The first sizing completion is observably false with the exact
  insufficient-buffer mapping and bytes 72; a fake TRUE sizing call is a
  false-GREEN.
- Immediate and pending sizing/completion paths preserve the effective error
  before wait/event cleanup, require a successful wait, and reject every other
  error or byte count.
- An immediate failed overlapped sizing call reads its completion information
  from the local `OVERLAPPED.InternalHigh`; its fake leaves `lpBytesReturned`
  untouched. Pending completion uses the result/information channel exposed by
  `GetOverlappedResult`.
- Every sizing-header field and checked region/array relationship is validated
  before allocation; full-response metadata must match it except for the live
  nonzero session.
- A self-consistent total above `72 + UINT16_MAX` fails before allocation.
- Snapshot validation is independent and checked: header/returned size,
  nonoverlap/in-bounds offsets, exact descriptors/`wTotalLength`, record
  counts/order/index ranges/default alternate/endpoints. Publication occurs
  last.
- Production validation is generic and bounded rather than hardcoding the
  retained 211-byte MI05 fixture. A distinct valid non-MI05/low-speed fixture
  passes, while mutations of every region and record relationship fail.
  RELEASE uses the same local event/OVERLAPPED helper, never a NULL-overlapped
  request on the caller handle.
- Raw descriptors and packed records are walked in the same actual order;
  alternate ordering/grouping and per-alternate endpoint-address uniqueness
  are enforced without forbidding reuse across distinct alternates.
- Interface groups preserve descriptor order and need only be unique, not
  numerically sorted. A valid descending two-interface snapshot passes, a
  duplicate interface fails, and endpoint-address reuse across alternates
  passes.
- A nonadjacent `[5, 2, 5]` duplicate fails; reducing all-prior uniqueness to an
  adjacent-only comparison fails the contract.
- The raw-order and duplicate-endpoint counterexamples both execute. The latter
  changes the second raw endpoint's address plus its matching packed record,
  not descriptor length; removing either production check fails the contract.
- Packed record offsets are consumed without unaligned typed dereference;
  executable sanitizer/trap evidence would fail a cast of bytes 131/147/179.
- Precommit failures release zero times. Every failure after a returned live
  session releases exactly once with that session, frees temporary ownership,
  and leaves output null. Successful valid-default cleanup is balanced; Task 5
  ownership guarantees are not overclaimed.
- Snapshot- and root-allocation failures both report `ERROR_NOT_ENOUGH_MEMORY`;
  only the postcommit root failure sends the exact one-session rollback release.
- Retained MI05 endpoint records and descriptors agree on bulk type 2 and
  512-byte maximum packets; either-side mutations are executable failures.
- RELEASE IOCTL accounting is separate from private event closure; event and
  caller-device handles are distinguishable, and the fake supplies per-call
  immediate/pending/failure schedules rather than a single global result.
- Each release ties its exact request/device to the exact created event through
  `OVERLAPPED.hEvent` and one matching close, including failure variants.
- Pending release variants consume exactly one completion on the same device
  and private `OVERLAPPED` with the scheduled result/error; immediate and
  wait-failed variants consume zero completions.
- The user wrapper compiles and links every collected real production unit,
  including a future `io.c`, with consistent sanitizer flags.

## Evidence

- `task-04-initialize.patch` is the exact generated base/head diff over fourteen
  owned production/test paths.
- `task-04-initialize.sha256` has exactly fifteen project-root-relative entries:
  the fourteen owned paths plus the patch, excludes itself, and verifies 15/15.
- All evidence is explicitly offline fake/static. No Wine, prefix, device,
  sysfs USB, driver, stage/select/load, application, build, Git, install, or
  CP24 action is claimed.

Approve only if mutation of sizing, offset arithmetic, commit order, session,
release accounting, caller ownership, or fake-derived effects would make an
executable contract fail without accepting a harness failure.
