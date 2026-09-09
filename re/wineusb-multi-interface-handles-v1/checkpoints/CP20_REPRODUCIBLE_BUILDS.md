# CP20 — independent multi-interface builds reproduce exactly

Reached at 2026-08-22T10:18:43-07:00. Battery was charging at 50%, above the
mandatory 10% stop threshold. This checkpoint remained hardware-free and did
not start Wine, access a prefix, stage an artifact, or expose a USB node.

## Independent source preparation

Two separate networkless, hardware-hidden namespaces each verified and
extracted the pinned Wine 11.15 archive, then independently applied USB-DI v1,
URB observation v2, exact RANGE v2, pipe-observe v3, and multi-interface
handles v1 with:

    patch --batch --forward --fuzz=0 -p1

Each resulting source tree contains 12,445 regular files, no symlinks, and no
`.orig` or `.rej` file. The complete trees match each other and the CP19
development source exactly.

## Clean configure and build

Build A initially stopped before configuration because the extracted Bison
binary could not find its bundled data directory. After
`BISON_PKGDATADIR=/run/io24-tools/usr/share/bison`, a second empty attempt
stopped because Bison's compiled-in `/usr/bin/m4` was absent. Both failed
directories and logs are preserved. No compilation occurred in either.

An isolated probe verified the exact pinned M4 binary. Build A was then
recreated empty and both final configurations used:

    BISON_PKGDATADIR=/run/io24-tools/usr/share/bison
    M4=/run/io24-tools/usr/bin/m4
    SOURCE_DATE_EPOCH=1787101002
    /run/io24-source/configure --quiet --enable-win64 --without-mingw \
      --without-x --without-freetype --with-usb \
      USB_CFLAGS=-I/run/io24-tools/usr/include/libusb-1.0 \
      USB_LIBS=/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0.5.0

Both configurations completed with the same three expected missing-feature
warnings and byte-identical output, Makefiles, and compile databases. Separate
`make -j1 dlls/wineusb.sys/all` runs used identical virtual paths, low CPU and
I/O priority, a 2 GiB address-space ceiling, CPU/wall timeouts, private
devices/sysfs/home/tmp/run, and unshared networking. Build A completed in
66.26 seconds and build B in 75.37 seconds; each reported zero swaps and no
warning from a WineUSB translation unit. Their complete build output is
byte-identical.

## Byte-identical candidate

Both clean sides and CP19's development build contain exactly:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys  (2,560 bytes)
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so                  (202,392 bytes)
    96f5a63a76d5f0e9a73425717d81e17d1fd6883c7a909508e703897a22fe4039  wineusb.so                      (102,600 bytes)

The builtin build ID is `0857e44f13501e673ba64c795a297fe8a757feb9`; the
Unix-library build ID is `be6c3c09298d93e060effd9433dfc5c955a54bfa`.
Both sides have the same 37 undefined dynamic symbols.

## Independent contracts

Each clean side independently passed, inside a fresh empty-sysfs/minimal-dev
networkless namespace:

- multi-interface handle population, atomic malformed rejection, structured
  markers, and null-buffer submission guard;
- pipe-observe source/binary/runtime behavior;
- exact captured RANGE-v2 behavior and source/binary checks;
- WineUSB USB-DI v1; and
- the CP15 class-IN evidence analyzer.

Both suites exited zero in 1.10 seconds and reported zero swaps. Their raw logs
differ only in randomized IRP and buffer addresses; after replacing those
pointer fields, their outputs are byte-identical with SHA-256
`fc4a95d0a63d9343985be16c95b893bac3872508778ba0e75a7189f13bc04b12`.

## Stop boundary

Stop at CP20. No candidate file is staged and no device action occurred. CP21
may stage only the triplet above after freezing this checkpoint and proving a
new real-harness selector RED/GREEN. Before live access it must validate a
fresh disposable clone and one USB-hidden driver-load. The null-buffer guard
must remain active so this single-blocker diagnostic cannot submit bulk data.
Firmware, full Universal Control, Voice FX, interface claims/detaches,
alternate-setting changes, and the protected prefix remain untouched.
