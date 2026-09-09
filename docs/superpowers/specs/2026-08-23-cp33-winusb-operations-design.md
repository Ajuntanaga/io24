# CP33 Exact WinUSB API, Function I/O, and Cancellation

Date: 2026-08-23  
Status: Approved for implementation planning  
Implementation state: Not started; CP32 remains the sealed baseline

## Purpose

CP33 completes the third offline host layer identified at CP30 by implementing
the exact fourteen `WinUsb_*` operations imported by the installed vendor
module. It connects Wine's user-mode `winusb.dll` to the generic `winusb.sys`
function driver added at CP32, and connects that function driver to the
function-scoped WineUSB PDO through validated URBs.

This is an offline interoperability implementation for the pinned Wine 11.15
source. It includes the code paths that will eventually claim an otherwise
unclaimed function interface, select alternate settings, and submit transfers,
but CP33 does not stage or load those paths and does not exercise them against
the physical io24.

Passing CP33 means the exact vendor-observed WinUSB surface is implemented and
reproducible under hardware-free tests. It does not mean that Universal Control
synchronizes, that the physical device accepts a request, or that a live run is
authorized.

## Evidence baseline

CP33 begins only from the sealed CP32 patch-check source. The CP32 production
patch is:

```
7df4011ea20fa36bf80f4bc0ba409c9dca812b7d76b00f19f1709774eebf75bb
re/wine-11.15-winusb-function-binding-v1.patch
```

The complete CP32 checksum seal and report are:

```
re/winusb-function-binding-v1/checkpoints/CP32_SHA256SUMS
re/winusb-function-binding-v1/checkpoints/CP32_WINUSB_FUNCTION_BINDING.md
```

Before a CP33 RED is accepted, every CP32 seal entry must reverify from the
CP32 artifact root. No prior live authorization is reusable; CP24 remains
consumed.

### Observed local source boundary

The pinned CP32 source establishes these facts:

- `dlls/winusb/main.c` implements only a permissive `WinUsb_Free` semantic
  stub; the other required exports remain specification stubs.
- `include/winusb.h` defines only the opaque handle and the `WinUsb_Free`
  prototype.
- `dlls/winusb.sys/main.c` implements PnP binding and device-interface
  lifecycle, but rejects create, read, write, device-control, and internal
  device-control requests.
- The WineUSB PDO accepts `IOCTL_INTERNAL_USB_SUBMIT_URB` for existing
  descriptor, configuration, bulk/interrupt, reset, vendor-control, and one
  retained class-interface path.
- `URB_FUNCTION_SELECT_INTERFACE` is logged and rejected with
  `STATUS_NOT_IMPLEMENTED`.
- `URB_FUNCTION_ABORT_PIPE` currently requests cancellation of every queued
  transfer on the PDO rather than only the selected pipe.
- pending WineUSB IRPs do not install a cancel routine, so `CancelIo` and
  `CancelIoEx` cannot reach the libusb transfer.
- asynchronous libusb completion records a USBD status, but the kernel event
  path currently completes the IRP with `STATUS_SUCCESS` regardless of that
  status.
- surprise removal completes queued IRPs without first establishing ownership
  of the still-live libusb transfers, creating a double-completion/lifetime
  hazard once real WinUSB asynchronous I/O is exposed.
- reset logs a `libusb_clear_halt` failure but still returns success.
- the lower Unix device is opened but no function interface is claimed, and no
  alternate setting is selected through libusb.

These are implementation observations, not claims about Windows internals.

### Exact vendor import and policy evidence

The installed module used for the CP30 import boundary is:

```
/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll
SHA-256 567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b
```

Its PE import table contains exactly these fourteen WinUSB operations:

```
WinUsb_AbortPipe
WinUsb_ControlTransfer
WinUsb_Free
WinUsb_GetAssociatedInterface
WinUsb_GetDescriptor
WinUsb_GetOverlappedResult
WinUsb_GetPipePolicy
WinUsb_Initialize
WinUsb_QueryDeviceInformation
WinUsb_ReadPipe
WinUsb_ResetPipe
WinUsb_SetCurrentAlternateSetting
WinUsb_SetPipePolicy
WinUsb_WritePipe
```

Read-only disassembly of the policy initializer at image address
`0x180095e20` narrows the required policy profile. For every pipe it sets
`PIPE_TRANSFER_TIMEOUT` to zero and `RESET_PIPE_ON_RESUME` to false. For OUT
pipes it sets `SHORT_PACKET_TERMINATE` to false. For IN pipes it sets
`AUTO_CLEAR_STALL`, `IGNORE_SHORT_PACKETS`, `ALLOW_PARTIAL_READS`, and
`AUTO_FLUSH` to false, then enables `RAW_IO`. The call at `0x180084d50`
retrieves `MAXIMUM_TRANSFER_SIZE` into a four-byte value.

That evidence defines CP33's policy-compatibility claim. Policy values outside
the observed profile must be implemented genuinely or rejected; they may not
return success while having no effect.

### Device topology relevant to CP33

The retained configuration fixture projects MI05 as one vendor interface:

- interface 5, alternate 0: zero endpoints;
- interface 5, alternate 1: bulk IN endpoint `0x81`, bulk OUT endpoint `0x01`;
- both endpoints have maximum packet size 512.

Initialization therefore cannot manufacture pipes from alternate 1. It must
start with alternate 0 and no data pipes. `WinUsb_SetCurrentAlternateSetting`
must make alternate 1's two pipes current before vendor bulk I/O can succeed.

### Documentation-backed constraints

The design uses the documented WinUSB contract as its semantic reference:

- `WinUsb_Initialize` requires a device handle opened for overlapped I/O,
  retrieves and caches descriptors, returns the default interface, and resets
  interface policies to defaults:
  <https://learn.microsoft.com/en-us/windows/win32/api/winusb/nf-winusb-winusb_initialize>
- associated-interface handles are zero-based after the default interface,
  may be retrieved only once, and must be freed:
  <https://learn.microsoft.com/en-us/windows/win32/api/winusb/nf-winusb-winusb_getassociatedinterface>
- `WinUsb_GetOverlappedResult` extracts the underlying device handle and uses
  normal `GetOverlappedResult` behavior:
  <https://learn.microsoft.com/en-us/windows/win32/api/winusb/nf-winusb-winusb_getoverlappedresult>
- a control transfer uses an eight-byte setup packet, is capped at 4 KiB, and
  uses both the interface handle and setup recipient fields:
  <https://learn.microsoft.com/en-us/windows/win32/api/winusb/nf-winusb-winusb_controltransfer>
- pipe policies, endpoint applicability, defaults, and `RAW_IO` restrictions
  are defined here:
  <https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/winusb-functions-for-pipe-policy-modification>
- `WinUsb_AbortPipe` aborts every pending transfer for one pipe, while
  `WinUsb_ResetPipe` resets the data toggle and clears stall:
  <https://learn.microsoft.com/en-us/windows/win32/api/winusb/nf-winusb-winusb_abortpipe>
  and
  <https://learn.microsoft.com/en-us/windows/win32/api/winusb/nf-winusb-winusb_resetpipe>
- changing the alternate setting is synchronous and is rejected while the
  target interface has outstanding I/O:
  <https://learn.microsoft.com/en-us/windows/win32/api/winusb/nf-winusb-winusb_setcurrentalternatesetting>

The exact private ABI and ownership model below are Wine design decisions
derived from those constraints and the pinned source. They are not assertions
about Microsoft's undocumented `winusb.dll` to `winusb.sys` IOCTL layout.

## Scope

CP33 must provide all of the following:

1. Real user-mode implementations and public prototypes for the exact fourteen
   imported operations.
2. A versioned Wine-private IOCTL ABI with no raw user pointers and explicit
   32/64-bit-stable layouts.
3. Per-device, per-open, per-interface, and per-pipe state with bounded
   ownership and teardown.
4. Descriptor and interface discovery, device-speed reporting, associated
   interface handles, and default policy initialization.
5. Function-scoped Linux interface claim without automatic kernel-driver
   detach, plus transactional alternate-setting selection and pipe-map update.
6. Synchronous control, descriptor, read, write, abort, reset, and policy
   behavior for the exact vendor profile.
7. Native overlapped completion through the caller's original file handle,
   including `ERROR_IO_PENDING`, `GetOverlappedResult`, `CancelIo`, and
   `CancelIoEx` semantics.
8. Pipe-specific abort, cancel-safe transfer lifetime, removal draining, and
   one completion for every accepted request.
9. Hardware-free RED/GREEN contracts, the complete retained matrix, patch
   replay, two independent clean builds, artifact comparison, and a checksum
   seal.

## Non-goals

CP33 does not:

- implement the eight unimported legacy exports such as `WinUsb_FlushPipe`,
  `WinUsb_QueryPipe`, power policy, or descriptor-parsing helpers;
- claim complete Windows WinUSB compatibility beyond the exact imported API
  and observed vendor policy profile;
- silently accept enabled policy behavior that is not implemented;
- implement isochronous WinUSB APIs or isochronous URBs;
- automatically detach a Linux kernel driver or set libusb auto-detach;
- claim interfaces outside the function-scoped child;
- change USB configuration through `libusb_set_configuration`;
- alter PaeDSPUSB MI00/MI03 or Linux ownership of interface 4;
- stage or select a Wine build, access or create a prefix, load a driver, run
  Universal Control or Voice FX, or open a USB node;
- perform a control, bulk, interrupt, alternate-setting, configuration,
  claim/detach, or firmware operation against the physical device;
- infer synchronization, preset, effect, or firmware behavior from offline
  API tests.

## Chosen architecture

CP33 uses one shared, versioned private IOCTL ABI between the public DLL and
the new function driver. The function driver translates validated user
requests into standard USB request blocks and forwards the original transfer
IRP down the existing function-scoped PDO. The lower WineUSB layer owns only
backend claim, pipe-handle validation, libusb transfer lifetime, and physical
completion.

