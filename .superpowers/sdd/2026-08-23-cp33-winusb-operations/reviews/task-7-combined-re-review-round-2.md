# Task 7 combined re-review — fix round 2

## Finding 1 — ADDRESSED

`select` is initialized to `NULL` at `session.c:1005`, making all early cleanup
paths safe at `session.c:1131`.

The contract now tracks real pool allocations and rejects unknown frees at
`tests/winusb_function_io_contract.c:59`, with dirty-stack invalid-state,
unknown-alternate, and allocation-failure schedules at
`tests/winusb_function_io_contract.c:1614`.

A focused real-translation-unit build using the pre-fix base `session.c`
returned feature exit 1 and detected three attempted frees of
`0xa5a5a5a5a5a5a5a5`. Thus the new lens is genuinely pre-fix-sensitive.

## Finding 2 — ADDRESSED

Function-child SELECT_CONFIGURATION now stages from `copy_pipe_table()` at
`unixlib.c:1491`, retires only records for interfaces named by the new
transaction at `unixlib.c:1508`, and retains the existing transactional COMMIT
publication at `unixlib.c:1648`.

The added behavioral case obtains a production-issued MI07 token, commits a
separate MI05 extension, and proves the MI07 claim and token remain usable at
`tests/wineusb_winusb_urb_contract.c:511`.

## Finding 3 — ADDRESSED

All three required isolated mutant roots exist and byte-match the report:

- Per-pipe generation mutation at
  `/tmp/io24-cp33-task7-mutant-generation-per-pipe/dlls/wineusb.sys/unixlib.c:1290`;
  the same-generation assertion is
  `tests/wineusb_winusb_urb_contract.c:568`.
- Pre-COMMIT publication mutation at
  `/tmp/io24-cp33-task7-mutant-publish-before-commit/dlls/wineusb.sys/unixlib.c:1575`;
  committed-pointer and staged-token checks are at
  `tests/wineusb_winusb_urb_contract.c:740`.
- Rollback-loss mutation at
  `/tmp/io24-cp33-task7-mutant-rollback-loses-old/dlls/wineusb.sys/unixlib.c:1661`;
  rollback preservation is asserted at
  `tests/wineusb_winusb_urb_contract.c:745`.

The mutant diffs exactly match the appended report, and each mutation
necessarily triggers its cited behavioral assertions. Reported hashes also
match the current four changed files and unchanged fake.

## New Breakage in the Fix Diff

None. The production changes are narrowly scoped and introduce no new Critical
or Important correctness, recovery, capacity, generation, or ownership
failure. The fake is byte-identical to the round-2 base.

## Out-of-Scope Observations

- The direct wrapper could not consume the scoped base snapshot because
  unchanged `winusb_busif.h` is intentionally absent; that harness exit 2 was
  excluded. The focused equivalent compile against only base `session.c`
  supplied valid feature-RED evidence.
- Existing LeakSanitizer-under-ptrace and deliberate clear-halt diagnostic
  noise are unchanged and outside this fix diff.
- No broad suite, Wine, prefix, USB, staging, or live operation was used.

## Final verdict

**All findings addressed, no new Critical/Important breakage.**
