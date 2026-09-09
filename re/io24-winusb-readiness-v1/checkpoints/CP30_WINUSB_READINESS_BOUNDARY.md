# CP30 — MI05/MI06 WinUSB readiness boundary

Reached offline on 2026-08-22. Battery was 95%. CP24's consumed authorization
was not reused. No Wine process, prefix, USB node, device interface, service,
Universal Control process, or firmware artifact was opened.

## Result

CP29 correctly creates function-scoped MI05 and MI06 children, but that is only
the bus-enumeration prerequisite. The pinned Wine stack lacks all three layers
required to make either child usable through WinUSB:

| Layer | Required behavior | Pinned Wine 11.15 |
| --- | --- | --- |
| Discovery | translate Microsoft OS 1.0 descriptors into `USB\MS_COMP_WINUSB` and extended properties | missing |
| Function binding | match the compatible ID, load a generic WinUSB function driver, register device interfaces | missing |
| User API | implement the fourteen `WinUsb_*` calls imported by the vendor module | 0/14 implemented |

This corrects the old project claim that Wine implements WinUSB over libusb.
Wine's `wineusb.sys` is the USB bus enumerator used by the PaeDSPUSB path; it is
not Microsoft's generic WinUSB function driver, and the similarly named
`winusb.dll` remains a stub surface.

## Vendor-module expectation

The analyzer reads the PE import table of the exact installed module:

    /home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll
    SHA-256 567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b

It confirms exactly fourteen imports from `WINUSB.DLL`:

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

The module contains one VID/PID `194f:0422` model at file offset `0x27e10c`.
Within the bounded model window:

- `0x27e300` records interface 5 plus `WINUSB`;
- `0x27e318` records interface 6 plus `WINUSB`;
- `0x27e810` contains the `DeviceInterfaceGUID` property name; and
- `0x27e851` contains the `MSFT100` marker followed by vendor code `0xa5`.

These are direct facts about the installed host module's model. They establish
the discovery contract it expects, not a live descriptor response from the
physical device.

## Windows contract

Microsoft documents that compatible firmware reports `WINUSB` through
Microsoft OS feature descriptors. Windows then creates the additional
compatible ID `USB\MS_COMP_WINUSB`, which the in-box `winusb.inf` matches.
The OS 1.0 sequence begins with string index `0xee`; the returned vendor code
is used for a vendor request with `wIndex=4` to obtain extended compatible IDs.
Extended properties can register `DeviceInterfaceGUIDs`.

Primary documentation:

- <https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/automatic-installation-of-winusb>
- <https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/microsoft-os-1-0-descriptors-specification>
- <https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-xusbi/601a3107-6583-4e80-867e-118829cb573e>

## Retained CP24 outcome

The postflight registry hashes to
`38b006a496f0d5d9e3183016d9716c163bcc7e502b69807c8a8bb5a0350aa7ea`.
Across all three retained instances for each function:

- MI05 has only `USB\Class_ff&SubClass_00&Prot_00`, its subclass reduction,
  and `USB\Class_ff`;
- MI06 has only `USB\Class_fe&SubClass_01&Prot_01`, its subclass reduction,
  and `USB\Class_fe`; and
- neither has `USB\MS_COMP_WINUSB`, a driver, or a service.

The setup trace hashes to
`ddc74cea184a22990939cf8bab7b846161847b784882e1b224b650f8fd83e124`.
It examines `C:\windows\inf\wineusb.inf`, whose only hardware match is
`root\wineusb`, then reports no compatible driver for MI05 at line 7878 and
MI06 at line 8168.

## Pinned and current Wine source

In the CP29 source:

- `wineusb.c:get_compatible_ids()` generates only USB class IDs;
- `wineusb.inf` installs only the root Wine USB bus;
- `winusb.spec` declares 21 of 22 exports as stubs; and
- `WinUsb_Free()` is an explicit semantic stub that logs `FIXME` and returns
  success without managing a handle.

Thirteen of the vendor module's fourteen imports are declared spec stubs. The
remaining import is `WinUsb_Free`, so all fourteen required calls are
semantically unimplemented.

This is not a pinned-version-only issue. On 2026-08-22, official Wine master
resolved to release 11.16 commit
`8da89f8493b21ebfbe344a54dbef0cde23c7ea59`; its WinUSB spec, API source,
bus compatible-ID function, and INF retain the same boundary. Official commit
`1df5309a822ac33daabda5654a3eaf93b88dffea` is explicitly titled
`winusb: Add WinUsb_Free stub.`

