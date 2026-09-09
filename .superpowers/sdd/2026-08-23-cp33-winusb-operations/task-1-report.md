# CP33 Task 1 report: executed hardware-free RED boundary

## Status and review history

Correction round 3 is complete. The round-0, round-1, and round-2 review
packages are preserved unchanged under `reviews/`. Round 0 correctly failed
because production objects
were compiled but unused, host fakes were incomplete, focused modes were
ignored, the vendor sequence was static-only, and raw tool failures could
collide with feature exit 1. Rounds 1 through 3 replace those source-only
boundaries with executed production harnesses and address every blocking
finding below.

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
calls. The fake records IOCTL codes, exact input/output lengths, overlapped
identity, allocation/free, duplicate/close, submission, release, and completion
state. Independent test-side fixed-width wire structures and constants define
the planned private ABI without depending on future production headers. Each
captured event is parsed by exact request type and validates named fields and
offsets: ABI size/version, descriptor type/index/language, policy ID/value
length/value, pipe ID, setup bytes, transfer length, direction/method,
returned bytes/value, and output mutation. Arbitrary byte scanning is absent.

CP32 exposes only actual `WinUsb_Free`. Each focused mode resolves its own
target export set from the loaded production module and reports distinct
target, present, and missing masks before initialization. Where applicable it
also executes the safely invalid real `WinUsb_Free(NULL)` negative path.
Absent exports are optional lookups and therefore feature RED, not link
failure; no fabricated private handle is ever passed. The `--vendor` mode
attempts the exact synthetic sequence in order:
initialize; speed query; configuration and string descriptors; maximum-policy
get; the exact eight policy-set pairs; alternate 1; synchronous/overlapped
control, read, and write; overlapped result; abort; reset; associated handle;
associated-first then root free. The fake Win32 boundary records IOCTL,
allocation, free, close, and overlapped-result events and asserts exact IOCTL
order, descriptor/policy/setup/pipe/length/overlapped arguments, results, and
associated-before-root free order. Every handle-dependent group first obtains
its handle from actual `WinUsb_Initialize` and safely stops with feature RED
when CP32 lacks it. Guard bytes surround all transfer outputs.

Focused modes: `--initialize`, `--handles`, `--descriptors`, `--policy`,
`--transfer`, `--cancel`, and `--vendor`; `--red` aggregates the six public
behavior groups plus the vendor-sequence group. All eight freshly returned
exactly 1 against CP32 with operation-specific missing masks.

### Generic function driver

The contract reuses the retained fake-WDM lifecycle boundary without modifying
it and includes the actual CP33-clone `dlls/winusb.sys/main.c`. It first runs
the retained CP32 lifecycle baseline, invokes actual `DriverEntry`, AddDevice,
start/remove PnP, create, and device-control dispatch functions, and delivers
guarded CP33 requests through `IRP.AssociatedIrp.SystemBuffer`.

The guarded request delivered through actual dispatch contains MI05 alternate 0 with zero endpoints and
alternate 1 with bulk `0x81` and `0x01`, each maximum packet size 512.
Baselines captured immediately before each dispatch assert exact lower-call
and completion deltas plus required session/generation/output mutation; no
post-call assertion relies on setup-time calls or prefilled endpoint bytes.
Focused modes `--lifecycle`, `--session`, `--alternate`, `--policy`, and
`--transfer` exercise different actual dispatch/IOCTL paths; `--red` aggregates
them. After the expected create/initialize prerequisite rejection, each
dependent focused group still dispatches its own actual operation IOCTL using
a real zeroed `FILE_OBJECT` with safely null per-file state. It asserts the
exact rejection status, dispatch/completion delta, zero output mutation, and
zero lower-stack delta; it never fabricates a file context. All six freshly
returned exactly 1 because CP32 rejects create and every CP33 IOCTL and has no
cleanup/transfer forwarding path.

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
Control setup bytes are subtracted only for control completions; an executed
bulk completion asserts all 32 payload bytes and `actual_length` agree.

Focused modes `--claims`, `--alternate`, `--control-descriptor`,
`--sync-pipes`, and `--transfer-lifetime` execute distinct call-table paths;
`--red` aggregates them. All six freshly returned exactly 1. CP32 lacks
function claims/alternate selection/function-scoped generic control, returns
success after reset backend failure, and leaves transfer ownership uncleared.

### Cancellation, abort, and removal

The cancellation wrapper also compiles/loads the actual Unix module. Its host
contract directly includes actual `dlls/wineusb.sys/wineusb.c` with a fake WDM
and fake Unix dispatcher. The dispatcher snapshots the fake-libusb cancel
counter, routes abort cancellation into loaded actual
`unix_usb_cancel_transfer`, and asserts its exact post-call delta. The contract directly invokes actual
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

All required/optional source stat/read, DLL read, `objdump`, and subprocess
exceptions are caught and diagnosed `HARNESS:` with exit 2.

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
An unreadable optional-source probe deterministically covers caught source-read
failure. In total the retained log contains 13/13 exit-2 usage/harness probes.

