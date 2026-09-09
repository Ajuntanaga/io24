# CP33 Task 9 R132 successor evidence correction — implementer report

Status: test-only R132 correction implemented. Production remains frozen and
Task 9 is not claimed complete. The workspace is intentionally non-Git; no
repository was initialized and no commit was created.

## Scope and safety

Changed only:

- `tests/winusb_function_io_contract.c`
- `tests/wineusb_winusb_busif_contract.c`
- this implementer report

No production, wrapper, support, RANGE, snapshot, manifest, progress, or
controller report path was changed. All execution was offline and host-only.
No Wine, prefix, USB/sysfs device path, staging/build selection, driver,
Universal Control, Voice FX, firmware, or network action was used. BAT0 was
checked before each meaningful verification phase and read `100` every time,
above the mandatory stop threshold.

The immutable base was checked before editing and again after the final mutant
restore:

```text
sha256sum --check .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r132-base.sha256
```

Result both times: exit 0, 2/2 snapshot paths `OK`.

## Required pre-edit RED

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
```

Result: exit 1, actual production compiled/executed, 34 dispatches, 29 mode
IOCTLs, 199 feature failures, no usage/prerequisite/compiler/link/crash/harness
exit 2.

```text
tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
```

Result: exit 1, actual `wineusb.c` compiled/executed, exactly 12 expected
cross-interface permit failures, no harness exit 2.

## Implemented evidence

Function contract:

- expanded the fake lower pending journal to retain two simultaneous original
  caller IRPs in FIFO order, with multiplicity-aware file/list/object-reference
  completion checks;
- queued two generic interface-recipient controls for interface 6, proved root
  interface 5 remains independent, completed only the first, proved interface 6
  stays blocked, then completed the second and required interface 6 to become
  permitted; the comment explicitly names the Boolean-accounting defect;
- after the real alternate IOCTL established the current pipe map, dispatched
  an endpoint-recipient control through the exact atomic FAST_MUTEX rendezvous,
  changed that real map while retaining the mutex, and required post-lock
  rejection before lower submission; the comment names pre-lock endpoint
  lookup;
- made thread creation and join failures terminal harness exit-2 paths. A
  failed creation safely releases the held mutex and clears the observation
  target; a failed join immediately exits without reading worker result,
  schedule effect, or worker-owned state. The comment names post-failed-join
  shared-state access.

Actual-lower contract:

- queues valid root-5 and interface-6 controls in both orders, explicitly
  proves the intended first/later order, and targets the later conflicting
  entry so first-entry-only classification cannot pass;
- snapshots exact pre-SELECT membership/order. Busy SELECT requires exact
  equality and absence of its own IRP. Permitted pending SELECT requires every
  prior entry in order followed by exactly one local SELECT;
- adds a one-shot exact-`wineusb_cs` fake observation that inserts a valid
  caller-owned root conflict only for the duration of that critical section;
- records membership assertions before retiring only fixture-owned entries.
  It makes no cancellation, cleanup, teardown, removal, or production-owned
  retirement claim.

## Final focused and retained evidence

Battery immediately before this phase: `100`.

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
```

Result: exit 1, 35 dispatches, 29 mode IOCTLs, 203 genuine feature failures,
no harness/compiler/link/crash marker.

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --lifecycle
```

Result: exit 0, 12 dispatches, 0 mode IOCTLs, 0 failures.

```text
tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
```

Result after final mutant restore: exit 1, exactly 12 expected cross-interface
permit failures and no harness marker.

```text
tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source --red
```

Result after final mutant restore: exit 0,
`WineUSB WinUSB metadata bus-interface contract: pass`.

## Manual ASan/UBSan evidence

Battery immediately before this phase: `100`. The wrapper's compile recipe was
replayed manually with the focused sources and these additional flags:

```text
cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -D__WINESRC__ \
  -fsanitize=address,undefined,alignment -fno-sanitize-recover=all \
  -fno-omit-frame-pointer \
  -Itests -I.io24-build/winusb-api-v1/dev-source/include \
  -I.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys \
  -I.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys \
  tests/winusb_function_io_contract.c \
  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c \
  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/transfer.c \
  -o "$temporary_directory/contract"
ASAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=1:detect_leaks=1 \
UBSAN_OPTIONS=halt_on_error=1:exitcode=1 \
  "$temporary_directory/contract" --control-descriptor