```
vendor dspusbdevice.dll
  -> public WinUsb_* call
  -> winusb.dll opaque interface handle
  -> versioned IOCTL on original overlapped CreateFile handle
  -> winusb.sys per-file state and URB translation
  -> same IRP, IOCTL_INTERNAL_USB_SUBMIT_URB
  -> function-scoped wineusb.sys PDO
  -> claimed MI05 only / selected alternate / libusb transfer
  -> completion unwinds through the original IRP and OVERLAPPED
```

Forwarding the original user IRP is essential. A nested asynchronous IRP would
separate `CancelIoEx` from the physical transfer and create two independent
completion lifetimes. The same-IRP design preserves the file object,
`OVERLAPPED`, event, completion-port association, cancellation identity, and
byte count from API entry to final completion.

### Rejected alternatives

**Kernel-heavy public handle implementation.** Keeping all descriptor parsing,
associated-handle allocation, and public API state in `winusb.sys` centralizes
state but makes every metadata operation an IOCTL and gives the kernel driver
user-mode pointer-shaped responsibilities. The chosen split keeps public
opaque handles and immutable descriptor parsing in the DLL while making
transfer-affecting policy authoritative in the kernel.

**Direct user-mode libusb bridge.** This bypasses the CP32 function driver and
PnP interface, duplicates function ownership, and makes claim/detach behavior
an application side effect. It is rejected.

**Nested kernel IRPs for asynchronous transfers.** This simplifies the lower
stack's input shape but breaks native cancellation identity and requires a
second state machine to relay every completion. It is rejected.

## Public header and export surface

`include/winusb.h` gains the exact public prototypes and the eight-byte
`WINUSB_SETUP_PACKET` layout. A new `include/winusbio.h` carries the documented
policy IDs and speed values used by applications. The layouts use Windows
fixed-width scalar types and compile-time size assertions where Wine permits.

Only the fourteen imported names become real `stdcall` exports in
`dlls/winusb/winusb.spec`. The other eight names remain explicit stubs so the
CP33 report cannot be misread as full WinUSB coverage.

The exact ownership mapping is:

| Operation | Primary owner | Kernel/backend action |
| --- | --- | --- |
| `WinUsb_Initialize` | DLL plus function driver | validate handle, initialize file session, cache snapshot |
| `WinUsb_Free` | DLL | retire handle; release kernel session on last handle |
| `WinUsb_GetAssociatedInterface` | DLL | allocate one handle for cached associated interface |
| `WinUsb_GetDescriptor` | DLL/cache or function driver | cached device/config data; descriptor URB fallback |
| `WinUsb_QueryDeviceInformation` | DLL/cache | return cached `DEVICE_SPEED` only |
| `WinUsb_GetPipePolicy` | function driver | return authoritative pipe policy |
| `WinUsb_SetPipePolicy` | function driver | validate and commit supported policy value |
| `WinUsb_SetCurrentAlternateSetting` | function driver/lower PDO | select interface, replace pipe map transactionally |
| `WinUsb_ControlTransfer` | function driver/lower PDO | generic control URB, sync or overlapped |
| `WinUsb_ReadPipe` | function driver/lower PDO | direct-buffer bulk/interrupt IN URB |
| `WinUsb_WritePipe` | function driver/lower PDO | direct-buffer bulk/interrupt OUT URB |
| `WinUsb_AbortPipe` | function driver/lower PDO | cancel matching pipe transfers only |
| `WinUsb_ResetPipe` | function driver/lower PDO | require no outstanding pipe I/O, clear halt |
| `WinUsb_GetOverlappedResult` | DLL/KernelBase | call `GetOverlappedResult` on original file handle |

## User-mode handle design

### Root and interface objects

`winusb.dll` allocates a reference-counted root object per successful
`WinUsb_Initialize`. It owns:

- a magic, ABI version, and live/retired state;
- the original device handle, which it references logically but never closes;
- the kernel session cookie returned by initialization;
- a validated device descriptor and projected configuration descriptor;
- an immutable array of interfaces, alternate settings, endpoints, and actual
  USB interface numbers;
- a lock protecting associated-handle issuance and final release;
- one interface-handle slot per projected interface.

Each public `WINUSB_INTERFACE_HANDLE` is a separate small object containing a
magic, root pointer, zero-based interface-array index, and live/retired state.
The default handle uses index zero. Associated index zero maps to root array
index one, matching the documented API.

`WinUsb_GetAssociatedInterface` accepts only the default handle. It rejects an
out-of-range index with `ERROR_NO_MORE_ITEMS`, a second live retrieval of the
same interface with `ERROR_ALREADY_EXISTS`, and allocation failure with
`ERROR_NOT_ENOUGH_MEMORY`. It never returns a partially initialized handle.

`WinUsb_Free` atomically retires exactly one interface handle. When the final
handle releases the root, the DLL sends a synchronous private release request,
frees the descriptor cache, destroys the lock, and frees the root. It never
closes the caller's device handle. A release failure caused by an already
closed device handle does not leak user-mode memory.

### Overlapped-handle validation and synchronous calls

