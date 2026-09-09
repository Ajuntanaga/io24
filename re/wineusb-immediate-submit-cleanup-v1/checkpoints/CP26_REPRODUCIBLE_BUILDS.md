# CP26 — independent immediate-submit cleanup builds reproduce exactly

Reached offline on 2026-08-22 and sealed at
2026-08-22T17:03:33-07:00.  Battery was 89% and charging at final verification.

## Independent source preparation

The independently prepared CP20 source-A and source-B trees were copied into a
new lineage.  The new patch was applied separately to each with
`patch --batch --forward --fuzz=0 -p1`.  Both 12,445-file results match each
other, the CP25 development source, and the independent patch-check tree
exactly.  Neither contains a symlink, `.orig`, or `.rej` file.

## Clean configuration and build

The first two empty configuration attempts stopped before compilation because
the isolated toolroot's `flex` was not on `PATH`.  They are preserved as
`build-a-configure-failed-flex` and `build-b-configure-failed-flex`.

Fresh empty final build roots then configured independently with the same
virtual paths and explicit tools:

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

Their Makefiles, compile databases, and generated config headers are
byte-identical.  Separate `make -j1 dlls/wineusb.sys/all` runs used low CPU and
I/O priority and a 180-second timeout.  Each ran with unshared networking,
minimal devices, empty sysfs, private runtime paths, read-only source/tool
mounts, and only its own build root writable.  Both exited zero; the only
warnings were Wine's inherited parser conflict notices, not WineUSB compiler
warnings.

## Byte-identical artifacts

Development, clean A, and clean B all contain exactly:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys  (2,560 bytes)
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so                  (202,392 bytes)
    93a30fce04fc59fb034d9c88b6becd9931c56892cf97f5eca7f27db99aa68264  wineusb.so                      (98,448 bytes)

The builtin build ID remains
`0857e44f13501e673ba64c795a297fe8a757feb9`; the new Unix-library build ID is
`22434621eb75a3f3bbc8e6823b271df03908b14e`.  Its 36 named undefined dynamic
symbols match CP21 exactly, as do the `ntdll.so`, `libusb-1.0.so.0`, and
`libc.so.6` dependencies.

## Independent regressions and final state

Each clean side independently passed six hardware-free contracts:

- immediate-submit cleanup and allocation lifetime;
- multi-interface handle population and null-buffer safety;
- pipe routing and observation;
- exact captured Clock Source RANGE behavior;
- WineUSB USB-DI v1; and
- the CP15 class-IN evidence analyzer.

CP24's full 76-entry project chain reverified afterward.  No candidate Wine or
build process remained.  No prefix, USB node, device interface, live service,
network, firmware, Universal Control, Voice FX, claim/detach, alternate
setting, configuration, or OUT transfer was accessed.

## Stop boundary

Stop at CP26 for this software lineage.  The triplet is reproducible but is not
copied into a staged artifact root and is not selected by the real harness.
Routing/ownership analysis may continue offline.  Any staging toward a future
device-visible run requires a new selector gate; the run itself additionally
requires fresh explicit authorization and preflight.  CP24's live allowance
is consumed and must not be retried.
