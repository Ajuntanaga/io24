# CP33 Task 3 implementation report

## Status

DONE. The CP33 development source now provides the additive metadata interface
v2, the lower cached-speed callback, exact upper-FDO v2 consumption, and the
per-file create/cleanup/close/removal lifecycle. All three prescribed GREEN
gates pass, the actual lower `wineusb.c` compiles in the host harness, and the
eight-entry Task 3 checkpoint verifies.

Commits: n/a (intentionally non-Git workspace).

## Implementation summary

- Preserved the metadata-interface v1 declaration and query behavior while
  appending the exact version-2 constant, callback typedef, and field layout.
- Added exact v2 query validation. Exact size/version succeeds with one
  reference; undersized, oversized, v1-sized/v2-version, unsupported-version,
  and incomplete-routine requests fail before caller-output mutation.
- Added `wineusb_metadata_get_speed()` in the lower WineUSB PDO. It recovers
  `struct usb_device` from the unchanged metadata-source `BusContext` using
  `CONTAINING_RECORD`, returns `HighSpeed` only from `device->high_speed`,
  otherwise `LowSpeed`, and returns `STATUS_DEVICE_NOT_CONNECTED` without
  writing the output after removal. It performs no descriptor request/read.
- Changed the upper function FDO to request the exact v2 interface, validate
  every returned member, call both getters, accept only canonical low/high
  speed, cache interface version and speed, and dereference the acquired
  interface on every post-query exit.
- Added `winusb_private.h` with the exact six-state `winusb_file_state`, exact
  required `winusb_file` member order/types, the retained device state, and the
  shared extended `winusb_device`.
- Initialized device spin lock, file list/count, signaled removal event,
  metadata-interface version, and cached speed before publication.
- Implemented create only for `WINUSB_DEVICE_STARTED`, with allocation and
  complete field initialization before locked insertion. `FsContext` is
  published only after insertion; allocation and state-race failures leave it
  unchanged.
- Implemented matching-context cleanup, admission closure through
  releasing/closing state, zero-outstanding signaling, idempotent close,
  one-time unlink/count decrement, outstanding drain before free, and
  surprise/remove admission closure. Removal waits for the open-file ownership
  event before deleting the FDO.
- Updated the retained fake narrowly under controller ruling R23: exact v2
  size/version/callback/context checks, speed/failure cases, balanced
  dereference, cached-version/speed checks, and host fakes for the new kernel
  primitives. The real driver inclusion and terminal CP32 pass line remain.

## TDD evidence

### Discarded harness attempts

The first test-only RED attempt was not accepted: the new bus test invoked an
absent callback after detecting it and exited 139, while the lifecycle test
invoked an absent cleanup dispatch and was normalized to harness exit 2. Only
test continuation guards were changed. The commands were rerun before any
production edit, producing the genuine feature RED below.

### Accepted focused RED before production

Commands:

```bash
IO24_DEV_SOURCE=.io24-build/winusb-api-v1/dev-source
tests/wineusb_winusb_busif_contract.sh "$IO24_DEV_SOURCE"
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --lifecycle
```

Bus-interface output:

```text
FAIL test_v2_query_and_speed_balance:267: v2 query returned 0xffffffffc00000bb
FAIL test_v2_query_and_speed_balance:268: v2 wrong size 0xa5a5
FAIL test_v2_query_and_speed_balance:270: v2 wrong version 42405
FAIL test_v2_query_and_speed_balance:271: v2 wrong context
FAIL test_v2_query_and_speed_balance:272: v2 wrong reference routine
FAIL test_v2_query_and_speed_balance:273: v2 wrong dereference routine
FAIL test_v2_query_and_speed_balance:274: v2 wrong GUID getter
FAIL test_v2_query_and_speed_balance:275: v2 wrong speed getter
FAIL test_v2_query_and_speed_balance:278: v2 query callback balance 0/0/0
9 WineUSB metadata bus-interface check(s) failed
```

Exit: 1. The pre-existing v1 and metadata validation cases produced no
failure; only the missing v2 success path failed.

Lifecycle output:

```text
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--lifecycle dispatches=8 mode-ioctls=0 last-ioctl=0 last-status=0 failures=17
```

Exit: 1. The real scoped `main.c` compiled and ran, the retained CP32 boundary
passed first, and the missing per-file lifecycle caused the feature failure.

### Prescribed GREEN

Commands:

```bash
IO24_DEV_SOURCE=.io24-build/winusb-api-v1/dev-source
tests/wineusb_winusb_busif_contract.sh "$IO24_DEV_SOURCE"
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --lifecycle
tests/winusb_function_binding_contract.sh "$IO24_DEV_SOURCE"
```

Exact output:

```text
WineUSB WinUSB metadata bus-interface contract: pass
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--lifecycle dispatches=12 mode-ioctls=0 last-ioctl=0 last-status=0 failures=0
CP32 winusb function-binding lifecycle checks passed
```

All three commands exited 0 with `-Wall -Wextra -Werror` and no diagnostics.

Additional host-only compile of the harness that includes the actual scoped
lower `wineusb.c`:

```text
actual wineusb.c host compile: pass
```

This was compilation only; it did not link/run Wine, a driver, or a USB path.

## Behavioral coverage

- v1 exact success verifies size, version, unchanged `BusContext`, function
  pointers, one reference, matching dereference, and guard preservation.
- v2 exact success verifies the appended layout, speed callback, unchanged
  context, guard preservation, and 1/1 reference balance.
- v2 undersize, oversize, v1-size/v2-version, and unsupported version verify
  whole-output nonmutation and zero callback/reference activity.
- The upper binding contract rejects returned wrong size/version, missing GUID
  or speed callbacks, GUID failure, speed failure, and noncanonical speed; all
  post-query cases retain balanced references and no FDO publication.
- Lifecycle mode verifies pre-start rejection, two distinct initialized file
  contexts, allocation failure without `FsContext` publication, cross-file
  context rejection, cleanup admission closure and idempotence, close clear,
  one-time list/count/free behavior, repeated-close safety, surprise-removal
  state, post-removal rejection, and final removal-event balance.
- Retained start/stop/restart/surprise/remove behavior passes with the exact
  terminal line `CP32 winusb function-binding lifecycle checks passed`.

## Files changed

Production:

- `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/winusb_busif.h`
- `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/winusb_busif.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/wineusb.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h` (new)

Contracts:

- `tests/wineusb_winusb_busif_contract.c`
- `tests/winusb_function_io_contract.c`
- `tests/winusb_function_binding_contract.c` (narrow R23 fake update)

Evidence/report:

- `re/winusb-api-v1/logs/task-03-lifecycle.sha256`
- `.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-3-report.md`

No wrapper, production/test path outside the authorized R23 scope,
patch-check source, immutable CP32 path, plan, handoff, or checkpoint from an
earlier task was edited by this implementation.

## Checkpoint verification

`task-03-lifecycle.sha256` contains exactly eight project-root-relative
entries: five production paths and three contract sources. It does not hash
itself.

Command:

```bash
sha256sum -c re/winusb-api-v1/logs/task-03-lifecycle.sha256
```

Output:

```text
.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/winusb_busif.h: OK
.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/winusb_busif.c: OK
.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/wineusb.c: OK
.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c: OK
.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h: OK
tests/wineusb_winusb_busif_contract.c: OK
tests/winusb_function_io_contract.c: OK
tests/winusb_function_binding_contract.c: OK
```

## Self-review

- The immutable Task 3 base diff shows no edit inside the pre-existing v1
  interface declaration. The v1 query branch still accepts its historical
  minimum size, writes the identical six fields, retains the same context,
  and references once.
- The v2 query uses exact size equality; it performs every validation before
  the structure assignment or reference callback.
- Lower speed derives the enclosing USB device from the metadata-source
  member, reads only removal/high-speed state under the existing critical
  section, and assigns the caller byte only on success.
- Upper v2 outputs are local until both callbacks and canonical-speed
  validation succeed. Dereference precedes every return after a successful
  query.
