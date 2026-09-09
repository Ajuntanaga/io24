# CP27 — interface-4 routing and firmware-scope analysis

Reached offline on 2026-08-22.  CP24's live authorization was already consumed
and was not reused.  This checkpoint made no device-visible call and did not
open a Wine prefix or extract a firmware image.

## Result

Interface 4 is the correct low-level transport for the Revelator IO 24 CTRL and
MIDI cables.  It is not a firmware interface, and redirecting PaeDSPUSB from
interface 4 to interface 5 would be wrong.

The duplicate interface-4 activity in CP24 is instead a composite-enumeration
scope failure.  PaeDSPUSB is installed once for MI00 and once for MI03.  Each
driver instance receives a full seven-interface configuration, finds interface
4, builds pipe handles `0x202` and `0x282`, and starts four reads on endpoint
`0x82`.  MI03 is the intended MIDI/CTRL instance; MI00 should not have been
shown interface 4 as part of its function descriptor.

This narrows firmware investigation without making firmware the current root
cause.  Interface 6 is the descriptor-defined DFU function.  Interface 5 is a
separate vendor-specific bulk function expected by the installed Universal
Control model.  Wine failed to bind either MI05 or MI06, so application/DFU
discovery remains a separate host-side gap after the interface-4 path.

## Passive descriptor topology

The new analyzer ran against the already sealed, passive usbmon capture:

    python3 tests/io24_usbmon_function_topology.py \
      --require-io24-topology \
      re/io24-passive-usbmon/passive-usbmon-range-v1-20260821T023641-0700/control-urbs.pcap

The capture hash is
`194a4b2619e0bddcdeef2108b0969cf13c029b3d2516309123c6567437b2922d`.
It contains one unique complete 392-byte configuration descriptor with SHA-256
`69131e7af6340cb70cdaaf134548e6f6ebab66c869a94b78073d69a9e3aaa51c`.
The analyzer reconstructs:

| Function root | Membership | Direct descriptor classification |
| --- | --- | --- |
| 0 | 0, 1, 2 | IAD-grouped UAC2 audio function |
| 3 | 3, 4 | UAC1 AudioControl collection; interface 4 is MIDIStreaming |
| 5 | 5 | vendor-specific; alt 0 empty, alt 1 endpoints `0x81`/`0x01` |
| 6 | 6 | DFU class `0xfe`, subclass 1, protocol 1; alt 0 has no endpoint |

Interface 3's UAC1 AudioControl header directly declares interface 4 as its one
streaming subordinate.  Interface 4 alt 0 directly declares class 1, subclass
3 and the bulk endpoint pair `0x02`/`0x82`.

The synthetic topology contract first failed because the analyzer did not yet
exist.  After the initial implementation, an added normal nine-byte
configuration-header case produced a second RED by being treated as a complete
configuration.  Requiring `captured_length >= wTotalLength` made that case GREEN
without weakening the full-descriptor checks.  Both commands now pass:

    python3 tests/io24_usbmon_function_topology_contract.py
    python3 tests/io24_usbmon_function_topology.py --require-io24-topology <sealed-pcap>

## PaeDSPUSB installation meaning

The decoded INF has SHA-256
`3473acc6dc107c93a7aa91bc012f3a2dbec5ea219e263c6ad5edebc13d6adf66`.
Its exact PID `0422` bindings are:

- `USB\VID_194F&PID_0422&MI_00` -> `_Install_11`, display name
  `Revelator IO 24`;
- `USB\VID_194F&PID_0422&MI_03` -> `_Install_13`, display name
  `Revelator IO 24 MIDI`.

The MI03 registration uses interface GUID
`{516B7C79-85AF-4B39-A2DD-BC5F1B78D909}` and names four logical endpoints:

    Revelator IO 24 CTRL In
    Revelator IO 24 MIDI In
    Revelator IO 24 CTRL Out
    Revelator IO 24 MIDI Out

Those names, together with the descriptor-defined MIDIStreaming pair, directly
place interface 4 in the CTRL/MIDI path.  They do not identify interface 4 as a
firmware transport.

## CP24 runtime separation

The runtime log has SHA-256
`ddc74cea184a22990939cf8bab7b846161847b784882e1b224b650f8fd83e124`.
Its two PaeDSPUSB lifecycles are separable by device path and line number:

- MI00 calls AddDevice at line 2238, registers the MI00 path through line 2442,
  receives all seven interfaces at lines 2694-2718, and submits four endpoint
  `0x82` reads at lines 3973-4033.
- MI03 calls AddDevice at line 5499, registers the MI03 path at lines 5653-5683,
  receives all seven interfaces at lines 5935-5959, and submits four endpoint
  `0x82` reads at lines 7102-7162.

Both configuration cycles report `scope=all_interfaces`, seven interfaces, two
pipes, and interface-4 handles `0x202`/`0x282`.  All eight reads failed before
bus submission because the physical interface remained owned by
`snd-usb-audio`.  CP26 repairs the separate immediate-submit lifetime defect,
but it does not create function isolation or solve interface ownership.

