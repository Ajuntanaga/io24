# io24 libusb event-loop interposer v3

Built, tested, and staged offline on 2026-08-19 PDT. This work did not open a
USB node, start Wine or Universal Control, or modify either Wine prefix.

## Purpose

The single authorized async-v2 live-read recorded four accepted standard IN
`GET_DESCRIPTOR(Device)` submissions and no `C` callback or immediate `E`
error. That localizes the failure to the asynchronous transfer/event path, but
v2 cannot distinguish an event pump that remains blocked from one that returns
or exits.

Version 3 retains v2's correlated `S`/`C`/`E` usbmon records and adds comment
records that the existing decoder safely ignores:

```text
# usbtap pid=123 tid=124 transfer=ffff880000000000 event=S
# usbtap pid=123 tid=125 transfer=ffff880000000000 event=C
# usbtap pid=123 tid=125 event=H-enter
# usbtap pid=123 tid=125 event=H-return status=0
```

PID/TID attribution disambiguates identical per-process transfer IDs. Paired
`H-enter`/`H-return` records wrap the exact `libusb_handle_events()` entry point
used by the retained Wine 11.15 `wineusb` source. A lone `H-enter` proves that
the event thread entered the pump but did not return during the capture. It
does not by itself prove why libusb blocked or why a USB request did not
complete.

File initialization is guarded by a C11 atomic flag so submission and event
threads cannot race while opening the shared evidence stream. Each metadata
line and its usbmon record are emitted under one stream lock.

## RED-GREEN contract

The existing deterministic fake-libusb contract was first extended to require
PID/TID attribution and event-loop lifecycle evidence. Against v2 it failed at
the intended boundary:

```text
callback contract (completed): pass
FAIL: PID/TID or event-loop lifecycle evidence is missing
ffff880000000000 ... S Ci:1:004:00 -115 8 = 80060001 00000400
ffff880000000000 ... C Ci:1:004:00 0 4 = 12010003
```

After implementation, both a fresh source build and the exact staged v3 bytes
pass callback success, asynchronous STALL, immediate submit rejection, normal
event-handler return, and a deliberately blocked event handler. The blocked
case is killed after one second and must contain one `H-enter` with no
fabricated `H-return`.

```text
callback contract (completed): pass
callback contract (stall): pass
callback contract (submit-error): pass
usbtap async control contract: pass
```

The existing `tests/usbmon_decode.py` parser ignores comment lines because
they do not match its anchored usbmon record expression.

## Artifact and provenance

Build command:

```bash
cc -std=c11 -Wall -Wextra -Werror -shared -fPIC -O2 \
  tests/usbtap.c -ldl \
  -o re/usbtap-event-v3/x86_64-unix/usbtap.so
```

- compiler: `cc (Ubuntu 15.2.0-16ubuntu1) 15.2.0`;
- artifact SHA-256:
  `bfc1a6ff8553c65e207c240eef8fdc59b50ef7ba8e9c7d89961d81ee6f48dd42`;
- ELF build ID: `ff24d6d05ad13a09da4dd5817c625b3215e737a3`;
- `../../tests/usbtap.c`:
  `44f718dc3011b284b0d761ed657e014692726d3bd65ef65c29f897dabae6e150`;
- `../../tests/usbtap_async_contract.c`:
  `95e2d13dd4daddbcdea364ef358a1587fdac7980110601a70170174bd61cb965`;
- `../../tests/usbtap_async_contract.sh`:
  `3c235c4d91d00dcd3ddbdd11f17e6e507c60b0bf4c34a1d1a5738fdacfba2f03`;
- `../../tests/uc_wine_sandbox.sh`:
  `f704f37fbe7bcd6ba828eb6f5616a144c06e285726ac31bee8b8af246da9f8d2`.

## Reversible staging and gate

The exact artifact is staged in the disposable sandbox as both
`out/usbtap-event-v3.so` and the active `out/usbtap.so`; both hashes match the
artifact above. The previous v2 bytes remain at `out/usbtap-async-v2.so` with
SHA-256
`fdd1a418be106ec91bafefbad8680eaec7ea8404148a18998178de630cfad916`.

The harness now refuses live-read unless the active tap matches the v3 hash.
Because lifecycle comments can make the log nonempty without a USB transfer,
the success gate now requires a real non-comment `S`, `C`, or `E` usbmon
record. `bash -n` and the exact active-artifact contract both pass. The
disposable prefix timestamp remained
`2026-08-19 00:15:12.496283080 -0700` throughout staging.

This is an offline diagnostic gate, not another live result. Do not move or
overwrite the current capture and do not rerun `live-read` without a new
explicit authorization. No full Universal Control or Voice FX work is
authorized.
