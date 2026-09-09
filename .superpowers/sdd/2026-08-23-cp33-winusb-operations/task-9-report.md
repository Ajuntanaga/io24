# CP33 Task 9 report — generic control and descriptor fallback

Status: test-first production freeze.  Historical RED/review outcomes are
never rewritten.  One earlier append placed R117 phases 2-3 and the R118 block
before the later R116 phase-2-through-R117-phase-1 sections, so physical section
order after R116 phase 1 is not chronological.  Use the R-number sequence and
`progress.md` as the canonical chronology; new evidence is appended at EOF.

## Test RED round 0 — rejected

The first eight-path test-only attempt added `--control-descriptor` to all four
wrappers/boundaries.  Fresh lead replay reached actual frozen production and
returned feature exit 1 in every case:

```text
function: exit 1, failures=2, CONTROL_IN remained STATUS_NOT_SUPPORTED and unforwarded
bus interface: exit 1, failures=2, actual wineusb.c returned STATUS_NOT_IMPLEMENTED and made no Unix call
lower Unix: exit 1, failures=2, actual unixlib.c reported unhandled URB function 0x8 and no control submit
public: exit 1, failures=11, missing WinUsb_ControlTransfer plus absent string fallback
```

No command produced a usage, compiler, linker, prerequisite, crash, or harness
exit 2.  All seven existing production paths remained byte-identical to
`task-9-base`, `transfer.c` remained absent, and the frozen lower wrapper and
RANGE hashes were unchanged.

Independent review nevertheless returned FAIL with four Important findings and
one material Minor:

- the function wrapper did not require or compile future `transfer.c`;
- the public mode reused the old descriptor and Task-10/12 transfer bundle,
  including an obsolete assertion that string fallback must fail;
- the function, bus-interface, and lower additions were one-case smoke tests,
  leaving the required length, MDL/method, setup, type/recipient/scope,
  timeout/payload, cache/fallback, completion/error/bounds/accounting, and RANGE
  matrices unproved; and
- the fake's new timeout/payload fields were unused, while one payload copy was
  bounded by setup length but not by the actual allocated transfer length.

The rejected head is frozen at `task-9-red-round-0-head.sha256`, eight entries,
manifest SHA-256
`7e95749503ce9891f554972a5eb6c116e61e9c5292002f06401c197b5749f2c5`.
R111 keeps all production frozen and requires an eight-path test-only
correction plus fresh independent review.

## Test RED correction round 1 — incomplete

The R111 correction improved four structural issues:

- the function wrapper conditionally compiles actual `transfer.c` whenever the
  production file exists while preserving an executable absent-feature RED;
- the public mode now has a dedicated Task-9 group rather than invoking the
  Task-10/12 read/write/overlapped bundle;
- the actual-`wineusb.c` bus-interface group separately exercises descriptor
  routing and adds generic malformed-request expectations; and
- fake control payload capture is bounded by both setup length and the actual
  allocated transfer payload.

All four focused commands still reached actual production and exited feature 1
without harness failure.  Retained touched-family modes passed, all seven
existing production paths remained base-identical, `transfer.c` remained
absent, and frozen lower-wrapper/RANGE hashes remained exact.

The worker explicitly reported that the full private and lower matrices remain
callable-head-deferred rather than completely encoded.  The controller therefore
does not accept this as the Task-9 RED boundary.  R112 freezes the exact eight
paths in `task-9-red-round-1-head.sha256` (manifest SHA-256
`f1abb67719a644d51257ab0bc499b2481c72d5caa1fdc65b5ebccb63d4773caa`)
and divides the remaining test-only work into four sequential boundary phases
before one combined independent review.

## R112 boundary phases 1-3 — complete, not yet accepted

The function-driver phase expanded the actual private WDM boundary across the
40-byte ABI, IOCTL methods and sizes, setup/type/recipient/scope admission,
direct-MDL identity, lower success/failure/pending behavior, allocation failure,
descriptor output, and 4096/4097 limits.  Its focused mode reached actual frozen
production and exited feature 1 with no harness failure.  The function contract
SHA-256 is
`faf687583b1192620146e66801794fb2efdb8de9805b36dc5e68d99c38dba8da`;
its wrapper remains
`66fb49ec13928154dd4f8bdb0d2a97ff86aac30361c25cadaff46721b0e726cc`.

The bus-interface phase expanded the actual `wineusb.c` boundary across generic
standard/class/vendor requests, all supported recipients, IN/OUT/zero-length
direct-MDL identity, original IRP/stack/file forwarding, immediate failure and
pending paths, malformed header/buffer/MDL/shape rejection, descriptor routing,
and 4096/4097 limits.  Its focused mode executed actual frozen `wineusb.c` and
exited feature 1 with no harness failure; default retained mode passed.  The
bus-interface contract SHA-256 is
`e0e01e03de55e7127c726f2f41f27eae3f1f4f7bb8b024b2c9035aa2d4654e76`;
its wrapper remains
`d3fbac5b716551ad3124ec0f12c685200729622c1c0d3af757986c859b4a3bfd`.

The lower Unix phase expanded actual `unixlib.c` across all admitted type and
recipient shapes, zero through 4096-byte positive cases, 4097 and malformed
rejections, exact setup/timeout/OUT payload, bounded guarded IN completion,
forbidden backend calls, and the exact RANGE request taking the generic backend
rather than a synthetic response.  Its focused mode exited feature 1 with 109
assertion failures and zero harness lines at the absent function-0x8 route.
Retained `--claims`, `--alternate`, `--sync-pipes`, and `--transfer-lifetime`
runs passed before a later redundant combined rerun was interrupted and excluded.
The lower contract SHA-256 is
`fd088386e7762a4f0ee2c3a00b22532fb6fb864822b68e9a985c9a7fde348310`;
the fake remains
`cd78a2f79ea6152272fb5307a7970e24de8e4fe49a7af2081a81e75412ba2f45`.
The frozen lower wrapper and RANGE source hashes remain exact.  A standalone
legacy RANGE rerun was unavailable against stale prebuilt artifacts and is not
counted as either success or failure.

All seven existing production paths remain byte-identical to `task-9-base` and
`transfer.c` remains absent.  Phase 4 owns only the public C contract and wrapper.
No phase result unlocks production until the combined eight-path head passes a
fresh independent review.

## R112 boundary phase 4 and combined RED head — review pending

The public phase replaced the obsolete string-descriptor failure expectation
with a dedicated Task-9 boundary.  It now exercises cached device/configuration
descriptors without submission, selector rejection, typed string/other fallback
requests, response/error bounds, guarded future IN/OUT control requests across
length/type/recipient/scope cases, and safe execution when the control symbol is
absent.  The wrapper conditionally links future `transfer.c` and preserves the
retained descriptor mode.

The focused actual-public-module command exited feature 1 with aggregate
`failures=10`, missing-symbol mask `0x2` for `WinUsb_ControlTransfer`, and no
harness/compiler/link/crash failure.  Retained `--descriptors` passed.  The
public contract SHA-256 is
`5b19a7cbb3b01fdb92c5d2fc10fb62ee34d81b1ed60e40fb37da323b0eb7e66f`;
its wrapper SHA-256 is
`a1bc5dd7d338a1f3b678a152a2c99cca274c832267d7459755edacc807f3cd75`.

The controller froze all eight test paths as `task-9-red-round-2-head`.
`task-9-red-round-2-head.sha256` verifies 8/8 unique entries and has SHA-256
`59bb94b56eff1359e8d8808a236fd48c51ca81055f0e976cae32373c3a7ef074`.
All seven existing production paths remain base-identical, `transfer.c` remains
absent, and the lower wrapper/RANGE hashes remain frozen.  This head is only a
review candidate; production remains locked pending a clean independent review.

## Combined RED round 2 — rejected

Independent review confirmed the manifest, all eight head files, all seven
base-identical production files, absent `transfer.c`, exact frozen lower/RANGE
hashes, and genuine executable feature RED at all four production boundaries.
It nevertheless returned FAIL with one Critical and six Important/material
findings:

- the function fake treats every lower IRP as a nested allocation and frees it,
  so correct original-IRP forwarding would be unsafe while nesting is not
  rejected;
- interface canonicalization, public associated-interface, endpoint-direction,
  current-alternate, and reserved-type expectations encode wrong admission;
- the exact generic RANGE tuple incorrectly expects a backend request and has
  no generic one-field-negative matrix, opposite R110;
- actual `wineusb.c` positives permit a raw buffer for nonzero transfers and a
  setup/transfer-length mismatch;
- allocation, pending completion, actual-length, error, free, and per-interface
  accounting assertions do not substantively expose the required behavior; and
- retained public string-descriptor behavior remains obsolete, while new
  control/fallback failure bounds and caller preservation are underasserted; the
  associated-handle schedule also loses one live root and double-frees another.

R113 preserves this exact rejected head and permits correction only in the
function C contract, bus-interface C contract, lower Unix C contract/fake, and
public C contract, one phase/writer at a time.  The three wrappers, all
production, frozen lower support, and RANGE sources remain immutable.  A fresh
combined review is mandatory before production unlock.

## R113 correction phase 1 — function contract complete

The function fake now distinguishes registered builder IRPs from the original
Task-9 request, requires exact original-IRP forwarding, and never casts, poisons,
or frees that original as a nested allocation.  It also corrects interface
low-byte canonicalization, requires zero submission on allocation failure, and
encodes delivered immediate/pending success/failure completion with exact
retirement, file-list/accounting, context-clear, and duplicate-completion
assertions.  These completion paths remain callable-head assertions until the
new production unit exists.

The focused frozen-production mode exits feature 1 with 85 intended failures
and zero harness failures; retained `--lifecycle` passes.  The sole changed file
is `tests/winusb_function_io_contract.c` at SHA-256
`6ba1b7093657f6192965ac41015ac85c1230c42f775ad6b8c797482ec7008a4e`.
Its wrapper remains round-2-identical, all production remains base-identical,
and `transfer.c` remains absent.

## R113 correction phase 2 — bus-interface contract complete

The actual-`wineusb.c` positives now use no raw `TransferBuffer`, carry the
incoming mapped direct MDL, and require setup `wLength` to equal the transfer
length.  The zero-length positive now has setup length zero.  Explicit negatives
cover raw-buffer/no-MDL, missing/unmappable/undersized MDLs, contradictory direct
buffer plus MDL, and short/long setup mismatches; 4096 remains positive and 4097
negative across the retained type/recipient/direction matrix.