- Every started/removing state read/write used for file admission is protected
  by the device spin lock. File-list mutation and count/event transitions are
  under that same lock; per-file state/outstanding inspection uses its lock.
- File allocation initializes the exact required state, session, reference,
  outstanding count, event, transfer list, snapshot, and interface members.
- Cleanup never frees. Close clears publication and unlinks once, waits on the
  zero-outstanding event when needed, and repeated close sees null context.
- Surprise/remove mark all linked contexts removed. The FDO removal path waits
  for file count to reach zero through `removal_event` before teardown.
- The eight checkpoint entries match the R23-expanded task path list and
  verify from the project root.
- No Wine invocation, prefix access/creation, sysfs USB inspection, USB-node
  access, device operation, build/driver stage/select/load, UC/Voice FX start,
  installation, Git action, or CP24 retry occurred.

## Concerns

No known implementation blocker. The original brief's checkpoint sentence
still says five production plus two contract sources, while the later R23
controller ruling and updated rubric/path list authorize three contract
sources and require exactly eight entries; this report and seal follow the
newer ruling. Full Wine builds and all live/device validation remain outside
this offline Task 3 authorization.

---

# Fix round 1 — 2026-08-24

This section is appended to the frozen round-0 report. It follows the newer
R24 ruling: the bus wrapper is an authorized fourth contract path and the
final task-local checkpoint has exactly nine entries.

## Review findings closed

1. **Removal ownership lasts through drain and destruction.** `driver_close`
   now leaves `file_count` nonzero while it waits for
   `zero_outstanding`, unlinks the context, frees its owned allocations, and
   frees the file context. Only then does it decrement `file_count` and signal
   `removal_event`. Thus the REMOVE waiter cannot proceed to final device
   destruction while the closer is still draining or destroying the context.
   The closing path performs no device access after the removal-state signal.
2. **The behavioral contracts no longer permit a false lifecycle or speed
   GREEN.** The wait fake now fails unsignaled waits unless a deterministic
   hook performs the scheduled work. Lifecycle mode starts REMOVE with one
   real file and one nonzero outstanding count. Its nested close/drain hook
   observes `file_count == 1`, an unsignaled removal event, and an unfreed file
   while outstanding work remains; it then drains the work and requires the
   free to precede the zero-count/removal signal. The bus contract includes
   the actual lower `wineusb.c`, obtains the real static speed callback through
   the production v2 query, and calls it using the metadata-source
   `BusContext`. It observes enclosing-device containment, `LowSpeed` and
   `HighSpeed`, both removed-state failures, and byte-for-byte output
   nonmutation on failure.
3. **Metadata v1 has an explicit retained success regression.** The binding
   fake additively serves exact v1 and v2 requests. The v1 test validates exact
   size/version, context, callbacks, GUID result, guard bytes, and balanced
   reference/dereference. The terminal retained line remains exactly
   `CP32 winusb function-binding lifecycle checks passed`.
4. **Every context-creating retained mode closes before REMOVE.** Session,
   alternate, policy, and transfer modes now run CLEANUP and CLOSE whenever
   `FsContext` remains published, require it to become null, then REMOVE, and
   require zero wait failures plus equal pool allocations/frees. Their current
   nonzero exits remain the expected later-task IOCTL feature REDs; no added
   lifecycle or leak assertion fails.

## Test-first RED evidence

The lifecycle contract changes were applied before the production fix.

Command:

```bash
tests/winusb_function_io_contract.sh \
  .io24-build/winusb-api-v1/dev-source --lifecycle
```

Output and exit:

```text
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--lifecycle dispatches=12 mode-ioctls=0 last-ioctl=0 last-status=0 failures=2
fix-round lifecycle RED exit=1
```

Those two failures were the intended observations that the then-current close
path had already decremented `file_count` and signaled `removal_event` when the
nonzero-outstanding drain began. There was no compile or harness failure.

The actual-lower speed and explicit-v1 additions close missing coverage rather
than a known production defect: both passed against the already-correct Task 3
metadata implementation, so no artificial RED was manufactured for them.

## Final prescribed GREEN gates

Commands:

```bash
IO24_DEV_SOURCE=.io24-build/winusb-api-v1/dev-source
tests/wineusb_winusb_busif_contract.sh "$IO24_DEV_SOURCE"
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --lifecycle
tests/winusb_function_binding_contract.sh "$IO24_DEV_SOURCE"
```

Output:

```text
WineUSB WinUSB metadata bus-interface contract: pass
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--lifecycle dispatches=12 mode-ioctls=0 last-ioctl=0 last-status=0 failures=0
CP32 winusb function-binding lifecycle checks passed
FINAL_GATE_EXITS bus=0 lifecycle=0 binding=0
```

All three wrappers compile their host contracts with `-Werror`. The bus wrapper
classifies missing source input as harness failure; the focused probe produced:

```text
HARNESS: missing WineUSB WinUSB metadata bus-interface contract input: /definitely/missing/io24-source/dlls/wineusb.sys/winusb_busif.h
MISSING_INPUT_EXIT=2
```

## Retained mode cleanup evidence

Commands:

```bash
for mode in --session --alternate --policy --transfer; do
  tests/winusb_function_io_contract.sh \
    .io24-build/winusb-api-v1/dev-source "$mode"
  printf '%s exit=%d\n' "$mode" "$?"
done
```

Output:

```text
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--session dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0xffffffffc00000bb failures=4
--session exit=1
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--alternate dispatches=5 mode-ioctls=2 last-ioctl=0x22200c last-status=0xffffffffc00000bb failures=4
--alternate exit=1
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--policy dispatches=5 mode-ioctls=2 last-ioctl=0x222014 last-status=0xffffffffc00000bb failures=4
--policy exit=1
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--transfer dispatches=5 mode-ioctls=2 last-ioctl=0x222022 last-status=0xffffffffc00000bb failures=4
--transfer exit=1
```

The unchanged count of four expected feature assertions in each retained mode,
together with the new teardown's zero wait-failure and allocation/free balance
checks, demonstrates that cleanup/close/remove contributes no hidden failure.

## Fix-round changed files

Production:

- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c`

Contracts:

- `tests/wineusb_winusb_busif_contract.c`
- `tests/wineusb_winusb_busif_contract.sh`
- `tests/winusb_function_io_contract.c`
- `tests/winusb_function_binding_contract.c`

Evidence:

- `re/winusb-api-v1/logs/task-03-lifecycle.sha256`
- `.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-3-report.md`

The other four sealed production paths are unchanged from the frozen round-1
base. No path outside fix-round ownership was edited.

## Final nine-entry checkpoint

Verification command:

```bash
manifest=re/winusb-api-v1/logs/task-03-lifecycle.sha256
count=$(wc -l < "$manifest")
printf 'ENTRY_COUNT=%s\n' "$count"
test "$count" -eq 9
if rg -n 'task-03-lifecycle\.sha256' "$manifest"; then
  exit 1
else
  printf '%s\n' 'SELF_REFERENCE=absent'
