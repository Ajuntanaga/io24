# CP33 Task 6 transactional function-claim report

Status: implementation complete within the R76/R77 offline host-only scope.
Commits: none (non-Git R1).

No Wine process, prefix, USB/sysfs path, runtime build/staging/selection, driver,
physical interface, or physical transfer was accessed. All execution was a
compiled host contract against fake WDM/libusb boundaries or the sealed CP32
lower artifact.

## TDD evidence

The lower and upper executable contracts were expanded before production code.
The production changes that made them pass were, respectively, transactional
function-child claim state/finalization in the real `unixlib.c`, and synchronous
post-select commit/rollback finalization in the real `session.c`.

### Required feature REDs

1. Exact lower command:

   ```text
   tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --claims
   ```

   Exit: `1`. The actual `unixlib.c` loaded and executed; the terminal summary
   was `CP33 lower executed mode=--claims completions=0 failures=29`. Failures
   were the absent claim journal, pending-token rules, finalization, busy
   mapping, rollback, and destruction-release behavior. This was a genuine
   feature RED, not compiler/harness exit 2.

2. Exact upper command:

   ```text
   tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
   ```

   Exit: `1`. The actual `session.c` compiled and executed and emitted the
   expected missing-finalization assertions: successful paths still had four
   lower calls rather than five, commit/rollback counters were zero, and the
   deterministic post-select rejection did not roll back. LeakSanitizer then
   also reported its current ptrace limitation. The contract assertions before
   that diagnostic establish a genuine feature RED; it was not exit 2.

R77's retained-fake `libusb_control_transfer` symbol repair is separately a
harness compatibility correction and is not counted as feature RED evidence.

## Implementation

- The shared private header declares reserved URB function `0x002f`, exact
  commit/rollback values `1`/`2`, and one fixed request containing the URB
  header, opaque transaction token, operation, and zero reserved field.
- A function child stores a 256-bit committed set and at most one pending
  transaction. A complete SELECT is validated before side effects, newly
  required interfaces are claimed in numeric ascending order, and partial
  failure releases this transaction's successful journal in reverse order.
- Successful SELECT returns a nonzero monotonic opaque token without committing
  the bitset. Finalization compares the registered pending token before use and
  never dereferences the caller token. Commit merges the journal; rollback
  reverses it; both destroy only that pending transaction. Stale, wrong,
  finalized, malformed, and second-pending operations are rejected.
- `LIBUSB_ERROR_BUSY` maps to `USBD_STATUS_REQUEST_FAILED` plus
  `STATUS_DEVICE_BUSY`. Repeated selection after commit creates an empty pending
  transaction and causes no duplicate libusb claim.
- Child destruction releases pending and committed interfaces exactly once
  before decrementing the parent/shared handle reference. No detach,
  auto-detach, or set-configuration call was introduced.
- The upper initialize path uses the SELECT `ConfigurationHandle` as the exact
  finalization token. Post-select state rejection synchronously rolls back
  before temporary state is freed or failure returns, leaving no file session,
  snapshot, interface array, output bytes, pending claim, committed claim, or
  selected state. Normal success sends commit exactly once before returning.
- R77 adds only a safe `LIBUSB_ERROR_NOT_SUPPORTED` synchronous-control result
  to the retained function-scope fake. The retained contract and wrapper remain
  unchanged.

## GREEN and regression gates

1. Lower claims, exact required command: exit `0`.

   ```text
   WineUSB pipe-observe fake-libusb behavior: pass
   CP33 lower executed mode=--claims completions=0 failures=0
   ```

2. Upper initialize, raw exact required command: exit `1`, with no contract
   assertion failure and only:

   ```text
   LeakSanitizer has encountered a fatal error.
   LeakSanitizer does not work under ptrace (strace, gdb, etc)
   ```

   The accepted Task-4 record used this same wrapper with
   `detect_leaks=1` and recorded exit 0; it did not use an `LSAN_OPTIONS`
   workaround. Thus this is classified as a current execution-environment
   limitation, not a GREEN claim for the raw command.