The same trace directly records:

    line 7878  no compatible driver for ...&MI_05...
    line 8168  no compatible driver for ...&MI_06...

No subsequent function driver is registered for either child.  This does not
prove the Universal Control plugin tried to open either one; it proves only that
Wine did not realize those functions as usable driver interfaces in this run.

## Wine composite-device cause

The inspected `unixlib.c` has SHA-256
`f08d7c20e084ecfc736818aa7a38bd72b5964652802590cde4ae419ef826b0eb`.
Its implementation states and demonstrates the mismatch:

- lines 172-180 explain that Wine creates separate devices itself and retain a
  FIXME for IAD cases where USBCCGP would not create raw-interface children;
- lines 186-213 create one child per raw interface;
- lines 199-202 give each child the same physical libusb handle; and
- lines 509-515 execute every URB through that shared physical handle.

The corresponding `wineusb.c` has SHA-256
`ab94b70ceae65eee5019e053c9bf7ec3ce01f20af2a3e824282fbbc3d786785c`.
It stores each child's interface index at lines 183-223, but the URB dispatch at
lines 681-727 passes only the Unix device and IRP.  The child's interface index
therefore does not scope GET_DESCRIPTOR, SELECT_CONFIGURATION, pipe population,
or submission.

Microsoft's USB composite-driver documentation says that a function driver
receives a partial configuration descriptor containing only the interfaces and
descriptors for its function.  It also describes USBCCGP as the parent that
creates function PDOs and multiplexes requests:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/how-to-select-a-configuration-for-a-usb-device
- https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/usb-common-class-generic-parent-driver

The correct repair shape is consequently broader than changing an interface
number: model the device's function collections, expose a function-scoped
configuration descriptor to each child, and constrain pipe/claim ownership to
that collection.

For this device, the minimum function map is `{0,1,2}`, `{3,4}`, `{5}`, `{6}`.
That would keep interface 4 visible to MI03 while removing it from MI00.

## Interfaces 5 and 6: direct facts versus inference

The installed `dspusbdevice.dll` was inspected statically and hashes to
`567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`.
It imports `WinUsb_Initialize`, `WinUsb_GetAssociatedInterface`,
`WinUsb_ControlTransfer`, `WinUsb_ReadPipe`, and `WinUsb_WritePipe`.  Its model
record beginning near file offset `0x27e110` names VID/PID `194f:0422`, encodes
the same seven-interface functional topology, and has records near `0x27e300`
that associate interfaces 5 and 6 with `WINUSB`.  Its strings also contain
`BulkSubdevice`, `FindBulkEndpoints`, the IO 24 CTRL name, and DFU/firmware
routines.

Direct conclusions:

- interface 5 is the descriptor's vendor-specific bulk function;
- interface 6 is the descriptor's DFU function;
- the installed module contains an IO 24 model associating MI05 and MI06 with
  WinUSB; and
- Wine left both children without compatible drivers in CP24.

Bounded inference:

- MI05 is likely the application's vendor bulk command/data channel; and
- MI06 is likely the application's DFU/firmware discovery channel.

Not established:

- that either interface was opened in CP24;
- that MI05 is required before the first UCNET `DA`;
- that device firmware is old, corrupt, or incompatible;
- that any firmware image has been located or parsed; or
- that a firmware transition/write is needed.

## Remaining process

The remaining interface-4 work should proceed in this order:

1. Add a device-free contract for the four function collections and the exact
   partial descriptors expected by MI00, MI03, MI05, and MI06.
2. Implement function-scoped child creation and descriptor/pipe projection in
   WineUSB.  Prove MI00 cannot see `0x02`/`0x82` while MI03 sees only the
   interface-3/4 collection and creates the pair once.
3. Independently specify how MI05 and MI06 acquire their expected WinUSB device
   interfaces.  Keep this separate from PaeDSPUSB's interface-4 repair.
4. Reproduce both changes in independent clean builds and add a real-harness
   selector RED/GREEN before staging anything.
5. Choose the interface-4 ownership architecture.  A libusb claim/detach is a
   device-visible, audio-affecting action and needs explicit authorization.  A
   native ALSA/MIDI bridge would avoid detachment but is a different and larger
   compatibility design.
6. Only after the host paths are isolated and discoverable should a newly
   authorized, single-run live diagnostic test for UCNET `DA` and
   `synchronize.json`.

Firmware work can continue offline in parallel only as inventory and format
analysis of installed artifacts.  Interface 6/DFU is the primary scope;
interface 5 may participate in application-mode commands or reboot transition,
but current evidence does not justify a device read, mode switch, or write.

## Boundary

Stop at CP27.  CP26 remains reproducible but unstaged.  No retry of CP24 is
authorized.  Any driver load, device-visible read, interface claim or detach,
alternate-setting or configuration change, class/vendor OUT, firmware access
to the device, firmware transition/write, full Universal Control launch, Voice
FX access, or protected-prefix access requires new explicit authorization and a
fresh full preflight.  Reconnection is not authorization.
