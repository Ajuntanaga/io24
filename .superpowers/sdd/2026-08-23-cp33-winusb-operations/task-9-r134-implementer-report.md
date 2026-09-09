# CP33 Task 9 R134 completion-allocation correction — implementer report

Status: the bounded R134 function-contract correction is implemented.
Production remains frozen and Task 9 is not claimed complete. The workspace is
intentionally non-Git; it was not initialized and no commit was created.

## Scope and safety

Changed only:

- `tests/winusb_function_io_contract.c`
- this new `task-9-r134-implementer-report.md`

`tests/wineusb_winusb_busif_contract.c`, all production/support/wrapper/RANGE
paths, every snapshot/manifest, `task-9-report.md`, and `progress.md` were not
edited. All work was offline and host-only. No Wine, prefix, USB/sysfs device,
driver/build/staging, network, firmware, preset, or effects action was used.
The only sysfs reads were the explicitly allowed BAT0 capacity reads. Capacity
was 81/80 percent before editing, 77 percent before focused/retained and
sanitizer verification, and never approached the 10 percent stop threshold.

## Immutable pre-edit identity

Commands:

```text
sha256sum --check .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r133-head.sha256
cmp -s tests/winusb_function_io_contract.c \
  .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r133-head/tests/winusb_function_io_contract.c
cmp -s tests/wineusb_winusb_busif_contract.c \
  .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r133-head/tests/wineusb_winusb_busif_contract.c
sha256sum --check .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r132-frozen.sha256
```

Results: R133 head check exit 0, 2/2 `OK`; both live-to-head comparisons
exit 0; frozen check exit 0, 14/14 `OK`. Starting identities:

```text
f5099dd8d9ec9e9a5a2a632f5e9411fe1390ab027ad63a9c70d819af0b85e508  tests/winusb_function_io_contract.c
9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348  tests/wineusb_winusb_busif_contract.c
2d1ad6b0da1cf9d39b059e13e4a9953c83b4fcbd79a3b6df26f0825a56228ba1  task-9-r133-head.sha256
```

## Correction

The existing four-object admission journal and exact per-pair retirement checks
remain intact. A separate completion-allocation observer now increments on
every `ExAllocatePool()` attempt while armed, including a failed attempt. The
two pending-request schedule resets and arms it immediately before each exact
`complete_pending_task9_irp()` call, disarms and requires zero attempts
immediately afterward, and leaves it disarmed during both intervening
alternate-selection calls. Thus alternate-selection allocations are excluded,
while a completion routine cannot create a replacement record or URB without
an executable failure.

The observer is independent of `control_pool_observing` and
`control_pool_tracking_frees`; disabling admission observation cannot disable
the completion interval. Reset code clears both observer fields so other test
groups retain their existing boundary.

## Bounded completion-recreation mutant

The same mutant was compiled twice from disposable copies of the function C;
the live file was never mutated. It allocated two replacement record/URB pairs
during the first pending completion, copied and used one pair for each original
IRP, let production free those replacements, and explicitly retired the four
admission-journaled originals in the expected pairwise order. Four replacement
objects were allocated before any original retirement, preventing allocator
address reuse from perturbing the identity ledger. Stored outcomes, counts,
list state, reference balance, and global allocation/free balance were retained.

The compile/run recipe for each disposable copy was:

```text
cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -D__WINESRC__ \
  -Itests -I.io24-build/winusb-api-v1/dev-source/include \
  -I.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys \
  -I.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys \
  "$temporary_copy/winusb_function_io_contract.c" \
  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c \
  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/transfer.c \
  -o "$temporary_copy/contract"
"$temporary_copy/contract" --control-descriptor
```

Against the immutable pre-observer R133 contract: compile exit 0, execution
exit 1, exactly 203 existing feature failures, no harness/compiler/crash
marker. This proves the requested mutant was a false-green before correction.

Against the corrected observer contract: compile exit 0, execution exit 1,
exactly 204 failures, no harness/compiler/crash marker. The sole added failure
was:

```text
FAIL control_completion_allocation_end:217: control_completion_allocation_attempts == 0
```

Mutant delta: 203 -> 204, exactly one observer failure. Both disposable trees,
their executables, and logs were removed. An early overbroad mutant draft ran
outside the bounded pending schedule and produced exit 139; it was discarded,
narrowed to the exact paused-admission interval, and is not used as mutation
evidence. The final bounded mutant had no crash or harness failure in either
pre/post replay.

## Fresh focused and retained evidence

Battery before this phase: 77 percent.

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
```

Result: exit 1; actual production compiled and executed; 35 dispatches, 29 mode
IOCTLs, exactly 203 genuine named feature-boundary failures. Compiler/linker,
harness, and crash markers: 0 each.

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --lifecycle
```

Result: exit 0; 12 dispatches, 0 mode IOCTLs, 0 failures. Compiler/linker,
harness, and crash markers: 0 each.

## Manual ASan/UBSan focused replay

Battery before this phase: 77 percent.

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
zero `AddressSanitizer`, `UndefinedBehaviorSanitizer`, `runtime error:`, or
`LeakSanitizer` markers; zero harness and crash markers. The temporary
executable and logs were removed.

## Final identity, exact delta, and self-review

```text
ad139419c758fe5b9aacd9c612bbb865f3baf96edc66aed42071f32df8b531f2  tests/winusb_function_io_contract.c
9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348  tests/wineusb_winusb_busif_contract.c
```

The exact unified diff from the verified immutable R133 function head uses
labels `r133-head/tests/winusb_function_io_contract.c` and
`live/tests/winusb_function_io_contract.c`:

```text
3bda52ddcb77d1ed7ad47473d10492ec7be8143f0ca5fed0a1e94958d6daa2de  74 lines
```

Self-review found the observer armed only for the two required completion
invocations, disarmed before every intervening alternate call, and independent
of the retained admission/free ledger. No expectation was weakened and no
source-text scan was used as feature evidence. All R133 per-pair identity,
distinct-result, retirement, outstanding-count, list, and reference checks
remain. The bus-interface live hash remains exactly frozen. Production reopen,
successor snapshot/controller evidence, and both independent reviews remain
outside this implementer scope.

Final post-report integrity replay at BAT0 capacity 75 percent: immutable R133
head check exit 0, 2/2 `OK`; frozen manifest check exit 0, 14/14 `OK`; live
function and bus-interface hashes remained the two values above; live mutant
residue count was zero.