```

Result: compile exit 0; focused execution exit 1 with the same 203 feature
failures; zero AddressSanitizer, UndefinedBehaviorSanitizer, runtime-error, or
LeakSanitizer markers. Temporary output was deleted afterward. No TSan result
was used.

## Bounded mutants

Each mutant was applied only to an owned C contract with `apply_patch`, run
offline through the same production boundary, then removed with `apply_patch`.

1. Early-clear/count mutant: inserted a second local completion immediately
   after completing the first of the two interface-6 requests, then ran the
   function focused command. Exit 1; failures changed 203 -> 208, including the
   required post-first-completion busy and second-IRP identity/count checks.
2. Endpoint bypass mutant: bypassed only the endpoint rendezvous and post-lock
   result checks, then ran the function focused command. Exit 1; failures
   changed 203 -> 201, exactly two fewer, proving both new endpoint lenses
   execute.
3. Forced join-failure mutant: forced the first successful `thrd_join` result
   through the terminal branch, then ran the function focused command. Exit 2
   with `HARNESS: Task-9 mutex worker join failed` followed by wrapper harness
   exit 2; no schedule/result assertion executed afterward.
4. Locked-list bypass mutant: disabled the one-shot exact-critical-section
   injection, then ran the actual-lower focused command against the final
   cleanup head. Exit 1; failures changed 12 -> 16, including wrong pending
   status, missing busy status, changed exact membership, and missing critical-
   section span.
5. Permitted-SELECT ownership bypass: bypassed only the exact append-once
   assertion, then ran the actual-lower focused command. Exit 1; failures
   changed 12 -> 9, exactly the three permitted cross-interface SELECT lenses.
6. Complete-list order mutant: moved the intended first child behind the later
   conflicting child in each two-entry schedule, then ran the actual-lower
   focused command. Exit 1; failures changed 12 -> 14, with one exact-order
   failure for each list order.

`rg -n "R132 MUTANT"` over both owned files was empty before final evidence.

## Final identity and self-review

```text
4d7cd4939eecab0b16fbc929c6d014714a3615e27da1140f6a99ca467c74f146  tests/winusb_function_io_contract.c
2ea41490d56a5b5071f341d1952f9da918890f6138639405f06c22187c7e6d0e  tests/wineusb_winusb_busif_contract.c
```

Self-review found no writes outside the three allowed paths. All accepted R131
witnesses remain. Expectations are derived from the Task-9 per-interface
ownership and original-IRP contracts, and execute included production through
the existing fake WDM/lower boundaries. Temporary mutants are absent; the
immutable 2/2 base still verifies. The focused modes intentionally remain
feature RED because production is frozen. Independent review, controller
freezing, and any later production unlock remain outstanding controller gates.

## R132 targeted-review correction round 1

Status: the four requested test-only corrections were implemented in the same
two live C contracts. Production remains frozen. This non-Git workspace was not
initialized and no commit was created. No controller/reviewer artifact,
immutable manifest/snapshot, production/support/wrapper/RANGE path,
`task-9-report.md`, or `progress.md` was changed.

Safety remained offline and hardware-free. No Wine, prefix, USB/sysfs device,
staging/build selection, UC/Voice FX, firmware, or network action was used.
BAT0 read `96` (`Discharging`) before the correction verification work and `93`
before the final focused/retained, sanitizer, and manifest phases, above the
mandatory stop threshold.

### Corrections

Function contract:

- The two pending MI06 requests now use one four-allocation journal. Their
  lower completion contexts and URBs are captured immediately after each
  admission, required nonnull and pairwise distinct, and required live in the
  allocation ledger.
- The fake lower journal retains each request's exact context/URB pair. The
  completion boundary requires the original IRP's lower stack to carry that
  exact pair.
- Request one stores `USBD_STATUS_SUCCESS`; request two stores
  `USBD_STATUS_TIMEOUT`. FIFO completion must deliver `STATUS_SUCCESS` only to
  IRP one and `STATUS_IO_TIMEOUT` only to IRP two.
- After completion one, only pair one must have one retirement while pair two
  remains live. After completion two, both pairs must have retired exactly
  once. The retained file-reference, outstanding-count, list, and alternate
  selection checks remain in place.

Actual-lower contract:

- The exact included-production `InsertTailList` call is interposed. While a
  busy SELECT is armed, passing that SELECT's exact list entry to the insertion
  boundary is counted and required to remain zero, catching transient
  enqueue/dequeue even when final membership and order are unchanged.
- On exit from the injected exact `wineusb_cs`, the removed fixture-owned
  conflict's setup packet is changed from root recipient to interface 6. The
  test proves the still-live URB is no longer a root-5 conflict and restores
  the fixture fields after dispatch. Thus an unlocked pointer capture cannot
  observe the former conflict.
- The two accepted later-conflict schedules remain, and two mirror schedules
  now place the sole conflict first with a later nonconflicting child for the
  same target. A multi-entry classifier that reads only `irp_list.Blink` fails
  both mirrors.

### Focused RED and retained evidence after final mutant restore

Battery immediately before this phase: `93`, `Discharging`.

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
```