The focused actual-`wineusb.c` mode exits feature 1 with 89 failures and zero
harness failures; retained `--red` passes.  The sole changed file is
`tests/wineusb_winusb_busif_contract.c` at SHA-256
`5e0428554d711ec7b03461e0cd2c59422528c98471d7441511b53516d8de6c07`.
Its wrapper and all production remain frozen, and `transfer.c` remains absent.

## R113 correction phase 3 — lower Unix contract/fake complete

The exact generic RANGE tuple now requires the shared synchronous 50-byte
synthetic response with zero backend allocation/submission/pending/cancel state.
Direction/type/recipient/request/value/index/length one-field misses each require
ordinary backend routing and cannot receive captured bytes.  The fake separates
safely copied fixture bytes from raw reported actual length, allowing an
oversized 4097 completion to reach production observably.  The matrix now also
covers allocation and immediate-submit failure, short/exact/oversized IN,
timeout/error/cancel mapping, duplicate completion, OUT preservation, guards,
forbidden calls, and exact allocation/free balance.

The focused actual-`unixlib.c` mode exits feature 1 with 182 failure lines and
zero harness lines; the affected retained `--transfer-lifetime` mode passes.
Per the bounded-run instruction, `--claims`, `--alternate`, and `--sync-pipes`
were not redundantly rerun in this correction phase.  The changed hashes are:

```text
3661182111456453de9acd123f2b6af0c969c36c147ff3f1f16e025e120d6cec  tests/wineusb_winusb_urb_contract.c
5efe8286dc665db90d2fec2e74d8aca5ac0527d7f6be27b92a5208bacfed57c9  tests/wineusb_winusb_urb_fake_libusb.c
```

The lower wrapper, RANGE sources, all production, and absent `transfer.c`
remain frozen.

## R113 correction phase 4 and combined RED round 3 — review pending

The public contract now uses the represented associated interface 2 for
low-byte canonicalization while preserving the high byte, separates valid
vendor from reserved type/recipient cases, rejects endpoint controls before the
correct alternate and wrong-direction/nonmember endpoints, and uses exact
current IN/OUT members after alternate selection.  It corrects root-only device
scope and stale-handle cases, exercises short/exact/oversized/error descriptor
and control replies with guarded caller preservation, and repairs the associated
handle/root schedule so every live object is released exactly once without a
reset or overwrite.  Retained string/other descriptor expectations now require
the Task-9 fallback instead of preserving unsupported behavior.

The focused public mode exits feature 1 with seven aggregate failures, missing
mask `0x2`, and no harness/compiler/link/crash failure.  Corrected retained
`--descriptors` intentionally exits feature 1 with four failures and no harness
failure because frozen production still lacks the fallback.  The sole changed
file is `tests/winusb_user_api_contract.c` at SHA-256
`8482de3efb6911f912f34a8ce203071f70b443db5c57b78792eda2b970b92e33`;
its wrapper remains frozen.

The controller froze the combined eight test paths as
`task-9-red-round-3-head`.  Its manifest verifies 8/8 unique paths and has
SHA-256 `81bdc988d1321585dd3a1f9222f29205671084a3de738be7d84ae3fc0c743ac3`.
All seven existing production paths remain base-identical, `transfer.c` remains
absent, and frozen lower/RANGE support remains exact.  This is a review
candidate only; production stays locked pending fresh independent acceptance.

## Combined RED round 3 — rejected

Fresh review confirmed exact manifest/workspace/base integrity and found the
prior Critical original-IRP hazard, direct-MDL shapes, RANGE routing, raw actual
length, and public fallback/lifetime findings substantively closed.  It still
returned FAIL with six Important gaps:

- the function recipient loop reverses CONTROL_IN/CONTROL_OUT selection and
  lacks explicit direction-mismatch negatives;
- function and lower endpoint positives run before a real current pipe map, and
  one unrelated device-index rejection is not contract-derived;
- upper context/URB releases are represented by a test-owned synthetic counter
  instead of real production allocator/free deltas;
- the lower fake does not count or balance control setup/payload buffers or
  assert the ownership flag;
- nonzero OUT is never completed with mutated staging, and failed lower
  completions do not prove zero effective length plus unchanged caller data; and
- public synchronous null-length, zero-length/null-buffer, and exact full-prefix
  IN-copy behavior are absent.

R115 preserves this rejected head and assigns a fresh round-4 implementer only
the function C contract, lower Unix C contract/fake, and public C contract,
sequentially.  All wrappers, bus-interface tests, production, lower support, and
RANGE sources stay frozen.

## R114 completion ownership resolution

Read-only tracing fixes the later implementation convention: the upper transfer
record/URB lives only in the completion `Context`; lower `DriverContext[0]`
remains exclusively the libusb transfer identity and slots 1-3 remain untouched.
The upper completion returns `STATUS_SUCCESS` to continue the single lower
terminal completion, never calls `IoCompleteRequest`, maps/bounds status and
information, unlinks and decrements once under the file lock, frees its upper
URB/record once, and only then releases the file I/O reference.  Cancellation,
queue-event failure, and removal lifetime remain assigned to later tasks.

## R115 correction phase 1 — function contract complete

The fresh round-4 implementer corrected setup-bit direction mapping and added
explicit nonzero opposite-IOCTL rejection.  Endpoint positives now follow the
actual SET_ALTERNATE path that installs a current pipe map, with pre-selection,
stale, nonmember, and wrong-direction negatives; the unsupported blanket device
high-index rejection was removed.  A scoped pool ledger now observes real
production allocation identity, size, and exactly-once frees for the upper URB
and record across immediate/pending success/failure and first/second allocation
failure, replacing the synthetic release counter.  These new production-object
assertions remain callable-head until `transfer.c` exists.

Focused frozen-production RED exits 1 with 163 failure lines and no harness,
compiler, linker, or crash failure; retained `--lifecycle` passes.  The only
changed file is `tests/winusb_function_io_contract.c` at SHA-256
`b09240eb54ce1a54385106619ef0dc9dd4048ef70beedf8a947caed83a4cbfb6`.
Its wrapper and all production remain frozen; `transfer.c` remains absent.

## R115 correction phase 2 — lower Unix contract/fake complete

The lower contract now installs a real current pipe map through actual
SELECT_CONFIGURATION, COMMIT, and SELECT_INTERFACE paths before endpoint
positives.  It rejects endpoint scope at alternate 0 and accepts exact alternate
1 IN `0x81`/OUT `0x01`, with nonmember, wrong-direction, stale, and association
negatives.  The fake exposes the submitted control buffer and ownership flag,
counts control-buffer allocation/free separately from transfer objects, and
balances submit-failure, completion/error/timeout, cancellation, and discarded
pending schedules.  Mutating only backend OUT staging cannot change caller
storage, and every failed completion requires zero effective length with exact
caller data and guard preservation.  Existing exact RANGE and raw oversized
actual-length coverage remains intact.

Focused actual-`unixlib.c` RED exits 1 with 235 failure lines and zero harness,
compiler, linker, or crash failures; retained `--transfer-lifetime` passes.  The
changed hashes are:

```text
d63592aed37b5da90de5dd891216bf5879dfda32f4772c02e6ef3a4db5c5ce83  tests/wineusb_winusb_urb_contract.c
c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb  tests/wineusb_winusb_urb_fake_libusb.c
```

The lower wrapper, all production, and absent `transfer.c` remain frozen.

## R115 correction phase 3 and combined RED round 4 — review pending

The public contract now admits synchronous zero-length control with a null
buffer and valid length output, rejects a null synchronous length pointer before
submission while preserving guarded state, and retains the nonzero null-buffer
rejection.  Exact and short IN success compare every returned prefix byte and
prove the tail/guards remain untouched; oversized response behavior remains
zero-length/no-mutation.  All earlier fallback, admission, endpoint, lifetime,
OUT-preservation, and missing-symbol assertions remain intact.

Focused `--control-descriptor` exits feature 1 with seven aggregate failures and
no harness/compiler/link/crash failure.  Corrected `--descriptors` exits feature
1 with four failures and no harness/compiler/link/crash failure.  The only
changed file is `tests/winusb_user_api_contract.c` at SHA-256
`4fa8f64b476a796cb7086176170b30f815f80c836dd50edc8d35e814ca6b654e`.

The controller froze the combined eight test paths as
`task-9-red-round-4-head`.  Its manifest verifies 8/8 unique paths and has
SHA-256 `9c28b3436d31d1caa889cc0422f28a23dd63630ce175539a53bdf7c688f2ee41`.
All seven existing production paths remain base-identical, `transfer.c` remains
absent, and frozen wrappers/lower/RANGE support remain exact.  This remains a
review candidate; production stays locked pending fresh independent acceptance.

## Combined RED round 4 — rejected

Fresh review confirmed the round-3 direction/current-pipe/pool-ledger,
normal-buffer ownership, public null/zero/exact-prefix, and all earlier major
closures.  It returned FAIL with two Critical contradictions and six Important
gaps:

- the function completion helper requires lower slot 0 despite the fake never
  creating it and R114 reserving it exclusively for lower state;
- the lower contract both accepts and rejects OUT on IN endpoint `0x81`;
- upper completion still permits `STATUS_MORE_PROCESSING_REQUIRED` or an upper
  terminal completion, opposite R114;
- no positive function CONTROL_OUT route exists;
- lower immediate-submit failure does not prove control-buffer ownership/free
  balance, and failed OUT error/timeout/cancel preservation is absent;
- actual `wineusb.c` descriptor routing uses a raw transfer buffer instead of
  the incoming mapped direct MDL; and
- public null synchronous length and nonzero null buffer preserve a seeded last
  error instead of requiring `ERROR_INVALID_PARAMETER`.

R116 preserves the rejected head and permits the final correction round only in
the function C contract, lower Unix C contract/fake, bus-interface C contract,
and public C contract, sequentially under the same fresh round-4/5 implementer.
All wrappers and production stay frozen.  A material round-5 review failure ends
the automatic correction loop under R9.

## R116 final correction phase 1 — function contract complete

The fake now owns and installs a unique lower slot-0 sentinel only for pending
schedules, retires it before invoking upper completion, and preserves slots 1-3.
Upper assertions depend only on a nonnull completion `Context`, require exact
`STATUS_SUCCESS`, forbid an upper `IoCompleteRequest`, and then simulate exactly
one lower terminal completion.  Positive nonzero direct-MDL CONTROL_OUT cases now
cover device, canonicalized interface, current OUT endpoint `0x01`, and
vendor/other recipients; CONTROL_IN retains current IN endpoint `0x81` and
cross-direction IOCTL negatives.

