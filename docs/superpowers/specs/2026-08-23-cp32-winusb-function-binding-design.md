# CP32 Generic WinUSB Function Binding and Device-Interface Lifecycle

Date: 2026-08-23  
Status: Implemented and independently reproduced offline  
Implementation state: Complete at CP32; not staged or selected

## Purpose

CP32 adds the missing generic WinUSB function-driver layer between CP31's
Microsoft OS 1.0 discovery support and a later implementation of the vendor's
required `WinUsb_*` APIs. It binds only USB function children whose compatible
ID is `USB\MS_COMP_WINUSB`, obtains the `DeviceInterfaceGUID` already parsed by
CP31, and gives that GUID a bounded Plug and Play device-interface lifecycle.

This is an offline interoperability change to the pinned Wine 11.15 source.
It is not a device experiment, Universal Control run, prefix operation,
firmware investigation, or transfer implementation.

## Evidence baseline

CP32 starts from the sealed CP31 candidate. Before this design pass, all 51
entries in `re/wineusb-ms-os-10-v1/checkpoints/CP31_SHA256SUMS` reverified and
the checksum file itself hashed to:

```
32afc37705b8f78d1a6f151f71e72be4475914c896eb8f660c647b660bf1b0ca
```

The relevant observed source facts are:

- `wineusb.sys` is the Wine USB root bus and child PDO enumerator.
- CP31 stores the Microsoft OS compatible ID, sub-compatible ID, vendor code,
  and parsed GUID on each function-scoped `usb_device` child.
- CP31 emits `USB\MS_COMP_WINUSB` ahead of USB class-compatible IDs when the
  descriptor metadata is valid.
- `wineusb.sys` already answers `IRP_MN_QUERY_INTERFACE` for a versioned USB
  bus interface.
- Wine has no `winusb.sys` function-driver module or matching `winusb.inf`.
- The separate user-mode `winusb.dll` has one permissive `WinUsb_Free` stub and
  all other relevant exports are specification stubs. It remains unchanged in
  CP32.

Microsoft's documented model has two layers: `Winusb.sys` is the function
driver selected by `USB\MS_COMP_WINUSB`, while `Winusb.dll` supplies the
user-mode API. A device-interface GUID is registered once, enabled after a
successful start, left enabled across a normal stop, and disabled during
surprise removal or removal.

Reference basis:

- CP31 checkpoint:
  `re/wineusb-ms-os-10-v1/checkpoints/CP31_MS_OS_10_DISCOVERY.md`
- Pinned bus and DLL source:
  `.io24-build/wineusb-ms-os-10-v1/patch-check-source/dlls/wineusb.sys/`
  and `dlls/winusb/`
- Microsoft WinUSB compatible-ID and GUID model:
  <https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/automatic-installation-of-winusb>
- Microsoft driver-defined interface guidance:
  <https://learn.microsoft.com/en-us/windows-hardware/drivers/wdf/using-driver-defined-interfaces>
- Microsoft device-interface lifecycle guidance:
  <https://learn.microsoft.com/en-us/windows-hardware/drivers/install/enabling-and-disabling-a-device-interface-instance>
- Current WineHQ WinUSB export status:
  <https://source.winehq.org/WineAPI/winusb.html>

The stored fields, compatible-ID output, present modules, and absent modules are
observations from the sealed local source. Windows lifecycle rules are
documentation-backed constraints. Choosing a private query interface instead
of a registry bridge is a CP32 design decision based on the observed Wine PnP
ordering; it is not a claim about undocumented Windows internals.

## Scope

CP32 must provide all of the following:

1. An INF route that matches exactly `USB\MS_COMP_WINUSB` and loads a new Wine
   `winusb.sys` function driver.
2. A versioned and reference-balanced bus interface through which that
   function driver obtains CP31's validated device-interface GUID.
3. A per-PDO function device object that registers the GUID and manages its
   symbolic link through add, start, stop/restart, failed start, surprise
   removal, and removal.
4. Fail-closed behavior for missing or invalid metadata and for every partial
   construction failure.
5. Deterministic behavior when a registration already exists and when two
   distinct PDOs use the same interface-class GUID.