Result: exit 1; actual production compiled/executed; 35 dispatches, 29 mode
IOCTLs, exactly 203 intended feature failures; no compiler, linker, crash, or
harness-exit-2 marker.

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --lifecycle
```

Result: exit 0; 12 dispatches, 0 mode IOCTLs, 0 failures.

```text
tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
```

Result: exit 1; actual included `wineusb.c` compiled/executed; exactly 12
expected cross-interface permit failures; no compiler, linker, crash, or
harness-exit-2 marker.

```text
tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source --red
```

Result: exit 0; `WineUSB WinUSB metadata bus-interface contract: pass`.

### Manual ASan/UBSan marker check

Battery immediately before this phase: `93`, `Discharging`. The established
manual focused recipe was replayed:

```text
cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -D__WINESRC__ \
  -fsanitize=address,undefined,alignment -fno-sanitize-recover=all \
  -fno-omit-frame-pointer \
  -Itests -I.io24-build/winusb-api-v1/dev-source/include \
  -I.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys \
  -I.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys \
  tests/winusb_function_io_contract.c \
  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c \
  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/transfer.c \
  -o "$temporary_directory/contract"
ASAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=1:detect_leaks=1 \
UBSAN_OPTIONS=halt_on_error=1:exitcode=1 \
  "$temporary_directory/contract" --control-descriptor
```

Result: compile exit 0; focused execution exit 1 with the same 203 intended
feature failures; zero `AddressSanitizer`, `UndefinedBehaviorSanitizer`,
`runtime error:`, or `LeakSanitizer` markers. The temporary executable and logs
were removed afterward.

### Required bounded executable mutants

Every mutant was applied only to an owned live C contract with `apply_patch`,
executed offline through the same production boundary, and removed with
`apply_patch` before final evidence.

1. Swapped context/URB pairs: swapped both live lower-stack pairs between the
   two original IRPs before FIFO completion. Function focused exit remained 1;
   failures changed 203 -> 213. Exact completion-pair, distinct per-IRP status,
   and pairwise retirement checks all detected the swap.
2. Reused context/URB pair: made request two present request one's captured
   record/URB pair at the post-admission ownership lens, then restored it before
   completion to avoid intentionally double-freeing the fixture. Function
   focused exit remained 1; failures changed 203 -> 206, precisely failing
   distinct context, distinct URB, and request-two exact-stack ownership.
3. Post-unlock classification: suppressed only the lock-exit setup-packet
   invalidation. Actual-lower focused exit remained 1; failures changed 12 ->
   13, adding only `removed conflict remained classifiable after wineusb_cs
   release`.
4. Transient busy SELECT insertion: called the interposed production insertion
   boundary for each armed busy SELECT, immediately removed the entry, and left
   final list snapshots unchanged. Actual-lower focused exit remained 1;
   failures changed 12 -> 26, adding exactly one transient-insertion failure for
   each of the 14 busy schedules.
5. Last-entry-only classification: temporarily interposed the production
   `IsListEmpty` decision so a multi-entry list was classified solely from
   `irp_list.Blink`. Actual-lower focused exit remained 1; failures changed 12
   -> 20. Only the two new conflict-first/nonconflicting-tail mirror schedules
   added failures: wrong pending result, missing busy URB status, one transient
   insertion, and changed exact membership for each mirror.

The following final residue check was empty:

```text
rg -n 'R132 MUTANT|reused_saved|busy_select_target|io24_IsListEmpty' \
  tests/winusb_function_io_contract.c tests/wineusb_winusb_busif_contract.c
```

### Immutable identities, live hashes, and exact rejected-head diff

```text
sha256sum --check .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r132-base.sha256
sha256sum --check .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r132-head.sha256
sha256sum --check .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r132-frozen.sha256
```

Results: all exit 0; base 2/2 `OK`, rejected head 2/2 `OK`, frozen 14/14
`OK`.

```text
f5099dd8d9ec9e9a5a2a632f5e9411fe1390ab027ad63a9c70d819af0b85e508  tests/winusb_function_io_contract.c
9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348  tests/wineusb_winusb_busif_contract.c
1f465399f426409b8c0963d09962d605e3edd7c8d162e50061f69e3920dae162  task-9-r132-base.sha256
2bf2c60c9f0c250051c09ddb6f1e9eb49ba6f149562360cdab585b374fcd0cc1  task-9-r132-head.sha256
343e2929b6f03cd9af0b2f957e2edfbfef4dc3fd0c86126906c75c6882d08a53  task-9-r132-frozen.sha256
```

The exact unified diff from the verified rejected head was generated with
`diff -u`, labels `rejected-head/tests/<file>` and `live/tests/<file>`, in
function-contract then actual-lower-contract order. Its combined identity is:

```text
12bbb5f66f72f1a3916a28cac2658fd653f8b194563fed8b6eab55b6217a28f3  474 lines
```

Per-file exact diff identities are:

```text
ef3705c99bdd52b9922a55f9a10306b875510c40b6824d061283d61099cfc8b2  winusb_function_io_contract.c  295 lines
5d6a65b00c99a0066e41189982c46ad354bbfe139f1154c9c92dce6a35c81457  wineusb_winusb_busif_contract.c  179 lines
```

Self-review of that exact diff found all accepted R131/R132 witnesses retained,
all new assertions executing included production through existing fake
boundaries, and no claim beyond test evidence. The two C files were stable
through final focused, retained, sanitizer, manifest, hash, and diff checks.
Independent reviewer/controller approval and any production-reopen decision
remain outside this implementer scope.
