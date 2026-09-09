# CP33 Task 9 R135 retained-allocator correction — implementer report

Status: the bounded R135 function-contract correction is implemented.
Production remains frozen and Task 9 is not claimed complete. This workspace
is intentionally non-Git; it was not initialized and no commit was created.

## Scope and safety

Changed only:

- `tests/winusb_function_io_contract.c`
- this new `task-9-r135-implementer-report.md`

The binding support contract, bus-interface contract, every
production/support/wrapper/RANGE path, snapshots/manifests,
`task-9-report.md`, and `progress.md` were not edited. Work stayed offline and
host-only. No Wine/prefix, USB device, driver/build/staging, network, firmware,
preset/effect, or hardware action occurred. BAT0 capacity was the only sysfs
path read: 68/67 percent before editing and 62 percent before final focused,
retained, and sanitizer verification, always above the 10 percent stop gate.

## Immutable pre-edit identity

```text
sha256sum --check .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r134-head.sha256
cmp -s tests/winusb_function_io_contract.c \
  .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r134-head/tests/winusb_function_io_contract.c
cmp -s tests/wineusb_winusb_busif_contract.c \
  .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r134-head/tests/wineusb_winusb_busif_contract.c
sha256sum --check .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r132-frozen.sha256
```

Results: R134 head exit 0, 2/2 `OK`; both live-to-head comparisons exit 0;
frozen manifest exit 0, 14/14 `OK`. Starting identities:

```text
ad139419c758fe5b9aacd9c612bbb865f3baf96edc66aed42071f32df8b531f2  tests/winusb_function_io_contract.c
9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348  tests/wineusb_winusb_busif_contract.c
7af721f59ec7d9b50ae47ebfee6c18aa8f9abcc1b72ce88490abcca6c4c56fd4  task-9-r134-head.sha256
```

## Correction

R134's direct per-attempt `ExAllocatePool()` observer is unchanged. Its begin
function now also snapshots the shared `pool_allocations` counter. Its end
function first retains the direct zero-attempt assertion, then requires the
shared count to equal the snapshot. The same existing begin/end calls still
enclose exactly each of the two `complete_pending_task9_irp()` invocations and
remain disarmed during all intervening alternate-selection work. Reset clears
the added snapshot.

Both allocator families already update this shared counter. In particular, the
retained allocator used by textually included actual `main.c` increments it
before its failure branch, so the new lens observes successful and failed
helper-routed attempts without a source scan or expectation weakening.

## Substantive actual-main helper recreation mutant

A disposable tree copied the immutable R134 function test plus actual
`winusb.sys/main.c`, `session.c`, `transfer.c`, and `winusb_private.h`. Live
production and live binding support were never mutated. Manual mutant changes
used `apply_patch`:

- copied actual `main.c` defined allocation/free helpers; because `main.c` is
  textually compiled through binding support, both helpers used the retained
  allocator rename;
- copied actual `transfer.c` called those helpers from `transfer_completion()`;
- an explicit disposable-only arm bounded the recreation to the two pending
  FIFO completions, and an executable counter assertion required exactly four
  retained-route allocation calls;
- all four replacement objects were allocated before any admitted original was
  retired, preventing address reuse from contaminating the identity ledger;
- each completion copied and used its replacement transfer/URB pair, freed it
  through the `main.c` helper, then freed the matching admitted original pair
  through the normal transfer route. Outcomes, list effects, per-pair
  retirement, references, outstanding counts, and final global balance stayed
  intact.

Both R134 and R135 mutant variants used this compile/run command:

```text
cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -D__WINESRC__ \
  -Itests -I.io24-build/winusb-api-v1/dev-source/include \
  -I"$temporary_root/dlls/winusb.sys" \
  -I.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys \
  "$temporary_test" \
  "$temporary_root/dlls/winusb.sys/session.c" \
  "$temporary_root/dlls/winusb.sys/transfer.c" \
  -o "$temporary_contract"
"$temporary_contract" --control-descriptor
```

Immutable R134 observer result: compile exit 0; execution exit 1; exactly 203
existing feature failures. The exactly-four helper-call assertion passed;
R134's direct-attempt assertion added zero failures. Harness, compiler/linker,
and crash markers were zero. This is the executable false-green.

Corrected R135 observer result: compile exit 0; execution exit 1; exactly 204
failures. The exactly-four helper-call assertion passed, the direct-attempt
assertion stayed quiet, and the sole added failure was:

```text
FAIL control_completion_allocation_end:220: pool_allocations == control_completion_pool_allocations_before
```

Primary mutant delta: 203 -> 204, exactly one new shared-allocation-lens
failure. Harness, compiler/linker, and crash markers were zero.

An initial schedule heuristic in the disposable mutant was too broad and
produced exit 139 during mutant construction. It was discarded, replaced with
the exact disposable arm plus helper-call assertion above, and is not evidence.
No core artifact was present. The final primary mutant compiled and executed
without a crash.

## Failed retained-helper attempt probe

A second disposable transfer copy made one `main.c` helper call during the
first exact completion interval after setting the retained fake's
`fail_next_pool_allocation` flag. Executable assertions proved one helper call
and a null result. Result: compile exit 0; execution exit 1; 205 failures. The
direct-attempt lens stayed quiet, while the new shared snapshot added one exact
failure at line 220. The retained fake's documented pre-failure increment also
left its final allocation/free balance unequal, adding the expected existing
teardown balance failure. Thus even a failed helper attempt reaches the new
completion-scoped lens; the primary successful recreation mutant remains the
required only-one-new-failure delta.

All validated disposable sources, executables, and logs were removed from the
exact temporary root after evidence collection.

## Fresh focused and retained evidence

Battery before this phase: 62 percent.

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
```

Result: exit 1; actual production compiled/executed; 35 dispatches, 29 mode
IOCTLs, exactly 203 genuine named feature-boundary failures. Both completion
allocation lenses added zero failures. Harness, compiler/linker, and crash
markers: zero.

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --lifecycle
```

Result: exit 0; 12 dispatches, 0 mode IOCTLs, 0 failures. Harness,
compiler/linker, and crash markers: zero.

## Manual ASan/UBSan focused replay

Battery before this phase: 62 percent.

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

Result: compile exit 0; execution exit 1 with exactly 203 feature failures;
AddressSanitizer, UndefinedBehaviorSanitizer, runtime-error, and LeakSanitizer
markers: zero. Harness, compiler/linker, and crash markers: zero. Validated
temporary sanitizer artifacts were removed.

## Final identities and exact R134 delta

```text
31c3070fd206088d91b383157bc09b98bc40abd956efb9fcef2806e17cc090aa  tests/winusb_function_io_contract.c
9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348  tests/wineusb_winusb_busif_contract.c
```

The exact unified diff from immutable R134 uses labels
`r134-head/tests/winusb_function_io_contract.c` and
`live/tests/winusb_function_io_contract.c`:

```text
dbad104e94f3dc7c1f582fb3fbb3e05d27546d5316a7582bf0e3d3d262916e73  34 lines
```

Self-review found only one production-facing expectation added: shared
allocation count must not change during either exact completion interval.
R134's per-attempt observer, admission journal, per-pair retirement/outcomes,
list/outstanding/reference evidence, and exact alternate exclusions remain.
No source scan was used as feature evidence. Production reopen, successor
snapshot/controller evidence, and both independent reviews remain outside this
implementer scope.

Final post-report integrity replay at BAT0 capacity 61 percent: immutable R134
head exit 0, 2/2 `OK`; frozen manifest exit 0, 14/14 `OK`; function and
bus-interface hashes remained the two values above; live mutant-residue count
was zero.
