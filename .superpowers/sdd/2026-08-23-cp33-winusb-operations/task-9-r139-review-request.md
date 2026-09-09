# Task 9 R139 corrected-test review request

Timestamp: 2026-08-25T18:28:18-07:00

## Requested verdict

Independently review the exact two-file R139 test correction. Return `PASS` only
if the correction removes contradictory fixture/oracle facts without weakening
the Task 9 production contract or creating a false green. Otherwise report each
Critical, Important, or material Minor finding with an exact file/line and a
concrete counterexample or mutant.

This is a test-correction review, not final R138 production review. Do not edit
any file.

## Authority and immutable bytes

The controller authorized the sealed proposal in
`task-9-r139-test-oracle-adjudication.md` over exactly:

- `tests/winusb_function_io_contract.c`
- `tests/wineusb_winusb_urb_contract.c`

The proposal and adjudication still verify through
`task-9-r139-adjudication.sha256`. The pre-edit bytes are frozen in
`task-9-r139-test-base/` and verify 2/2 through
`task-9-r139-test-base.sha256`.

The corrected candidate is frozen in `task-9-r139-test-head/` and verifies 2/2
through `task-9-r139-test-head.sha256`, whose SHA-256 is
`fd27abae1e92fb4b93f96e4c49f2792f205e6f693331d17b090b6992d8b05e62`.
Both live tests are byte-identical to that candidate.

The complete base-to-head delta is 11 insertions and one deletion:

- refresh `control_expected_setup` after the MI06 endpoint-positive fixture
  changes its exact packet to `82 06 01 00 83 00 00 00`;
- explain predicate isolation and set `f.device.function=FALSE` for only the six
  interface-recipient one-field RANGE misses whose low interface bytes do not
  equal the function fixture's interface 5.

The device-recipient negative is unchanged. The dedicated function-scoped
`wIndex=0xab07` high-byte witness remains unchanged and executable.

## Fresh controller replay

All four live production-boundary focused modes compiled, executed, and exited
0:

- upper function: failures=0;
- actual `wineusb.c`: pass;
- actual `unixlib.c`: failures=0;
- public DLL: failures=0.

Retained upper lifecycle and actual-lower `--red` both exited 0. The frozen
legacy RANGE wrapper reproduced its already-adjudicated R128 loader/support
mismatch (`undefined symbol: libusb_control_transfer`) before assertions. This
is not feature evidence. Its approved stronger substitute is the current lower
`--control-descriptor` matrix: it executed live `unixlib.c`, kept the exact
RANGE positive local, routed all seven one-field negatives generically, and
exited 0.

## Review questions

1. Does the upper insertion repair only the stale expected packet while still
   requiring exact lower-boundary setup bytes?
2. Do the six Unix fixture changes isolate RANGE predicate negatives from
   unrelated function-scope rejection, without weakening the separate low-byte
   scope witness or the device-recipient negative?
3. Does the exact frozen delta match the sealed proposal and touch no other
   test, production, support, wrapper, RANGE, or prior evidence byte?
4. Can any incorrect R138 production behavior now pass that the pre-R139
   contract was intended to reject? Give a bounded mutant if so.

## Safety

Read-only, offline host review only. Do not invoke Wine or a prefix, build or
stage a driver, access USB/device/sysfs paths, use the network, or touch
firmware, presets, effects, or live hardware.
