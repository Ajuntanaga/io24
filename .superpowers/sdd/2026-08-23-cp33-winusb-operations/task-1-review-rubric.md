# Task 1 independent review rubric

The reviewer is read-only and evaluates both spec compliance and code/test quality.

## Required scope

- Only the ten named contract/fake files, four named logs/checkpoint files, two fresh CP32-derived roots, and the implementer report may be created.
- No production file in either CP33 source clone may differ from the immutable CP32 source.
- No plan, spec, ledger, handoff, retained test, Wine prefix, device, driver, sysfs USB path, or live application may be modified or accessed.

## Required evidence

- The CP32 seal has exactly the expected successful entries and no failure.
- Both source clones were made fresh and compare equal to CP32 with `diff -qr --no-dereference`.
- Vendor evidence records the pinned DLL SHA-256, exactly fourteen expected imports, and both requested disassembly windows.
- All five contracts exit exactly `1` against untouched CP32 for their named absent or incorrect CP33 behavior.
- No accepted RED is a usage error, missing input/fake, compiler/harness failure, crash, unrelated retained failure, or test that does not exercise the actual production translation unit.
- Shell wrappers use a fresh temporary directory, accept only the documented arguments/modes, exit `2` on usage error, and compile with `cc -std=c11 -Wall -Wextra -Werror`.
- The two lower wrappers compile actual `unixlib.c` against the complete fake libusb and use only the sealed CP32 `dlls/ntdll/ntdll.so` build artifact.
- C fixtures share the required guard/accounting convention. MI05 has alternate 0 with no endpoints and alternate 1 with bulk `0x81`/`0x01`, maximum packet size 512.
- Fake libusb exposes counters for claim, release, detach, auto-detach, set-configuration, set-alternate, control, bulk, interrupt, cancel, clear-halt, transfer-free, and close.
- `task-01-red.sha256` is nonempty and verifies from the project root.

## Quality checks

- Assertions name observable contract breaks and derive expected values independently of production helpers.
- Host fakes enforce ownership, guard bytes, exact counts, and forbidden-call detection rather than merely returning success.
- Test modes remain additive and usable by later focused RED/GREEN tasks.
- Diagnostics distinguish feature RED (`1`) from harness/usage failure (`2` or other).
- Generated logs contain no accidental host secrets or unrelated environment dump.

## Verdict

Return `PASS` only when every required item is supported by direct file inspection and fresh read-only commands. Otherwise return `FAIL` with findings ordered by severity and exact file/line references. Do not edit files.
