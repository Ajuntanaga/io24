# CP28 — WineUSB function scope developed offline

Reached offline on 2026-08-22. CP24's one bounded live authorization was
already consumed and was not reused. This checkpoint did not open a Wine
prefix, USB node, device interface, Universal Control, Voice FX, or firmware
image.

## Result

WineUSB now models the IO24 composite device as four function children instead
of seven raw-interface children:

| Child ID | Function membership | Partial configuration length |
| --- | --- | ---: |
| `MI_00` | `{0,1,2}` UAC2 audio | 218 bytes |
| `MI_03` | `{3,4}` UAC1 AudioControl plus MIDIStreaming | 133 bytes |
| `MI_05` | `{5}` vendor bulk | 41 bytes |
| `MI_06` | `{6}` DFU runtime | 27 bytes |

The base physical device event remains. Raw children `MI_01`, `MI_02`, and
`MI_04` are no longer emitted when a one-configuration composite device has a
valid function grouping.

This fixes CP27's interface-4 scope defect in the offline implementation:
`MI_00` cannot select interface 4, while `MI_03` can select interfaces 3 and 4
and receives the existing bulk handles `0x202` and `0x282`. Interface 4 remains
the CTRL/MIDI transport; it was not redirected to interface 5.

## Test-first evidence

The device-free contract is:

    tests/wineusb_function_scope_contract.c
    tests/wineusb_function_scope_fake_libusb.c
    tests/wineusb_function_scope_contract.sh

It loads the real built WineUSB Unix call table against a synthetic libusb
device and drives actual add-device events, asynchronous configuration-
descriptor completions, and `SELECT_CONFIGURATION` URBs.

The final exact-device contract first ran against the sealed CP26 artifact. It
exited 1 with 24 checks failing for the intended reasons:

- raw children 1 and 2 appeared where function roots 3 and 5 were expected;
- each physical descriptor request retained the caller's partial length rather
  than requesting the complete 392-byte physical configuration;
- every returned descriptor remained physical-device-wide; and
- the `MI_00` child accepted interface 4 and populated handle `0x282`.

That RED is retained in `../logs/contract-red-contained.log`.

The candidate passes the same contract. For each function it handles both the
normal nine-byte configuration-header probe and the subsequent full partial-
descriptor request. Every underlying read-only descriptor request asks for the
complete 392-byte physical configuration, then returns only the caller's
function projection.

## Exact sealed-descriptor projection

The contract's literal physical configuration is byte-identical to the already
sealed passive usbmon descriptor:

    69131e7af6340cb70cdaaf134548e6f6ebab66c869a94b78073d69a9e3aaa51c  392 bytes

An independent parser in `../logs/literal-projection-audit.log` reconstructs
the projections and proves that the contract literals match:

    root 0  218 bytes  21155db5bc22bc720e687bfe5871a7ef01634093b9fd9a45b7a6c6396dc3f9f4
    root 3  133 bytes  05f51f0907afc7a64f87d32bb93af967890245a35068d1323f685c6edc582b75
    root 5   41 bytes  0da5e0dee72833200b2b6c308989b54e378ab33497a02102c8ef3cb07d34a591
    root 6   27 bytes  d035f125d75008c43bee2d0742b5fb5ff76c5fb33a4bed1f7371bb32b3e3a556

The projection retains all alternate settings, endpoints, class-specific
interface descriptors, class-specific endpoint descriptors, the relevant IAD,
and the DFU functional descriptor. It rewrites only configuration
`wTotalLength` and `bNumInterfaces`.

## Implementation boundary

The change is confined to `dlls/wineusb.sys/unixlib.c` and layers on the sealed
CP26 immediate-submit cleanup source.

For single-configuration composite devices, it:

1. obtains active IADs from the pinned libusb 1.0.29 interface;
2. recognizes legacy UAC1 AudioControl header collections such as `{3,4}`;
3. emits only function-root child events while preserving root interface IDs;
4. snapshots each child's membership and physical configuration length;
5. projects completed configuration descriptors to that membership; and
6. rejects an out-of-function interface in `SELECT_CONFIGURATION` before any
   pipe handle is changed.

When the device has multiple configurations or no valid grouping is found,
the prior raw-interface behavior remains. Descriptor completion uses a copied
membership snapshot rather than a live child pointer, avoiding a new
completion-time device-lifetime dependency.

The implementation adds no libusb claim, detach, release, alternate-setting,
configuration-setting, control-write, bulk-write, or device-open path. The two
new undefined symbols are exactly:

    libusb_get_active_interface_association_descriptors
    libusb_free_interface_association_descriptors

Both exist in the pinned build header and host runtime library. The older
device-free fake libusb fixtures gained no-device/not-found stubs for those two
read-only APIs; their prior behavior is unchanged.

## Development build and patch check

The changed translation unit rebuilt in hardware-hidden containment with no
WineUSB compiler warning. The development artifacts are:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    88ab927a25c818e308589414c94c06bb41e9b3cba8aa364535e94f958b5b89c0  wineusb.so

The patch is `../../wine-11.15-wineusb-function-scope-v1.patch`, SHA-256
`3c44d15b710cc99c253590ace734c28ba5f2fb1f0b7a678dac195ea5184c4a7e`.
It applies to the CP26 source with fuzz zero. The resulting independent
12,445-file patch-check tree matches the development source, contains no
symlink, and contains no `.orig` or `.rej` file.

## Retained regression boundary

The function-scope contract and CP26's six retained hardware-free contracts
pass together:

- immediate-submit allocation cleanup;
- multi-interface handle population and null-buffer safety;
- pipe routing and observation;
- exact captured Clock Source RANGE behavior;
- WineUSB USB-DI v1; and
- the CP15 class-IN evidence analyzer.

The CP27 synthetic topology contract and the analyzer applied to the sealed
passive capture also pass. The preserved class-interface-IN v1 passthrough and
older URB-observe source-count tests are not retained regressions: both were
superseded before CP26 by exact RANGE-v2 and the later two-case observation
source.

## Stop boundary at CP28

CP28 is development evidence, not staged evidence. No selector, staged triplet,
Wine prefix, service, driver, or hardware state was changed. CP29 independently
reproduces the artifacts; it does not broaden this boundary.
