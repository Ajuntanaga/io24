# CP32 — generic WinUSB function binding is reproducible

Reached offline on 2026-08-23. The complete 51-entry CP31 seal reverified
before implementation; its checksum file remains:

    32afc37705b8f78d1a6f151f71e72be4475914c896eb8f660c647b660bf1b0ca  CP31_SHA256SUMS

CP24's consumed live authorization was not reused. No Wine process, prefix
content, USB node, driver/service, Universal Control, Voice FX, or firmware
artifact was opened.

## Result

CP32 completes the second of the three host layers identified at CP30:

| Layer | CP31 | CP32 |
| --- | --- | --- |
| Microsoft OS 1.0 discovery and `USB\MS_COMP_*` translation | implemented and behavior-tested offline | retained |
| Generic WinUSB binding and device-interface lifecycle | missing | implemented and behavior-tested offline |
| Vendor-required `WinUsb_*` operations | 0/14 | still 0/14 |

This is a real PnP-layer advance, but it is not usable or stageable MI05/MI06
support. Applications can use none of the fourteen operations required by the
installed vendor module, and CP32 deliberately supplies no kernel I/O protocol.

## Binding and metadata contract

The CP31 WineUSB PDO now exposes one private, versioned metadata interface:

    {a6523832-2ca5-42ff-aa70-c760f06a8e73}

It is a Wine kernel contract, not an application-visible device-interface
GUID. A query succeeds only for the exact internal GUID, version 1, a
sufficient buffer, complete reference/dereference/getter routines, exact
validated `WINUSB` metadata, a live child, and a canonical GUID. Rejections do
not mutate output or acquire a reference. Success acquires exactly one
reference; the function driver validates the returned structure, obtains a
caller-owned binary GUID, and dereferences it on every path.

The new INF matches one model ID only:

    USB\MS_COMP_WINUSB

It selects the demand-start kernel service `winusb`, embeds and publishes
`winusb.inf`, and uses the standard `USBDevice` setup class. It has no VID,
PID, MI, USB class, PaeDSPUSB, or root-device match. Discovery-nonsupporting
children therefore retain their prior class IDs and selection behavior.

## Per-PDO lifecycle

`dlls/winusb.sys/main.c` creates no global device singleton. Each eligible PDO
gets an independent FDO, copied GUID, registered symbolic link, and lifecycle
state. The ordered behavior is:

1. query and validate metadata before FDO creation;
2. create, attach, and register transactionally, cleaning every partial
   failure;
3. enable the registered interface only after lower-stack START succeeds;
4. leave it enabled across a successful normal STOP and restart without a
   duplicate enable;
5. disable it after failed restart or surprise removal, retaining one bounded
   final attempt when disable itself fails; and
6. always forward REMOVE, detach, free the symbolic-link allocation, and
   delete the FDO even when the final disable reports failure.

Two distinct PDOs using the same interface-class GUID keep distinct symbolic
links and state. Informational registration success, including
`STATUS_OBJECT_NAME_EXISTS`, is accepted. Create, read, write, device-control,
and internal-device-control requests return `STATUS_NOT_SUPPORTED`; close is
idempotently successful.

## Genuine RED and test-hardening

The current three CP32 contracts were rerun against the sealed CP31 source in
an unshared-network, empty-sysfs container. They each exited 1 for the intended
missing production surface:

- no `winusb_busif.h`/`.c` metadata interface;
- no generic `dlls/winusb.sys/main.c`; and
- no `winusb.inf`, resource, configure, or loader publication.

No unrelated harness/compiler failure was accepted as the feature RED.

During GREEN development, the WDM fake's reset routine was found to clear its
global assertion-failure counter. That could turn an earlier failed assertion
into an apparent pass. Preserving the counter made a new wrong-interface-
version case genuinely RED; production then gained strict returned size,
version, context, callback, and balanced-dereference validation. The harness
also gained realistic Unicode initialization and correct two-stack-location
IRP forwarding.

The first real contained Wine build found a separate issue the host-inclusion
test could not model: the function driver referenced a GUID object defined in
the bus driver's binary. Replacing that link-time cross-driver symbol with a
shared initializer and module-local constants made both real driver modules
link cleanly. These corrections are part of the final contracts and patch.

## Independent contract matrices

Both clean sides independently pass:

    WineUSB Microsoft OS 1.0 behavior matrix: pass
    WineUSB Microsoft OS 1.0 PnP ID contract: pass
    WineUSB function-scope contract: pass
    WineUSB immediate-submit cleanup contract: pass
    WineUSB multi-interface handle contract: pass
    WineUSB pipe-observe plus bounded OS 1.0 reader contract: pass
    WineUSB captured-RANGE source/binary contract: pass
    wineusb USBDI V1 contract checks passed
    io24 usbmon class-IN evidence contract: pass
    io24 usbmon function topology contract: pass
    io24 WinUSB readiness contract: pass (known RED and synthetic structural GREEN)
    WineUSB WinUSB metadata bus-interface contract: pass
    CP32 winusb function-binding lifecycle checks passed
    CP32 WinUSB function-binding INF contract: pass

The OS 1.0 line expands to all eleven retained discovery scenarios. The CP30
readiness analyzer remains a frozen known-boundary self-contract rather than a
forward CP32 oracle; its synthetic contract still passes while its historical
literal structural check remains intentionally non-stageable.

