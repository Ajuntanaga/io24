# io24 durable libusb logging interposer v5

Built, tested, and staged offline on 2026-08-19 PDT after the v4 live-read.
This work did not open a USB node, start Wine or Universal Control, or modify
either Wine prefix. The real-libusb integration test ran in a Bubblewrap
namespace where the probe independently rejected visible `/dev/bus/usb`,
`/sys/bus/usb/devices`, or `/run/udev` paths.

## Evidence boundary and discriminator

V4 recorded four successful calls through the tap's real
`libusb_submit_transfer()` target, but native libusb diagnostics stopped after
enumeration and open. Upstream libusb 1.0.29 emits a debug record at the
exported submit entry before dispatching to the backend. Its global log
callback replaces the default stderr sink, and `LIBUSB_DEBUG=4` fixes the
runtime log level from process start. The missing submit record therefore left
the native sink/routing path unproved; it did not prove that submit was skipped.

The relevant upstream sources are pinned to the installed 1.0.29 release:

- `libusb/io.c`, exported `libusb_submit_transfer()` entry;
- `libusb/core.c`, environment log level, callback selection, and stderr
  fallback; and
- `libusb/libusb.h`, global callback mode and API contract.

The staged Wine `wineusb.so` calls `libusb_init(NULL)`, so v5 interposes that
exact entry point. Before calling the real initializer it:

1. resolves the real initializer and `libusb_set_log_cb()` through
   `RTLD_NEXT`;
2. fails closed with status `-12` if either target is unavailable;
3. installs a global callback before native initialization; and
4. writes every callback message to the existing `IO24_USBLOG` stream with
   PID, TID, level, newline escaping, locking, and an immediate flush.

`R-init` and `R-submit` records use `dladdr()` to record the actual object and
symbol selected for both critical routes. `L-global-installed` proves callback
installation preceded the real initializer. V3's correlated `S`/`C`/`E` and
`H-enter`/`H-return` records are otherwise unchanged.

## RED-GREEN and hardware-empty contracts

New files:

- `../../tests/usbtap_log_contract.c` SHA-256:
  `3d6ba95ef3897f0599b97e74c0e9d692bd4cabc4883c9c6561f881800a7a9d81`;
- `../../tests/usbtap_log_contract.sh` SHA-256:
  `c3da48262a490aa9fae140934bce002ca6c86327084c98ac937b1dc7e2cec6b8`.

The fake-libusb contract emits initialization, submit, and event diagnostics
through a controllable global callback. Against unchanged v3 it was first
observed RED at the intended boundary:

```text
FAIL: libusb global callback was not installed before init
```

After implementation it requires all native messages in the dedicated file,
none on stderr, a real-submit resolver record naming the fake library, and the
unchanged asynchronous transfer/event evidence:

```text
usbtap durable libusb log contract: pass
callback contract (completed): pass
callback contract (stall): pass
callback contract (submit-error): pass
usbtap async control contract: pass
```

The revised empty-device integration files are:

- `../../tests/libusb_debug_contract.c` SHA-256:
  `2c9713d6092a75ccb5d3d0e62869a1a195e2e9084fb3dab8290f1a3838663adc`;
- `../../tests/libusb_debug_contract.sh` SHA-256:
  `29ac765bc91358dea2cfc8d4d8f57ed39fc6dff4071e57b1eea402f0b1a28c82`.

That contract loads the real system libusb with v5 preloaded and calls only
`libusb_init()` and `libusb_exit()`. It requires real-library `R-init`
provenance, callback installation, durable init/exit records, and no escaped
libusb stderr record. The source build, the exact build artifact, and the exact
staged artifact each passed:

```text
libusb durable-log empty-device contract: pass
```

## Artifact and provenance

Build command:

```bash
cc -std=c11 -Wall -Wextra -Werror -shared -fPIC -O2 \
  tests/usbtap.c -ldl \
  -o /tmp/io24-usbtap-log-v5.so
```

- compiler: `cc (Ubuntu 15.2.0-16ubuntu1) 15.2.0`;
- artifact SHA-256:
  `9734fd0d09254f8717059b5abb0e05089ddf0cf024a526fc8965ebb0dc6341fc`;
- ELF build ID: `acad8398130205bf1c5e97c56fe8bbabac37053d`;
- installed `/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0` SHA-256:
  `e422dc361a501e8175a94e16228704de7ca6376037fc29a0e7272e8fe2c8edc1`;
- revised `../../tests/usbtap.c` SHA-256:
  `306906839abca6a8c0d2abad7ca0a2db78b2fe99fcef4dc44942c35f14ad2c0c`;
- unchanged `../../tests/usbtap_async_contract.c` SHA-256:
  `95e2d13dd4daddbcdea364ef358a1587fdac7980110601a70170174bd61cb965`;
- unchanged `../../tests/usbtap_async_contract.sh` SHA-256:
  `3c235c4d91d00dcd3ddbdd11f17e6e507c60b0bf4c34a1d1a5738fdacfba2f03`;
- revised `../../tests/uc_wine_sandbox.sh` SHA-256:
  `241141a3016cb295351214e27cf4333ce0f0c79be044922ab327f99096d49547`.

The durable-log contract also calculates the tested ELF hash and requires it
to equal the harness's single `USBTAP_LOG_V5_SHA256` value. The harness refuses
`live-read` unless the active file matches that v5 hash.

## Reversible staging and next gate

The exact ELF is staged only in the disposable sandbox as both
`out/usbtap-log-v5.so` and active `out/usbtap.so`; both hashes match the
artifact above. V3 remains recoverable at `out/usbtap-event-v3.so` with
SHA-256
`bfc1a6ff8553c65e207c240eef8fdc59b50ef7ba8e9c7d89961d81ee6f48dd42`.

The current 584-byte v4 capture remains at `out/live-service-usb.txt` with
SHA-256
`d1a0faa893c348a53bfe4ef4160c8ecbaf9e90c84f8547fb974929d4100e8885`
and timestamp `2026-08-19 00:56:36.133867593 -0700`. The disposable
`prefix/system.reg` timestamp remained
`2026-08-19 00:56:36.649863629 -0700` during staging.

This offline stage is not a live result and does not authorize another
`live-read`. Before any future run, preserve and byte-verify the v4 capture,
refresh the device/node, interface ownership, process, artifact, prefix,
capacity, and isolation gates, and obtain a new explicit one-run authorization.
Do not retry automatically, alter timeouts, interrupt the event pump, detach a
driver, claim an interface, send a control write, or proceed to full Universal
Control or Voice FX.