Focused frozen-production RED exits 1 with 187 failure lines and zero harness
lines; retained `--lifecycle` passes.  The only changed file is
`tests/winusb_function_io_contract.c` at SHA-256
`9fdf20921329fa4adfff09e0accc6e4c5ac02b2b6b6a29430e89eabbe6c53abd`.
All production remains frozen and `transfer.c` remains absent.

## R117 evidence closure phase 2 — lower Unix contract complete

Each failed OUT backend error, timeout, and cancellation schedule now snapshots
the full known caller payload, tail, and guards before submission.  After
backend-only staging mutation and completion/cancel, it requires zero effective
length and exact equality to that pre-submit image.  The post-submit generic
helper baseline was removed, while existing free/cancel balance remains.

Focused actual-`unixlib.c` RED exits 1 with 256 failure lines and zero harness
lines; retained `--transfer-lifetime` passes.  The only changed file is
`tests/wineusb_winusb_urb_contract.c` at SHA-256
`8b25c7a60289082bca6c51576c6ef3e16a9962fd68234f9571fb70d5dc2b7f21`.
The fake remains frozen at
`c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb`;
all production remains frozen and `transfer.c` absent.

## R117 evidence closure phase 3 and adjudicated head — review pending

The short descriptor-header negative now uses an otherwise-valid original
request/stack/file, GET_DESCRIPTOR function, null raw buffer, incoming mapped
18-byte direct MDL, valid descriptor selectors, and only a header length of
`sizeof(header)-1`.  It requires invalid-parameter/URB failure with no Unix
dispatch or list insertion; raw/no-MDL and other shape negatives remain separate.

Focused actual-`wineusb.c` mode remains honest feature exit 1 with zero harness
lines; retained `--red` passes.  The only changed file is
`tests/wineusb_winusb_busif_contract.c` at SHA-256
`364ca248cb3b7edb0f9a7757b1773b0eea3d2fc289e953e0d6cb7abdc66b3a17`.

The controller froze all eight test paths as
`task-9-red-adjudicated-head`.  Its manifest verifies 8/8 unique paths and has
SHA-256 `1847b65374af0d4235f2ed90c442ce61ac697124de8b49a3a902f4b7ce7a7df3`.
All seven existing production paths remain base-identical, `transfer.c` remains
absent, and the lower fake, public C, wrappers, lower support, and RANGE sources
remain R117-frozen.  Production stays locked pending the two mandatory clean
independent reviews.

## R117 mandatory reviews — failed; Task 9 blocked

Both independent reviews verified the adjudicated manifest, workspace equality,
base-identical production, absent `transfer.c`, and all frozen hashes.  Both
returned FAIL and independently identified the same descriptor contradiction:
`dispatch_descriptor()` preserves zeroed `DriverContext[1..3]`, but the shared
completion oracle requires the three nonzero control-only sentinels.  Every
accepted descriptor completion therefore fails for a correct original-IRP
implementation unless production corrupts unrelated driver-context slots.

The holistic review additionally found two Important false-GREEN gaps:

- descriptor allocation-failure cases do not require terminal completion or
  prove file/list/interface accounting unwind; and
- malformed descriptor rejection does not prove caller direct-MDL output bytes
  remain unchanged at the upper or actual-`wineusb.c` boundary.

The other seven R117 closures were found substantively represented.  R118
enforces R117's terminal condition: preserve
`task-9-red-adjudicated-head.sha256` at
`1847b65374af0d4235f2ed90c442ce61ac697124de8b49a3a902f4b7ce7a7df3`,
keep all production locked/base-identical with `transfer.c` absent, and make no
automatic test correction or production edit.  Continuation requires a new
explicit controller adjudication after the pause.

## R116 final correction phase 2 — lower Unix contract complete

Endpoint positives now use exact IN `0x81` and OUT `0x01`; cross-direction pairs
remain pre-submit negatives.  Immediate submit failure asserts transfer-object
and control-buffer allocation/free counts plus FREE_BUFFER ownership.  Failed
OUT error, timeout, and cancellation schedules mutate only backend staging and
require zero effective length with exact caller payload, tail, and guard
preservation plus cancel/release balance.

Focused actual-`unixlib.c` RED exits 1 with 256 failure lines and zero harness,
compiler, linker, or crash failures; retained `--transfer-lifetime` passes.  The
contract SHA-256 is
`5dd29a78fba129705f47c2f66b88637d40118be111677c99ffef0c9bb76c982a`;
the fake remains
`c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb`.
The lower wrapper and all production remain frozen.

## R116 final correction phase 3 — bus-interface contract complete

The actual-`wineusb.c` descriptor positive now uses no raw transfer buffer and
carries the original mapped 18-byte direct MDL, with exact original IRP, stack,
file, and MDL identity assertions.  Raw/no-MDL, missing, unmappable, and
undersized descriptor shapes require pre-Unix rejection; the current undersized
production route remains part of the intended feature RED.

Focused actual-`wineusb.c` mode exits feature 1 with no harness/compiler/link/
crash failure; retained `--red` passes.  The only changed file is
`tests/wineusb_winusb_busif_contract.c` at SHA-256
`5194a7119cfa4294298ec0f0c8767cf33db001be2c9d9593effe1178c08a1fb0`.
Its wrapper and all production remain frozen.

## R116 final correction phase 4 and combined RED round 5 — review pending

The public contract now requires `ERROR_INVALID_PARAMETER` for a null
synchronous length pointer and for a nonzero null buffer, while proving no
submission and exact preservation of caller data, guards, and length storage.
The valid zero-length/null-buffer case and all earlier public matrices remain.

Focused `--control-descriptor` and corrected `--descriptors` both remain honest
feature-exit-1 modes with no harness/compiler/link/crash failure.  The only
changed file is `tests/winusb_user_api_contract.c` at SHA-256
`97b22b246ee385ca9f10c1d96da2fdd80c35713106c2251842b98ed979329fe3`.

The controller froze the combined eight test paths as
`task-9-red-round-5-head`.  Its manifest verifies 8/8 unique paths and has
SHA-256 `57b0282c5347a04e79ce9223d593db7be5fc2eace90c5458d9bf965b6e24c1e7`.
All seven existing production paths remain base-identical, `transfer.c` remains
absent, and frozen wrappers/lower/RANGE support remain exact.  This is the final
automatic RED review candidate under R9; production remains locked pending
independent acceptance.

## Combined RED round 5 — rejected; automatic loop stopped

Two independent final reviews verified all manifests/frozen invariants and the
R116 closures, but found seven unique material callable-head gaps:

- completion registration does not assert all success/error/cancel invoke flags;
- upper URB-to-NT mapping does not cover cancellation, timeout, removal,
  invalid-parameter, invalid-pipe, busy, no-memory, and generic failure;
- descriptor-specific upper ABI/MDL/allocation/pending/completion/accounting
  validation is incomplete;
- file-reference acquisition and the required unlink/decrement, upper-free,
  reference-release retirement order are unobserved;
- no nonzero direct-MDL CONTROL_IN positive targets current endpoint `0x81`;
- failed-OUT preservation snapshots caller storage only after submission; and
- the short descriptor-header negative is confounded by a forbidden raw buffer.

R116/R9 therefore stop the automatic correction loop and keep production locked.

## R117 controller adjudication — evidence closure authorized

The controller does not waive the failed RED gate.  R117 preserves
`task-9-red-round-5-head` as rejected evidence and authorizes one non-iterative
closure package in only the function C contract, lower Unix C contract, and
bus-interface C contract.  The result is named `task-9-red-adjudicated-head`,
not round 6.  The lower fake, public contract, every wrapper, all production,
lower support, and RANGE sources remain frozen.  Two independent clean reviews
are mandatory; any material finding blocks Task 9 without an automatic edit.

## R117 evidence closure phase 1 — function contract complete

The function contract now asserts all success/error/cancel completion invoke
flags before manual invocation; covers the approved cancellation, timeout,
removal, invalid-parameter, invalid-pipe, busy, no-memory, and generic
URB-to-NT mappings with zero failure information; adds a descriptor-specific
ABI/MDL/allocation/immediate/pending/completion/accounting matrix; observes the
real file-reference hold plus unlink/decrement, upper-object free, and final
dereference order; and adds a nonzero 37-byte current-endpoint `0x81`
CONTROL_IN direct-MDL positive.

Fresh controller replay after the last one-token harness correction confirms
focused feature exit 1 with 322 failure lines and zero harness lines; retained
`--lifecycle` passes.  The only changed file is
`tests/winusb_function_io_contract.c` at SHA-256
`77fa4f038ef4d9fde37bace8c3650f5023b2e851493f2d995145b21704fdb017`.
All production remains frozen and `transfer.c` remains absent.

## R119 post-pause controller adjudication — two-file RED closure authorized

The explicit resume after the R118 pause does not waive the rejected RED gate
or unlock production.  The controller preserves `task-9-red-adjudicated-head`
and both failed reviews as immutable evidence, then authorizes one bounded,
non-automatic correction in only:

- `tests/winusb_function_io_contract.c`; and
- `tests/wineusb_winusb_busif_contract.c`.

The function contract may correct only the descriptor
`DriverContext[1..3]` preservation contradiction, require terminal completion
and exact file/list/interface/reference unwind for descriptor allocation
failures, and snapshot malformed descriptor direct-MDL output.  The shared
retirement oracle may be reset and verified per request only as required to
make that accounting proof independent of earlier requests.  The actual
`wineusb.c` contract may add only the corresponding malformed-descriptor
direct-MDL output-nonmutation witness.

Every other test, fake, wrapper, production, lower-support, and RANGE path
remains frozen.  Work stays offline with the interface unplugged; no Wine,
prefix, build, staging, USB, Universal Control, Voice FX, preset, or firmware
action is authorized by this ruling.  After focused and retained execution,
the controller may freeze the exact eight-path result as
`task-9-red-postpause-head`.  This is not round 6 and does not replace the
rejected R117 head.  Two independent clean reviews remain mandatory, and any
material finding blocks Task 9 again without an automatic follow-up edit.

## R120 predecessor trace-overflow ruling — bounded harness repair authorized

The first R119 focused replay ended with corrupted global counters.  A manual
ASan/UBSan build traced this to `IoCompleteRequest` appending ten bytes past the
retained function-binding contract's 512-byte `trace`; the adjacent global was
the Task-9 `counts` structure.  The same global-buffer-overflow reproduces from
the untouched `task-9-red-adjudicated-head` function C snapshot, so it is a
predecessor harness-integrity defect, not evidence about production or a new
R119 behavior assertion.