`WinUsb_Initialize` validates the input handle and queries its file mode. A
synchronous file handle fails with `ERROR_INVALID_HANDLE`, as does null or an
unqueryable handle. The output handle is set to null before work begins and is
published only after the complete snapshot validates.

Every private request uses the original overlapped device handle:

- if the public API receives a caller `OVERLAPPED`, the DLL passes that exact
  structure to `DeviceIoControl` and returns immediately on
  `ERROR_IO_PENDING`;
- if the public API is synchronous, the DLL creates a private manual-reset
  event and local `OVERLAPPED`, submits the IOCTL, waits only when pending,
  obtains the final result, closes the event, and preserves the meaningful
  last error;
- `WinUsb_GetOverlappedResult` validates the interface handle, extracts the
  original file handle, and delegates directly to `GetOverlappedResult`.

No helper thread, shadow event, or second file handle is introduced for a
caller-supplied overlapped operation.

## Wine-private IOCTL ABI

A new private header under `include/wine/` is shared by `winusb.dll` and
`winusb.sys`. Version 1 uses fixed-width fields, explicit sizes, reserved-zero
validation, and no pointer-sized or user-pointer members.

Every request begins conceptually with:

```
uint32_t size;
uint32_t version;
uint64_t session;
uint32_t interface_index;
uint32_t reserved;
```

The first initialization request has session zero. Success returns a nonzero
session cookie. All later requests must match the file context's live cookie
and interface bounds. Stale, cross-file, unknown-version, wrong-size, nonzero-
reserved, and integer-overflow inputs fail before state or output mutation.

The IOCTL families are:

| Family | Transfer method | Data shape |
| --- | --- | --- |
| initialize snapshot | `METHOD_OUT_DIRECT` | fixed request; bounded descriptor snapshot output |
| release, alternate, abort, reset, policy | `METHOD_BUFFERED` | scalar fixed-size request/result |
| read, control-IN, descriptor | `METHOD_OUT_DIRECT` | fixed metadata plus caller output MDL |
| write, control-OUT | `METHOD_IN_DIRECT` | fixed metadata plus caller input MDL |

The direct methods deliberately pass the transfer buffer as the second
`DeviceIoControl` buffer even for writes; the method controls whether the I/O
manager probes and locks it for device read or device write. The fixed request
remains in `SystemBuffer`, the data remains in `MdlAddress`, and final
`IoStatus.Information` is the public transferred-byte count.

No IOCTL uses `METHOD_NEITHER`. No structure contains an application address,
an `OVERLAPPED` pointer, a descriptor pointer, a URB pointer, or a kernel pipe
handle.

## Function-driver state

### Device state

The CP32 `winusb_device` extension retains its existing PnP and symbolic-link
state and gains:

- a lock protecting started/removing state and its open-file list;
- the lower bus-interface version and cached canonical device speed;
- an open-file list and count;
- a removal drain event.

The lower WineUSB metadata interface gains an additive version 2. Version 1
remains byte-for-byte valid for the CP32 contract. Version 2 appends a getter
that returns only canonical WinUSB speed values: `0x03` for high speed or
higher and `0x01` for full speed or lower. The value comes from the already
stored lower-child `high_speed` observation; it is not inferred from a
descriptor.

Create succeeds only while the FDO is started and allocates one file context
in `FileObject->FsContext`. Cleanup stops new requests and cancels that file's
outstanding transfers. Close frees the context only after cleanup and the
outstanding count reach zero. Create, cleanup, and close are independently
idempotent under their valid I/O-manager ordering.

### Per-file session state

A file context owns:

- uninitialized, initializing, initialized, releasing, closing, or removed
  state;
- the current nonzero session cookie;
- temporary and committed descriptor snapshots;
- projected interface state and current alternate numbers;
- current generation-tagged lower pipe handles and endpoint metadata;
- authoritative policy values for every current pipe;
- an outstanding-transfer list plus per-interface and per-pipe counts;
- a zero-outstanding event used by release, cleanup, and removal.

Initialization, release, and alternate selection are serialized per file.
Transfer admission takes a short state reference and cannot race the session
from initialized to releasing. Descriptor parsing and lower URB waits occur
without holding a spin lock.

## Initialization and descriptor snapshot

`IOCTL_WINE_WINUSB_INITIALIZE` is synchronous at the public API boundary. The
function driver:

1. verifies that the device is started and the file has no live session;
2. obtains the device descriptor through
   `URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE`;
3. obtains the projected configuration header and then the validated complete
   projected configuration descriptor;
4. parses every descriptor with checked addition, checked offsets, minimum
   descriptor lengths, and exact `wTotalLength` bounds;
5. requires at least one interface and a valid default alternate setting;
6. builds a `URB_FUNCTION_SELECT_CONFIGURATION` for each projected interface's
   default alternate setting;
7. lets the lower function child claim only those interfaces and populate
   generation-tagged pipe handles;
8. commits the descriptor, interface, pipe, speed, and default-policy state
   atomically only after all lower work succeeds; and
9. returns one bounded snapshot containing offsets and lengths rather than
   pointers.