## Patch replay and clean builds

The production patch is:

    7df4011ea20fa36bf80f4bc0ba409c9dca812b7d76b00f19f1709774eebf75bb
    re/wine-11.15-winusb-function-binding-v1.patch

It changes twelve Wine production paths and applies to sealed CP31 with fuzz
zero. A reverse dry-run succeeds on the patch-check tree. Patch-check and
development contain 12,453 identical regular files, zero symlinks, and no
`.orig` or `.rej` remnants.

Build A and build B began as separate empty roots. Each used the same virtual
source/tool paths, pinned Bison/Flex/M4/libusb inputs,
`SOURCE_DATE_EPOCH=1787101002`, `make -s -j1`, a 2 GiB virtual-memory cap,
low CPU/I/O priority, a 300-second timeout, unshared networking, empty sysfs,
minimal devices, and read-only source/tools. Configure and build both exited
zero. Only identical optional gettext/GnuTLS/no-sound warnings and Wine's
inherited WRC parser notice appeared.

Top-level Makefile, config.status, `include/config.h`, configure output, and
build output are byte-identical. Raw `config.log` differs only in eight random
compiler temporary-object basenames; normalization makes the logs identical.

## Reproducible artifacts

Clean A and clean B match byte-for-byte:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  wineusb.sys fake PE  2,560 bytes
    28617460085c0a2f8ae4782f3147bcad8a475a5b01daebba72b64380c118808e  wineusb.sys.so     213,840 bytes
    1edd11b0336a241c1ac8c667fb1d21db3bfac08b0ebdc8f672aa2931785490d9  wineusb.so         147,016 bytes
    b4e48cfca26754279ece31bfd285bfd8ce248acac7ab0967fadfc1b70d57720c  wineusb.res
    bacee6355cda7eb6bb19a7c8f73d2b8babfc4a22d19b47c31cffc1985f7427eb  winusb.sys fake PE   2,560 bytes
    dd1f3f199999546ff64ea7c1daa1306fba0a5958f7c1102df3b49ebfca20be46  winusb.sys.so      137,368 bytes
    d63357cb4ce680b4ed6500ad30c235065c5c8ef9fbed28cd54af4c8acaa5f23f  winusb.res             552 bytes

Build IDs are `b4a791abfd282baa306eaae3fae91c3a199c6243` for
`wineusb.sys.so`, `fc1f9fb7f02492a67d4203fc9cea27bfd9b39a6b` for
`wineusb.so`, and `5c192b2f7ac26224eff1afef26d1656886ae7248` for
`winusb.sys.so`.

## No-transfer boundary

The new `winusb.sys.so` has no dynamic NEEDED entry and no libusb undefined
symbol. The new module and added patch lines contain no libusb API, URB submit,
claim/release, kernel detach/attach, configuration, alternate-setting, control,
bulk, or interrupt transfer call. The complete user-mode `dlls/winusb` tree is
identical to CP31. The embedded fake PE contains the exact USBDevice class,
`USB\MS_COMP_WINUSB` model, and `%12%\winusb.sys` service strings.

The CP32 WineUSB fake PE is byte-identical to CP31. The changed bus module only
exports already parsed metadata through the private interface; no new Unix or
physical-device operation was introduced.

## Safety state and interpretation

At the final passive snapshot, BAT0 was 100%/Full. The same io24 was present as
`194f:0422`, serial `AB7C22200355`, sysfs `1-2`, authorized, high speed, and
configuration 1. Interfaces 0–4 remained bound to `snd-usb-audio`; 5–6 were
unclaimed. No relevant Wine, wineserver, Xvfb, UC/Voice, make, or bubblewrap
process existed. The protected prefix directory mtime remained
`2026-08-12 00:31:35.825186221 -0700`; only directory metadata was read.

These are passive host-state observations, not a device experiment. No USB
node was opened and no control, bulk, interrupt, OUT, claim/detach,
configuration, alternate-setting, driver load, or prefix operation occurred.

CP32 changes no interface-4 ownership behavior. CP29 still gives MI03 the
correct CTRL/MIDI function view, while Linux physical ownership remains a
separate architecture decision. Preset, effect, component-model, and prior
wire evidence are unchanged. Firmware is further narrowed rather than
implicated: MI06 remains the likely direct DFU route, but the complete user API
layer still precedes any meaningful application or firmware test.

## Next coherent offline slice

Implement the exact fourteen imports confirmed at CP30:

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

That slice must be test-first and hardware-free, define the user/kernel handle
and IOCTL boundary, cover synchronous and overlapped completion/cancellation,
and rerun the complete matrix in two independent clean builds. A selector and
staging contract comes only after all three layers are GREEN.

## Stop boundary

Stop at CP32. The candidate is reproducible but not staged or selected. Do not
run the legacy UC capture, retry CP24, access a prefix, load a driver, or infer
that the synthetic OS-descriptor fixtures match the physical io24.

Any staging, device-visible read, driver load, claim/detach, alternate or
configuration change, transfer, Universal Control, Voice FX, firmware
transition/write, or protected-prefix access requires fresh explicit
authorization and full preflight. CP24 remains consumed; reconnection is state
evidence, not authorization. Pause at 10% battery or lower.