6. Hardware-free RED/GREEN contracts, the complete retained contract matrix,
   two independent clean builds, patch replay, artifact comparison, and a
   checksum seal.

## Non-goals

CP32 does not:

- implement or change any `WinUsb_*` user-mode export;
- define a WinUSB user/kernel IOCTL protocol;
- submit a URB or perform control, bulk, interrupt, or isochronous I/O;
- claim, release, detach, or rebind a Linux USB interface;
- select a configuration or alternate setting;
- stage or select a Wine build or load a driver in a prefix;
- run Universal Control, Voice FX, or any capture harness;
- access a USB node, sysfs USB namespace, or physical device;
- change interface 4 ownership or the PaeDSPUSB MI00/MI03 path;
- inspect presets, effects, synchronization, firmware, or DFU behavior.

The later fourteen-operation WinUSB API slice begins only after CP32 is sealed.
Selector and live-device work remain later, separately authorized phases.

## Chosen architecture

The selected architecture is a new `winusb.sys` function driver backed by a
Wine-private, versioned `IRP_MN_QUERY_INTERFACE` contract exported by the
existing `wineusb.sys` bus PDO.

```
CP31 function child
  -> USB\MS_COMP_WINUSB compatible ID
  -> Wine SetupAPI selects winusb.inf
  -> winusb.sys AddDevice receives that child's PDO
  -> function driver queries the PDO's metadata bus interface
  -> bus returns the validated DeviceInterfaceGUID
  -> function driver registers once and owns enable/disable/teardown
```

This preserves the distinction between a USB bus driver and a generic
function driver without changing Wine's PnP manager. It also leaves a coherent
kernel endpoint for the later user-mode WinUSB APIs.

### Rejected alternatives

**Device-registry bridge.** Windows records Microsoft OS extended properties in
the device hardware key, but Wine has no clean hook between creating the devnode
and calling a selected function driver's `AddDevice`. Implementing that path
would require an unrelated `ntoskrnl.exe` PnP change or a registry-writing side
effect in an ID or capability query. That timing and scope are not justified by
CP32.

**Bus-owned device-interface registration.** The existing bus already holds the
GUID, so it could register the interface directly. This is smaller but merges
bus and function responsibilities, does not actually provide a WinUSB function
binding, and leaves no clean driver boundary for subsequent WinUSB operations.

**Direct user-mode libusb access.** This bypasses Windows PnP selection and
device-interface semantics, duplicates ownership logic, and would immediately
raise Linux claim/detach questions. It is outside this design.

## Component design

### 1. WineUSB metadata bus interface

New files in `dlls/wineusb.sys`:

- `winusb_busif.h`
- `winusb_busif.c`

`winusb_busif.h` is a private cross-driver header consumed by both
`wineusb.sys` and `winusb.sys`. It defines interface version 1 and the internal
interface GUID:

```
GUID_WINEUSB_MS_OS_10_METADATA_INTERFACE
{a6523832-2ca5-42ff-aa70-c760f06a8e73}
```

This GUID identifies the Wine kernel contract. It is not a device-interface
GUID and is never exposed to applications.

The version-1 structure begins with the standard `INTERFACE` fields: size,
version, bus context, reference routine, and dereference routine. Its only
operation is conceptually:

```
NTSTATUS GetDeviceInterfaceGuid(void *context, GUID *guid);
```

The query helper obeys these rules:

- accept only the exact internal interface GUID, version 1, and a buffer at
  least as large as the version-1 structure;
- reject null pointers, unknown GUIDs, other versions, and short buffers with
  no output mutation and no reference acquisition;
- populate the entire structure only after validation;
- acquire exactly one interface reference before returning success;
- never return raw pointers to the child metadata or its GUID string.

`GetDeviceInterfaceGuid` operates on the immutable `usb_device` child context.
It succeeds only if the compatible ID is the exact, validated `WINUSB` value and
the stored GUID string is present and converts through `RtlGUIDFromString`.
It copies a binary `GUID` to caller-owned storage. Empty, malformed, unrelated,
or removed-child metadata fails without changing the caller's output.

The PDO's existing `IRP_MN_QUERY_INTERFACE` branch dispatches the established
USBDI interface unchanged and the new metadata interface by its distinct GUID.
No other PnP or transfer behavior changes in `wineusb.sys`.

