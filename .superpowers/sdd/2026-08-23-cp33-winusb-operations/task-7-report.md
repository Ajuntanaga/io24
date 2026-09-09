# CP33 Task 7 implementer report (partial; not a completion claim)

## Test-first public DLL boundary

Before production edits, I added the focused `--alternate` user-contract mode
and executed it against the sealed Task-6 production source.  It returned
feature exit 1 (one missing `WinUsb_SetCurrentAlternateSetting` definition),
not harness exit 2:

```text
CP33 public executed mode=--alternate target-mask=0x88c present-mask=0x19c
missing-mask=0x800 ... failures=1
```

The public contract now invokes the real DLL sources and fake DeviceIoControl
boundary.  It checks the public symbol, root and associated-handle routing,
exact 32-byte alternate request header and index, unknown/stale handle,
unknown alternate without submission, immediate failure preservation, and a
pending successful submission.  The focused public gate is green:

```text
CP33 public executed mode=--alternate target-mask=0x88c present-mask=0x99c
missing-mask=0 ... failures=0
exit 0
```

## Changed paths and SHA-256

```text
7443e37451478fd3102d4d3381342fb3fe54c8ce8fd9f63967ee903a6367a1bb  dlls/winusb/main.c
5b9df910e1e1bac6587048e2af337197e8e3933c1ad9582ca699e62991fc0bfe  dlls/winusb/winusb_private.h
aed7eb71709f9aabf126030c1f8f6b3bfd2cc0be84530fc52ad68c20e1083a0e  dlls/winusb/Makefile.in
872946bfeffefba238869498d707e94b9d8d3be60089c0e431f188ddf717b775  dlls/winusb/io.c
055068552fc5e7bfae339e5619f6e1110d3fbab5028ae8185f0581a4634f334f  tests/winusb_user_api_contract.c
781989250735120f7f4eb60d347c13d18541be652d6c07f97ec98ecfc87f6a4b  tests/winusb_user_api_contract.sh
```

## R86 corrected fixtures and current result

R86 replaced the malformed upper request with an exact guarded 32-byte
`wine_winusb_alternate_request` (zero output length), and the lower request
with a variable-sized two-pipe URB.  Both corrected fixtures first returned
feature exit 1 against Task-6 production.  The current focused gates are
green: upper alternate, lower alternate, public alternate, retained claims,
and sanitizer-enabled initialize all exit 0.

The current production implementation is a narrow functional slice only.  It
does not yet satisfy the full R84/R85 token-table, stale-generation, and
rollback/preservation matrix; therefore this report remains an implementer
progress record, not a Task-7 completion claim.

## Superseded blocker

I did not implement or claim the upper/lower alternate path.  The frozen
focused `--alternate` cases are not valid inputs for the required production
ABI: the upper contract sends a 64-byte test-only `struct request`, instead of
the exact 32-byte `wine_winusb_alternate_request`; the lower contract declares
two pipes while using `sizeof(USBD_INTERFACE_INFORMATION)` as its interface
length.  R84/R85 require the production code to reject each condition before
the backend call.  Making those current tests green would create a false
GREEN by weakening the required validation.

Current lower/upper alternate gates therefore remain the sealed expected RED
(exit 1, three executed assertions each) pending a corrected test-first
fixture.  The existing Task-6 claim regression remained green (exit 0).  No
Wine process/prefix, build staging, USB/sysfs/device, or other live action was
used.

## Task 7 fix round 2

No-Git checkpoint label: `task-7-round-2-head` (synthetic working label only;
no checkpoint snapshot, manifest, commit, or seal was created).  The verified
starting snapshot was `task-7-round-2-base`.

### TDD RED/GREEN: alternate cleanup ownership

The upper contract now executes the real separately compiled `session.c`,
tracks every pointer returned by its session-pool allocator, rejects an
unknown `ExFreePool` pointer without calling libc `free`, and dirties the
reused call frame with `0xa5` before invalid-state, unknown-alternate, and
first-allocation-failure schedules.

RED used the exact base `session.c` in the retained temporary source root; its
SHA-256 is the round-2-base value
`220323174f1b35a334872cad5b332e238df1ce4a146bb728e0c8474850c5abd2`:

```text
tests/winusb_function_io_contract.sh /tmp/io24-cp33-task7-upper-unknown-free-red --alternate
exit 1
FAIL ExFreePool: rejected unknown session pointer 0xa5a5a5a5a5a5a5a5  (three times)
CP33 function executed mode=--alternate ... failures=6
```

Production initializes `select` to `NULL`.  GREEN:

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --alternate
exit 0
CP33 function executed mode=--alternate ... failures=0
```

### TDD RED/GREEN: partial claim extension

The new lower regression commits MI07 alternate 0 with a descriptor-backed
bulk `0x82` token, proves that token usable, commits MI05 alternate 1 through
a separate function transaction, then proves MI07 remains claimed and the
original MI07 token remains current and usable.  Against the pre-fix live
`unixlib.c` it produced the required feature RED:

```text
tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source \
  .io24-build/winusb-function-binding-v1/build-a \
  .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --claims
