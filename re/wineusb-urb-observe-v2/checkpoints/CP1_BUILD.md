# Checkpoint 1 — isolated build complete

Reached at `2026-08-19T19:11:06-07:00`. This checkpoint compiled the
observation-v2 WineUSB overlay without a connected io24, USB visibility, udev,
network, host home, or host package installation. Nothing from this checkpoint
is live-staged.

## Containment and resources

The build ran in Bubblewrap with separate user/PID/network/IPC/UTS namespaces,
all capabilities dropped, a minimal `/dev`, empty `/sys`, private `/run` and
`/tmp`, and an empty `/home`. Only the clean source was mounted read-only; only
the project-local build and log directories were writable. An explicit audit
verified that `/dev/bus/usb`, `/sys/bus/usb/devices`, `/run/udev`, and the
protected Wine prefix were absent.

Configuration and compilation used idle I/O priority, nice level 15, a 2 GiB
virtual-memory limit, a 900-second timeout, and `make -j1`.

## Clean source and packages

Wine 11.15 was freshly extracted from the pinned, signed archive. USB-DI v1
and observation v2 then applied in that order with `--fuzz=0`. The resulting
changed sources are:

```text
12758dab119e4291c136e9e3ecefdf33d16bc40021ff0624da5b9c7ce0ec34f5  dlls/wineusb.sys/wineusb.c
639d1708593aceb60a7c74c39521fb3b2ecc6f88ee0eb205be2a70014e40add5  dlls/wineusb.sys/unixlib.c
93422cbd9975088b217ef4730620ef1512e70e3879750e8dc4860f0db75ae33b  dlls/wineusb.sys/usbdi.c
4296c33f7aa300a042b8198b6715e8d1e108c3907a58a7ed3d8e96c250890886  dlls/wineusb.sys/usbdi.h
```

The exact m4, flex, bison, and libusb development packages listed in
Checkpoint 0 were downloaded, re-verified against their prior hashes, and
extracted under `.io24-build/wineusb-observe-v2/tools`; `dpkg` did not install
them. Configure used the extracted libusb header and the already installed,
matching `libusb-1.0.so.0.5.0` runtime.

## Configure evidence

The first attempt stopped before generation because X headers were absent;
the second stopped because FreeType headers were absent. Both logs are
preserved. Since neither subsystem participates in WineUSB, the final clean
build explicitly used:

```text
/run/io24-source/configure --enable-win64 --without-mingw \
  --without-x --without-freetype --with-usb
```

The final configure confirmed both `libusb.h` and
`libusb_interrupt_event_handler`, generated its Makefile, and completed.
Relevant log hashes:

```text
7bfe9de8d1757e107ce05871c50995445c91eab6cba2672bf80224ef7072552c  logs/configure.log
e118a8e949d7f94ef5d6c2ae8a52fb40ea8e7a2013020ffe13f49d81ead221e0  logs/configure-final.log
bf69dc9a5fbe9f4723c51202e9f51258b9b5136a168221d888a80f1c08a1d83a  logs/configure-final2.log
```

## Build result

`make -j1 dlls/wineusb.sys/all` completed. The only warnings were Wine's
pre-existing five shift/reduce conflicts while generating the generic WRC
parser; the modified WineUSB translation units compiled without a warning or
error. The build log SHA-256 is
`a0f968537bfb0de9f3e823b38cca2fef7ef41d35160d87333091233891cb8e48`.

Exact first-build artifacts:

```text
b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys (2,560 bytes)
e5d4d22ec48ac4321627b30fb014133193d7d77bff3f296e867c1cafe7e07520  x86_64-unix/wineusb.sys.so (190,464 bytes)
03a4c63ec669bf4f05789dfffd42c55e10d9e0ef990a1cc0622c1a0ab7812826  x86_64-unix/wineusb.so (88,584 bytes)
```

The Windows builtin has ELF build ID
`ec6ff07331507ab0cdb34f2134cc8e25f9e529d1`; the Unix library has build ID
`72fc32d7eff9270708f09965cd07d0498018d77d`. Both `IO24_OBSERVE` format
strings are present in the builtin. The fake PE is unchanged from USB-DI v1,
as expected because the implementation resides in the paired Wine builtin.

## Pause/resume boundary

This is a safe pause: the device is unnecessary, no Wine process was started,
and no sandbox overlay or protected prefix was changed. Resume at Checkpoint 2
by independently rebuilding for byte reproducibility, running the existing
USBDI contract plus new source/binary observation assertions, and exercising
the exact artifacts in USB-hidden driver containment. Any difference between
independent build hashes or any test failure is a hard pause before staging.