The output buffer is capped by the 16-bit USB configuration length plus its
fixed header. All descriptors are accumulated in temporary kernel memory and
copied to the direct output only after complete validation. A short output
buffer returns the required size without exposing a partial committed session.

The DLL validates the returned version, total size, nonoverlapping offsets,
descriptor lengths, configuration total length, interface count, alternate
ordering, and endpoint bounds independently before publishing the opaque
handle. If DLL-side validation fails, it sends release and reports
`ERROR_BAD_DEVICE`.

`WinUsb_GetDescriptor` serves the cached device and projected configuration
descriptors when the request selects those cached objects. String and other
descriptor requests use a synchronous direct-output descriptor IOCTL and a
lower descriptor URB. The function never returns bytes from outside the
projected function configuration.

`WinUsb_QueryDeviceInformation` accepts only `DEVICE_SPEED`, only on the
default handle, and returns the cached one-byte canonical value with correct
input/output length handling. Unknown information types fail with
`ERROR_INVALID_PARAMETER`.

## Function claims, alternate settings, and pipe handles

The lower `URB_FUNCTION_SELECT_CONFIGURATION` path gains a transactional
function-claim step. For a function child it calls `libusb_claim_interface`
only for interface numbers in that child's function bitset. Already claimed
interfaces for that same lower child are idempotent. A partial failure releases
only claims acquired by that transaction and leaves the prior state intact.

No call enables libusb auto-detach and no path calls
`libusb_detach_kernel_driver`. If an interface is already owned by another
driver, initialization fails and reports the ownership conflict; CP33 does not
seize it. Claims remain owned by the lower function child until its teardown
and are released before the shared physical libusb handle is decremented.

`WinUsb_SetCurrentAlternateSetting`:

1. validates the public handle and session;
2. requires the alternate descriptor to exist for that exact interface;
3. rejects the request if the interface has any outstanding transfer;
4. builds a sized `URB_FUNCTION_SELECT_INTERFACE` containing only the target
   interface and alternate endpoints;
5. has the lower layer validate function membership and current claim, call
   `libusb_set_interface_alt_setting`, and populate new pipe handles;
6. commits the alternate number, endpoint map, new handle generation, and
   default policy values only after lower success; and
7. preserves the complete previous alternate and pipe map on failure.

An encoded lower pipe handle includes the endpoint address, pipe type, actual
interface number, alternate number, and generation. The lower layer validates
all fields before using it. An old handle becomes invalid immediately after a
successful alternate change. Applications never see this handle; they pass the
endpoint address as `PipeID` and the function driver resolves it through the
current map.

For the retained MI05 fixture, initialization commits alternate 0 with no
data pipes. Selecting alternate 1 produces exactly bulk IN `0x81` and bulk OUT
`0x01`, both with maximum packet size 512.

## Exact pipe-policy contract

Each current pipe receives documented defaults during initialization and after
a successful alternate change. `GetPipePolicy` and `SetPipePolicy` validate
that the endpoint belongs to the interface handle and that the policy applies
to its type and direction.

CP33 supports the vendor-observed profile:

| Policy | Required value/action |
| --- | --- |
| `SHORT_PACKET_TERMINATE` | OUT only; false supported |
| `AUTO_CLEAR_STALL` | IN only; false supported |
| `PIPE_TRANSFER_TIMEOUT` | four-byte value; zero supported |
| `IGNORE_SHORT_PACKETS` | IN only; false supported |
| `ALLOW_PARTIAL_READS` | IN only; documented default true; vendor change to false supported |
| `AUTO_FLUSH` | IN only; false supported |
| `RAW_IO` | IN only; false and true supported; true enforces packet multiple and maximum size |
| `MAXIMUM_TRANSFER_SIZE` | four-byte read-only value; 4 MiB for this high-speed bulk path |
| `RESET_PIPE_ON_RESUME` | false supported |

Attempts to set `MAXIMUM_TRANSFER_SIZE`, wrong value lengths, wrong endpoint
directions, or unknown policy IDs fail with `ERROR_INVALID_PARAMETER`.
Requests to enable timeout, short-packet termination, auto-clear, ignore-short,
auto-flush, or resume-reset remain outside the exact vendor profile and fail
with `ERROR_NOT_SUPPORTED` until their behavior exists. They do not return
success as stored no-ops.

With `RAW_IO` enabled, reads must be a nonzero multiple of the endpoint's
maximum packet size and no larger than 4 MiB. The observed vendor profile does
not enable `RAW_IO` on OUT pipes. Zero-length reads retain documented local
completion behavior only when partial reads are enabled; the vendor disables
that policy. Zero-length writes are forwarded to the lower stack.

## Control, descriptor, read, and write translation

### Control transfer

The public setup packet and buffer length must agree and may not exceed 4096
bytes. Direction comes from bit 7 of `RequestType` and selects the IN or OUT
direct IOCTL. Recipient validation follows the documented rules:

- device recipient requires the default interface handle;
- interface recipient overwrites the low byte of `Index` with the actual USB
  interface number represented by the handle;
- endpoint recipient requires the endpoint to exist in that interface's
  current alternate setting and preserves the validated endpoint address;