exit 1
FAIL group_claims: submit_request(&extension_device,&pipe)==STATUS_SUCCESS
FAIL group_claims: io24_fake_libusb_counts()->clear_halt==clear_before+2
CP33 lower executed mode=--claims completions=0 failures=2
```

The fix copies committed function pipe state into staging, retires only
records for interfaces named by the new transaction, and publishes that
staged table only on COMMIT.  Rollback continues to discard staging while the
old committed pointer/table remains untouched.  The same command then exited
0 with `CP33 lower executed mode=--claims completions=0 failures=0`.

### R97/R98 isolated final-head mutants

All roots remain present under `/tmp`; each contains a copied
`dlls/wineusb.sys` plus a read-only source-include symlink.  Workspace source
and tests were not mutated for these runs.

1. `/tmp/io24-cp33-task7-mutant-generation-per-pipe`

```diff
- interface->AlternateSetting, generation)))
+ interface->AlternateSetting, generation + i)))
- table->next_generation = generation + 1; /* terminal after max; never wrap */
+ table->next_generation = generation + interface->NumberOfPipes;
```

```text
tests/wineusb_winusb_urb_contract.sh /tmp/io24-cp33-task7-mutant-generation-per-pipe \
  .io24-build/winusb-function-binding-v1/build-a \
  .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --alternate
exit 1
FAIL group_alternate: ((uintptr_t)old0>>9)==((uintptr_t)old1>>9)
FAIL group_atomicity: submit_request(&device,r)==STATUS_SUCCESS
CP33 lower executed mode=--alternate completions=0 failures=2
```

2. `/tmp/io24-cp33-task7-mutant-publish-before-commit`

```diff
  transaction->pipe_table = table;
+ published = calloc(1, sizeof(*published));
+ *published = *table;
+ free(params->device->pipe_table);
+ params->device->pipe_table = published;
```

The actual mutant includes the allocation-failure cleanup around the shown
publication block.

```text
tests/wineusb_winusb_urb_contract.sh /tmp/io24-cp33-task7-mutant-publish-before-commit \
  .io24-build/winusb-function-binding-v1/build-a \
  .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --alternate
exit 1
FAIL group_target_only: device.pipe_table==committed
FAIL group_target_only: submit_request(&device,&pipe)==STATUS_INVALID_PARAMETER
FAIL group_target_only: device.pipe_table==committed
FAIL group_target_only: submit_request(&device,&pipe)==STATUS_SUCCESS
CP33 lower executed mode=--alternate completions=0 failures=4
```

3. `/tmp/io24-cp33-task7-mutant-rollback-loses-old`

```diff
- else release_claim_transaction(params->device, transaction);
+ else
+ {
+     release_claim_transaction(params->device, transaction);
+     free(params->device->pipe_table);
+     params->device->pipe_table = NULL;
+ }
```

```text
tests/wineusb_winusb_urb_contract.sh /tmp/io24-cp33-task7-mutant-rollback-loses-old \
  .io24-build/winusb-function-binding-v1/build-a \
  .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --alternate
exit 1
FAIL group_target_only: device.pipe_table==committed
FAIL group_target_only: submit_request(&device,&pipe)==STATUS_SUCCESS
FAIL group_target_only: io24_fake_libusb_counts()->clear_halt==before+1
CP33 lower executed mode=--alternate completions=0 failures=3
```

### Focused GREEN gates

Each command below exited 0:

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --alternate
LSAN_OPTIONS=detect_leaks=0 tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --lifecycle
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --session
tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --alternate
tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --claims
tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --sync-pipes
tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --transfer-lifetime
tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source
tests/winusb_function_binding_contract.sh .io24-build/winusb-api-v1/dev-source
```

Terminal evidence was respectively `failures=0` for all four upper modes;
`failures=0` for lower alternate/claims/sync-pipes and
`completions=2 failures=0` for transfer-lifetime; metadata printed
`WineUSB WinUSB metadata bus-interface contract: pass`; retained binding
printed `CP32 winusb function-binding lifecycle checks passed`.

Expected negative `err:wineusb` clear-halt noise remains in lower focused
output and is unchanged.  The earlier reviewer Cannot-Verify provenance gaps
are also unchanged; this round does not broaden into provenance reconstruction.

### Final files and SHA-256

```text
f118747b7cce73967519d6192896fded8279c31b483e4be24d18ea6f55879f64  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c
0bc1e63b49f0ee839a5236adbbef7fbfd3cfd920e589d4706688dfa312798fc5  .io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c
6e77c16ca86b929058de191733636e68194fdb534be942d20d8b841c2fd08a26  tests/winusb_function_io_contract.c
89e109b56fc0aa55a3945c202fc2146b5d18a8cd4255f44d3f4a493cce987aec  tests/wineusb_winusb_urb_contract.c
d2e0d300209199307010edd44704586e741b987ce629dffd925771b85633fec6  tests/wineusb_winusb_urb_fake_libusb.c (unchanged)
c18c0df3ceb2838948d53dc9de3e6bb3914ce225f1361d26a2d6d1ea5eacb429  /tmp/io24-cp33-task7-mutant-generation-per-pipe/dlls/wineusb.sys/unixlib.c
9aa4bb3f4b847e7f66ad9a78eacc2d3ec762d6d41a1d3d966ef4d527d99666fe  /tmp/io24-cp33-task7-mutant-publish-before-commit/dlls/wineusb.sys/unixlib.c
23237fcd71cfe6a79976ab38102147dd55774923583cb9b2c5f81aaa23a807b7  /tmp/io24-cp33-task7-mutant-rollback-loses-old/dlls/wineusb.sys/unixlib.c
```