R120 keeps `tests/winusb_function_binding_contract.c` and every other frozen
path immutable.  It authorizes only the already-owned function C contract to
clear the retained trace at each Task-9 control/descriptor dispatch boundary,
matching the retained contract's existing per-schedule reset pattern.  The
focused mode must then retain a coherent feature-exit-1 summary, and a manual
ASan/UBSan replay must show no sanitizer marker.  Production remains locked and
`transfer.c` remains absent.

## R119/R120 correction complete — post-pause RED review candidate

The function contract now seeds and rechecks descriptor
`DriverContext[1..3]`, snapshots every malformed descriptor output buffer,
requires one terminal completion and exact idle file/list/interface/reference
state for rejection and allocation-failure paths, and resets/verifies the
accepted-path retirement ledger for every request.  Allocation observation and
retirement-order observation are separate, so a valid partial-allocation unwind
does not have to impersonate the two-free success sequence.  The retained trace
is cleared at each Task-9 dispatch boundary without changing the frozen binding
support.

Function focused execution remains genuine feature RED: exit 1, 598 failure
lines, coherent final counters of 87 dispatches and 84 mode IOCTLs, and zero
harness/compiler/link/crash markers.  The same focused source built manually
with ASan/UBSan also exits feature 1 with 598 failure lines and zero sanitizer
markers.  Retained `--lifecycle` exits 0 with zero failures.  Function C is
SHA-256 `fd1bab4fc9afaf96e126ad0f5107b2b507e21424b6b26afa613f6c4f7fe357cc`.

The actual-`wineusb.c` contract now snapshots the complete 64-byte caller
buffer for every malformed descriptor case that has observable output, while
retaining exact status, URB status, no-Unix-submit, and empty-list assertions.
The missing-MDL case has no caller output and remains a pure rejection check.
Focused `--control-descriptor` exits feature 1 with 101 failure lines and zero
harness/compiler/link/crash markers; retained `--red` exits 0.  Bus-interface C
is SHA-256 `55b153335b6e77fa988fdae25a8cc1e0275260e3a3c8558e2d3915b00115ab0f`.

The frozen lower focused mode remains feature exit 1 with 256 failure lines and
its retained `--transfer-lifetime` mode exits 0.  The frozen public
`--control-descriptor` and `--descriptors` modes remain their prior clean
feature-exit-1 results, with seven and four contract failures respectively and
no harness failure.

The controller froze the exact eight test paths as
`task-9-red-postpause-head`.  Its manifest verifies 8/8 unique entries, matches
the live workspace exactly, and has SHA-256
`350435823218f4375d59455c4065457303bdad7d9f4be85c43c6987ea25173a8`.
Only function C and bus-interface C differ from the rejected R117 head.  The
other six test paths, both RANGE sources, and all seven existing production
paths remain frozen; `transfer.c` remains absent.  This is a review candidate
only.  Production stays locked until two independent reviews both return clean.

## R119/R120 mandatory reviews — one PASS, one FAIL; candidate rejected

The targeted reviewer independently verified the 8/8 manifest, exact live
equality, two-file delta, production freeze, focused/retained results, and
sanitizer replay.  It returned PASS with no material finding.

The holistic reviewer verified the same invariants but returned FAIL on one
Important false-GREEN.  `DESCRIPTOR_REJECT` and
`DESCRIPTOR_ALLOC_REJECT` require one increment of the retained global
completion counter, but the retained `IoCompleteRequest` fake ignores its IRP
argument.  A mutant can therefore complete a shadow IRP once while setting the
incoming descriptor IRP's status/information directly and preserving every
pool, list, interface, reference, pending-state, and DriverContext assertion.
The caller's IRP would remain uncompleted even though the current contract
passes.

R121 preserves `task-9-red-postpause-head` at manifest SHA-256
`350435823218f4375d59455c4065457303bdad7d9f4be85c43c6987ea25173a8`
as rejected evidence and keeps production locked.  All other R119/R120
closures were reviewed cleanly.  No automatic correction is authorized; a new
controller ruling must first identify and freeze a sound completion-identity
instrumentation boundary.

## R122 completion-identity instrumentation boundary

Preprocessing analysis confirms that `tests/winusb_function_io_contract.c`
cannot soundly interpose on the retained completion fake by itself.  The
binding C source textually includes production `main.c`; renaming or wrapping
`IoCompleteRequest` at that include boundary renames both the fake definition
and every production call, so a wrapper defined afterward receives nothing.
Function-like macro and linker-wrap variants either break the definition,
require changing the frozen wrapper, or still miss same-translation-unit calls.

R122 therefore expands Task-9 test-only ownership by exactly one additive
support path: `tests/winusb_function_binding_contract.c`.  That fake may record
and reset only the actual completed IRP pointer and completion count.  The
function contract may reset those observations at each descriptor dispatch and
require exactly one completion whose pointer is the still-live local incoming
IRP.  The binding wrapper, bus-interface correction, every other test/support
path, RANGE sources, and all production remain frozen.

After focused function, retained lifecycle, retained standalone binding, and
manual ASan/UBSan gates, the controller may freeze a nine-path
`task-9-red-postpause-identity-head` review candidate.  Production remains
locked until two independent clean reviews pass.

## R122 correction complete — completion identity review candidate

The retained completion fake now records its actual IRP argument and a
per-reset completion count.  `dispatch_descriptor()` clears both observations
before each schedule and, while its local caller IRP remains alive, requires
exactly one completion whose pointer equals that local IRP.  The fake's prior
counter and trace behavior is unchanged.

Fresh function focused execution remains coherent feature exit 1 with 598
failure lines, 87 dispatches, 84 mode IOCTLs, and zero completion-identity or
harness markers.  Retained lifecycle and the standalone CP32 binding contract
both exit 0.  A manual ASan/UBSan focused build exits feature 1 with zero
sanitizer or identity markers.  A bounded fake mutation that records the
separate synchronous IRP instead of the actual completion argument adds 22
exact `io24_last_completed_irp == &irp` failures, increasing the focused total
from 598 to 620; the temporary mutant was removed after execution.

The controller froze nine exact test/support paths as
`task-9-red-postpause-identity-head`.  Its manifest verifies 9/9 unique entries,
matches the live workspace exactly, and has SHA-256
`408b80f6480c088d2d0877f658be5a4d7078f289a4c757f5d727ddfa0be618b7`.
Function C is
`e09ac9193b334ba03808aa8d3b5cc3ea084e662bd7670af06a0aaf6709fdb631`;
binding support C is
`2b20eef2e7146782a25fa00255e253604c94a20f71158fed1f50b872913fa36e`.
The bus-interface correction and other six Task-9 test paths remain unchanged
from the rejected R119/R120 candidate.  RANGE and all production paths remain
frozen; `transfer.c` is absent.  This is a review candidate only, and two clean
independent reviews are still required before production unlock.

## R122 mandatory reviews — both FAIL; identity candidate rejected

Both independent reviewers verified the nine-path manifest, exact live
equality, production freeze, focused/retained/sanitizer results, and the sound
descriptor completion-identity correction.  Both nevertheless returned FAIL
on the same remaining Important false-green.  `dispatch_control()` does not
reset or inspect the new completion journal.  A malformed control request can
therefore return `STATUS_INVALID_PARAMETER` without terminally completing the
incoming IRP, while an allocation-failure mutant can set that IRP's status but
complete a shadow IRP once.  The existing rejection and aggregate-completion
assertions accept those outcomes.

R123 preserves `task-9-red-postpause-identity-head` at manifest SHA-256
`408b80f6480c088d2d0877f658be5a4d7078f289a4c757f5d727ddfa0be618b7`
as rejected evidence.  The descriptor correction itself is accepted as sound,
and neither review found another material issue.  Production remains locked,
all seven existing production paths remain base-identical, and `transfer.c`
remains absent.

## R124 generic-control original-IRP boundary

The R122 support fake already provides the required actual-argument journal;
no further support edit or instrumentation expansion is necessary.  R124
authorizes only `tests/winusb_function_io_contract.c` to clear that journal at
the start of `dispatch_control()` and, after driving any pending completion but
while the local caller IRP remains alive, require exactly one completion whose
pointer equals that IRP.  Applying the assertion at the dispatch boundary
covers malformed rejection, allocation failure, immediate success/failure, and
pending schedules uniformly.

The binding support, descriptor path, bus-interface correction, every other
test/support/wrapper path, both RANGE sources, and all production remain
frozen.  Required evidence is the focused function RED, retained lifecycle,
standalone binding, manual ASan/UBSan replay, and a bounded control-only
wrong-IRP mutant.  The controller may then freeze the exact nine-path result as
`task-9-red-postpause-original-irp-head`.  Two independent clean reviews remain
mandatory before any Task-9 production edit.

## R124 correction complete — original-IRP review candidate

`dispatch_control()` now clears the retained completion journal before each
generic-control schedule and, after driving any pending completion, requires
exactly one completion whose recorded pointer is the still-live local incoming
IRP.  No binding-support or descriptor-path code changed.

Fresh focused execution remains coherent feature exit 1 with 598 failure
lines, 87 total dispatches, 84 mode IOCTLs, and zero completion-identity or
harness markers.  Retained lifecycle and standalone binding both exit 0.  A
manual ASan/UBSan focused build exits feature 1 with the same 598 failures and
zero sanitizer or identity markers.  A bounded control-only mutant overwrote
the journal with the separate synchronous IRP immediately before the new
assertion.  It added exactly 61 `io24_last_completed_irp == &irp` failures,
raising the focused total to 659; the temporary mutant was then removed.

The controller froze nine exact test/support paths as
`task-9-red-postpause-original-irp-head`.  The manifest verifies 9/9 unique
entries, matches the live workspace exactly, and has SHA-256
`1427ef7decf3143d5e3aa78d490c62391e5b507d8230eccf91f19249e99c5ac3`.
Only function C differs from the rejected R122 candidate; its SHA-256 is
`261e9858ba33eec0ab2e42a1c96026ff0a977d758cd280adffc06bd87ad20ccd`.
Binding support remains SHA-256
`2b20eef2e7146782a25fa00255e253604c94a20f71158fed1f50b872913fa36e`.
All seven existing production paths compare byte-for-byte with the Task-9 base,
`transfer.c` remains absent, the lower wrapper remains
`4076a1bda411fe2295f8f1afe2c6f54ee0a49bbf93632a95d03c316a2a0b0829`,
and the RANGE C/wrapper remain
`c04391b8e0156ea3a4ffeeff69d76862976ffa922394d95712b96db268a5878c`
and `6b1ccba2f22a749052e88f179c55fb7a6d9e71a6eed1dfa99ca63f451a7f22b3`.
This is a review candidate only.  Production remains locked until both
independent reviews return clean.

