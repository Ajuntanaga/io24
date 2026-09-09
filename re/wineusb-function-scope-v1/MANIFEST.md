# WineUSB composite-function scope v1

This lineage implements and independently reproduces the CP27 repair for
WineUSB composite-function leakage. It is offline evidence only: nothing here
is staged or selected for a device-facing run.

## Outcome

For the Revelator IO 24's one physical 392-byte configuration, the candidate
emits the Windows-style function children and partial configurations:

    MI_00  {0,1,2}  218 bytes  UAC2 audio
    MI_03  {3,4}    133 bytes  UAC1 AudioControl + MIDIStreaming CTRL/MIDI
    MI_05  {5}       41 bytes  vendor bulk
    MI_06  {6}       27 bytes  DFU runtime

The development and independent A/B artifacts match byte-for-byte. The core
offline result for interface 4 is therefore reproducible: MI00 rejects
interface 4 without populating a pipe, while MI03 retains interface 4 and gets
handles `0x202`/`0x282`.

## Checkpoints

- `checkpoints/CP28_FUNCTION_SCOPE_DEVELOPMENT.md` records the final RED,
  exact sealed-descriptor contract, implementation, development build, patch
  check, and retained regressions.
- `checkpoints/CP29_REPRODUCIBLE_BUILDS.md` records independent source
  preparation, clean A/B builds, artifact identity, independent contracts, and
  the stop boundary.

## Production patch

    3c44d15b710cc99c253590ace734c28ba5f2fb1f0b7a678dac195ea5184c4a7e  re/wine-11.15-wineusb-function-scope-v1.patch
    63f336e8143ce6eeacaf1157f4f497ec87cd2412f3e6c01b75cbd34313abbc24  dlls/wineusb.sys/unixlib.c after patch

The patch layers directly on the sealed CP26 source and applies with fuzz zero.
Source A, source B, development, and patch-check contain 12,445 matching
regular files and no symlink, `.orig`, or `.rej` file.

## Test inputs

    676eb98f8599aa31474750579e355a30fa866956998d6b1ffedaba15ed061253  tests/wineusb_function_scope_contract.c
    8c2331d92d0dca513b3f0899e8a1a67b0f49e9ec4bd370bd64eae218e77e363e  tests/wineusb_function_scope_contract.sh
    e88c3da355498a1722c2c218d7ce9ecc54b83b736c06f5e970cffb7043682e7a  tests/wineusb_function_scope_fake_libusb.c
    9d62066b42e2c0fb4a24de98fad7f93b4b980d8d640b3e0490608f32af0aa59f  tests/wineusb_pipe_observe_fake_libusb.c
    615fa0dd2a1df49215ffcd0fe2f4e14aa204d322052af229d951d962a9091161  tests/wineusb_class_interface_in_fake_libusb.c

The last two changes are fixture-only IAD API stubs. The literal contract input
matches the sealed 392-byte descriptor with SHA-256
`69131e7af6340cb70cdaaf134548e6f6ebab66c869a94b78073d69a9e3aaa51c`.

## Reproducible artifacts

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    88ab927a25c818e308589414c94c06bb41e9b3cba8aa364535e94f958b5b89c0  wineusb.so

All three hashes are identical in development, build A, and build B.

## Evidence logs

- `logs/contract-red-contained.log`: exact function-scope RED against CP26.
- `logs/literal-projection-audit.log`: independent comparison to the sealed
  physical configuration and four projected hashes.
- `logs/patch-check.log` and `logs/source-preparation.log`: fuzz-zero and source
  equivalence evidence.
- `logs/configure-{a,b}.log` and resource companions: independent clean
  configuration.
- `logs/build-{a,b}.log` and resource companions: bounded clean builds.
- `logs/artifact-comparison.log`: configuration and artifact byte identity,
  build ID, and symbol boundary.
- `logs/contracts-{a,b}.log` and resource companions: complete independent
  hardware-free matrices.

## Explicit exclusions

There was no staging, selector edit, real harness, Wine prefix, protected
`.wine-io24` access, USB node, device interface, driver/service load, network,
Universal Control, Voice FX, firmware extraction, live read, claim/detach,
alternate or configuration change, or OUT transfer.

Firmware is not the current demonstrated blocker. Remaining interface-4 work
is an explicit ownership architecture and a separately authorized live test;
remaining MI05/MI06 discovery is a different compatibility layer.
