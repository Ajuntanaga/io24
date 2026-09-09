# io24 interface routing v1 manifest

## Current state

CP27 is complete offline.  The passive descriptor, PaeDSPUSB INF, CP24 runtime
trace, Wine source, and installed Universal Control hardware-access module now
support a function-level routing model for interfaces 0 through 6.

The immediate conclusion is that interface 4 is not a misplaced firmware
route.  It is the USB Audio Class 1 MIDIStreaming member of the interface-3/4
function, with bulk endpoints `0x02` and `0x82`.  PaeDSPUSB's MI03 installation
names two logical cables on that transport: CTRL and MIDI.

The CP24 duplicate interface-4 reads instead expose a Wine composite-device
scope defect: both MI00 and MI03 receive the full seven-interface configuration
and independently construct the same interface-4 pipes.  Wine creates one child
per raw interface, disregards the device's IAD and AudioControl collections,
shares the same physical libusb handle between those children, and does not pass
the child's interface index into URB submission.

Interfaces 5 and 6 are a separate boundary.  The passive descriptor identifies
interface 5 as a vendor-specific alternate-setting bulk pair and interface 6 as
DFU.  Static model data in the installed Universal Control module associates
both with `WINUSB`, while CP24 recorded no compatible driver for either Wine
child.  That is evidence of an independent application-discovery gap, not proof
that either interface was opened or that firmware is defective.

## Device-free analyzer

The topology analyzer and synthetic behavior contract are:

    tests/io24_usbmon_function_topology.py
    tests/io24_usbmon_function_topology_contract.py

The contract was developed test-first.  It first failed because the analyzer
did not exist, then exposed and prevented acceptance of a normal truncated
nine-byte configuration-header response as a complete descriptor.  It now
passes both the synthetic fixture and the sealed passive usbmon capture.

## Evidence roots

The complete CP27 report and hash chain are under `checkpoints/`.  It pins:

- the CP24 runtime trace and PaeDSPUSB inputs in the disposable Wine sandbox;
- the sealed passive usbmon capture;
- the exact Wine source inspected;
- the two topology scripts;
- the installed Universal Control hardware-access module inspected statically;
  and
- the CP24 and CP26 predecessor seals.

## Stop boundary

No device-visible operation, driver load, Wine process, service, USB node,
claim, detach, alternate-setting change, configuration change, OUT transfer,
firmware extraction, firmware write, Universal Control launch, Voice FX access,
network access, or protected-prefix access occurred at CP27.

The next safe work is still offline: specify and test USBCCGP-equivalent function
collections and partial configuration descriptors, then specify MI05/MI06 WinUSB
discovery separately.  A future interface-4 ownership experiment requires a new
explicit authorization because it may involve a claim/detach or an alternative
native bridge.  CP24's one-run live authorization remains consumed.