Frozen adjacent hashes remain
`87ffe326022144f45313bb734b487633bd7c0766f4c74eb7c60a56f4f04c2e5c`
for `wineusb.sys/wineusb.c` and
`1ab7456c87ca7f835120059bd780afbb2f3caca017491b1c92a7d36963f9f847`
for `tests/wineusb_winusb_busif_contract.c`.  Self-review found no edit outside
the four changed owned files and this append-only report.  No Wine process or
prefix, physical USB/sysfs/device path, build staging, driver load, live
interface claim, configuration/alternate change, or transfer was used.

### Exact pre-COMMIT mutant diff addendum

The complete mutation hunk abbreviated above is:

```diff
  transaction->token = allocate_claim_transaction_token();
  transaction->pipe_table = table;
+ {
+     struct wineusb_pipe_table *published = calloc(1, sizeof(*published));
+     if (!published)
+     {
+         free(transaction->pipe_table);
+         free(transaction);
+         req->Hdr.Status = USBD_STATUS_REQUEST_FAILED;
+         return STATUS_NO_MEMORY;
+     }
+     *published = *table;
+     free(params->device->pipe_table);
+     params->device->pipe_table = published;
+ }
  for (interface_number = 0; interface_number < 256; ++interface_number)
```

### Task-7 round-2 continuation: local reproduction (2026-08-24)

This continuation re-ran the required isolated rollback-preservation mutant and
the focused gates against the current workspace. The workspace was compared
directly with the supplied `task-7-round-2-base` tree because repository Git
metadata is intentionally unavailable in this checkout. Only the expected four
owned implementation/contract paths differ; the owned fake is identical.

The isolated source root was already present and its rollback branch discards
the committed table after releasing the pending transaction. It was not copied
into or applied to the workspace.

```text
tests/wineusb_winusb_urb_contract.sh /tmp/io24-cp33-task7-mutant-rollback-loses-old \
  .io24-build/winusb-function-binding-v1/build-a \
  .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --alternate
exit 1
FAIL group_target_only: device.pipe_table==committed
FAIL group_target_only: submit_request(&device,&pipe)==STATUS_SUCCESS
FAIL group_target_only: io24_fake_libusb_counts()->clear_halt==before+1
CP33 lower executed mode=--alternate completions=0 failures=3
```

Focused GREEN gates reproduced as follows:

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --alternate
exit 0
CP33 function executed mode=--alternate dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0 failures=0

tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source \
  .io24-build/winusb-function-binding-v1/build-a \
  .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --alternate
exit 0
CP33 lower executed mode=--alternate completions=0 failures=0

tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source
exit 0
WineUSB WinUSB metadata bus-interface contract: pass

tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --alternate
exit 0
CP33 public executed mode=--alternate target-mask=0x88c present-mask=0x99c missing-mask=0 fake-events=20 submits=4 releases=1 completions=0 failures=0

tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source \
  .io24-build/winusb-function-binding-v1/build-a \
  .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --claims
exit 0
CP33 lower executed mode=--claims completions=0 failures=0

tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
exit 1
LeakSanitizer has encountered a fatal error: LeakSanitizer does not work under ptrace

LSAN_OPTIONS=detect_leaks=0 tests/winusb_function_io_contract.sh \
  .io24-build/winusb-api-v1/dev-source --initialize
exit 0
CP33 function executed mode=--initialize dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0 failures=0
```

The lower modes emitted their established deliberate fake `Failed to clear
halt` diagnostic; their terminal contract failure counts above are zero. No
production correction was needed in this continuation.

Final SHA-256 values:

```text
f118747b7cce73967519d6192896fded8279c31b483e4be24d18ea6f55879f64  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c
0bc1e63b49f0ee839a5236adbbef7fbfd3cfd920e589d4706688dfa312798fc5  .io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c
6e77c16ca86b929058de191733636e68194fdb534be942d20d8b841c2fd08a26  tests/winusb_function_io_contract.c
89e109b56fc0aa55a3945c202fc2146b5d18a8cd4255f44d3f4a493cce987aec  tests/wineusb_winusb_urb_contract.c
d2e0d300209199307010edd44704586e741b987ce629dffd925771b85633fec6  tests/wineusb_winusb_urb_fake_libusb.c
23237fcd71cfe6a79976ab38102147dd55774923583cb9b2c5f81aaa23a807b7  /tmp/io24-cp33-task7-mutant-rollback-loses-old/dlls/wineusb.sys/unixlib.c
```
