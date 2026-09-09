# Task 9 R136 bounded allocator-route mutants

These artifacts are offline, hardware-free copied fixtures.  No live production
source was modified.  Every case contains the exact copied function contract,
binding support, `winusb.sys/main.c`, `session.c`, `transfer.c`, and private
header used for its compile, plus compiler output, execution output, and exit
files.  `manifest.sha256` seals every artifact except itself.

Run all five cases from any directory with:

```text
sh .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r136-mutants/replay.sh
```

The script compiles into a validated `mktemp` directory, runs only
`--control-descriptor`, checks the exact failure deltas and diagnostic-marker
counts, and removes its temporary files.  Its compile form for each case is:

```text
cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -D__WINESRC__ \
  -I"$case_root/tests" \
  -I.io24-build/winusb-api-v1/dev-source/include \
  -I"$case_root/dlls/winusb.sys" \
  -I.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys \
  "$case_root/tests/winusb_function_io_contract.c" \
  "$case_root/dlls/winusb.sys/session.c" \
  "$case_root/dlls/winusb.sys/transfer.c" -o "$temporary_binary"
"$temporary_binary" --control-descriptor
```

## Cases and expected results

| Case | Boundary | Expected result |
| --- | --- | --- |
| `admission/r135` | Actual-main helper preallocates a replacement record/URB pair during the first admission; immutable R135 has no admission lens. | compile 0, run 1, 203 baseline failures |
| `admission/r136` | The identical one-admission mutant under corrected R136. | compile 0, run 1, 204 failures; the only delta is `control_retained_allocation_end` |
| `completion/bypass` | Actual-main helper recreates four replacement objects during the two completions while the copied binding deliberately omits the retained hook. | compile 0, run 1, 203 baseline failures |
| `completion/r136` | The identical completion recreation under the final retained hook. | compile 0, run 1, 204 failures; the only delta is `control_retained_allocation_end` |
| `failed/r136` | One actual-main helper allocation is forced to fail during the first exact completion interval. | compile 0, run 1, 204 failures; the only delta is `control_retained_allocation_end` |

The admission mutant asserts two helper allocations and two helper frees while
preserving the four admitted original allocations and their pairwise retirement
journal.  The completion mutant asserts four helper allocations and four helper
frees while preserving statuses, list/outstanding effects, original-pair
retirement, references, and final balance.  The failed-attempt fixture asserts
one helper call, a null return, and zero helper frees.  Because the retained fake
intentionally increments its shared diagnostic counter before returning the
forced failure, the copied test first proves that one-attempt delta and then
restores only that diagnostic count; teardown remains an independent balance
check and therefore does not create a second failure.

Successful compiler logs are intentionally empty.  Stored `run.log` files are
the complete stderr/stdout streams, and each `.exit` file records the process
exit independently.
