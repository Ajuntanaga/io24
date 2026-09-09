# CP31 — bounded Microsoft OS 1.0 discovery is reproducible

Reached offline on 2026-08-23 after work begun on 2026-08-22. Starting battery
was 95% and fully charged. The complete CP30 seal reverified before work.
CP24's consumed live authorization was not reused.

## Result

The first of CP30's three missing WinUSB layers is now implemented and
independently reproducible:

| Layer | CP30 | CP31 |
| --- | --- | --- |
| Microsoft OS 1.0 discovery and `USB\MS_COMP_*` translation | missing | implemented and behavior-tested offline |
| Generic WinUSB function binding and device-interface lifecycle | missing | still missing |
| Vendor-required `WinUsb_*` user operations | 0/14 | still 0/14 |

This is a meaningful host-stack advance, but not usable MI05/MI06 support.
There is still no function driver to bind the new compatible ID, no registered
device interface for the vendor application to open, and none of its fourteen
required user-mode operations has been implemented.

## Microsoft discovery contract implemented

The Unix backend performs one bounded, fail-soft discovery sequence while a
USB device is being enumerated:

1. `bmRequestType=0x80`, `bRequest=0x06`, `wValue=0x03ee`, `wIndex=0`,
   `wLength=18`, timeout 1000 ms;
2. validate length/type, fixed UTF-16LE `MSFT100` signature, returned vendor
   code, and zero pad;
3. `bmRequestType=0xc0`, `bRequest=vendor`, `wValue=0`, `wIndex=4`, first a
   16-byte header and then the exact declared body;
4. atomically map compatible/sub-compatible IDs by first-interface number;
5. only when an active-config child is actually emitted, request
   `bmRequestType=0xc1`, `bRequest=vendor`, `wValue=interface<<8`, `wIndex=5`,
   first a 10-byte header and then the exact declared body; and
6. carry a valid `DeviceInterfaceGUID` with the child event.

Microsoft documents the fixed index `0xee`, the vendor-code feature requests,
extended compatible ID, and `DeviceInterfaceGUID` property here:

- <https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/automatic-installation-of-winusb>
- <https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/microsoft-defined-usb-descriptors>
- <https://learn.microsoft.com/en-us/windows-hardware/drivers/network/mb-interface-model-supplement>
- <https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-xusbi/601a3107-6583-4e80-867e-118829cb573e>

The production implementation is generic. It contains no IO24 VID/PID,
interface number, vendor code, compatible ID, or GUID hardcode.

## Parser and allocation bounds

All feature-descriptor allocations are capped at 4096 bytes. The parser
requires:

- version `0x0100` and correct `wIndex`;
- exact header/count/section length arithmetic;
- zero header and function reserved bytes;
- function reserved byte 1 equal to one;
- no duplicate interface sections;
- uppercase ASCII letters, digits, or underscore in IDs, with correct NUL
  padding;
- well-bounded property sections and exact section count;
- the singular `DeviceInterfaceGUID` property as `REG_SZ`;
- UTF-16LE with zero high bytes; and
- a canonical brace-and-hyphen GUID with a terminating NUL.

If any compatible-ID function section is malformed, no section is published.
If properties are unavailable, malformed, unrelated, or omit the GUID, the
compatible ID remains valid and the GUID stays empty. No property request is
made for a compatible-ID section whose interface is absent from the active
configuration.

## PnP identity translation

The builtin validates the shared ID again before formatting. A compatible ID
without a sub-compatible ID produces:

    USB\MS_COMP_WINUSB

With both IDs, the more specific ID precedes the compatible-only fallback:

    USB\MS_COMP_XUSB10&MS_SUBCOMP_ABC
    USB\MS_COMP_XUSB10

These precede the existing USB class-compatible IDs. The parsed GUID is copied
into the child model for the next layer; CP31 deliberately does not register a
device interface or bind a function driver.

## Test-first development

The unchanged sealed CP29 Unix library failed the valid fake-device scenario
with seven intended assertions: zero descriptor requests, no MI05/MI06
compatible IDs, no vendor codes, and no GUID metadata.

Two additional failures improved the final boundary:

- an unknown interface 200 section triggered an unnecessary property request;
  property reads are now deferred to emitted children; and
- a malformed second function section leaked the already parsed first section;
  compatible-ID parsing is now atomic and clears the complete table on error.

The final eleven-scenario matrix covers valid discovery, non-support, malformed
string, malformed/truncated/oversized compatible descriptors, malformed and
unrelated properties, mixed compatible/sub-compatible IDs, unknown interfaces,
and a malformed later function. The separate formatter contract covers simple,
specific-plus-fallback, maximum-width, and malformed PnP IDs.

All request values in those tests are synthetic fixtures. The `0xa5` vendor
code and IO24-shaped MI05/MI06 model come from static inspection of the
installed vendor module, not from a physical-device descriptor read. CP31
therefore proves implementation behavior, not the io24's live response.

## Retained behavior