### 2. Generic WinUSB function driver

New module directory `dlls/winusb.sys`:

- `Makefile.in`
- `main.c`
- `winusb.inf`
- `winusb.rc`

The module is a native subsystem kernel driver importing `ntoskrnl`. It has no
Unix library and makes no libusb call.

Each function device extension owns only per-PDO state:

- the physical PDO and the lower attached device object;
- the binary device-interface GUID;
- the symbolic-link `UNICODE_STRING` returned by
  `IoRegisterDeviceInterface`;
- lifecycle state: added, started, stopped, or surprise-removed;
- booleans recording whether the interface was registered and is enabled.

There is no global active-device singleton. Distinct MI05/MI06 PDOs therefore
remain independent even if firmware reports the same interface-class GUID.

#### AddDevice

`AddDevice` performs this ordered transaction:

1. Send a synchronous `IRP_MN_QUERY_INTERFACE` to the supplied PDO for
   metadata interface version 1.
2. Call `GetDeviceInterfaceGuid`, copy the result, and immediately balance the
   acquired interface reference on both success and failure paths.
3. Fail without creating an FDO if metadata is unavailable or invalid.
4. Create an unnamed function device object and initialize every extension
   field before publishing it.
5. Attach the FDO to the PDO stack and retain the returned lower-device object.
6. Register the copied GUID against the physical PDO with no reference string.
7. Treat any `NT_SUCCESS` result, including the informational
   `STATUS_OBJECT_NAME_EXISTS`, as a valid registration.
8. On attach or registration failure, detach if necessary, free any returned
   symbolic-link allocation, delete the FDO, and return the original failure.
9. Clear `DO_DEVICE_INITIALIZING` only after all required state exists.

Registration is persistent by Windows design. A later failed start may leave a
disabled SetupAPI registration, but it must leave no enabled symbolic link and
no live function device object after removal.

#### PnP dispatch

`IRP_MN_START_DEVICE` is forwarded synchronously to the lower driver first.
The interface is enabled only after lower-stack success. On the first start,
lower-stack or enable failure leaves the interface disabled and fails the IRP.
Any `NT_SUCCESS` enable result is accepted. On restart after a normal stop, the
interface is already enabled and is not enabled a second time. If that lower
restart fails, the function driver attempts to disable the previously enabled
interface before returning failure. A failed disable leaves the local enabled
flag set so the mandatory removal path can make one final attempt.

`IRP_MN_QUERY_STOP_DEVICE`, `IRP_MN_CANCEL_STOP_DEVICE`, and other ordinary PnP
IRPs pass down without inventing local policy.

`IRP_MN_STOP_DEVICE` passes down and records the stopped state only if the lower
stack succeeds; otherwise the prior state is retained. It deliberately leaves
the interface enabled. CP32 has no accepted I/O to queue, and a later start does
not issue a duplicate enable.

`IRP_MN_SURPRISE_REMOVAL` marks the extension surprise-removed, attempts to
disable the interface if it is enabled, and forwards the IRP. Successful disable
or `STATUS_OBJECT_NAME_NOT_FOUND` records the interface disabled. Any other
failure is logged and leaves the enabled flag set so `IRP_MN_REMOVE_DEVICE` can
make one final bounded attempt; it cannot block removal.

`IRP_MN_REMOVE_DEVICE` makes one disable attempt if an orderly path or a failed
earlier disable has left the interface enabled. It then records the local
interface state disabled regardless of that final result, forwards the mandatory
remove IRP, detaches, frees the symbolic-link string, marks the extension
removed, and deletes the FDO. It must complete its cleanup whether the device
was never started, failed its first start, stopped, or was surprise-removed. It
never attempts to disable an interface already known to be disabled.

PnP state is serialized by the PnP manager; CP32 adds no lock solely for this
state. The later I/O implementation must revisit synchronization before it
introduces handles or outstanding requests.

#### Non-PnP dispatch

CP32 exposes discoverability, not I/O capability. The driver explicitly fails
create, read, write, device-control, and internal-device-control requests with
`STATUS_NOT_SUPPORTED` and zero information. Close succeeds as an idempotent
cleanup operation. No IOCTL number or transfer structure is introduced.

### 3. INF and build registration

