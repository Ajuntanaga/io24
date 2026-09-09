# Task 9 R147 immutable-authority and descriptor-lifetime adjudication

Timestamp: 2026-08-26T00:27:11-07:00

## Decision

R147 resolves the four executable false-green classes that rejected R146 and
is ready for two independent preauthorization reviews.  It is a proposal only:
the live R139 tests and active R138 production remain frozen and unchanged.

## Corrections

1. Both generic and endpoint rejection helpers capture the complete caller
   fixture before production runs, deep-copy the pointed pipe table, retain the
   original pipe-table pointer and device handle, change only the expected URB
   status to `USBD_STATUS_INVALID_PARAMETER`, and place the live URB status at
   `USBD_STATUS_NOT_ACCESSED`.  Post-call comparison is byte-exact for the
   complete fixture and pipe table.
2. Endpoint journal authority is compared with the captured pre-call device
   handle.  Mutating the live handle and then using it can no longer validate
   itself.
3. The fake returns a freshly copied mutable top-level configuration view.
   Exact descriptor free poisons `bNumInterfaces`, `wTotalLength`, and
   `interface`; a later get refreshes the complete view.  Moving production's
   correct free before traversal therefore fails safely at feature status 1.
4. Every exported fake entry records the global call witness as its first
   executable operation.  The three device/configuration journal entries
   increment their dedicated counter immediately afterward; local result
   initialization follows both increments.

## Exact proposal

- direct patch:
  `task-9-r147-proposed-lifetime-and-reject-state-oracle.patch`
- patch SHA-256:
  `8285b45f3c59c0b6442c59df1a943843f8ad45a997fd5e74d2315c20ed753801`
- candidate lower contract SHA-256:
  `45c33598b8cf74298248a4e5e0ad3826527259c8dc8474e7e0d8fe1007c4681a`
- candidate fake SHA-256:
  `bd76d84e99227549eb587317971c33707457b56d93de3a90e1e5672b509bab15`
- copied production SHA-256:
  `ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`

The patch applies directly to frozen R139, touches exactly the lower execution
contract and fake, passes `git apply --check`, and reconstructs both candidate
hashes byte-for-byte in a fresh disposable tree.

## Executable adjudication

All 24 named production mutants compiled and ran copied production through the
fake boundary.  Each canonical log contains the fake pass marker, exits 1,
reports nonzero feature failures, and is byte-distinct from the other 23 logs.
The early-free row is a safe feature failure, not a signal or harness failure.

Focused `--control-descriptor` and retained `--red` baseline and final replays
all exit 0 with zero failures.  The evidence archive is
`task-9-r147-isolated-evidence.tar.gz`, SHA-256
`71a549fb9314b2ff1bc829d7dc36ca9ffacb71ac2301741d36e0ee9b5a6a814a`.

## Gate

Controller preflight passes.  R147 remains unapplied until both independent
reviews pass and the user gives new exact authorization for this patch hash and
two-file scope.
