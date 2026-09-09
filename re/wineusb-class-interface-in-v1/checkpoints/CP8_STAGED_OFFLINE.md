# CP8 — class-IN v1 staged and driver-loaded offline

Reached at `2026-08-19T23:15:00-07:00`. This is the required pause before any
device-connected class-IN observation.

## Staging result

The CP7 byte-identical triplet was copied into the versioned class-IN-v1
directory and reverified against clean build B:

```text
b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa  x86_64-unix/wineusb.sys.so
d5cbdf21f773488523c16bec90af8d83f9c7a9464afc39dceefdea16e399edbc  x86_64-unix/wineusb.so
```

The harness now pins and read-only mounts those three files for `driver-load`
and a separately authorized `live-read`. No observation-v2 selector remains;
syntax validation passed. Harness SHA-256:

```text
4706b84e5ea5daff2b274af28f6faf051fc66797cb5d569ecc9237ea4effaf7c  tests/uc_wine_sandbox.sh
```

The exact staged artifacts passed the fake-libusb class-IN behavioral and
source/binary contract plus USB-DI v1 with USB, sysfs, udev, host home, and
network hidden. The intentional immediate-submit-error fixture produced the
only error-level line. The unit exited 0 in 2.049 seconds, peaked at 21.2 MiB,
and used zero swap.

## Clone and driver-load result

The source observation sandbox was copied into a `.partial` path using idle
I/O and strict resource limits. Counts, path/size manifests, symlink targets,
key bytes, and the inherited CP4 checkpoint matched; key inodes were
independent. Only then was it promoted to:

```text
/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.class-in-v1-20260819
```

Exactly one USB-hidden driver-load ran in that clone:

```text
unit=io24-wine-driver-load-822720.service
invocation=0233fe7e28e94120ad439220eaff61fa
exit=0/SUCCESS
runtime=22.922s
cpu=4.692s
memory_peak=57.3M
swap=0B
start_status=0
query_status=0
```

Isolation, the exact registry-handle probe, corrected Windows 7 NT DDI path,
and SSE2 path passed. The pinned WineUSB builtin loaded. PaeDSPUSB reported
`RUNNING` and cleanup unloaded it. With no USB PDO, there were zero class-IN,
class-OUT, or observation records. This is offline driver compatibility
evidence only, not an io24 response or UCNET synchronization result.

## Sealed evidence and postflight

The complete relative checksum manifest verifies under:

```text
/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.class-in-v1-20260819/out/checkpoints/driver-load-class-in-v1-20260819T231029PDT/
```

`SHA256SUMS` SHA-256:

```text
4e9e14779bf20a8a8f76a00a4ebb261268764624b6f8a135198832275e6270c1
```

Postflight found no io24, no candidate Wine/UC/Xvfb process, and no surviving
transient unit. The protected prefix and source observation sandbox retained
their prior evidence. The clone registry changed only as expected during its
disposable driver run; the inherited live capture stayed at SHA-256
`f7ae3a97696dfd1ceff7b511c307d054422250e481deceb7b180167538762a67`.

## Required pause

Stop here. The previous live authorization remains consumed. Do not start a
class-IN live-read merely because the device is connected. A future run needs
a fresh preflight and explicit one-run authorization. No class OUT,
select-interface/alternate-setting implementation, interface claim/detach,
timeout change, full Universal Control, Voice FX, or protected-prefix access
is authorized.
