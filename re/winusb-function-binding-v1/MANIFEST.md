# Generic WinUSB function binding v1

This lineage completes CP30's second missing WinUSB layer: generic function
binding and a bounded device-interface lifecycle using the Microsoft OS 1.0
metadata implemented at CP31. It is an offline development and reproducibility
checkpoint. Nothing is staged, selected, loaded, or exposed to the io24.

## Outcome

The sealed-CP31 function child can now pass its validated
`DeviceInterfaceGUID` through a private version-1 `IRP_MN_QUERY_INTERFACE`
contract. A new generic `winusb.sys` function driver:

1. binds only the exact compatible ID `USB\MS_COMP_WINUSB`;
2. validates and balances the metadata interface before creating an FDO;
3. registers a per-PDO device interface using the descriptor-provided GUID;
4. enables it only after successful lower-stack start;
5. preserves it across normal stop/restart;
6. makes bounded disable attempts during failed restart, surprise removal,
   and removal; and
7. rejects create, read, write, device-control, and internal-device-control
   requests because CP32 deliberately adds no I/O protocol.

The user-mode `dlls/winusb` tree is byte-identical to CP31. The fourteen
operations imported by `dspusbdevice.dll` remain 0/14 implemented. CP32
therefore proves discovery and PnP lifecycle, not usable MI05/MI06 transport.

## Test-first evidence

All three current contracts fail for the intended missing-feature reason
against the sealed CP31 source: the metadata interface header is absent, the
function driver is absent, and the exact INF/build publication is absent.

Against CP32, the metadata contract covers rejected query versions/sizes,
output nonmutation, exact WINUSB validation, removed children, malformed GUIDs,
and balanced references. The lifecycle contract compiles the actual
`dlls/winusb.sys/main.c` against a WDM-shaped fake boundary and covers add,
start, stop/restart, lower/enable/disable failures, duplicate registration,
same-GUID distinct PDOs, surprise removal, orderly removal, partial
construction cleanup, and explicit I/O rejection. The semantic INF contract
parses model, service, resource, and loader publication sections.

Two test-harness defects were corrected before accepting GREEN. The fake
kernel originally erased its global failure count during reset, which could
hide assertions; after preserving that count, a new wrong-interface-version
case exposed and drove strict consumer-side validation. The host test also
gained a realistic `RtlInitUnicodeString` stub and correct two-stack-location
IRP forwarding. The first real Wine link then exposed a cross-driver GUID
symbol reference that host inclusion could not reveal; the interface now uses
a shared initializer with module-local GUID objects.

Both independent clean sides pass the eleven-scenario CP31 OS-descriptor
matrix, PnP-ID formatting, function scope, immediate-submit cleanup,
multi-interface handles, pipe observation, captured RANGE, USBDI, retained
class-IN evidence, topology, the CP30 readiness self-contract, and all three
new CP32 contracts.

## Production patch

    7df4011ea20fa36bf80f4bc0ba409c9dca812b7d76b00f19f1709774eebf75bb
    re/wine-11.15-winusb-function-binding-v1.patch

The 665-line patch changes twelve production paths. It applies to the sealed
CP31 source with `--fuzz=0`; a reverse dry-run succeeds on the separately
patched CP32 tree. Development and patch-check match across 12,453 regular
files, with zero symlinks and no `.orig` or `.rej` leftovers.

## Reproducible artifacts

Independent clean build A and clean build B are byte-identical:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  wineusb.sys fake PE
    28617460085c0a2f8ae4782f3147bcad8a475a5b01daebba72b64380c118808e  wineusb.sys.so
    1edd11b0336a241c1ac8c667fb1d21db3bfac08b0ebdc8f672aa2931785490d9  wineusb.so
    b4e48cfca26754279ece31bfd285bfd8ce248acac7ab0967fadfc1b70d57720c  wineusb.res
    bacee6355cda7eb6bb19a7c8f73d2b8babfc4a22d19b47c31cffc1985f7427eb  winusb.sys fake PE
    dd1f3f199999546ff64ea7c1daa1306fba0a5958f7c1102df3b49ebfca20be46  winusb.sys.so
    d63357cb4ce680b4ed6500ad30c235065c5c8ef9fbed28cd54af4c8acaa5f23f  winusb.res

Both builds used identical virtual paths, pinned tool inputs,
`SOURCE_DATE_EPOCH=1787101002`, one-job/low-priority limits, empty sysfs,
minimal devices, read-only source/tools, and unshared networking.

## Evidence

- `checkpoints/CP32_WINUSB_FUNCTION_BINDING.md`: full result, interpretation,
  and stop boundary.
- `logs/cp31-seal-reverification.log`: complete 51-entry predecessor check.
- `logs/contract-red-contained.log`: current contracts against sealed CP31.
- `logs/contracts-build-a.log` and `contracts-build-b.log`: independent full
  predecessor-plus-CP32 matrices.
- `logs/clean-builds.log`: build recipe, containment, and output summary.
- `logs/artifact-comparison.log` and `config-log-comparison.log`: exact and
  normalized reproducibility evidence.
- `logs/patch-check.log`: fuzz-zero applicability and 12,453-file equality.
- `logs/boundary-audit.log`: no-transfer, no-user-API, dependency, and embedded
  INF proof.
- `logs/final-passive-state.log`: final cached host/device state only.

`checkpoints/CP32_SHA256SUMS` seals the report, design, handoff, protocol,
production patch/source, tests, logs, build configurations, clean outputs, and
predecessor checksum chain.

## Safety and remaining boundary

The new function driver has no Unix library, dynamic dependency, libusb
symbol, URB submission, WinUSB IOCTL, claim/detach, configuration,
alternate-setting, transfer, or firmware path. The unchanged WineUSB fake PE
still hashes exactly as CP31. No Wine process, prefix content, USB node, driver,
service, Universal Control, Voice FX, or firmware artifact was opened.

The next coherent offline slice is the exact fourteen imported `WinUsb_*`
operations, with synchronous/overlapped completion, cancellation, pipe policy,
descriptor, associated-interface, and alternate-setting contracts. Staging or
any live/prefix action remains separately authorized and comes only after the
complete stack and a hash-pinned selector are green. Interface-4 physical
ownership remains a separate architecture decision.