## R124 mandatory reviews — two PASS; production RED gate accepted

The targeted and holistic reviewers independently verified the exact 9/9
manifest and live equality, one-file R122-to-R124 delta, base-identical
production, absent `transfer.c`, frozen lower/RANGE/wrapper hashes, focused and
retained results, and manual sanitizer replay.  Both confirmed that the shared
control dispatch now requires exactly one completion of its still-live local
IRP across all 61 rejection, allocation-failure, immediate, and pending
schedules, while the equivalent 22 descriptor schedules and every prior
retirement/accounting/direct-MDL assertion remain intact.  Both returned PASS
with no Critical, Important, or material Minor finding.

R125 accepts `task-9-red-postpause-original-irp-head` at manifest SHA-256
`1427ef7decf3143d5e3aa78d490c62391e5b507d8230eccf91f19249e99c5ac3`
as the Task-9 RED seal and freezes every test/support/wrapper/RANGE path.
Production implementation is unlocked for exactly eight paths: new
`winusb.sys/transfer.c`; `winusb.sys/Makefile.in`, `main.c`, and
`winusb_private.h`; `wineusb.sys/wineusb.c` and `unixlib.c`; and public
`winusb/main.c` and `io.c`.

The implementation boundary is explicit.  A helper starts with
`irp_consumed=FALSE`; pre-forward validation/allocation failures return
ownership to `main.c`, which releases the acquired file I/O reference and
terminally completes the IRP.  Once the original IRP is passed to
`IoCallDriver`, the helper sets `irp_consumed=TRUE` for both immediate and
pending results.  The lower layer then owns the sole `IoCompleteRequest`, while
the upper completion maps status/information, unlinks/decrements once, frees its
URB/record once, releases the already-acquired file I/O reference last, and
returns `STATUS_SUCCESS` without completing the IRP.  Lower slot 0 remains
lower-owned; upper completion Context owns the upper record and slots 1-3 stay
untouched.  Tests remain frozen throughout production implementation.

## R126 production-exposed fixture/support ruling

The three disjoint R125 production slices reached their actual boundaries.
Lower bus-interface and Unix focused/retained gates are green.  Public retained
descriptors are green, while public focused has one failure.  Kernel lifecycle
is green, while kernel focused has four failures and standalone binding exits
harness 2.

Read-only root-cause tracing shows that none of those six outcomes represents a
production behavior defect.  In the function contract's supported-length loop,
`CONTROL_SEED()` snapshots the expected setup before the loop replaces the
request's little-endian wLength; the lower fake therefore compares the exact
production copy against stale guard bytes four times.  In the associated public
fixture, `fake_reset()` clears `control_response_override`, after which the
fixture assigns a one-byte length without restoring the flag.  The fake reports
its unrelated synchronous default of five bytes for a one-byte output, which
the production wrapper correctly rejects just as the adjacent 17-for-16 case
requires.  Finally, the retained standalone binding wrapper still compiles
routed `main.c` and `session.c` without conditionally linking the now-present
`transfer.c`, so its undefined helper is a link failure rather than lifecycle
evidence.

R126 reopens exactly `tests/winusb_function_io_contract.c`,
`tests/winusb_user_api_contract.c`, and
`tests/winusb_function_binding_contract.sh`.  It authorizes only refreshing the
expected setup after wLength is changed, restoring the explicit one-byte public
response override after reset, and conditionally adding `transfer.c` to the
standalone binding sources.  No semantic expectation or fake behavior changes.
Every other test/support/wrapper/RANGE path and all eight production paths are
frozen.  The affected focused and retained modes must become green, and bounded
removal mutations must reproduce exactly four stale-setup failures, one public
failure, and the unresolved-helper link failure respectively.  These lines are
only reached or linked once the Task-9 production surface exists, so the
accepted missing-feature RED remains unaffected.

## R127 standalone object-reference support boundary

The R126 wrapper correction successfully adds actual `transfer.c` to the
retained standalone build.  Linkage then exposes exactly two missing fake-WDM
symbols: `ObReferenceObject` and `ObDereferenceObject`.  The full Task-9
function contract already defines and substantively observes both functions,
but the standalone lifecycle translation unit intentionally omits that later
Task-9 instrumentation and does not execute a control/descriptor request.

R127 therefore reopens exactly `tests/winusb_function_binding_contract.c` for
standalone-only, nonnull-checking definitions of those two WDM symbols.  They
must be guarded by `WINUSB_FUNCTION_BINDING_STANDALONE`, so the focused Task-9
contract continues using its existing reference-count/order observers.  No
production or other test/support path may change.  Standalone binding must exit
0; function focused/lifecycle results must remain unchanged; deleting either
shim must reproduce only its expected unresolved-symbol harness failure.

## R128 legacy RANGE gate adjudication

The required legacy RANGE command was attempted with the available offline
artifacts.  Its CP32 Unix library is exactly the sealed artifact at SHA-256
`1edd11b0336a241c1ac8c667fb1d21db3bfac08b0ebdc8f672aa2931785490d9`,
but it cannot load against today's shared class-interface fake: that fake is
SHA-256 `615fa0dd2a1df49215ffcd0fe2f4e14aa204d322052af229d951d962a9091161`,
not the RANGE-v2 sealed
`f70f767da5d1d3475e44694eeec73d6a9290fce72c333f8f856706d2642067bd`,
and no longer exports the CP32 library's unrelated `libusb_control_transfer`
import.  This is a loader/support mismatch, not feature evidence.

A second diagnostic used a compatible historical library.  Its executable
exact-RANGE behavior passed, but the frozen wrapper then rejected the current
source through its legacy SELECT_INTERFACE text scan.  Running that same scan
against the untouched `task-9-base` snapshot also fails, proving that this is a
predecessor-invalid source assertion rather than an R125 production regression.

R128 leaves the RANGE C and wrapper byte-frozen at
`c04391b8e0156ea3a4ffeeff69d76862976ffa922394d95712b96db268a5878c`
and `6b1ccba2f22a749052e88f179c55fb7a6d9e71a6eed1dfa99ca63f451a7f22b3`.
For Task-9 final gating, it substitutes the stronger current lower
`--control-descriptor` boundary: that contract compiles and executes live
`unixlib.c`, requires the exact 50-byte synthetic response with zero libusb
allocation/submission, and sends direction, type, recipient, request, value,
index, and length one-field negatives through ordinary generic libusb.  An
isolated widened-predicate production mutant must exit feature 1.  Both legacy
diagnostics remain recorded separately, and final independent review must
accept this gate substitution before sealing.

## R129 post-GREEN completeness rejection

The first R125 production head is not sealable even though its focused modes
are green.  Review traced that result to missing executable coverage and three
fixture accommodations in production, not to an acceptable implementation:

- the upper has no transfer-owned per-interface counter, validates mutable
  session/interface state without the session mutex, always selects interface
  zero, and releases the file I/O reference before its final record and object
  reference retirement;
- upper descriptor fallback admits only device/configuration types, while
  control validation accepts only reserved value `1` and conditionally ignores
  a setup-length mismatch when the fixture's uninitialized high byte is
  `0xa5`;
- the lower generic exact-RANGE response runs before structural/buffer
  validation, duplicates rather than shares the canonical predicate, skips
  function-scope validation when the interface index high byte is nonzero, and
  reports requested rather than actual length for short OUT completion; and
- the public descriptor fallback submits type zero and zero-length requests,
  while `next_handle_token` was changed from `1` to `3` solely so the focused
  test's hard-coded token `1` remained invalid.

R129 freezes all production and reopens exactly the function, lower Unix, and
public focused C contracts.  The correction must first repair the uninitialized
control seed and hard-coded invalid handle, then add behavioral schedules for
the missing interface/accounting/state/retirement, descriptor, RANGE/buffer,
scope, and short-OUT cases.  Current production must reach genuine feature RED
without a harness/compiler/link/crash failure before any production path can
reopen.  All wrappers, support files, bus-interface coverage, retained RANGE
sources, snapshots, and manifests remain unchanged.

## R130 actual-lower alternate-accounting correction

The corrected upper function contract can prove that a pending transfer on one
interface does not block an alternate change on another interface, but its fake
lower boundary cannot prove the same result through actual `wineusb.c`.
Independent lifetime review traced a successor false-GREEN to the retained
Task-7 guard there: every `URB_FUNCTION_SELECT_INTERFACE` is rejected whenever
the child-wide IRP list is nonempty.  R91 and R100 explicitly carried
replacement of that conservative rule into Tasks 9-12 once real transfer
ownership existed, and R109 assigns Task 9 real per-interface ownership for its
control and descriptor records.

R130 therefore reopens exactly `tests/wineusb_winusb_busif_contract.c` while all
production remains frozen.  Its existing actual-`wineusb.c`
`--control-descriptor` mode must retain same-target blocking and add one queued
generic interface-recipient control for interface 1 followed by
SELECT_INTERFACE for interface 0.  Current production must feature-RED by
returning `STATUS_DEVICE_BUSY` without a second Unix submission; corrected
production must send the alternate URB while the interface-1 request remains
queued, then let the test retire its local list fixture without invoking
cancellation or teardown.

The later production-unlock ruling must widen the upper kernel paths by
`winusb.sys/session.c` and the lower paths by `wineusb.sys/wineusb.c`.  Under
`wineusb_cs`, the lower may scan stable queued IRPs and classify only
unambiguous Task-9 traffic: descriptors and device-recipient controls belong to
interface 0, while interface-recipient controls use the canonical low byte of
`wIndex`.  Endpoint/other/unknown/non-Task-9 IRPs remain conservatively
conflicting.  No retained lower context, DriverContext expansion, cancellation,
release, cleanup, or removal work is authorized; those stay with Tasks 11-13.

## R131 holistic RED-review correction

The targeted review of the corrected R129/R130 head passed after the pending
control schedule set the expected file-wide I/O count to two only around its
allowed cross-interface alternate call.  The independent holistic review still
found four Important successor gaps, so production remains frozen and exactly
the function and actual-lower C contracts remain open.

The function contract must send the exact one-byte request that the rejected
production special-cases: little-endian setup length `0xa501` against declared
length one, with a one-byte direct MDL, and require rejection before lower
submission.  Its concurrency witness must use an atomic event published by the
FAST_MUTEX fake when the worker actually blocks, rather than racing on plain
file fields or counters; it must mutate file state while retaining the mutex,
release, and join only when thread creation succeeded.  The interface-state
allocation used by initialization must also be deliberately poisoned so the
two-interface schedule behaviorally proves transfer ownership begins at zero
instead of inheriting allocator contents.

