# WineUSB Microsoft OS 1.0 discovery v1

This lineage implements CP30's first missing WinUSB layer: bounded Microsoft
OS 1.0 descriptor discovery and compatible-ID translation in WineUSB. It is an
offline development and reproducibility checkpoint only. Nothing is staged,
selected, or exposed to a physical device.

## Outcome

WineUSB can now, against a behaviorally exact fake libusb backend:

1. request and validate the fixed 18-byte OS string at index `0xee`;
2. use its vendor code to retrieve and atomically parse the extended
   compatible-ID descriptor at `wIndex=4`;
3. retrieve a bounded extended-properties descriptor at `wIndex=5` only for
   an actually emitted function child;
4. carry a valid `DeviceInterfaceGUID` value with that child; and
5. generate Windows-style `USB\MS_COMP_*` and optional `MS_SUBCOMP_*` PnP IDs
   before the existing USB class-ID fallbacks.

This completes the discovery translator, not the WinUSB stack. Generic WinUSB
function binding/device-interface registration remains missing, and Wine's
fourteen operations imported by the vendor module remain 0/14 implemented.
The parsed GUID is preserved for the next layer but is not registered in CP31.

## Test-first evidence

The unchanged CP29 binary made zero OS-descriptor requests and failed the valid
fixture with seven intended assertions. Two further RED/GREEN cases caught an
unnecessary property request for a descriptor-only unknown interface and a
partial-compatible-ID leak when a later function section was malformed.

The final matrix covers eleven scenarios:

    valid
    no_string
    bad_string
    malformed_compat
    truncated_compat
    oversize_compat
    malformed_properties
    unrelated_property
    mixed_ids
    unknown_interface
    malformed_second_function

The fake backend asserts exact request type, request, value, index, length,
order, and timeout. The parser caps every allocated descriptor at 4096 bytes,
validates reserved fields and section arithmetic, rejects malformed ID padding
and duplicate interfaces, and validates a canonical UTF-16LE GUID. A malformed
compatible-ID descriptor is discarded atomically. An absent or malformed
properties descriptor leaves a valid compatible ID usable and its GUID empty.

The fixture's vendor code `0xa5`, interface IDs, and GUIDs are synthetic values
informed by the installed vendor-module model. They are not a live response
from the io24.

## Production patch

    d63c0b6727c6fa313153738aa0a33bfd5f0cc799e90012d92257eebb0a0ed6d4
    re/wine-11.15-wineusb-ms-os-10-v1.patch

The 590-line, six-file patch layers on the sealed CP29 source with fuzz zero.
Development and separately patched sources match across all 12,447 regular
files, with no `.orig` or `.rej` files.

## Reproducible artifacts

Independent clean build A and clean build B are byte-identical:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys  2,560 bytes
    13669869e34219947862da6dc46e94fb3a3aaf03902b84cca86cbbee663bff94  wineusb.sys.so                  209,216 bytes
    228cf6b8006714887d6adeb0bc7dff040fba201f84cae1265a292cc115b517c9  wineusb.so                      147,056 bytes

Both clean sides pass the complete retained and CP31 matrices in networkless,
USB-hidden, read-only containment. The incremental development Unix artifact
retained predecessor debug/build metadata and therefore has a different full
hash; its selected runtime sections are byte-identical to clean A. CP31 seals
the two clean outputs.

## Evidence

- `checkpoints/CP31_MS_OS_10_DISCOVERY.md`: full result, interpretation, and
  stop boundary.
- `logs/contract-red-contained.log`: verbatim unchanged-CP29 RED.
- `logs/bounds-red-green.log`: all three test-first boundaries.
- `logs/contract-green-contained.log`: CP31 behavior matrix and PnP IDs.
- `logs/retained-contracts.log`: independent retained matrices.
- `logs/clean-builds.log`: clean preparation, containment corrections, and
  byte identity.
- `logs/artifact-audit.log`: dependency, symbol, source, and patch boundary.
- `logs/debug-invocation-boundary.log`: the diagnosed `WINEDEBUG=-all`
  dlopen-harness artifact.
- `logs/patch-check.log`: fuzz-zero patch and source equivalence.

`checkpoints/CP31_SHA256SUMS` seals 51 documentation, production-source,
patch-check, test, evidence, configuration, predecessor-chain, and clean-build
artifact entries.

## Safety and remaining boundary

The only new actionable libusb dependency is `libusb_control_transfer`, used
for bounded descriptor-IN discovery. There is no claim, detach, alternate-
setting change, configuration change, class OUT, or protected-prefix action.
That descriptor reader would become device-visible if staged, so the candidate
is deliberately not stageable while function binding and user APIs are absent.

Preset, effect, component-model, and prior protocol evidence is unchanged.
CP31 enables no synchronization and yields no new preset/effect wire data.
Firmware remains narrowed rather than implicated: MI06 is still only the
descriptor-defined DFU function and likely direct firmware route, while two
WinUSB host layers remain unimplemented.

The next coherent offline slice is a generic WinUSB function binding and
device-interface lifecycle contract. The legacy real capture remains
fail-closed, and interface-4 physical ownership remains a separate decision.