Both clean artifacts independently pass:

    WineUSB function-scope contract: pass
    WineUSB immediate-submit cleanup contract: pass
    WineUSB multi-interface handle contract: pass
    WineUSB pipe-observe plus bounded OS 1.0 reader contract: pass
    WineUSB captured-RANGE source/binary contract: pass
    wineusb USBDI V1 contract checks passed
    io24 usbmon class-IN evidence contract: pass
    io24 usbmon function topology contract: pass
    io24 WinUSB readiness contract: pass (known RED and synthetic structural GREEN)
    WineUSB Microsoft OS 1.0 behavior matrix: pass
    WineUSB Microsoft OS 1.0 PnP ID contract: pass

The retained wrappers were derived for CP31 because the old static guards
forbade every synchronous `libusb_control_transfer`. They now permit exactly
the one audited OS-reader call site while continuing to reject claim, detach,
alternate-setting, and configuration calls. Their fake backend explicitly
returns unsupported for discovery, proving predecessor behavior remains
fail-soft. The sealed predecessor scripts were not changed.

The frozen CP30 readiness analyzer remains a known-RED contract and is not a
forward CP31 oracle: it searches for one literal complete
`USB\MS_COMP_WINUSB` string, while CP31 deliberately constructs a generic
prefix plus validated descriptor value in separate code. Its synthetic
contract still passes, and the unchanged binding/API blockers it reports
remain true.

## Patch and independent clean builds

The production patch is:

    d63c0b6727c6fa313153738aa0a33bfd5f0cc799e90012d92257eebb0a0ed6d4
    re/wine-11.15-wineusb-ms-os-10-v1.patch

It changes six WineUSB files, applies to a sealed CP29 clone with fuzz zero,
and produces a patch-check tree identical to development across 12,447 regular
files. No `.orig` or `.rej` file exists.

Clean A and clean B began as independent empty roots, used the same virtual
source/tool paths and `SOURCE_DATE_EPOCH`, configured without Mingw/X/Freetype
and with the pinned libusb header/library, and built one job in unshared network
namespaces. The clean outputs match byte-for-byte:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys  2,560 bytes
    13669869e34219947862da6dc46e94fb3a3aaf03902b84cca86cbbee663bff94  wineusb.sys.so                  209,216 bytes
    228cf6b8006714887d6adeb0bc7dff040fba201f84cae1265a292cc115b517c9  wineusb.so                      147,056 bytes

The clean Unix build ID is `ade7b8b8a7a8f98c5646c75e5d649a2b5f9f6e06`.
Its dependencies remain `ntdll.so`, `libusb-1.0.so.0`, and `libc.so.6`.
The one new unique undefined libusb symbol is `libusb_control_transfer`.
There is no claim, detach, set-interface-alt, or set-configuration symbol.

The incremental development Unix artifact retained predecessor debug/build
metadata and therefore does not share the clean full-file hash. Its selected
runtime sections are byte-identical to clean A. The two clean outputs are the
reproducibility basis and the artifacts sealed here.

## Relation to interface 4, presets/effects, and firmware

Interface 4 is out of this change. CP29's function-scoping result remains
intact: MI00 excludes interface 4 and MI03 owns the CTRL/MIDI function view.
Physical interface-4 ownership under Linux is still unresolved and requires a
separate architecture decision before a live test.

Preset layouts, Voice FX/component-model findings, and earlier protocol facts
are unchanged. They sit above this transport layer. CP31 does not synchronize
Universal Control, expose a device interface, call a `WinUsb_*` operation, or
produce new preset/effect wire evidence.

Firmware is further narrowed, not implicated. MI06 remains descriptor-defined
DFU and the likely direct firmware route, but function binding and all user
APIs are still absent below any firmware investigation. No firmware image,
version, response, transition, or write was examined.

## Next coherent offline slice

Specify and implement a generic WinUSB function binding and device-interface
lifecycle, test-first. That slice must at least prove:

1. `USB\MS_COMP_WINUSB` binds only an eligible function child, without
   disturbing PaeDSPUSB MI00/MI03;
2. the parsed GUID becomes a stable registered device interface;
3. add/remove, failed-start, duplicate-GUID, and teardown paths are bounded;
4. the function binding owns no transfer behavior it has not implemented; and
5. discovery-nonsupporting devices retain existing class behavior.

Only after that layer is clean should the exact fourteen `WinUsb_*` operations
be implemented. A selector/staging contract comes after the complete stack,
not after CP31 or CP32.

## Stop boundary

Stop at CP31. The candidate is reproducible but not staged or selected. The
legacy UC capture remains fail-closed. Do not run it, retry CP24, or infer that
the new reader has observed a physical device.

No Wine process, prefix, USB node, device interface, driver/service load,
Universal Control, Voice FX, protected prefix, firmware image, live read,
claim/detach, alternate or configuration change, class OUT, mode transition,
or write was used. Builds and tests had networking unshared; read-only official
Microsoft documentation was consulted separately. Any staging or live
device/prefix action needs fresh explicit authorization and a full preflight.
CP24 remains consumed; reconnection is state evidence, not authorization.
Pause at 10% battery or lower.