The actual-`wineusb.c` contract must represent physical function root 5 and
associated interface 6.  Descriptor and device-recipient controls block an
alternate on 5 and permit 6; interface-recipient control with low `wIndex` 6
blocks 6 and permits 5; endpoint-recipient, other-recipient, and unrelated
queued URBs remain conservatively conflicting with both.  Local fixtures retire
their caller-owned list entries directly and make no cancellation or teardown
claim.

Two final implementation facts remain explicit source-review invariants because
the runtime boundaries cannot distinguish them without brittle text scans:
generic exact RANGE must call the existing canonical helper rather than copy its
predicate, and public handle allocation must restore `next_handle_token` from
the rejected value 3 to its base value 1.  Neither exception permits production
to reopen until the corrected RED replay and independent review pass.

## R132 R131-review successor correction

The first R131 candidate compiles and reaches both intended production
boundaries.  Function focused execution is genuine feature RED with 199
failures, retained lifecycle is green, and a manual ASan/UBSan focused replay
has the same 199 failures without a sanitizer marker.  The actual-lower focused
mode is genuine feature RED with exactly twelve cross-interface permit
failures, while its retained mode is green.  The exact `0xa501` request,
pointer-identifying atomic mutex event, poisoned two-interface allocation,
root-5/interface-6 recipient matrix, and post-descriptor expectation reset all
passed targeted review.  The earlier ASan overflow was a stale expected-pipe
fixture value and is corrected before the root select.

The independent holistic review nevertheless rejected this head.  A single
pending transfer per interface cannot distinguish a real count from a Boolean.
The mutex schedule mutates file state but does not prove endpoint lookup occurs
after acquiring the same mutex.  Each lower schedule queues only one child, so
a first-entry-only classifier remains possible.  The critical-section fakes do
not observe that classification occurs under `wineusb_cs`.  Busy SELECT does
not prove that its stack IRP stayed out of the device list, and permitted SELECT
proves only nonnull links before a cleanup helper can mask the defect.  Finally,
a failed C11 join records a check and then continues to touch worker-owned
state, which is not a safe harness terminal path.

R132 keeps every production file frozen and reopens only
`tests/winusb_function_io_contract.c` and
`tests/wineusb_winusb_busif_contract.c`.  Function C must keep two same-interface
caller-owned requests pending together, complete only one and require the
target alternate to remain blocked, then complete the second and permit it.
Its existing exact-mutex rendezvous must also drive an endpoint-recipient
request after a real pipe map exists; the test changes that endpoint while
holding the mutex and requires post-lock rejection.  Join failure must terminate
the harness before any worker-owned state is read.

The actual-lower contract must queue valid root-5 and interface-6 children in
both orders and require either conflicting later entry to block its target.
Every busy SELECT must leave the exact prior list order and membership intact;
every permitted pending SELECT must appear exactly once after the prior entries
before local retirement.  A one-shot fake may add a conflicting caller-owned
entry only for the duration of `wineusb_cs`, proving the classifier observes
the locked list without a source scan.  The fixture removes only its own entries
and makes no cancellation, cleanup, teardown, or removal claim.

The GCC TSan exit 66 is retained only as an invalid diagnostic: a minimal C11
`thrd_create` worker containing one atomic load reproduces the same libtsan
zero-page crash, while equivalent pthread atomic and complete mutex schedules
are TSan-clean.  It is neither feature evidence nor a Task-9 race report.
Focused and retained replays, ASan/UBSan diagnostics, an exact frozen candidate,
and two independent clean reviews remain mandatory before production reopens.

## R133 first R132-successor review correction

The first R132 successor was frozen as the exact 2/2
`task-9-r132-head.sha256` candidate at manifest SHA-256
`2bf2c60c9f0c250051c09ddb6f1e9eb49ba6f149562360cdab585b374fcd0cc1`.
Controller replay reproduced function feature exit 1 with 203 failures,
actual-lower feature exit 1 with twelve failures, both retained GREENs, and a
manual ASan/UBSan feature replay with the same 203 failures and no sanitizer or
harness marker. The other fourteen Task-9 paths remained hash-exact.

Both mandatory reviews rejected the candidate. They independently found that
the two identical pending controls prove aggregate multiplicity but not two
distinct per-request completion contexts and URBs or their individual
retirement; swapped or shared contexts can pass. The targeted review also
found three lower false greens: a captured IRP can be classified after
`wineusb_cs` because its URB stays valid after lock exit; a busy SELECT can be
transiently inserted and removed before the final list snapshot; and both
two-child schedules put the conflict last, allowing a last-entry-only
classifier.

R133 preserves the rejected head and reopens only the same two live C
contracts for the mandatory review fix. Function C must journal two distinct
live context/URB pairs, use distinguishable stored completion outcomes, and
prove only the matching pair retires at each completion. Bus-interface C must
invalidate or change the injected child's classification fields at lock exit,
observe every production-boundary list insertion so a busy SELECT is never
transiently queued, and add mirror first-conflict schedules. All production,
support, wrappers, RANGE, other tests, snapshots, and rejected evidence remain
frozen. Fresh focused/retained, sanitizer, bounded mutants for all four gaps, a
new exact candidate, and clean independent re-review remain mandatory before
production reopens.

## R134 R133-review completion-allocation correction

The corrected R133 head was frozen as the exact 2/2
`task-9-r133-head.sha256` candidate at manifest SHA-256
`2d1ad6b0da1cf9d39b059e13e4a9953c83b4fcbd79a3b6df26f0825a56228ba1`.
Controller replay reproduced function feature exit 1 with 203 failures,
actual-lower feature exit 1 with twelve failures, both retained GREENs, and a
manual ASan/UBSan function replay with the same 203 failures and no sanitizer
or harness marker.  The fourteen frozen paths and all stored evidence verified.

The targeted re-review passed with no material finding, and every R133 lower
correction reviewed cleanly.  The holistic re-review nevertheless found one
Important function false-green.  Allocation observation is paused before the
two pending-request completions while only frees remain journaled.  A completion
routine can allocate replacement context/URB objects, copy and use those
objects, free the four originally observed objects in the expected pairwise
order, free the untracked replacements, and preserve all statuses, counts, and
global allocation balance.  The existing final 4/4 check would still pass.

R134 preserves `task-9-r133-head` as rejected evidence and reopens only
`tests/winusb_function_io_contract.c`.  The actual-lower contract is frozen at
SHA-256 `9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348`;
all production, support, wrappers, RANGE, other tests, snapshots, and prior
evidence remain frozen.  The correction must independently forbid or count
allocations only around each `complete_pending_task9_irp()` call, excluding
intervening alternate-selection work, and a bounded completion-time recreation
mutant must be caught by that executable lens.  Fresh focused/retained,
ASan/UBSan, exact-snapshot, frozen-path, and two-clean-review gates remain
mandatory before production reopens.

## R135 R134-review retained-allocator correction

The R134 successor was frozen as the exact 2/2 `task-9-r134-head.sha256`
candidate at manifest SHA-256
`7af721f59ec7d9b50ae47ebfee6c18aa8f9abcc1b72ce88490abcca6c4c56fd4`.
Controller replay reproduced function feature exit 1 with 203 failures,
actual-lower feature exit 1 with twelve failures, both retained GREENs, and a
manual ASan/UBSan function replay with the same 203 failures and no marker.
The exact 74-line delta, fourteen frozen paths, twelve controller artifacts,
and live candidate equality all verified.

Targeted review passed cleanly.  Holistic review nevertheless found one
Important allocation-route false-green.  The function contract renames pool
allocation while including the binding fixture, which textually includes
actual `winusb.sys/main.c`; allocations compiled into that production unit use
the retained fake allocator rather than R134's direct completion observer.  A
bad completion can call new `main.c` allocation/free helpers, clone the
transfer/URB pair, retire the four admission-journaled originals correctly,
use and free the unobserved replacements, and preserve all statuses, list,
reference, and global balance checks.

R135 preserves `task-9-r134-head` as rejected evidence and reopens only
`tests/winusb_function_io_contract.c`.  The actual-lower contract stays frozen
at SHA-256 `9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348`;
all production, support, wrappers, RANGE, other tests, snapshots, and prior
evidence remain frozen.  Retain the direct per-attempt observer, snapshot the
shared `pool_allocations` count at each completion interval, require that count
unchanged at interval end, and prove a bounded recreation mutant routed through
actual `main.c` helpers now fails.  The retained allocator increments the
shared count before its own failure branch, so the combined lens covers both
successful and failed helper attempts while excluding alternate calls.  Fresh
focused/retained, sanitizer, exact-snapshot, frozen-path, and two-clean-review
gates remain mandatory before production reopens.

## R136 R135-review retained-admission and replay correction

The R135 successor was frozen as the exact 2/2 `task-9-r135-head.sha256`
candidate at manifest SHA-256
`fe3bd2130c4af10935088c22cf9541182d78816b2b1bb50213613073da1815ae`.
Controller replay reproduced function feature exit 1 with 203 failures,
actual-lower feature exit 1 with twelve failures, both retained GREENs, and a
manual ASan/UBSan function replay with the same 203 failures and no marker.
The exact 34-line delta, fourteen frozen paths, twelve controller artifacts,
and live equality all verified.

Both mandatory reviews rejected the candidate.  They found that the direct
admission journal still cannot see replacement pairs allocated through actual
`main.c`'s retained allocator before completion begins.  A bad implementation
can preallocate those pairs during admission, preserve the two original stack
pairs and outcomes, then copy/use/free the replacements during completion while
retiring the four journaled originals in the expected order; neither R135
completion interval observes an allocation.  Holistic review also found the
required helper mutant unverifiable because its exact sources and logs were
removed, and found the unsigned shared-counter equality theoretically
wrap-capable.

R136 preserves `task-9-r135-head` as rejected evidence and reopens exactly
`tests/winusb_function_io_contract.c` and
`tests/winusb_function_binding_contract.c`.  Binding support may add only a
default-no-op hook at retained `ExAllocatePool` entry before failure handling.
The function contract may enable it as a nonwrapping Boolean attempt latch,
armed around each pending admission and completion.  Retain the direct
admission journal; use a nonwrapping direct completion latch; keep all
alternate calls outside completion intervals; and remove or demote the shared
arithmetic equality.  Preserve exact mutant sources/diffs, pre/post logs,
exits, and hashes for admission-time and completion-time actual-`main.c` helper
routes plus a retained failed attempt.  The lower contract remains frozen at
`9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348`;
all production, wrappers, RANGE, other tests/support, snapshots, and prior
evidence remain frozen.  Fresh function focused/lifecycle, standalone binding,
sanitizer, exact-snapshot, frozen-path, and two-clean-review gates remain
mandatory before production reopens.

