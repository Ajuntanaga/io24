# CP19 — full interface pipe-handle population, offline

Reached at 2026-08-22T10:05:51-07:00. Battery was charging at 39%, above the
mandatory 10% stop threshold. CP18's 26-entry seal first reverified. The same
io24 serial `AB7C22200355` was connected at sysfs `3-1`, re-enumerated as USB
device 4, but CP19 exposed no host USB node and launched no Wine service.

## Questions the new diagnostics answer

1. Did Wine validate the entire variable-length SELECT_CONFIGURATION request?
2. How many embedded interfaces and pipes were accepted and populated?
3. Did malformed input fail before any partial handle mutation?
4. Can a valid handle plus a null mapped buffer reach libusb?

Stable `IO24_HANDLE_POPULATION` and `IO24_PIPE_SAFETY` events answer those
questions without logging payload contents or adding USB actions.

## Test-first evidence

The first valid RED ran the real CP18 Unix library against a fake libusb SONAME
with hardware and networking hidden. A three-interface request put one pipe on
the second record and two on the third. CP18 processed only the empty first
record, leaving all later handles null. A second request demonstrated that a
malformed later record returned success after partially populating the first
record; its old handle also contained uninitialized high bytes.

After a two-pass parser made the behavioral assertions pass, the contract
remained RED only for missing lifecycle telemetry. Structured validation,
rejection, and population markers then made that phase GREEN.

A separate RED gave the real Unix library a valid bulk handle, length 512, and
a null transfer buffer. CP18 allocated and submitted a fake libusb transfer and
returned `STATUS_PENDING`. The final implementation instead records
`IO24_PIPE_SAFETY event=transfer_reject reason=null_buffer`, sets
`USBD_STATUS_INVALID_PARAMETER`, returns `STATUS_INVALID_PARAMETER`, and makes
zero libusb allocations or submissions. This guard leaves MDL compatibility
unimplemented while making a later handle-population diagnostic fail closed.

## Implementation

The patch is:

    f7fab610716f7a0cc2349cffe4f3a3edf45ada1a4527c451c7a0c71f718facde  re/wine-11.15-wineusb-multi-interface-handles-v1.patch

It layers on pipe-observe v3, applies with fuzz zero, changes only
`dlls/wineusb.sys/unixlib.c`, and reproduces the 12,445-file development source
exactly with no symlink or patch leftover. It makes the handle union
deterministic, validates every interface and declared pipe count in a first
pass, then populates every interface in a second pass. Malformed input is
atomic and fail closed. The patch adds no USB API.

## Build and regressions

The hardware-hidden, networkless incremental build emitted no warning in the
changed translation unit and produced:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    96f5a63a76d5f0e9a73425717d81e17d1fd6883c7a909508e703897a22fe4039  wineusb.so

The PE and builtin remain byte-identical to CP17. The new 102,600-byte Unix
library has build ID `be6c3c09298d93e060effd9433dfc5c955a54bfa` and the same
37 undefined dynamic symbols as CP18.

The new behavior/safety contract, pipe-observe runtime contract, exact
RANGE-v2 contract, USB-DI v1 contract, and CP15 analyzer contract all pass
inside containment with empty `/sys`, minimal `/dev`, and no network. An extra
legacy `wineusb_urb_observe_contract.sh` invocation retained in the evidence
fails its obsolete exact-count assertion that there is only one
`URB_FUNCTION_CLASS_INTERFACE` case; RANGE-v2 has intentionally had two since
CP14, so this is not a CP19 regression and was not part of CP16–CP18's declared
suite.

## Stop boundary

Stop at CP19. Nothing is staged and no live device action occurred. CP20 must
produce two independent clean, byte-identical builds from the pinned archive
and six-patch chain before any selector or device work. Firmware, full
Universal Control, Voice FX, interface claims/detaches, alternate-setting
changes, and the protected `.wine-io24` prefix remain untouched.
