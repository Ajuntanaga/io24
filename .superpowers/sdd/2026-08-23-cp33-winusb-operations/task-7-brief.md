# CP33 Task 7 alternate-selection implementation brief

Read this first. The approved design's function-claims/alternate/pipe-handle
section, plan Task 7, and ledger rulings R18, R52, R71, and R83-R85 apply. The
frozen base is `task-7-base`, taken only after Task 6 independently passed and
its thirteen-path checkpoint verified.

This task is hardware-free and offline. Never run Wine, access or create a
Wine prefix, inspect USB/sysfs, stage or select a build, load a driver, start
Universal Control or Voice FX, claim a physical interface, change a physical
alternate/configuration, or perform a live transfer. Do not edit CP32 or
`patch-check-source`.

## Exact ownership

Production (nine paths):

- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h`
- `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/wineusb.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb/main.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb/winusb_private.h`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb/Makefile.in`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb/io.c` (new)

Tests (eight paths; R92 supersedes R89's count):

- `tests/winusb_function_io_contract.c`
- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`
- `tests/wineusb_winusb_busif_contract.c`
- `tests/wineusb_pipe_observe_contract.c`
- `tests/wineusb_pipe_observe_fake_libusb.c`
- `tests/winusb_user_api_contract.c`
- `tests/winusb_user_api_contract.sh`

Do not edit any other source, fake, wrapper, ABI header, plan/spec/ledger,
evidence, snapshot, or checkpoint. The controller owns logs, review packages,
and seals. Use `apply_patch` for every manual edit. Other agents may be working
in the workspace; preserve their changes and never revert unrelated content.

R89/R92 permit the lower fix round to edit only
`wineusb.sys/{wineusb.c,unixlib.c}` and the five lower test paths named above.
The existing
`wineusb_winusb_busif_contract.sh` wrapper remains frozen. Preserve every
pre-existing metadata-interface v1/v2 assertion in its C contract.

## Test-first boundary

The controller already captured genuine sealed-Task-6 REDs:

```text
tests/winusb_function_io_contract.sh ... --alternate
exit 1: three executed failures (status, lower dispatch, generation)

tests/wineusb_winusb_urb_contract.sh ... --alternate
exit 1: actual lower SELECT_INTERFACE reaches STATUS_NOT_IMPLEMENTED,
three executed failures
```

Before any production edit, add the narrow public `--alternate` wrapper mode
and C cases, then run it against unchanged production and require feature exit
1, not harness exit 2. Cover default and R71 associated handles, exact
`interface_index = AssociatedInterfaceIndex + 1`, swapped associated indices,
unknown/stale handle, unknown alternate, immediate and pending helper success,
helper failure/error preservation, exact 32-byte request fields, one submit,
and balanced acquisition/release. Preserve every existing mode and assertion.

Expand the upper and lower C contracts before their corresponding production
edits. Required cases include unknown interface/alternate; target-interface
outstanding nonzero; function membership and committed-claim rejection; exact
MI05 alternate 1 metadata (`0x81`, `0x01`, bulk, 512); backend failure with no
state/generation/output mutation; successful second generation; stale prior
token; wrong slot/generation/endpoint/type/interface/alternate; capacity and
generation exhaustion before backend; and zero detach, auto-detach, or
set-configuration calls. Tests must execute the actual translation units and
existing fakes, never copied production logic or source-text scans.

The R89 lower repair must give the libusb fake an exact active MI05 descriptor
(alternates 0 and 1; alternate 1 endpoints `0x81` and `0x01`, bulk, 512 bytes)
and must execute the real `wineusb.c` dispatch through the retained bus-interface
contract. A pending child IRP must reject SELECT_INTERFACE before the Unix call
and leave output/tokens/state unchanged. The same lower matrix must prove exact
descriptor matching, unclaimed/function-scope rejection, target-only token
replacement, actual stale-token rejection, wrong slot/generation/record fields,
capacity and terminal generation exhaustion, configuration rollback preservation,
and destruction of staged and committed tables.

## Public DLL boundary

