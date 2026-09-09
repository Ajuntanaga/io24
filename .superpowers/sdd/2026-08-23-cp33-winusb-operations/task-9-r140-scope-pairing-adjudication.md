# Task 9 R140 scope-pairing adjudication request

Timestamp: 2026-08-25

## Verdict requested

Authorize one additive test-only correction in exactly:

- `tests/wineusb_winusb_urb_contract.c`

The proposed delta is sealed in `task-9-r140-proposed-scope-pairing.patch`.
No upper test, production, support, wrapper, RANGE, snapshot, prior manifest,
prior evidence, device, Wine/prefix, build/staging, firmware, preset/effect, or
live-hardware path is requested for reopening.

## Why R139 is not sealable

Both independent reviewers found the same Important false green. R139 runs the
exact RANGE positive only as a function device but runs all six repaired
interface-recipient negatives only as non-function devices. Production can
therefore keep exact behavior for non-function devices while widening RANGE
only for function devices, and the complete R139 lower focused contract still
passes.

The controller reproduced the targeted mutant in a temporary source copy: the
actual lower wrapper exited 0 with zero failures. R139 remains frozen as
rejected evidence; no live byte was changed during reproduction.

## Proposed bounded correction

Retain all R139 behavior and add three lenses:

1. Run the exact RANGE positive once as a non-function device, closing
   scope-conditioned suppression.
2. For each of the six interface-recipient one-field negatives, retain the
   non-function generic-routing case and add a function-scoped mirror that must
   reject without libusb activity, synthetic payload mutation, or URB success.
3. Centralize that mirror assertion in one local test helper that snapshots and
   compares the caller storage.

The device-recipient negative remains unchanged. The existing function exact
positive, structural admission negatives, generic request, and
`0xab05`/`0xab07` low-byte witnesses remain unchanged.

## Isolated proof

Only temporary copies were changed:

- proposed test against live R138 production: exit 0, failures=0;
- targeted scope-conditioned broad/suppress mutant: exit 1, failures=16;
- non-function exact-RANGE suppression mutant: exit 1, failures=4;
- holistic function-only direction-widening mutant: exit 1, failures=3.

The temporary tree was not used for any Wine, device, build/staging, firmware,
preset/effect, or live-hardware action and will be deleted after packaging.

## Next gate

Do not apply the proposal without controller authorization. If authorized,
verify the R139 live head and patch dry-run, apply only the sealed one-file
delta, replay focused and retained host gates, run the three bounded mutants,
freeze the corrected test, and obtain two clean independent reviews before
resuming R138 sanitizer, full mutant, production-review, or final seal gates.