- request-type and recipient bits outside the USB setup layout fail closed.

The function driver creates `URB_FUNCTION_CONTROL_TRANSFER`, sets its eight
setup bytes exactly after interface-recipient canonicalization, attaches the
user MDL, and forwards the original IRP. The lower Unix path supports standard,
class, and vendor request types and all four recipients after function-scope
validation. Control transfers use a bounded five-second backend timeout.

The retained exact class-IN RANGE response remains an explicit retained
fixture path. Generic class requests do not synthesize unknown response bytes.

### Descriptor transfer

Descriptor fallback uses `URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE` with a
direct output MDL. Function-projected configuration filtering remains in the
lower layer. Actual returned length is bounded by both the request and mapped
buffer, and no short caller buffer receives an unchecked copy.

### Pipe transfer

`WinUsb_ReadPipe` accepts only a current IN bulk or interrupt endpoint.
`WinUsb_WritePipe` accepts only a current OUT bulk or interrupt endpoint. The
function driver resolves the public endpoint address to the generation-tagged
lower handle, applies the exact policy validation, constructs
`URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER`, attaches the original direct MDL,
and forwards the same IRP.

Synchronous calls require a nonnull `LengthTransferred`. Overlapped calls may
pass null for that public pointer; completion byte count remains available
through `WinUsb_GetOverlappedResult`. Immediate success reports the actual
length, pending returns `ERROR_IO_PENDING`, and final completion reports the
URB-derived status and actual length.

CP33 does not claim general large-transfer segmentation. Requests above the
reported maximum fail. That is sufficient for the vendor's observed `RAW_IO`
profile and avoids claiming an unimplemented serial chunking state machine.

## Cancellation, abort, reset, and removal

### Transfer ownership

Every accepted asynchronous lower transfer has exactly three objects with one
owner at each stage:

- the original I/O-manager IRP, owned by the stack until one final completion;
- a nonpaged kernel transfer context, owned by the WineUSB PDO pending queue;
- a Unix transfer context and libusb transfer, owned by the Unix backend until
  it reports completion and the kernel releases it.

The libusb transfer is no longer auto-freed in its callback. The callback
records final status and length, queues one completion event, and leaves the
opaque transfer context valid. The kernel completion path first removes cancel
visibility and queue membership, then asks Unix to release the completed
transfer, clears `DriverContext`, and completes the IRP. This removes the
current callback-to-cancel use-after-free window.

A cancel routine is installed before a request becomes externally pending. A
small submitting/pending/completed state in the kernel context handles a
cancel that races backend submission. The cancel routine takes a temporary
context reference, marks cancellation requested, and invokes
`libusb_cancel_transfer` once a backend transfer exists. It never completes the
IRP; only the backend completion event owns final completion.

Tests must force cancellation before submission, during submission, after
submission, concurrent with natural completion, and after completion. Each
case must prove one backend release, one queue removal, one upper completion,
and no context access after free.

### AbortPipe

`WinUsb_AbortPipe` is synchronous as an API request but does not wait for every
aborted transfer's callback. The function driver validates the current public
pipe and submits `URB_FUNCTION_ABORT_PIPE`. The lower PDO iterates only pending
bulk/interrupt URBs whose encoded pipe handle equals the requested handle and
requests cancellation for those transfers. Control, descriptor, other-pipe,
and other-file transfers are untouched.

### ResetPipe

`WinUsb_ResetPipe` fails with a busy status while the selected pipe has any
outstanding transfer. Once clear, it submits
`URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL`. The lower layer validates the
generation-tagged handle, calls `libusb_clear_halt` for the exact endpoint, and
maps backend failure rather than returning unconditional success.

### Cleanup and PnP removal

File cleanup closes transfer admission, requests cancellation of every
outstanding IRP for that file, and waits or pends through the shared zero-count
event rather than completing still-owned libusb transfers directly. Session
release uses the same drain mechanism.

Surprise removal marks every upper and lower context removed, stops admission,
requests backend cancellation, and lets backend completion retire live
transfers. Remove waits for the bounded ownership drain before destroying the
lower Unix device, releases claimed interfaces, detaches, and deletes objects.
No path completes a queued transfer merely by unlinking it while libusb still
owns it.

## Error mapping

The function driver translates USBD/backend status before the original IRP
completes:

| Condition | NT status | Public result |
| --- | --- | --- |
| caller or session validation | `STATUS_INVALID_PARAMETER` | `ERROR_INVALID_PARAMETER` |
| stale/null public handle | DLL validation | `ERROR_INVALID_HANDLE` |
| missing interface/pipe | `STATUS_NOT_FOUND` | `ERROR_NOT_FOUND` or documented API-specific error |
| allocation failure | `STATUS_NO_MEMORY` | `ERROR_NOT_ENOUGH_MEMORY` |
| pending transfer | `STATUS_PENDING` | `ERROR_IO_PENDING` |
| cancellation/abort | `STATUS_CANCELLED` | `ERROR_OPERATION_ABORTED` |
| backend timeout | `STATUS_IO_TIMEOUT` | `ERROR_SEM_TIMEOUT` |
| removed device | `STATUS_DEVICE_NOT_CONNECTED` | device-not-connected error |
| endpoint stall or request failure | bounded failure mapping | `ERROR_GEN_FAILURE` |
| output too small | `STATUS_BUFFER_TOO_SMALL` | `ERROR_INSUFFICIENT_BUFFER` |
| unsupported enabled policy | `STATUS_NOT_SUPPORTED` | `ERROR_NOT_SUPPORTED` |