Create `io.c` and add it to the DLL Makefile. Move, do not duplicate, the
minimal acquired-handle structure and internal helper declarations needed by
`io.c` into the DLL private header. DLL `main.c` retains the private registry,
lookup, and token allocator; expose only the existing acquire/release,
fail-after-release, and synchronous-submit behavior. The alternate wrapper
must acquire the opaque handle once, retain the root through the synchronous
request, validate that the requested alternate belongs to the acquired exact
interface in the immutable snapshot, submit one
`IOCTL_WINE_WINUSB_SET_ALTERNATE`, and release on every path. Never cast an
opaque public token to an object or implement a second DeviceIoControl path.

## Upper function-driver boundary

Add only the alternate IOCTL to the accepted dispatch set and keep the
per-file session mutex across it. Validate the exact private layout/version,
session, zero reserved fields, zero output length/MDL, interface index,
alternate descriptor, current file/device state, and the R91 conservative
file-wide outstanding rule. Do not use an unconnected per-interface counter;
R89 separately proves the lower child-wide pending-IRP rejection. Preallocate a
complete temporary pipe/state replacement, build an exactly sized
`URB_FUNCTION_SELECT_INTERFACE`, and acquire the device finalization mutex
across final state validation, lower submission, and commit. On success copy
the returned generation handles and atomically replace only the target
interface state. On any failure preserve the prior alternate, pipe map,
generation, policy placeholder state, and caller output.

Initialization must retain generation-tagged handles returned by the committed
default SELECT_CONFIGURATION. Release, cleanup, close, and removal must free
the exact current state once. Do not add transfer or policy behavior owned by
Tasks 8-13.

Until Tasks 9-12 create actual transfer ownership records, alternate selection
must run only when its dispatch is the file's sole outstanding request. Those
later tasks must refine this conservative rule into real per-interface
increment/decrement accounting; Task 7 does not claim target-specific pending
I/O behavior from a field that production never updates.

## Lower boundary and portable tokens

Use the R84 256-slot table on each `unix_device`; never use the old two-byte
packed union handle. Tokens are nonzero 32-bit integer values carried through
`HANDLE`, with a 9-bit one-based slot and 23-bit nonzero generation. Validate
the table record's full generation, endpoint, pipe type, actual interface,
alternate, current flag, function membership, committed claim, and active
descriptor before any clear-halt/transfer/backend action.

SELECT_CONFIGURATION stages a complete token/current-alternate map inside its
claim transaction and publishes it only on COMMIT. ROLLBACK and destruction
discard staged state. SELECT_INTERFACE validates exact sizes, one interface,
descriptor endpoints, scope/claim, available slots/generation, and no pending
child IRP before calling `libusb_set_interface_alt_setting` exactly once. Only
backend success publishes new target-interface records and returned handles;
other interfaces remain current. Any validation/backend failure leaves all
tables, generations, alternates, and returned pipe fields unchanged.

R87 migrates the retained pipe-observe source to the new token contract. It
must obtain each exercised handle from the actual SELECT_CONFIGURATION or
SELECT_INTERFACE path on the same fake child, then pass that returned handle
to clear-halt/transfer. It may no longer fabricate or decode the legacy packed
endpoint/type value. Preserve its backend route, return-value, allocation, and
terminal pass assertions; do not add a production legacy-compatibility path.
R92 permits only a disabled-by-default exact MI05 descriptor control in its
separate fake so token lookup can be descriptor-validated without weakening
the retained default behavior or editing its wrapper.

## Required gates and report

Run and report exact exits for:

```bash
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --alternate
tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source \
  .io24-build/winusb-function-binding-v1/build-a \
  .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --alternate
tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --alternate
tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source \
  .io24-build/winusb-function-binding-v1/build-a \
  .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --claims
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
```

If raw LeakSanitizer again refuses ptrace, also run initialize with
`LSAN_OPTIONS=detect_leaks=0`, report both honestly, and retain explicit
allocation balances. Write `.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-7-report.md`
with test-first evidence, exact changed paths/hashes, caveats, and no live
claim. Do not create the controller's head snapshot, diff, review, ledger
entry, focused GREEN logs, checkpoint, or seal.
