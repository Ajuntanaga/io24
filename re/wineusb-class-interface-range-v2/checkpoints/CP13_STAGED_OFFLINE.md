# CP13 — RANGE v2 staged and driver-loaded offline

Reached at 2026-08-21T03:37:06-07:00. This is the required hard pause after
offline staging and before any device-connected live-read.

## Staging and selector result

CP12 was frozen before advancing the active files. Its former manifest and
harness are preserved byte-for-byte as CP12_MANIFEST_SNAPSHOT.md and
CP12_HARNESS_SNAPSHOT.sh, and the CP12 checksum seal verifies against them.

The exact CP12 byte-reproduced triplet was atomically staged:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa  x86_64-unix/wineusb.sys.so
    9518320f495ace5cabc27ef4e740f182b3840700fba3e9371b36b7e12538dea2  x86_64-unix/wineusb.so

A real-harness selector contract was written before the selector change. It
replaced systemd-run only after the outer harness completed all validation,
then inspected the exact command that would be launched. RED exited 1 because
WINEDLLPATH still selected class-IN v1. After the minimal selector change,
GREEN proved that driver-load mounts only the versioned RANGE-v2 root and
hash-pinned files. Reverting the selector path or hash would fail this
contract.

The staged files passed the compiled exact-RANGE fake-libusb behavior and
source/binary contracts plus USB-DI v1 with hardware, host home, sysfs, and
networking hidden. They also compare byte-for-byte to clean build B.

Current harness and selector-contract hashes are:

    7a6beb27534114bdc125bc498d5a13fba13b6609a0545dc073081ef013da15e1  tests/uc_wine_sandbox.sh
    1aa8b3dae12197e45e3ed870d2c04ff5b6a4843f4dcc9c309ed3e7c7e80f1012  tests/uc_wine_sandbox_range_v2_selector_contract.sh

## Fresh disposable clone

The unchanged observation-v2 baseline was copied under a bounded transient
user service into a partial path, completely verified, and only then promoted
to:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.range-v2-20260821

The clone has 5,097 regular files, 41 symlinks, 708 directories, and zero
special files. Full content plus path/type/mode/owner/group/size/mtime/symlink
metadata matched the source. The copied system.reg had independent storage.

Clone unit io24-sandbox-clone-range-v2-20260821.service, invocation
c03510a6bb544119807ec00b295309bd, completed successfully in 21.301 seconds,
used 2.668 CPU seconds, peaked at 384.5 MiB, and used zero swap.

## One USB-hidden driver-load

Exactly one driver-load was launched:

    unit=io24-wine-driver-load-865198.service
    invocation=2ac650364d6b47d5800532bd0f13eeb1
    result=success
    runtime=12.924s
    cpu=2.026s
    memory_peak=112M
    swap=0B
    start_status=0
    query_status=0

The harness supplied a private /dev, empty host /sys, hidden host home and
session bus, and unshared networking. Its unit journal records the RANGE-v2
WINEDLLPATH, read-only versioned root, and exact fake-PE and Unix-library
mounts.

Isolation, the exact registry-handle probe, corrected Windows 7 NT DDI path,
and SSE2 path passed. The WineUSB builtin and PaeDSPUSB loaded, PaeDSPUSB
reported RUNNING, and cleanup unloaded it. The two error-level trace lines
match the same pre-existing wineboot and winebth messages in CP8.

No USB PDO existed inside the hardware-hidden namespace. Consequently there
were zero class-IN, captured-RANGE, rejection, class-OUT, or observation
markers. This validates the exact staged overlay, selector, driver
compatibility, and cleanup only. It does not validate a live device response
or Universal Control synchronization.

## Evidence and postflight

The complete 31-entry relative checksum manifest verifies under:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.range-v2-20260821/out/checkpoints/driver-load-range-v2-20260821T033607PDT/

Its SHA256SUMS SHA-256 is:

    45087b770cdb8bf2405423b7a8a0183497881039f08c96a83b0c49da2988cfba

Postflight found the transient driver unit collected, no surviving candidate
Wine, UC, Xvfb, capture, build, or Bubblewrap process, and protected prefix
inode 3427833 with timestamp 2026-08-12 00:31:35.825186221 -0700. The source
sandbox and its retained capture remain unchanged. Only the fresh clone's
registry files changed as expected during its disposable Wine run; its
inherited capture and usbtap stayed byte-identical.

## Required pause

Stop at CP13. The prior live-read authorization remains consumed. A future
RANGE-v2 live-read requires a fresh complete preflight and new explicit
one-run authorization. Device connection alone is not authorization.

Do not expose the USB node, retry a prior run, detach or claim an interface,
change alternate settings, add class OUT, issue a USB write, start full
Universal Control or Voice FX, or access the protected prefix without a
separate explicit authorization.