No error path publishes a handle, commits an alternate setting, changes a
policy, reports transferred bytes that were not completed, or leaks an acquired
interface/transfer reference.

## Test-first verification

### Genuine RED

Before production changes, add the CP33 public, private-ABI, function-driver,
lower-URB, and asynchronous-lifetime contracts and run them against an
untouched sealed CP32 source. The accepted RED must identify the absent public
definitions, rejected create/IOCTL path, missing alternate/control/cancel
support, and wrong lower abort/reset/removal semantics. A harness compiler
failure, missing fake, or unrelated predecessor failure is not a feature RED.

The exact RED log is retained before any production file changes.

### Public DLL contract

A native host contract compiles the actual `dlls/winusb/main.c` with a fake
Win32 I/O boundary and tests behavior through the exported functions. It
covers:

- null, invalid, synchronous, and valid overlapped device handles;
- initialization failure at every allocation, IOCTL, snapshot, and parsing
  boundary with null output and balanced release;
- default and associated handle indexing, duplicate retrieval, independent
  free order, and last-handle release;
- cached device/configuration descriptor and speed queries;
- synchronous private-event submission and exact caller-overlapped pass-through;
- immediate success, pending, failed completion, and
  `WinUsb_GetOverlappedResult` delegation;
- exact setup packet, pipe ID, lengths, policy values, IOCTL choice, and error
  propagation for all fourteen operations.

Production gains no test-only entry point.

### Private ABI and function-driver contract

A second native contract compiles the actual `dlls/winusb.sys/main.c` against
a fake WDM/lower-stack boundary. It covers:

- additive metadata-interface v2 with unchanged v1 behavior;
- create-before-start rejection, per-file contexts, cleanup, close, stop,
  restart, surprise removal, and remove;
- every ABI version/size/reserved/session/interface overflow rejection with
  guard-buffer nonmutation;
- descriptor two-stage retrieval, malformed descriptor matrices, temporary
  rollback, and exact snapshot offsets;
- successful MI05 alternate-0 initialization with zero pipes;
- successful alternate-1 commit with endpoints `0x81` and `0x01`;
- alternate failure and outstanding-I/O rejection preserving old state;
- direction, endpoint, stale generation, control recipient, and 4 KiB checks;
- policy defaults, exact vendor changes, read-only maximum, RAW_IO validation,
  and unsupported enabled-policy failure;
- same-IRP URB forwarding, direct MDL reuse, final status mapping, and byte
  counts.

### Lower WineUSB contract

The real lower kernel and Unix sources run against fake libusb and cover:

- transactional claim of only the function bitset, idempotence, partial
  rollback, release, busy ownership failure, and absence of detach calls;
- function-scope validation for generic control recipients;
- SELECT_INTERFACE validation, backend call, pipe generation, and rollback;
- pipe-handle endpoint/type/interface/alternate/generation validation;
- pipe-specific abort leaving other requests untouched;
- reset success and exact backend-failure propagation;
- immediate submit failure cleanup;
- backend control/bulk/interrupt status and length mapping;
- transfer-context retention until kernel release;
- cancellation and natural-completion races with one final completion;
- surprise removal and remove with no live transfer at Unix-device destruction.

### Exact vendor-profile contract

A frozen analyzer records the PE hash, fourteen import names, and literal
policy call-site evidence. A synthetic call sequence then exercises:

1. initialize and query speed;
2. configuration and string descriptor retrieval;
3. maximum-transfer query;
4. the exact OUT and IN policy initialization sequences;
5. alternate 1 selection;
6. synchronous and overlapped control/read/write;
7. overlapped result and cancellation;
8. pipe abort and reset; and
9. free in every valid handle order.

The analyzer must distinguish import presence, callable implementation, exact
profile semantics, and hardware-free synthetic execution. It may not label a
structural grep as physical compatibility.

### Regression and reproducibility gates

After GREEN:

1. Run every retained CP32 and predecessor WineUSB contract unchanged unless a
   documented semantic extension requires an additive assertion.
2. Run every new CP33 contract from both clean source trees.
3. Generate one production patch and apply it with fuzz zero to a second
   pristine CP32-derived tree.
4. Prove development and patch-check source equality with no `.orig`, `.rej`,
   or symlink mismatch.
5. Configure and build two empty roots with the retained pinned tools,
   identical virtual paths, read-only source/tools, unshared networking, empty
   sysfs, minimal devices, one job, low priority, memory cap, and timeout.
6. Compare `winusb.dll`, `winusb.sys`, `wineusb.sys`, their builtin halves, and
   generated resources byte for byte.
