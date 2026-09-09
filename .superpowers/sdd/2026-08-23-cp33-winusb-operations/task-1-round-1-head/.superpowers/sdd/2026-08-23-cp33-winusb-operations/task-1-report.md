# CP33 Task 1 report: executed hardware-free RED boundary

## Status and review history

Correction round 1 is complete. The initial round-0 package is preserved
unchanged under `reviews/`. Round 0 correctly failed because production objects
were compiled but unused, host fakes were incomplete, focused modes were
ignored, the vendor sequence was static-only, and raw tool failures could
collide with feature exit 1. Round 1 replaces those source-only boundaries with
executed production harnesses and addresses every blocking finding below.

No production source was edited. No Wine process/prefix, USB device/node,
sysfs USB path, driver, selector, Universal Control, Voice FX, or CP24 action
was used. All work remained offline and hardware-free.

## Files in Task 1 ownership

The two fresh roots remain:

- `.io24-build/winusb-api-v1/dev-source/`
- `.io24-build/winusb-api-v1/patch-check-source/`

The ten corrected contract/fake files are:

- `tests/winusb_user_api_contract.c`
- `tests/winusb_user_api_contract.sh`
- `tests/winusb_function_io_contract.c`
- `tests/winusb_function_io_contract.sh`
- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_contract.sh`
- `tests/wineusb_winusb_urb_fake_libusb.c`
- `tests/winusb_overlapped_cancel_contract.c`
- `tests/winusb_overlapped_cancel_contract.sh`
- `tests/io24_winusb_vendor_profile_contract.py`

The four Task 1 evidence files are:

- `re/winusb-api-v1/logs/cp32-seal-verify.log`
- `re/winusb-api-v1/logs/dspusbdevice-winusb-callsite.log`
- `re/winusb-api-v1/logs/cp33-red.log`
- `re/winusb-api-v1/logs/task-01-red.sha256`

`re/winusb-api-v1/checkpoints/` and this report are the only other Task 1
paths created. No review, ledger, plan, spec, handoff, retained test, or other
evidence file was edited.

## Immutable baseline and vendor evidence

The pre-creation CP32 verification remains valid: exactly 72 checksum lines,
all 72 ending in `OK`, with no failure. The CP33 root nonexistence guard passed
before initial creation.

The static vendor evidence remains:

- SHA-256 `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`;
- exactly the expected fourteen imports;
- policy-get disassembly at `0x180084d50`;
- initializer disassembly at `0x180095e20`;
- the exact nine policy pairs grouped as `all`, `out`, `in`, and `get`.

## Executed production harnesses

### Public DLL

The wrapper builds the actual `dlls/winusb/main.c` (and optional future
`io.c`) as a loadable host module, builds the contract executable with an
exported controllable fake Win32 boundary, then uses `dlopen`/typed `dlsym`
calls. The fake records IOCTL codes, input/output lengths, overlapped identity,
allocation/free, duplicate/close, submission, release, and completion state.

CP32 exposes only actual `WinUsb_Free`; focused handle and vendor modes invoke
that production export and detect its missing ownership/release behavior.
Absent exports are optional lookups and therefore feature RED, not link
failure. The `--vendor` mode attempts the exact synthetic sequence in order:
initialize; speed query; configuration and string descriptors; maximum-policy
get; the exact eight policy-set pairs; alternate 1; synchronous/overlapped
control, read, and write; overlapped result; abort; reset; associated handle;
associated-first then root free. A 26-entry typed trace asserts the operation
order, exact descriptor/policy/setup/pipe/length/overlapped arguments, every
result, and the two-handle free order. Guard bytes surround all transfer outputs.

Focused modes: `--initialize`, `--handles`, `--descriptors`, `--policy`,
`--transfer`, `--cancel`, and `--vendor`; `--red` aggregates the six public
behavior groups plus the vendor-sequence group. All eight freshly returned
exactly 1 against CP32.

### Generic function driver

The contract reuses the retained fake-WDM lifecycle boundary without modifying
it and includes the actual CP33-clone `dlls/winusb.sys/main.c`. It first runs
the retained CP32 lifecycle baseline, invokes actual `DriverEntry`, AddDevice,
start/remove PnP, create, and device-control dispatch functions, and delivers
guarded CP33 requests through `IRP.AssociatedIrp.SystemBuffer`.

The delivered MI05 descriptor has alternate 0 with zero endpoints and
alternate 1 with bulk `0x81` and `0x01`, each maximum packet size 512.
Focused modes `--lifecycle`, `--session`, `--alternate`, `--policy`, and
`--transfer` exercise different actual dispatch/IOCTL paths; `--red` aggregates
them. All six freshly returned exactly 1 because CP32 rejects create and every
CP33 IOCTL and has no cleanup/transfer forwarding path.

### Lower Unix backend

The wrapper compiles actual `dlls/wineusb.sys/unixlib.c`, links it only with
the assigned fake libusb and sealed CP32 `dlls/ntdll/ntdll.so`, loads the new
module, resolves `__wine_unix_call_funcs`, runs the retained pipe-observe
behavior baseline, and invokes real Unix call-table operations.

The fake is externally resettable/queryable, records exact interface,
alternate, configuration, endpoint/type/length, and control setup fields,
supports injected submit/claim/alternate/control/clear-halt failures, and
provides controlled natural/cancel completion. It exposes and the contract
asserts claim, release, detach, auto-detach, set-configuration, set-alternate,
control, bulk, interrupt, cancel, clear-halt, transfer-free, and close counts.
Forbidden detach, auto-detach, and set-configuration counts must remain zero.

Focused modes `--claims`, `--alternate`, `--control-descriptor`,
`--sync-pipes`, and `--transfer-lifetime` execute distinct call-table paths;
`--red` aggregates them. All six freshly returned exactly 1. CP32 lacks
function claims/alternate selection/function-scoped generic control, returns
success after reset backend failure, and leaves transfer ownership uncleared.

### Cancellation, abort, and removal

The cancellation wrapper also compiles/loads the actual Unix module. Its host
contract directly includes actual `dlls/wineusb.sys/wineusb.c` with a fake WDM
and fake Unix dispatcher. The dispatcher routes abort cancellation into the
loaded actual `unix_usb_cancel_transfer`, so fake-libusb cancel accounting is
produced by the real lower path. The contract directly invokes actual
`usb_submit_urb`, `driver_internal_ioctl`, and `pdo_pnp` paths.

Focused `--lower` observes actual all-pipe abort (two cancels for a requested
single pipe), `--upper` observes pending submission without a cancel routine,
and `--teardown` observes completion before any physical cancellation.
`--red` aggregates the three. All four freshly returned exactly 1.

### Exact vendor analyzer

Python retains the hash/import/disassembly checks and invokes the public
contract's executable `--vendor` sequence. On CP32 the executable sequence
returns 1, while all static evidence passes. Python reports static definitions
as supplemental evidence (1/14 including stub `Free`) and does not confuse that
with callable behavior; the synthetic behavioral profile is RED.

All `objdump` and subprocess exceptions are caught and diagnosed `HARNESS:`
with exit 2.

## Fresh RED, mode, usage, and harness evidence

The complete retained output is `re/winusb-api-v1/logs/cp33-red.log`.

Aggregate results against untouched CP32:

- public: exit 1;
- function: exit 1;
- lower: exit 1;
- cancel: exit 1;
- vendor: exit 1.

The same log records 24/24 focused-mode executions at exit 1 with distinct
named diagnostics: public 8, function 6, lower 6, cancel 4.

Usage with missing arguments returned 2 for all five families. Invalid-mode
probes returned 2 for all four shell wrappers. Missing public/lower inputs and
an intentionally unavailable `objdump` returned 2 with `HARNESS:` diagnostics.
In total the retained log contains 12/12 exit-2 usage/harness probes.

Every shell compiler/linker command is guarded; a failure prints `HARNESS:`
and exits 2. Runtime loader/symbol failures are also `HARNESS:` exit 2. A child
crash or unexpected status is remapped to `HARNESS:` exit 2. Exit 1 is reserved
for successfully executed observable CP33 contract failures.

The accepted round-1 run contained no compiler/linker failure, missing input,
crash, syntax error, retained-baseline failure, or unrelated failure.

## Source equality and checkpoint

Both final commands produced no output and exited 0:

- `diff -qr --no-dereference .io24-build/winusb-function-binding-v1/patch-check-source .io24-build/winusb-api-v1/dev-source`
- `diff -qr --no-dereference .io24-build/winusb-function-binding-v1/patch-check-source .io24-build/winusb-api-v1/patch-check-source`

Thus both CP33 production clones remain byte-for-byte equal to CP32.

Checkpoint: `re/winusb-api-v1/logs/task-01-red.sha256`.

It contains 11 entries (ten Task 1 contract/fake files plus `cp33-red.log`).
`sha256sum --check` from the project root returned exit 0 and all 11 entries
were `OK`.

## Explicit round-0 finding self-review

1. **Unused production objects:** corrected. Public loads actual `main.c`;
   function invokes actual driver entry/dispatch; lower loads/invokes actual
   Unix calls; cancel invokes actual kernel and loaded lower cancel paths.
2. **Missing/inert fakes:** corrected. Win32, WDM/lower, and libusb state is
   controllable and asserted; MI05 and guard regions cross production calls;
   fake libusb records required/forbidden operations and completion races.
3. **No synthetic vendor sequence:** corrected with the typed public
   `--vendor` operation order, invoked by the Python analyzer.
4. **Ignored modes:** corrected. Each advertised mode has a distinct named
   executed behavior group; all 24 focused modes were independently run.
5. **Exit-code collision:** corrected. Usage/input/compiler/linker/loader/tool,
   subprocess, and unexpected runtime status paths return 2 with `HARNESS:`;
   fresh probes verify the separation.

## Concerns

No Task 1 correction blocker remains. This evidence establishes a complete
offline executable RED boundary; it does not claim CP33 GREEN, build
reproducibility, Wine runtime compatibility, or physical USB compatibility.