## R137 R136-review second-ordinal replay correction

The R136 successor is frozen as the exact 3/3 `task-9-r136-head.sha256`
candidate at manifest SHA-256
`f1f81159399034bf492f419c6e3fda61fadc2305251cd2833b9710ad0ec98298`.
Controller replay reproduced function feature exit 1 with 203 failures,
actual-lower feature exit 1 with twelve failures, lifecycle/standalone
binding/lower retained GREEN, and manual ASan/UBSan with the same 203 failures
and no marker.  Its 142-line diff, fourteen controller artifacts, fourteen
frozen paths, and 54-file replayable evidence bundle all verified.  Independent
replay reproduced the five declared first-ordinal cases.

Holistic review passed cleanly.  Targeted review nevertheless found one
Important evidence-only gap: the admission, completion, and failed-attempt
fixtures all target operation ordinal one.  A candidate can omit only the
second admission and completion hook calls while every existing replay keeps
its declared result.  Source inspection sees the live calls, but cannot replace
the required executable witness.

R137 leaves the live R136 candidate and every existing source/artifact frozen.
It authorizes only a new additive, sealed task-local package with hookless
controls and corrected cases targeting admission two and completion two.  Each
control must remain exactly 203; each corrected case must add exactly one
retained-latch failure, with helper allocation/free balance, the original 4/4
journal, successful compile, feature exit 1, and zero direct-lens or bad marker.
Fresh two-review acceptance of the unchanged R136 head plus this additive
evidence remains mandatory before production reopens.

## R137 additive second-ordinal package completion

The interrupted R137 packaging process was recovered after all four copied
fixtures had already compiled and executed but before their zero-byte
instruction/replay placeholders were completed. No fixture source, mutation
diff, stored compiler output, stored execution output, live R136 source, prior
artifact, or production path was changed during recovery.

`task-9-r137-second-intervals/manifest.sha256` now seals exactly 56 unique
non-self files at manifest SHA-256
`5d273ba5347f12783e227580da2c56d20f59c66b1d14769504d9342b842b4513`.
Immediate verification passed 56/56. The package contains top-level and
per-case instructions, top-level and per-case replay entry points, exact source
copies and mutation diffs, compiler logs/exits, complete run logs/exits, and a
stored all-case replay result.

Fresh replay compiled every copied fixture successfully and exited package 0.
The second-admission hookless control and second-completion hook-bypass control
each exited feature 1 with exactly 203 failures, zero retained-latch failures,
zero direct-lens/helper-accounting failures, and zero bad markers. Their
unchanged-R136 counterparts each exited feature 1 with exactly 204 failures,
exactly one `control_retained_allocation_end` failure, zero direct-lens or
helper-accounting failures, and zero bad markers. Both normalized
control/corrected log comparisons were exact after removing only the intended
retained-latch witness and normalizing source line numbers and terminal failure
counts.

The frozen `task-9-r136-head.sha256` reverified 3/3 and the prior
`task-9-r136-mutants/manifest.sha256` reverified 54/54 after the R137 replay.
BAT0 was 24 percent and charging. No io24 device, Wine/prefix, contained build,
staging, network, firmware, preset/effect, or live hardware action occurred.
Production remains frozen. `task-9-r137-review-request.md` defines the two
mandatory independent read-only review lenses; no production reopen or Task-9
completion claim is made before both return clean PASS verdicts.

## R138 R137 mandatory reviews — both PASS

The targeted and holistic reviewers independently verified the unchanged 3/3
R136 head, prior 54/54 evidence bundle, additive 56/56 R137 package, fourteen
frozen paths, live candidate equality, and a fresh additive replay. Both
returned final PASS verdicts with no Critical, Important, or material Minor
finding.

Controller replay again reproduced successful compilation and the exact
203/204 control-to-R136 failure counts for both admission two and completion
two, retained counts 0/1, exact normalized comparisons, and zero direct,
helper-accounting, or bad markers. The controller also reverified all three
manifests after review.

Both reviewers separately examined and withdrew an initial provenance concern
about the hook-bypass binding. The prior 54-file bundle is an explicit
immutable review input, its `completion/bypass` case is the sealed hookless
control, and the R137 binding is byte-identical to that source and the R136
base at SHA-256
`dd9f1f86ffa6ce35e00715fbead4f971678caa6890faa20d3b97c657b36eb25a`.
The R137 diff records the new second-completion mutation; the complete
inherited binding is separately copied and sealed. No immutable-byte or replay
bypass remains.

R138 accepts the unchanged R136 candidate plus the additive R137 package. It
reopens only the R125 eight-path production boundary as widened by R130 to add
`winusb.sys/session.c`, solely for the R129-R131 correction. Every test,
support, wrapper, RANGE, snapshot, manifest, and prior evidence path remains
frozen. The implementation must retain the R125 original-IRP ownership rule,
implement per-interface accounting and the locked conservative lower scan,
reuse the canonical RANGE helper, restore `next_handle_token` to seed 1, and
add no Tasks 11-13 behavior. Fresh focused, retained, sanitizer, mutant,
freeze, and independent production-review gates remain mandatory before Task
9 seals.

The exact verdicts and nine-path boundary are recorded in
`task-9-r137-targeted-review.md`, `task-9-r137-holistic-review.md`, and
`task-9-r137-review.md`. BAT0 was 30 percent and charging. No production,
Wine/prefix, io24 device, USB/sysfs device path, driver/build/staging, network,
firmware, preset/effect, or live hardware action occurred during review or
adjudication.

## R139 authorized oracle correction — applied, replayed, and rejected

The controller authorized the sealed R139 two-test proposal. Before editing,
the proposal/adjudication manifest verified 2/2, the live test hashes matched
the declared R139 pre-edit bytes, and `git apply --check` succeeded. An exact
2/2 rollback snapshot was created as `task-9-r139-test-base/`.

Only the sealed changes were applied: the upper MI06 endpoint positive now
refreshes its exact expected setup packet, and six Unix interface-recipient
RANGE negatives run as non-function fixtures so they reach generic routing.
The resulting live diff is exactly eleven insertions and one deletion and is
frozen 2/2 in `task-9-r139-test-head/` at manifest SHA-256
`fd27abae1e92fb4b93f96e4c49f2792f205e6f693331d17b090b6992d8b05e62`.

All four focused boundaries exited 0; upper and Unix summaries reported zero
failures. Upper lifecycle and actual-lower retained `--red` also exited 0. The
legacy RANGE wrapper reproduced R128's predecessor-invalid loader mismatch
before assertions; the approved executable lower substitute passed. The exact
fourteen replay artifacts verify at manifest SHA-256
`0cf8ce97cb349d6a1093d731bf8508d77178674c5a66b12c5737591d9c75b24f`.

Both mandatory reviewers nevertheless returned `REQUEST CHANGES` with the
same Important false green. The exact RANGE positive remains function-scoped,
while all six interface negatives are non-function fixtures. Production can
use the exact predicate for non-function devices but widen it only for
function devices; every R139 assertion then passes while bad function-scoped
tuples synthesize RANGE. Controller reproduction applied the targeted mutant
only in `/tmp`; the actual lower focused wrapper exited 0 with zero failures.
The temporary tree was deleted.

R139 is rejected. The upper expectation correction is sound, but the two-file
head is not an accepted final oracle. R138 sanitizer, final mutants, production
review, and seal work remain stopped.

## R140 proposed two-scope RANGE evidence

R140 requests one additive correction in exactly
`tests/wineusb_winusb_urb_contract.c`. The proposal retains every R139 byte,
adds a non-function exact RANGE positive, and pairs each of six interface
one-field negatives across function-scope reject/no-mutation and non-function
generic-routing paths. The device-recipient negative, structural checks,
generic request, exact function positive, and `0xab05`/`0xab07` witnesses stay
unchanged.

In disposable copies, the proposed test stayed green against live R138
production. It caught the R139 passing broad/suppress mutant at exit 1 with 16
failures, a non-function-only exact suppression mutant with four failures, and
a function-only direction-widening mutant with three failures. The patch dry
runs cleanly against the live frozen R139 head and produces the byte-exact
isolated candidate.

`task-9-r140-adjudication.sha256` seals the two R139 verdicts, combined
adjudication, proposed patch, successor request, and isolated proof 6/6 at
manifest SHA-256
`1c75fcd2f42a9066a3b0efb69042b1c245e769f68e897aacdfee13b0ce009354`.
This is a proposal only. Every live byte remains frozen until explicit
controller authorization.

## R140 preauthorization reviews — rejected before live application

Both reviewers returned `REQUEST CHANGES`. Targeted review found that the new
scope-reject helper did not observe allocation attempts/counts/frees, buffer
activity, or submit attempts; allocate/free-before-error production therefore
passed. Holistic review independently confirmed that defect and found two more
Important false greens: no function/in-scope low-byte membership case and no
tail-guard loop on the non-function exact positive.

R140 was never applied. Its exact 6/6 package remains preserved at manifest
SHA-256
`1c75fcd2f42a9066a3b0efb69042b1c245e769f68e897aacdfee13b0ce009354`,
and both live tests remain byte-identical to the rejected R139 head.

## R141 proposed complete three-scope matrix

R141 replaces, rather than layers on, the rejected R140 proposal. It still
requests exactly `tests/wineusb_winusb_urb_contract.c`, but applies directly
from the live R139 head. A consistent `{0,1,5}` interface set models
function/in-scope membership. Exact positives and all seven one-field misses
run across non-function, function/out-of-scope, and function/in-scope states.
The recipient negative routes generically in all three; each of the other six
negatives rejects only in the out-of-scope function case and routes generically
otherwise.

Shared exact-positive assertions now require the 50-byte payload, exact
reported length/status, prefix and complete tail guards, zero transfer
allocation attempts/counts/frees, zero buffer activity, zero submit attempts,
no pending transfer, and null `DriverContext`. Scope rejection additionally
requires unchanged transfer length and complete caller storage.

The isolated candidate executes live R138 production at exit 0 with zero
failures and detects six production mutants: R139 broad/suppress (60 failures),
membership suppress/direction widen (14), reject allocate/free (6),
non-function tail corruption (1), non-function exact suppression (4), and
membership-conditioned recipient widening (10). Every mutant is an executable
copied-`unixlib.c` run, not a source scan.

