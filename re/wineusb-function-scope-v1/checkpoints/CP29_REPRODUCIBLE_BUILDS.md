# CP29 — function-scoped WineUSB builds reproduce exactly

Reached offline on 2026-08-22. Battery was 97% and charging before the clean
builds. No IO24 device-facing operation was authorized or performed.

## Independent source preparation

The sealed CP26 source-A and source-B trees were copied into this new lineage.
The function-scope patch was applied independently to each with:

    patch --batch --forward --fuzz=0 -p1

Source A, source B, the CP28 development source, and the separately prepared
patch-check source match across all 12,445 regular files. No source tree has a
symlink, `.orig`, or `.rej` file. Evidence is retained in
`../logs/source-preparation.log` and `../logs/patch-check.log`.

## Clean contained configuration and build

Build A and build B started as separate empty roots. Each configured through
the same virtual paths and explicit pinned tools:

    PATH=/run/io24-tools/usr/bin:/usr/bin:/bin
    BISON=/run/io24-tools/usr/bin/bison
    BISON_PKGDATADIR=/run/io24-tools/usr/share/bison
    FLEX=/run/io24-tools/usr/bin/flex
    M4=/run/io24-tools/usr/bin/m4
    SOURCE_DATE_EPOCH=1787101002
    /run/io24-source/configure --quiet --enable-win64 --without-mingw \
      --without-x --without-freetype --with-usb \
      USB_CFLAGS=-I/run/io24-tools/usr/include/libusb-1.0 \
      USB_LIBS=/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0.5.0

Both configurations exited zero. Their top-level and include Makefiles,
compile databases, and generated `include/config.h` are byte-identical.

Separate low-priority, one-job builds ran with a 180-second timeout, unshared
networking, minimal `/dev`, empty `/sys`, private `/run` and `/tmp`, read-only
source/tool mounts, and only the corresponding build root writable:

    make -j1 dlls/wineusb.sys/all

Build A exited zero in 2:27.14 and build B in 2:15.23. The only compiler-tool
warning on either side is Wine's inherited WRC grammar notice for five
shift/reduce conflicts. No WineUSB translation unit warning or error appears.

## Byte-identical artifacts

Development, clean A, and clean B are byte-identical at all three deliverables:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys  (2,560 bytes)
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so                  (202,392 bytes)
    88ab927a25c818e308589414c94c06bb41e9b3cba8aa364535e94f958b5b89c0  wineusb.so                      (126,096 bytes)

The Unix library build ID is
`1bb30939ec9d971c53102dfcd5d63e4738408599`. It has 38 unique named undefined
symbols, exactly two more than CP26: the active-IAD getter and matching free
function documented at CP28. Its dynamic library dependencies remain
`ntdll.so`, `libusb-1.0.so.0`, and `libc.so.6`.

Full evidence is in `../logs/artifact-comparison.log`.

## Independent contracts

Each clean side independently passed the function-scope contract and all
retained contracts listed at CP28. The exact-device assertions include:

- child roots `0`, `3`, `5`, and `6`, with no raw child 1, 2, or 4;
- nine-byte header probes that advertise partial total lengths;
- complete partial descriptors of 218, 133, 41, and 27 bytes;
- rejection of interface 4 by the `MI_00` function before handle mutation; and
- acceptance by `MI_03`, including handles `0x202` and `0x282`.

The sealed passive topology still reconstructs `{0,1,2}`, `{3,4}`, `{5}`, and
`{6}`. Contract logs A and B each exited zero in under three seconds.

## Meaning for interface 4

The composite-enumeration half of the interface-4 blocker is now implemented,
test-first, and reproducible offline. PaeDSPUSB's MI00 instance will no longer
be offered interface 4 by this candidate; its MI03 MIDI/CTRL instance retains
interface 4.

This does not yet prove live transport. The physical interface was still owned
by `snd-usb-audio` in CP24, and no ownership mechanism was added here. A future
libusb claim/detach design can disrupt host audio and requires a separately
chosen architecture plus explicit authorization. A native ALSA/MIDI bridge is
a larger alternative. MI05/MI06 driver discovery also remains a separate
compatibility gap and is not evidence of a firmware fault.

## Stop boundary at CP29

The reproducible triplet is not copied into a staged artifact root and is not
selected by the real harness. No Wine prefix, USB node, driver, service,
Universal Control, Voice FX, network, firmware image, claim/detach, alternate
setting, configuration request, control transfer, or OUT transfer was used.

Any staging requires a new hash-pinned selector contract first. Any later live
diagnostic additionally requires fresh explicit authorization and a full
preflight. CP24 remains consumed and must not be retried; reconnection is not
authorization.
