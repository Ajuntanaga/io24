# Checkpoint 2 — reproducibility and contracts complete

Reached at `2026-08-19T19:18:06-07:00`. This is the last checkpoint before
staging the observation-v2 WineUSB overlay. The io24 remained disconnected,
the protected Wine prefix was unchanged, and neither build had access to USB,
udev, the network, or the host home directory.

## Independent reconstruction

A second Wine 11.15 source tree was extracted independently from the pinned
archive. USB-DI v1 and observation v2 again applied in that order with
`--fuzz=0`. Configure used the same virtual source/build paths, local package
inputs, flags, and resource limits as the first build. The second build log is
byte-identical to the first:

```text
a0f968537bfb0de9f3e823b38cca2fef7ef41d35160d87333091233891cb8e48  logs/build-wineusb.log
a0f968537bfb0de9f3e823b38cca2fef7ef41d35160d87333091233891cb8e48  logs/build-repro.log
```

## Reproducible artifacts

The two clean builds produced byte-identical copies of all three required
WineUSB artifacts:

```text
b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys (2,560 bytes)
e5d4d22ec48ac4321627b30fb014133193d7d77bff3f296e867c1cafe7e07520  x86_64-unix/wineusb.sys.so (190,464 bytes)
03a4c63ec669bf4f05789dfffd42c55e10d9e0ef990a1cc0622c1a0ab7812826  x86_64-unix/wineusb.so (88,584 bytes)
```

The two ELF build IDs also match across the independent builds:

```text
wineusb.sys.so  ec6ff07331507ab0cdb34f2134cc8e25f9e529d1
wineusb.so      72fc32d7eff9270708f09965cd07d0498018d77d
```

## USB-hidden contracts

Both the original and reconstructed source/build pairs passed:

- the compiled USB-DI v1 interface contract; and
- the observation-v2 source/binary contract.

The observation contract requires exactly one class-interface case and one
select-interface case, verifies their diagnostic markers in the compiled
builtin, and rejects submission calls, libusb calls, buffer copying, success
returns, or any departure from the common `STATUS_NOT_IMPLEMENTED` path.

The independent rerun occurred in Bubblewrap with an empty `/sys`, no
`/dev/bus/usb`, a private network namespace, and an empty `/home`. Evidence:

```text
095e885256246ce4b26b344ddd7ea4c75ec3d43012f99b39ff074b03977f8f2f  logs/source-contracts.log
44d6ab4d2bb184a30e26c0fdd22c07dc064758342e23263c1a95b506073f157d  logs/repro-contracts.log
```

Both logs end with:

```text
wineusb USBDI V1 contract checks passed
wineusb URB observation contract: pass
```

## Pause/resume boundary

This is a safe pause with no Wine process started and no overlay staged. The
next and final offline checkpoint may copy only these exact three artifacts
into the versioned observation-v2 directory, update the disposable harness to
pin their hashes, and run `driver-load` with USB hidden. Any hash mismatch,
harness syntax failure, unexpected USB visibility, driver-load regression, or
surviving Wine process is a hard pause. A live trace remains a separate gate
that requires the device and fresh explicit authorization.