`task-9-r141-adjudication.sha256` verifies 6/6 at manifest SHA-256
`78e386e8da2e8232009bc4b4e445f02f5afde02a4a56ee432e80459a366fb324`.
The sealed patch dry-runs cleanly and produces the byte-exact isolated
candidate. This remains a proposal under independent preauthorization review;
no live edit is authorized or applied.

## R141 preauthorization reviews — rejected before live application

Both reviewers returned `REQUEST CHANGES`. Targeted review executed a bad
function/in-scope direction-negative production copy that wrote the first 49
captured RANGE bytes into caller storage before completion. R141 only required
inequality with the complete 50-byte answer, so the actual wrapper still exited
0 with zero failures.

Holistic review found two independent Important gaps. Exact success did not
observe synchronous `libusb_control_transfer()` activity followed by the
correct local response, and every non-function fixture retained impossible
function count/root/bitmap metadata. R141 was never applied. Its live base
remains the 2/2 rejected R139 head.

## R142 coherent three-scope proposal and isolated proof

R142 retained the complete R141 truth table while making non-function metadata
coherent, comparing the full exposed fake count/record and allocation/submit
state around exact and reject paths, and requiring complete guarded caller
storage to remain unchanged for every pending generic miss.

The isolated candidate executed live R138 production at exit 0 with zero
failures. It killed eight compiled bad production variants: broad/suppress
(66 failures), membership suppress/direction widen (20), reject allocate/free
(18), non-function tail write (1), coherent non-function suppression (10),
synchronous control then local response (6), targeted 49-byte pre-completion
write (1), and membership recipient widening (10). Final restored replay again
exited 0 with zero failures.

The one-file patch dry-runs from live R139 and produces candidate SHA-256
`c4175a58739f09b5d05ccbec6870fbc6cc4dd24ba2ff311272e7e3bff3d53051`.
`task-9-r142-adjudication.sha256` verifies 6/6 at manifest SHA-256
`85820f80ba02cdeec90eb351c827892930410cfe428f3b65986bea325e8499dc`.
R142 remained unapplied while both preauthorization reviews ran.

## R142 preauthorization reviews — rejected before live application

Holistic review proved the exact status postcondition was self-fulfilling:
`reset_control()` seeds zero, already `USBD_STATUS_SUCCESS`, so omitting the
production success-status write passes all three exact positives. Targeted
review executed a different false green: an exact-path
`libusb_get_device()`/`libusb_get_device_descriptor()` probe mutates none of the
snapshotted fake state, so the actual wrapper still exited 0 with zero failures.
The same instrumentation blind spot applies before scope rejection.

R142 is rejected. R143 may be proposed only in a disposable tree and must add a
non-success exact-status sentinel plus a fake-boundary-wide libusb call witness.
Because the witness must live at the fake entry points, the successor proposal
necessarily requests exactly the lower contract and its fake support path. Live
tests and production remain frozen; no R143 application is authorized.

## R143-R145 boundary-witness successors — rejected before application

R143 added the non-success exact-status sentinel and a global first-operation
call witness to all 32 exported fake libusb entries. Its isolated candidate
stayed green and killed eleven copied-production mutants, but review proved
that generic, malformed-admission, and null-buffer rejection helpers still
observed only partial backend state.

R144 extended the complete backend snapshot to those helpers and killed all
fourteen required mutants. Review then proved that endpoint-recipient rejection
was an unbounded exception: extra device/configuration actions could execute
while the expected return, zero-control, and no-pending checks still passed.

R145 added exact dedicated call counts for the retained endpoint authority
sequence and killed sixteen mutants. Review showed that equal counts did not
bind argument identity or order; a same-count null-handle substitution still
passed. R143, R144, and R145 were never applied. The live base remained the
frozen rejected R139 two-file head.

## R146 endpoint authority journal — rejected before application

R146 appended ABI-identical ordinal and pointer-lineage journals to the lower
contract and fake. Nineteen copied-production mutants executed through the
fake and failed as intended, with clean focused/retained baseline and final
replays.

Both reviews nevertheless returned `REQUEST CHANGES`. Executable variants
proved four material gaps: post-call handle authority was self-referential; a
correct descriptor release moved before traversal remained invisible; generic
and endpoint rejections could corrupt caller-visible state; and active-config
local initialization preceded the claimed first executable global witness.
R146 was never applied.

## R147 lifetime and rejection-state oracle — rejected before application

R147 moved executable work behind the global witness, made the fake active
configuration a refreshable mutable view whose exact release poisons the view,
captured the pre-call device handle, and added complete fixture plus deep
pipe-table snapshots to generic and endpoint rejection. Twenty-four canonical
mutants failed as features and focused/retained baseline and final replays were
clean.

Independent review found that function-scope rejection still omitted the
complete snapshot and that the literal unconditional early-release variant was
converted to harness exit 2 by retained preflight. Controller follow-up proved
the malformed-admission and exact null-buffer helpers shared the partial-state
gap, and a changed/null pipe-table pointer could crash the nominal deep
comparison. R147 was rejected and never applied.

## R148 unified safe rejection state — sealed proposal under review

R148 applies directly from frozen R139 and still requests exactly the lower
contract and fake. It factors complete fixture and pipe-table comparison into
safe predicates, checks pointer identity before any deep read, and uses the
same snapshot in generic, endpoint, function-scope, malformed/mismatched/
undersized admission, and forked null-buffer rejection. It also preserves
retained product assertion failures as top-level feature failures while
keeping genuine harness paths at exit 2.

Fresh focused and retained baseline/final replays compile copied production
through the candidate fake and exit 0 with zero failures. All 29 canonical
copied-production mutants exit feature 1 with nonzero assertions. Rows 1-28
emit the fake pass marker; literal unconditional early release instead emits
retained assertion evidence, continues through the requested lower group,
prints its normal summary, and exits 1 with 96 failures and no crash or harness
substitution. The 29 logs have 29 distinct hashes.

The candidate fake retains 32 compiled exports, 33 source witness references,
32/32 first compiled global-count accesses, three immediate dedicated journal
increments, identical count/record layouts, complete resets, and a passing
mutable-view poison/refresh probe. The twelve-hunk direct patch reconstructs
candidate hashes
`56a7aace5141dff885e4859659cc1e729031deeba76e371cbbcc1b64ebdf7cf5`
and
`bd76d84e99227549eb587317971c33707457b56d93de3a90e1e5672b509bab15`
byte-for-byte. Patch SHA-256 is
`23333adc2918a72e2f1b32c53713533620f1be782373d1fcd389f4c598f2d08a`;
the 101-entry evidence archive SHA-256 is
`561da904b991e9fcf41c55f1c95230f7a8f90d5e24c228069e9f606b22dea4a1`.

Two independent read-only preauthorization reviews are in progress. No live
test or production byte is reopened, no application is authorized, and Task 9
remains active.

## R148 source-bound mutation supplement — controller verified, reviews pending

The first targeted R148 preauthorization review returned `REQUEST CHANGES` on
the evidence package rather than accepting the mutation claims. The archive
bound each row to a log, exit, failure count, and mutant hash, but did not ship
the actual per-row mutated source, a diff, or a deterministic materialization
recipe. The claimed 29 feature REDs therefore lacked source-bound provenance.
No R148 byte was applied, and the review gate remained closed.

The additive source-bound replay now supplies, for every row, the exact mutated
`unixlib.c`, zero-fuzz reconstructible diff, deterministic recipe, mutated
pre/post hashes, restored source/hash, execution log/exit, structured result,
and row manifest. All 29 copied-production executions exited 1 with their exact
nonzero assertion counts; rows 1-28 emitted one fake pass marker, while row 29
carried the retained-assertion witness and emitted none. All 29 mutant source
hashes are distinct, and the four before/after focused and retained gates exit
0 with zero failures.

The deterministic archive
`task-9-r148-source-bound-evidence.tar.gz` has SHA-256
`36f43b038bb0bab62fde7975a7acd0a14de8e6f33946ce077e12e6e4c65b6a06`.
The standalone controller verifier checked 313/313 package entries, all 29 row
manifests, all 29 zero-fuzz reconstructions, all classifications and
restorations, four clean replays, the embedded generator, safe archive paths,
and all four frozen live-file hashes, then returned `PASS`.

This closes the identified controller-side provenance packaging defect only.
The combined original R148 proposal and additive supplement still require new
clean targeted and holistic independent verdicts. R148 remains unapplied;
production, tests, fake, protected prefix, USB/device, staging, and the R138
closure gate remain frozen.

## R148 holistic rejection and R149 lifecycle-oracle successor

The repaired R148 package received a targeted `PASS`, but holistic review
proved two Important false greens. Releasing a pipe-table allocation while
preserving its pointer value still passed the deep rejection-state comparison,
and caching nested configuration data before releasing the top-level fake
object left static descendants traversable. Controller reproduction confirmed
focused exit 0 for the first defect and focused plus retained exit 0 for the
second. R148 was rejected and never applied.

R149 is a new direct, test-only proposal from the frozen live head. It requires
per-pointer allocation liveness before pipe-table comparison, makes the fake
configuration/interface/alternate/endpoint graph a bounded mutable view, and
poisons every layer on exact release. The wrapper compiles the existing
allocation observer into the fake while preserving its opt-in reclamation
checks.

The final source-bound oracle first reproduces all three escapes against exact
R148, then catches them under R149 at feature exit 1 with assertion counts 1,
10, and 5. Focused and retained clean gates pass before and after, three actual
harness cases remain exit 2, and the older allocation-reclamation audit passes
at exit 0 with zero failures.

The direct three-file patch SHA-256 is
`69ad5fb4e1f406a947313ba662cfefff73a45e6d1487086994c3ae0f1d18fa95`.
Candidate hashes are
`29082348c3d29d75a99e9290c0c54fe8586a3fc8d4bc248e61f1633a1efe59ac`
for the lower contract,
`1096aa0298a3950103d1ce1a5497b2afb07d43b41a8832fa03954282ef8a9539`
for the fake, and
`6c2b64c2e1a7b328af951f6d33df36739b51683eeb8bfbac98ccaa6dbadea7cf`
for the wrapper. The 86-entry evidence archive SHA-256 is
`f9d9879bf0806482d555c7c69fe7e75348e173df0344634b758fb48fffe00527`.

The standalone controller verifier returned `PASS` for 86/86 package entries,
two source-bound rows, three feature executions, four clean gates, direct patch
reconstruction, and all five frozen live surfaces. R149 remains unapplied and
awaits fresh targeted and holistic independent review; Task 9 remains active.