`dlls/winusb.sys/winusb.inf` uses the system `USBDevice` setup class:

```
Class=USBDevice
ClassGuid={88bae032-5a81-49f0-bc3d-a4ff138216d6}
```

Its manufacturer/model table has one match only:

```
USB\MS_COMP_WINUSB
```

The service name is `winusb`, its binary is `%12%\winusb.sys`, its type is a
demand-start kernel driver, and it uses Wine's `WinePlugPlay` load-order group.
There is no VID/PID, MI-number, device-class, or interface-class wildcard.

`winusb.rc` embeds `winusb.inf` as a `WINE_DATA_FILE`.
`loader/wine.inf.in` publishes that embedded INF in `[InfFiles]`, and
`configure.ac` adds `WINE_CONFIG_MAKEFILE(dlls/winusb.sys)`. No root-device
entry is added to `wineboot`; this is a compatible-ID-selected child function
driver, not a root enumerator.

### 4. User-mode WinUSB DLL

`dlls/winusb` is unchanged. In particular, CP32 does not turn
`WinUsb_Initialize`, `WinUsb_Free`, or any pipe/descriptor function into an
implemented API. This preserves the boundary that a registered device
interface alone is not transfer readiness.

## Error and cleanup contract

| Failure point | Required result |
| --- | --- |
| Unknown bus-interface GUID/version/size | No output mutation, no reference, `STATUS_NOT_SUPPORTED` |
| Missing, malformed, unrelated, or removed-child metadata | No GUID output, `AddDevice` fails before FDO publication |
| Metadata reference acquired but getter fails | Dereference exactly once, no FDO |
| `IoCreateDevice` fails | Return failure, no attachment or registration |
| Attachment fails | Delete FDO, no registration |
| Interface registration fails | Detach, free any link allocation, delete FDO |
| Registration already exists | Accept informational success and use returned stable link |
| Initial lower start fails | Never enable; later remove cleans the FDO |
| Interface enable fails | Fail start, record disabled, later remove cleans the FDO |
| Restart after stop fails | Attempt disable, retain enabled state on failure for final removal retry, fail restart |
| Surprise removal | Attempt disable once, forward, retain FDO until remove; leave state enabled only if the call failed |
| Remove before start | Do not disable an interface that was never enabled; detach and delete |
| Disable fails before final removal | Retain enabled state and retry once during remove |
| Final disable fails during removal | Log, mark local state disabled, continue mandatory detach/free/delete cleanup |

## Test-first verification

### RED evidence

Before production changes, add CP32 contracts and run them against an untouched
CP31-derived source. The expected RED must be caused by the absent metadata
interface, `winusb.sys`, INF route, and lifecycle behavior. Save the exact log;
do not accept a compiler or harness defect unrelated to those missing features.

### Metadata bus-interface contract

A native host test links the real `winusb_busif.c` and uses literal expected
values. It covers:

- unknown GUID, null input, wrong version, and undersized buffer;
- output and guard-buffer nonmutation on every rejection;
- exact version-1 structure, callbacks, context, and one reference on success;
- balanced dereference by a consumer;
- exact `WINUSB` acceptance, including a valid sub-compatible fallback;
- empty, lowercase, internally terminated, malformed, unrelated, and removed
  metadata rejection;
- valid mixed-case hexadecimal GUID conversion to independently derived binary
  fields;
- no output mutation when GUID conversion fails.

### Function-driver lifecycle contract

A native host test compiles the actual `dlls/winusb.sys/main.c` against a fake
WDM boundary. It reaches behavior through `DriverEntry`, `AddDevice`, and the
installed dispatch table; production does not gain test-only entry points.
The fake boundary supplies complete WDM-shaped inputs and replaces only kernel
services that cannot run natively. Assertions target the real extension state,
IRP status/information, resources, and a literal ordered kernel-call trace, not
the existence of the fake itself.

The matrix covers:

- successful query/create/attach/register/start/enable;
- missing metadata and balanced reference on getter failure;
- create, attach, registration, lower-start, and enable failures;
- `STATUS_OBJECT_NAME_EXISTS` registration;
- normal stop and successful restart without disable/re-enable;
- failed restart, including a failed disable followed by one final removal
  attempt;