Primary Wine sources:

- <https://gitlab.winehq.org/wine/wine/-/commit/8da89f8493b21ebfbe344a54dbef0cde23c7ea59>
- <https://gitlab.winehq.org/wine/wine/-/blob/8da89f8493b21ebfbe344a54dbef0cde23c7ea59/dlls/winusb/winusb.spec>
- <https://gitlab.winehq.org/wine/wine/-/blob/8da89f8493b21ebfbe344a54dbef0cde23c7ea59/dlls/winusb/main.c>
- <https://gitlab.winehq.org/wine/wine/-/commit/1df5309a822ac33daabda5654a3eaf93b88dffea>

## Contract

The self-contained contract passes:

    python3 tests/io24_winusb_readiness_contract.py
    io24 WinUSB readiness contract: pass (known RED and synthetic structural GREEN)

The exact retained-artifact boundary also passes:

    python3 tests/io24_winusb_readiness.py --require-known-boundary ...

Its result is:

    vendor imports: 14/14
    io24 MI05/MI06 WINUSB model: present
    compatible-ID translation: missing
    generic WinUSB INF match: missing
    required WinUSB APIs implemented: 0/14
    known CP30 boundary: confirmed
    structural readiness: NOT READY
    stageable from this audit alone: NO

The independent `--require-structural-ready` invocation exits 1 with exactly
three blockers. The synthetic contract then supplies the three necessary
source surfaces and proves a structural GREEN. It also asserts
`behavioral_implementation_proven=false` and `stageable=false`; actual
implementation behavior needs separate contracts and cannot be inferred from
non-stub declarations or an INF match.

The complete CP29 hardware-free regression matrix was rerun in an unshared
network namespace with a read-only repository, minimal devices, absent sysfs,
and a private temporary home. Function scope, immediate cleanup,
multi-interface handles, pipe observation, captured RANGE, USBDI, retained
class-IN evidence, passive topology, and the new readiness contract all exited
zero. `tests/uc_wine_capture.sh uc` now exits 1 before any process or filesystem
mutation and names the CP30 boundary; a future behavioral selector must remove
that guard deliberately.

## Meaning for presets, effects, and firmware

This is below the preset/effect model rather than a contradiction of it.
Installed component-model facts, previous device protocol results, preset
layouts, and Voice FX findings remain intact. What is blocked is new Universal
Control synchronization and wire evidence: its hardware module cannot
enumerate or operate the expected WinUSB interfaces under current Wine.

MI05 remains the likely application bulk command/data path, while MI06 is the
descriptor-defined DFU function and likely firmware discovery path. Those are
bounded inferences from static model and topology evidence; neither was opened
in CP24. The result narrows firmware further: host compatibility has three
unimplemented layers before device firmware can be evaluated as a cause.

## Coherent implementation sequence

1. Add fake-libusb behavior contracts for OS string index `0xee`, the returned
   vendor code, extended compatible IDs (`wIndex=4`), malformed descriptors,
   non-supporting devices, and extended properties.
2. Implement generic WinUSB function binding and device-interface lifecycle,
   without changing PaeDSPUSB's MI00/MI03 path.
3. Implement the exact fourteen imported operations, including synchronous and
   overlapped transfer completion, cancellation, pipe policy, descriptors,
   alternate settings, and associated interfaces.
4. Run the complete retained contract matrix and two independent clean builds
   before any selector or staging work.
5. Separately choose interface-4 ownership. Discovery does not solve the CP24
   `snd-usb-audio` ownership boundary.

Adding only `USB\MS_COMP_WINUSB` is not a usable or stageable fix: Wine would
still lack both the function binding and API implementation.

## Stop boundary

Stop at CP30. CP29 remains reproducible but unstaged. Do not run the legacy UC
capture, retry CP24, or infer a firmware defect. Any staging needs a future
hash-pinned selector contract after the complete stack is GREEN. Any device or
prefix action requires a fresh explicit authorization and full preflight.

No driver load, device read, claim/detach, alternate or configuration change,
control transfer, OUT transfer, full Universal Control, Voice FX, firmware
transition/write, or protected-prefix access is authorized by this checkpoint.