fi
sha256sum -c "$manifest"
```

Output:

```text
ENTRY_COUNT=9
SELF_REFERENCE=absent
.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/winusb_busif.h: OK
.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/winusb_busif.c: OK
.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/wineusb.c: OK
.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c: OK
.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h: OK
tests/wineusb_winusb_busif_contract.c: OK
tests/wineusb_winusb_busif_contract.sh: OK
tests/winusb_function_io_contract.c: OK
tests/winusb_function_binding_contract.c: OK
```

## Fix-round self-review and concerns

- The close path retains device-removal ownership until no outstanding work or
  file-owned allocation survives; only the final zero-count transition can
  release REMOVE.
- Actual production lower code, not a copied helper, supplies the tested speed
  callback. The query result is the only route used to call it.
- The bus wrapper retains `-Werror`; only source-wide unused-variable and host
  missing-wide-character-prototype warnings from otherwise garbage-collected
  `wineusb.c` paths are suppressed.
- The explicit v1 regression is additive and does not replace the v2 upper-FDO
  behavior.
- No Wine invocation, Wine prefix access/creation, sysfs or USB-node access,
  USB/device operation, build/driver stage/select/load, UC/Voice FX start,
  installation, Git action, full matrix/build, or CP24 retry occurred.

No Task 3 implementation blocker remains. Session/alternate/policy/transfer
functional IOCTL assertions remain RED for their assigned later tasks; this
round only requires and now verifies their leak-free per-file teardown.

---

# Fix round 2 — 2026-08-24

## Narrow test-only change

`tests/wineusb_winusb_busif_contract.c` now executes two additional invalid-
argument cases through `GetDeviceSpeed` returned by the actual included
`wineusb.c` v2 query:

- valid metadata-source context plus null output returns
  `STATUS_INVALID_PARAMETER`;
- null context plus a `0x3c` output sentinel returns
  `STATUS_INVALID_PARAMETER` and leaves the sentinel unchanged.

Both calls also require the enclosing `usb_device` snapshot and the query
guard bytes to remain unchanged. The query-acquired interface is dereferenced
exactly once after all callback cases. No callback was copied or reimplemented,
and no source-text assertion was added.

This is characterization coverage for already-present production null guards,
and production was frozen for this round, so the valid new contract passed
immediately. A production mutation that removes the null-output guard fails the
first status assertion; removal of the null-context guard fails or crashes the
second case, and an erroneous failure-path store fails the literal sentinel
assertion.

The first compile after editing was not accepted because the test-local
snapshot declaration landed in the adjacent test function. Exact harness
output was:

```text
/home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/tests/wineusb_winusb_busif_contract.c: In function ‘test_actual_lower_speed_callback’:
/home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/tests/wineusb_winusb_busif_contract.c:383:5: error: ‘before’ undeclared (first use in this function)
  383 |     before = device;
      |     ^~~~~~
/home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/tests/wineusb_winusb_busif_contract.c:383:5: note: each undeclared identifier is reported only once for each function it appears in
HARNESS: compiling actual wineusb.c metadata bus-interface contract failed
exit=2
```

The declaration was corrected in the test only before any result was accepted.

## Round-2 GREEN gates

Commands:

```bash
IO24_DEV_SOURCE=.io24-build/winusb-api-v1/dev-source
tests/wineusb_winusb_busif_contract.sh "$IO24_DEV_SOURCE"
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --lifecycle
tests/winusb_function_binding_contract.sh "$IO24_DEV_SOURCE"
```

Exact output:

```text
WineUSB WinUSB metadata bus-interface contract: pass
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--lifecycle dispatches=12 mode-ioctls=0 last-ioctl=0 last-status=0 failures=0
CP32 winusb function-binding lifecycle checks passed
ROUND2_GATE_EXITS bus=0 lifecycle=0 binding=0
```

## Scope and checkpoint

The frozen `task-3-round-1-head` manifest verified 10/10 before editing. A
post-change comparison against its ten snapshotted paths reported only these
two changed paths:

- `tests/wineusb_winusb_busif_contract.c`
- `re/winusb-api-v1/logs/task-03-lifecycle.sha256`

This report is the third and final authorized changed path for fix round 2:

- `.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-3-report.md`

All five production paths, the bus wrapper, lifecycle contract, and retained-
binding contract remain byte-identical to `task-3-round-1-head`.

The lifecycle seal retains the same nine path names, does not hash itself, and
changes only the bus-contract source digest. Verification output:

```text
ENTRY_COUNT=9
SELF_REFERENCE=absent
.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/winusb_busif.h: OK
.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/winusb_busif.c: OK
.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/wineusb.c: OK
.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c: OK
.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h: OK
tests/wineusb_winusb_busif_contract.c: OK
tests/wineusb_winusb_busif_contract.sh: OK
tests/winusb_function_io_contract.c: OK
tests/winusb_function_binding_contract.c: OK
```

No production, wrapper, other-test, controller, snapshot, or other artifact was
edited. No Wine invocation, prefix access/creation, USB or sysfs/device access,
driver/build/load/stage/select action, full build/matrix, CP24 retry, Git
action, installation, or external action occurred. No round-2 concern remains.