- orderly removal, surprise-then-remove, remove-before-start, and
  failed-start-then-remove;
- disable failure not preventing mandatory teardown;
- two independent PDOs sharing one interface-class GUID but receiving distinct
  symbolic links;
- explicit rejection of create/read/write/control requests and absence of any
  URB or Unix/libusb call.

### INF semantic contract

An INF-aware test parses the actual model and service sections rather than
grepping an exact source line. It proves that:

- the sole model match is `USB\MS_COMP_WINUSB`;
- the install section selects service `winusb` and binary `winusb.sys`;
- the setup class is `USBDevice` with its documented class GUID;
- no VID/PID, MI, USB class, PaeDSPUSB, or root match exists;
- the built driver resource embeds `winusb.inf` and Wine's loader publishes it.

### Regression and reproducibility gates

After GREEN:

1. Run every retained WineUSB contract from CP31 and its sealed predecessors.
2. Run the new CP32 contracts from both clean build source trees.
3. Generate one production patch and apply it with checks enabled to a second
   pristine CP31-derived source tree.
4. Configure and build two independent trees with networking unshared.
5. Compare the PE, builtin, and any generated resource artifacts byte for byte.
6. Verify that production source contains no new libusb claim, detach,
   configuration, alternate-setting, transfer, or firmware path.
7. Record commands, tool versions, outputs, hashes, observations, and
   inferences separately.
8. Seal the report and all retained evidence with `CP32_SHA256SUMS` and verify
   the seal from its artifact root.

## Planned artifact layout

Development and clean-build state remains outside `/tmp`:

```
.io24-build/winusb-function-binding-v1/
  dev-source/
  patch-check-source/
  build-a/
  build-b/

re/winusb-function-binding-v1/
  checkpoints/
    CP32_WINUSB_FUNCTION_BINDING.md
    CP32_SHA256SUMS
  logs/

re/wine-11.15-winusb-function-binding-v1.patch
```

New root-level tests use the existing naming convention:

```
tests/wineusb_winusb_busif_contract.c
tests/wineusb_winusb_busif_contract.sh
tests/winusb_function_binding_contract.c
tests/winusb_function_binding_contract.sh
tests/winusb_function_binding_inf_contract.py
```

The final checkpoint updates `re/IO24_HANDOFF.md` only after all CP32 gates are
GREEN and the checksum seal verifies.

## Completion criteria

CP32 is complete only when all of these statements are supported by retained
evidence:

- CP31's seal verified before work began.
- A genuine missing-feature RED was observed before production implementation.
- Only `USB\MS_COMP_WINUSB` selects the new function driver.
- PaeDSPUSB MI00/MI03 and discovery-nonsupporting children retain prior IDs and
  driver selection behavior.
- A CP31 GUID reaches a per-PDO function driver through a validated, balanced
  bus interface.
- The device interface is registered once, enabled only after successful
  start, retained across normal stop, and subject to bounded disable attempts
  and unconditional local cleanup during every failure/removal path.
- Same-GUID distinct PDOs remain independent and re-registration is bounded.
- No WinUSB user API, transfer, claim/detach, configuration, alternate-setting,
  prefix, device, Universal Control, preset/effect, or firmware behavior was
  added or exercised.
- Retained contracts and new contracts pass in both independent clean trees.
- Patch replay is clean, build artifacts compare as required, and the CP32 seal
  verifies.

Passing CP32 proves only offline function binding and device-interface
lifecycle. It does not prove that the physical io24 returns the synthetic
Microsoft OS descriptor fixtures, that Linux ownership permits access, that
Universal Control synchronizes, or that presets, effects, and firmware paths
work.

## Safety and stop boundary

All CP32 work remains offline. Do not run Wine, access or create a Wine prefix,
load or stage the driver, open a USB node or sysfs device path, run Universal
Control or Voice FX, retry CP24, or reuse any consumed live authorization.
Do not claim/detach an interface, change an alternate setting or configuration,
send a class or vendor request, transition modes, or read/write firmware.

The connected device, if present, is state evidence only. Stop work if battery
reaches 10 percent or lower. A selector or live validation requires a separate
architecture decision, a fresh explicit authorization, and a full preflight
after the complete WinUSB stack is implemented and sealed.