7. Verify the exact DLL export surface, private ABI structure sizes, Unix
   symbol additions, and absence of detach/auto-detach/configuration/firmware
   calls.
8. Record commands, versions, outputs, hashes, observations, and inferences
   separately.
9. Seal the report and retained evidence with `CP33_SHA256SUMS`, then verify
   the seal from its artifact root.

## Planned incremental gates

CP33 remains one checkpoint but is implemented through five offline gates:

1. **Handle and metadata:** public header, exports, private ABI, create/file
   context, initialize snapshot, free, associated handles, descriptors, speed.
2. **Function and pipe state:** scoped claim, configuration, alternate
   selection, generation-tagged pipes, exact vendor policy profile.
3. **Synchronous transfers:** generic control, read, write, abort, and reset
   with error mapping and immediate cleanup.
4. **Overlapped lifetime:** original-IRP forwarding, pending completion,
   cancel routine, `CancelIoEx`, abort races, cleanup, and removal drain.
5. **Closure:** exact 14/14 synthetic profile, predecessor matrix, patch replay,
   two clean builds, comparisons, report, handoff update, and seal.

Each gate begins with a focused failing test and ends with its focused GREEN.
No gate creates a partial selector or live candidate.

## Planned artifact layout

Durable work remains outside `/tmp`:

```
.io24-build/winusb-api-v1/
  dev-source/
  patch-check-source/
  build-a/
  build-b/

re/winusb-api-v1/
  checkpoints/
    CP33_WINUSB_API.md
    CP33_SHA256SUMS
  logs/
    cp32-seal-verify.log
    cp33-red.log
    dspusbdevice-winusb-callsite.log

re/wine-11.15-winusb-api-v1.patch
```

Expected new or expanded root-level contracts are:

```
tests/winusb_user_api_contract.c
tests/winusb_user_api_contract.sh
tests/winusb_function_io_contract.c
tests/winusb_function_io_contract.sh
tests/wineusb_winusb_urb_contract.c
tests/wineusb_winusb_urb_contract.sh
tests/winusb_overlapped_cancel_contract.c
tests/winusb_overlapped_cancel_contract.sh
tests/io24_winusb_vendor_profile_contract.py
```

The final checkpoint updates `re/IO24_HANDOFF.md` only after every gate is
GREEN and the checksum seal verifies.

## Completion criteria

CP33 is complete only when retained evidence supports all of these statements:

- the CP32 seal verified before CP33 production work;
- genuine missing-feature REDs were captured against untouched CP32;
- all fourteen imported exports have public prototypes and real definitions;
- the other eight legacy exports remain explicitly outside the completion
  claim;
- the private ABI is versioned, pointer-free, direct-buffered where required,
  and rejects malformed or stale requests without mutation;
- initialization validates an overlapped file handle and returns a bounded,
  independently validated descriptor/interface snapshot;
- associated handles, free order, cached descriptors, and speed queries obey
  the defined ownership contract;
- only the selected function interfaces are claimed and no automatic detach or
  configuration change exists;
- MI05 starts at alternate 0 with no pipe and selects alternate 1 to obtain
  exactly bulk `0x81` and `0x01` generation-tagged pipes;
- the exact vendor policy sequence succeeds, RAW_IO restrictions are enforced,
  and unsupported enabled policy behavior fails honestly;
- synchronous and overlapped control/read/write requests use the original IRP,
  original file handle, caller MDL, correct final length, and mapped status;
- `CancelIo`, `CancelIoEx`, pipe abort, reset, cleanup, surprise removal, and
  remove cannot double-complete, leak, or access a released transfer;
- pipe abort affects one pipe only and reset propagates backend failure;
- the complete predecessor matrix and all CP33 contracts pass in both clean
  trees;
- patch replay is clean, required artifacts reproduce byte-for-byte, and the
  CP33 seal verifies;
- no prefix, driver, device, UC, Voice FX, class/vendor transfer, claim/detach,
  alternate/configuration change, staging, selector, or firmware action was
  performed during CP33.

Passing CP33 proves an offline, hardware-free exact vendor WinUSB contract. It
does not prove that the physical io24 exposes the synthetic descriptor fixture,
that a Linux claim will succeed in the live namespace, that any captured or
unknown request receives the expected device response, or that Universal
Control reaches synchronization.

## Safety and stop boundary

All CP33 implementation and verification remains offline. Do not run Wine,
access or create a Wine prefix, stage or select the candidate, load a driver,
open a USB node, address a sysfs USB device path, or run Universal Control or
Voice FX. Do not retry CP24 or treat a connected device as authorization.

Do not perform a live claim, detach, alternate-setting change, configuration
change, control transfer, bulk/interrupt transfer, reset, firmware transition,
or protected-prefix operation. Stop work if battery reaches 10 percent or
lower.

Any selector design comes only after CP33 is sealed. Any live or prefix
validation requires a fresh explicit authorization and a full preflight with
the exact candidate, namespace, ownership, request set, retry count, expected
state change, rollback, evidence plan, and battery stop rule.
