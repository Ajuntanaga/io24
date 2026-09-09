# Task 9 R139 frozen-oracle adjudication request

Timestamp: 2026-08-25T18:08:04-07:00

## Verdict requested

Authorize one test-only correction round over exactly:

- `tests/winusb_function_io_contract.c`
- `tests/wineusb_winusb_urb_contract.c`

The proposed behavioral correction is recorded in
`task-9-r139-proposed-test-oracle.patch`. No wrapper, support, RANGE, production,
snapshot, manifest, or prior evidence path is requested for reopening.

## Production state

The R138 production correction is implemented in six of the nine authorized
paths. The other three authorized paths remain byte-identical to the R138 base.
Actual `wineusb.c`, public focused, and upper retained-lifecycle executions are
green. The frozen upper and Unix focused modes are not sealable because their
remaining expectations contradict the R129-R131 requirements.

The live frozen tests were not edited. Their SHA-256 values remain:

```text
b18c2f40cc0fbb4bf37ad076293cacf26ecdc43c995b3434fd262abc91f2356a  tests/winusb_function_io_contract.c
f87cec8e3a5ed0db71dbd5692e49a5e25838a3d28a115d5833e73639c16a24f4  tests/wineusb_winusb_urb_contract.c
```

## Finding 1: stale endpoint packet oracle

At the two-interface MI06 endpoint positive, the frozen function contract calls
`CONTROL_SEED()`, changes the request from the seeded device packet to endpoint
packet `bmRequestType=0x82, wIndex=0x0083`, and immediately calls
`CONTROL_ACCEPT()` without updating `control_expected_setup`. GDB stopped at the
real lower boundary with:

```text
actual   82 06 01 00 83 00 00 00
expected 80 06 01 00 00 00 00 00
```

The production packet is the required exact endpoint packet. Normalizing it to
the stale device expectation would violate the exact setup-copy and endpoint
recipient contract. Adding the same expectation copy used by the neighboring
positive cases is the minimal correction.

## Finding 2: RANGE mutants are out of fixture scope

The frozen Unix contract requires six interface-recipient one-field RANGE
mutants to reach generic libusb routing. Their low `wIndex` bytes are `0` or
`1`, while each `reset_control()` fixture is function-scoped only to interface
`5`. Correct R129 low-byte scope validation therefore rejects them before
generic routing. The separate `0xab07` high-byte witness now rejects correctly;
blindly restoring the old nonzero-high-byte bypass would make that required
witness fail.

Running those six predicate-isolation mutants as non-function devices preserves
their one-field RANGE mutations and removes the unrelated scope rejection. The
device-recipient negative remains unchanged because it has no interface-scope
dependency.

## Isolated proof

Only temporary copies under `/tmp` were changed. Against the same live R138
production head:

```text
function corrected-copy focused: exit 0, failures=0
Unix corrected-copy focused:     exit 0, failures=0
```

The live frozen function mode has exactly one failure at the stale packet
comparison. The live frozen Unix mode has exactly 42 failures: seven assertions
for each of the six out-of-scope interface predicate mutants. The temporary
corrections remove all of them without weakening the dedicated high-byte scope
witness.

## Boundary

Task 9 remains active and unsealed. Do not run sanitizer, mutant, freeze,
manifest, or independent production-review closure as if the live focused gate
were green. After controller approval, apply only the proposed test correction,
replay the focused and retained gates, freeze the corrected tests, and obtain
fresh independent review before continuing the R138 final gates.