Every shell compiler/linker command is guarded; a failure prints `HARNESS:`
and exits 2. Runtime loader/symbol failures are also `HARNESS:` exit 2. A child
crash or unexpected status is remapped to `HARNESS:` exit 2. Exit 1 is reserved
for successfully executed observable CP33 contract failures.

The accepted round-3 aggregate/mode run contained no compiler/linker failure, missing input,
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
3. **No synthetic vendor sequence:** corrected with the fake-boundary-observed
   `--vendor` operation order, invoked by the Python analyzer.
4. **Ignored modes:** corrected. Each advertised mode has a distinct named
   executed behavior group; all 24 focused modes were independently run.
5. **Exit-code collision:** corrected. Usage/input/compiler/linker/loader/tool,
   subprocess, and unexpected runtime status paths return 2 with `HARNESS:`;
   fresh probes verify the separation.

## Round 2 correction evidence and self-review

The amended covering commands against untouched CP32 produced these exact
statuses and final diagnostics:

- `winusb_user_api_contract.sh ... --handles`: exit 1, `fake-events=0 ... failures=1`;
- `winusb_user_api_contract.sh ... --vendor`: exit 1, `fake-events=0 ... failures=1`;
- `winusb_function_io_contract.sh ... --session`: exit 1, `dispatches=1 ... failures=4`;
- `winusb_function_io_contract.sh ... --alternate`: exit 1, `dispatches=1 ... failures=4`;
- `winusb_function_io_contract.sh ... --transfer`: exit 1, `dispatches=1 ... failures=4`;
- `wineusb_winusb_urb_contract.sh ... --transfer-lifetime`: exit 1, `completions=2 failures=1`;
- `winusb_overlapped_cancel_contract.sh ... --lower`: exit 1, `cancels=2 ... failures=3`;
- `winusb_overlapped_cancel_contract.sh ... --teardown`: exit 1, `cancels=0 completions=2 failures=3`;
- vendor analyzer with an unreadable optional `io.c`: exit 2 with
  `HARNESS: vendor static/executable tool failure: ... Permission denied`.

Round-1 finding self-review:

1. **Substantive fake effects:** fixed. Function and cancel baselines are taken
   immediately before real calls and exact deltas/output ownership are checked;
   MI05 crosses guarded dispatch; lower forbidden counters remain exact zero.
2. **Caller-authored vendor trace:** removed. Observed events are emitted only
   by fake Win32 boundary functions and checked for exact semantic translation.
3. **Uncaught Python reads/stats:** fixed and covered by deterministic exit-2
   unreadable-source evidence.
4. **Fabricated public private handles:** removed. The literal `0x2200` is gone;
   every dependent group uses only a handle returned by production initialize.
5. **Non-control setup subtraction:** fixed. Bulk capacity is the full transfer
   length and the natural 32-byte completion proves copy/actual-length agreement.

Previously addressed findings remain intact: all four C families execute real
production paths and all 24 advertised focused modes remain distinct.

## Round 3 correction evidence and self-review

The public executable now validates exact typed fake-boundary events. Its wire
definitions are independent of production, fixed-width, size-asserted, and
selected solely from the exact IOCTL and input/output lengths. The boundary
captures typed metadata, output bytes before and after the call, returned-byte
count, and exact `OVERLAPPED` identity. Semantic validation compares named
fields and exact offsets; the former arbitrary integer search was removed.

Fresh focused public commands against untouched CP32 all returned 1 and
reported these actual loaded-module masks:

- `--initialize`: target `0x80`, present `0x4`, missing `0x80`;
- `--handles`: target `0x8c`, present `0x4`, missing `0x88`;
- `--descriptors`: target `0x190`, present `0x4`, missing `0x190`;
- `--policy`: target `0x18c0`, present `0x4`, missing `0x18c0`;
- `--transfer`: target `0x22a2`, present `0x4`, missing `0x22a2`;
- `--cancel`: target `0x481`, present `0x4`, missing `0x481`;
- `--vendor` and aggregate `--red`: target `0x3fff`, present `0x4`, missing `0x3ffb`.

Fresh focused function commands all returned 1 after executing actual CP32
dispatch. `--session` recorded IOCTL `0x222002`, `--alternate` recorded
`0x22200c`, `--policy` recorded `0x222014`, and `--transfer` recorded
`0x222022`; each returned `STATUS_NOT_SUPPORTED` (`0xc00000bb`). Lifecycle
separately executed the real entry/AddDevice/PnP/create path with no CP33 mode
IOCTL. Later GREEN execution retains the full create, initialize, then
operation sequence and uses only a production-created file context.

The complete retained round-3 matrix is 5/5 aggregate feature REDs at exit 1,
24/24 focused modes at exit 1, and 13/13 usage/harness probes at exit 2. The
Python unreadable-optional-source probe deterministically returned 2 with a
`HARNESS:` permission diagnostic. No compiler, linker, loader, tool, syntax,
crash, retained-test, or unrelated failure was admitted as feature RED.

Round-2 finding self-review:

1. **Arbitrary public byte scanning:** removed. Exact IOCTL/length dispatch and
   independent named-member validation now prove the planned wire semantics,
   including output/result bytes and free/close ordering.
