# CP17 — independent pipe-observe builds are reproducible

Reached at 2026-08-21T05:24:23-07:00. Work continued immediately toward
CP18 under the user's three-checkpoint request. Battery was discharging at
54%; the mandatory pause threshold remains 10%.

## Outcome

PASS, offline only. Two source trees were independently extracted from the
hash-pinned Wine 11.15 archive in separate hardware-hidden, networkless
Bubblewrap invocations. Each independently received USB-DI v1, URB observation
v2, exact captured RANGE v2, and pipe-observe v3 with:

    patch --batch --forward --fuzz=0 -p1

Each resulting tree contains 12,445 regular files, zero symbolic links, and
zero `.rej`/`.orig` files. Full content comparison reports the trees identical.

## Independent bounded builds

Build A and B used separate empty output directories but identical virtual
paths (`/run/io24-source` and `/run/io24-build`), pinned extracted build tools,
`SOURCE_DATE_EPOCH=1787101002`, and `make -j1`. Each invocation unshared user,
PID, network, IPC, UTS, and cgroup namespaces, dropped all capabilities, hid
host devices and sysfs, imposed a 2 GiB address-space ceiling plus CPU and wall
limits, and used nice level 15 with idle I/O priority.

Both configurations exited zero in about 20 seconds and peaked at 137,016 KiB
RSS. Both builds exited zero in about 71 seconds, peaked below 137 MiB RSS, and
used zero swap. Their complete configure output and complete build output are
also byte-identical. Neither modified WineUSB translation unit emitted a
warning.

## Byte-identical candidate triplet

All candidate files compare byte-for-byte between build A and B:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys  (2,560 bytes)
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so                  (202,392 bytes)
    90d060571d9f8a56aea8d91485802fe500920f741fb5787543a8c141ae104eb9  wineusb.so                      (92,328 bytes)

The common builtin build ID is
`0857e44f13501e673ba64c795a297fe8a757feb9`; the common Unix-library build ID
is `8a975849185b8c68b22e8f1d136ec8e58c9814be`. Generated `Makefile` and
`compile_commands.json` are also byte-identical. The detailed comparison is:

    ../logs/cp17-artifact-comparison.txt

## Independent contracts

Each clean side independently passed, inside a fresh hardware-hidden and
networkless namespace:

- pipe-observe fake-libusb behavior plus source/binary/runtime markers;
- exact captured RANGE-v2 fake-libusb behavior plus source/binary contract;
- WineUSB USB-DI v1; and
- the CP15 class-IN usbmon evidence analyzer contract.

Each full suite exited zero in 1.20 seconds and peaked below 7.4 MiB RSS. Raw
source preparation, configure, build, resource, and contract logs are retained
under `.io24-build/wineusb-pipe-observe-v3/logs/` and included in the CP17
checksum seal.

## Safety and next gate

No candidate file is staged at CP17. The active sandbox harness still selects
the sealed RANGE-v2 triplet. No sandbox, Wine prefix, USB node, driver, or
connected device was accessed.

CP18 may now stage only the exact reproduced triplet above, write and first
fail a real-harness selector contract, make the minimal hash-pinned selector
change, validate it, clone a fresh disposable sandbox, and perform one
USB-hidden driver-load. Only after those gates pass may the user's new device-
testing authorization be consumed for one bounded live diagnostic run. Never
touch the protected `.wine-io24` prefix or perform firmware work. Pause safely
at 10% battery or lower.