3. Upper initialize assertion run:

   ```text
   LSAN_OPTIONS=detect_leaks=0 tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
   ```

   Exit `0`:

   ```text
   CP32 winusb function-binding lifecycle checks passed
   CP33 function executed mode=--initialize dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0 failures=0
   ```

4. Retained function scope with the sealed CP32 lower artifact, exact required
   command: exit `0`, terminal line
   `WineUSB function-scope contract: pass`.

   Before R77, the unchanged retained wrapper/fake exited 1 at `dlopen` because
   the sealed artifact imported `libusb_control_transfer`. The same exit-1
   undefined-symbol result reproduced with a copied `task-6-base` header layout,
   proving it predated this head. After the authorized fake-only R77 symbol,
   existing configuration/IAD projection assertions execute and pass.

5. Metadata regression:

   ```text
   tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source
   ```

   Exit `0`: `WineUSB WinUSB metadata bus-interface contract: pass`.
   Metadata v1/v2 definitions and behavior remain intact; no v3 was added.

## Frozen wrapper/source hashes

```text
4076a1bda411fe2295f8f1afe2c6f54ee0a49bbf93632a95d03c316a2a0b0829  tests/wineusb_winusb_urb_contract.sh
76fecbd9533983d9b764dbda5bf3874ffd9b9e9a89dee6984f3c75e0cb3ae941  tests/winusb_function_io_contract.sh
8c2331d92d0dca513b3f0899e8a1a67b0f49e9ec4bd370bd64eae218e77e363e  tests/wineusb_function_scope_contract.sh
676eb98f8599aa31474750579e355a30fa866956998d6b1ffedaba15ed061253  tests/wineusb_function_scope_contract.c
```

These equal the controller-recorded frozen values.

## Owned-path inventory and current SHA-256

```text
5302e8bc082cade008c16f7bdb1969035fb559c59e6654f807e88285099eb599  .io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/winusb_busif.h
3d7cd11d19818a03afcd0e94089e66a4889c499bbb2a98485ef497562224c670  .io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/wineusb.c
23079216bd62ede0fa4aacc0e5d3e1722b66394cd7c5eba4d8dc9002d8a75248  .io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.h
9e5d0e745a0b4ea0aaffa2c1b0477a4de8af8b0fe120f73c4485f2293efb2708  .io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c
aa18767e417a7c9fc468e3da3053a6a26cd8fe91e3a9127e84e82b6e87d0a333  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c
4657b50592e88a2b6f71c8f4db1a746f82701a5d104c4c68f63a37bd6cc45711  tests/wineusb_winusb_urb_contract.c
c1cd66070b8e941af0318391a26c5074d333e3b4b889a21ebffa86ad62530ee5  tests/wineusb_winusb_urb_fake_libusb.c
72f1b4778e72e714738f14cf494c36067f38a18f6877c4d9110afa6d1e5cf514  tests/wineusb_pipe_observe_contract.c
dca7c91a845e1213732ecb6d939f22e0af1ae407059665f7880c50b856872efb  tests/winusb_function_io_contract.c
ce7a98d00e2a9dfda0dd65d9cf94a50681498cc5f06aded20ea9025b92333c2f  tests/wineusb_function_scope_fake_libusb.c
```

`unixlib.h` is owned but unchanged from `task-6-base`; the other nine owned
paths differ. All ten owned paths were self-reviewed against the updated base.
No path outside the R76/R77 ownership list was edited.

## Concern / non-claim

The exact sanitizer-enabled upper wrapper cannot be reported GREEN in this
current ptrace environment; its raw exit is 1 even though it emits no contract
failure. The separately identified assertion run is GREEN only with leak
detection disabled. No runtime Wine build, live hardware behavior, physical
claim compatibility, or system integration is claimed.