2. **Collapsed focused RED surface:** removed. Public groups resolve and report
   their own target/missing export masks from the actual module; dependent
   function groups issue distinct actual IOCTL rejections with safely null
   per-file state. The focused log demonstrates different masks, codes, and
   statuses rather than only different mode labels.

Round-2 protections remain intact: fake-boundary-authored vendor events,
initialization-returned handles, baseline/delta accounting, guarded MI05 data,
control-only setup subtraction, caught Python/tool failures, real production
execution, and harness/feature exit separation.

## Round 4 response-propagation correction

The exact typed descriptor IOCTL now returns the independently chosen eight
bytes `08 03 52 00 34 00 21 00` through its real direct-output buffer and sets
the DeviceIoControl byte count to 8. The exact typed get-policy IOCTL returns
the independent value `0x13579bdf`, value length 4, and a 48-byte fixed-width
response through its real buffered output and byte-count channel. Boundary
request/response validation remains separate from the public caller checks.

Both focused and vendor callers fill descriptor buffers and their outer/tail
guards with `0xa5`, initialize every pure returned-length slot to
`0xd15c0ded`, and assert the exact cached-device and boundary string bytes plus
lengths 18 and 8 immediately after the real dlsym-resolved calls. Policy
callers guard the four-byte value, initialize it to `0x6a5bc4d3`, pass the
required valid four-byte in/out capacity, and then assert caller-visible value
`0x13579bdf` and value length 4. A wrapper that submits the correct typed IOCTL
but discards or misroutes the returned response therefore fails independently
of the fake-boundary request assertions.

The same audit added exact caller checks for cached speed byte 3 and returned
length 1; synchronous/overlapped control lengths 5/7; read lengths 11/13 plus
exact guarded read bytes; write lengths 17/19 with unchanged outbound data;
and delegated overlapped-result length 23. Each pure output length is reset to
`0xd15c0ded` immediately before its production call. Boundary events separately
assert the corresponding returned-byte values and exact caller OVERLAPPED.

Fresh public `--descriptors`, `--policy`, `--vendor`, and `--red` runs each
returned feature RED 1 on untouched CP32 with missing masks `0x190`, `0x18c0`,
`0x3ffb`, and `0x3ffb`; initialization remains a genuine prerequisite and no
private handle was fabricated. The complete round-4 matrix retained in
`cp33-red.log` is 5/5 aggregate REDs at 1, 24/24 modes at 1, and 13/13
usage/harness probes at 2. The CP32 seal is 72/72 OK, both clone diffs are
empty, and the refreshed 11-entry checkpoint verifies 11/11 OK.

## Concerns

No Task 1 correction blocker remains. This evidence establishes a complete
offline executable RED boundary; it does not claim CP33 GREEN, build
reproducibility, Wine runtime compatibility, or physical USB compatibility.

## Round 5 `GetPipePolicy` returned-length correction

The focused public `--policy` caller now supplies independently guarded
eight-byte value storage and a valid input `ValueLength` capacity of 8. All
eight storage bytes begin at sentinel `0x6d`; the surrounding 32-bit guards
begin at `0xa5a5a5a5`. The existing fake Win32 boundary continues to author an
exact four-byte policy response with value `0x13579bdf` and response
`value_length` 4 through the typed 48-byte IOCTL response. It does not receive
or mutate the public caller's `ValueLength` pointer.

Immediately after the real dlsym-resolved `WinUsb_GetPipePolicy` call, the
focused caller asserts the first four bytes as the independent expected value,
returned `ValueLength == 4`, bytes 4 through 7 still equal `0x6d`, and both
outer guards remain intact. If a production wrapper copies the policy value but
omits the returned-length assignment, `ValueLength` remains 8 and this contract
fails. The boundary independently asserts a typed request capacity of 8 and a
typed response actual length of 4, including exact pipe, policy, header,
response-value, response-size, and returned-byte fields.

The frozen vendor path is unchanged: its real policy-8 call still supplies an
exact four-byte input capacity, and its typed trace still requires request
`value_length == 4`. Thus the focused case proves the shared wrapper's 8-to-4
output-length propagation without changing vendor evidence.

Fresh `-std=c11 -Wall -Wextra -Werror` public builds completed cleanly.
Focused public `--policy`, `--vendor`, and `--red` each returned the intended
feature RED exit 1; `--policy` reported target mask `0x18c0`, present mask
`0x4`, and missing mask `0x18c0`. The regenerated round-5 evidence contains
5/5 aggregate feature REDs at exit 1, 24/24 focused modes at exit 1, and 13/13
usage/harness probes at exit 2. The CP32 seal verifies 72/72 entries, both
production-clone diffs are empty, and the refreshed Task 1 checkpoint verifies
11/11 entries.

No production source, clone, plan, specification, ledger, review snapshot,
handoff, or retained test was edited. No Wine process or prefix, USB/sysfs
path, physical operation, application, or CP24 action was used. CP32 still
lacks the CP33 public exports, so this is intentionally executable feature RED
evidence and does not claim CP33 GREEN or runtime/device validation.
