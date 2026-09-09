# io24 v6 resolver live-read and next URB boundary

Performed exactly once on 2026-08-19 PDT after the user explicitly authorized
one bounded v6 live-read. The authorization covered that run only. The run was
not retried. This manifest was completed during the subsequent resume from the
sealed evidence; the resume itself did not open a USB node or start Wine,
Universal Control, or a device service.

## Fresh preflight and exact run

- Active `out/usbtap.so` and versioned `out/usbtap-resolver-v6.so` both matched
  SHA-256
  `dbce256b328b53866dd13dbe382c28b216a1baf64bdb47fc746b722375e86977`,
  size 21,584 bytes, and ELF build ID
  `fdc6614838445964b3dbc8ab55726fd894268be1`.
- Exactly one `194f:0422`, serial `AB7C22200355`, was present at sysfs `1-2`
  and `/dev/bus/usb/001/003`, configuration 1, authorized at 480 Mbit/s.
- Interfaces 0 through 4 were owned by `snd-usb-audio`; interfaces 5 and 6
  were unclaimed. No Wine, UC, Xvfb, or project io24 process was running.
- The run used the disposable prefix only. The protected
  `/home/ajuntanaga/.wine-io24` retained timestamp
  `2026-08-12 00:31:35.825186221 -0700`.
- The isolation gate exposed only `/dev/bus/usb/001/003` to the transient
  Bubblewrap service, with host home, audio, GPU, session bus, and external
  network unavailable.

The one authorized run was transient unit
`io24-wine-live-read-560914.service`. It started at
`2026-08-19T03:00:13.893691-07:00`, was not retried, and ended at
`03:00:36.127414-07:00` with status 1. It consumed 3.630 seconds CPU over
22.234 seconds wall time and peaked at 106.6 MiB memory. The candidate service
was initially stopped, the registered `PreSonus Hardware Access Service`
reached `RUNNING`, and no UCNET `DA` arrived within the bounded readiness
window. Service `RUNNING` is not synchronization evidence.

## Sealed transfer capture

The exact 2,166-line capture is 224,247 bytes, SHA-256
`f7bb87af84915b94a201d7762af0f2f27c017762981c8387175bf2face56c576`,
and timestamp `2026-08-19 03:00:35.410575331 -0700`. It records two contained
Wine processes:

| PID | init/resolver | submits | callbacks | event enter/return |
| --- | ---: | ---: | ---: | ---: |
| 74 | 1 | 94 | 94 | 96 / 95 |
| 204 | 1 | 43 | 43 | 45 / 44 |

Both processes installed the native libusb callback and resolved the real
`libusb_submit_transfer`. Across them, all 137 submissions were accepted, all
137 produced callbacks, and every callback status was zero. There are no
immediate-submit error (`E`) records. Every transfer is an asynchronous control
IN on endpoint zero; there is no bulk/interrupt transfer and no control-OUT
payload.

All setup packets are standard `GET_DESCRIPTOR` requests:

```text
  3  8006000100001200  device descriptor
  6  8006000200000900  configuration header
  6  8006000200008801  full 392-byte configuration
 11  8006000300000001  language string
  5  8006010309040001
  5  8006020309040001
  5  8006030309040001
  3  8006100309040001
  9  8006130309040001
  9  8006160309040001
  3  8006190309040001
  6 each for string indices 0x21 through 0x2c
```

Callback lengths were 4 bytes x11, 9 x6, 16 x3, 18 x8, 22 x24, 26 x23,
30 x24, 32 x8, 38 x24, and 392 x6. The returned descriptors identify
`194f:0422`, `PreSonus`, `Revelator IO24`, and serial `AB7C22200355`.

The capture's usbmon-style `Ci:1:004:00` text is not a live node identity.
`tests/usbtap.c:emit_record()` hard-codes bus `1` and address `004`; the actual
run-time node is established independently by preflight and the transient unit
as sysfs `1-2`, `/dev/bus/usb/001/003`.

This conclusively removes the earlier descriptor-completion blocker: native
libusb reaped each request and the Wine-side callbacks ran. It does not prove
Universal Control synchronization or general driver compatibility.

## First later failure boundary

The sealed `service-install.log` contains this repeatable sequence:

```text
line 3248   URB function 0x1b unsupported
line 3256   IoAllocateErrorLogEntry size 120
line 6276   URB function 0x01 unsupported
line 6294   IoAllocateErrorLogEntry size 92
line 8619   URB function 0x1b unsupported
line 8627   IoAllocateErrorLogEntry size 120
line 10947  URB function 0x01 unsupported
line 10965  IoAllocateErrorLogEntry size 92
```

Wine 11.15 defines `0x1b` as `URB_FUNCTION_CLASS_INTERFACE` and `0x01` as
`URB_FUNCTION_SELECT_INTERFACE`. The retained patched Wine source handles
descriptor, bulk/interrupt, reset, select-configuration, and vendor requests,
but neither of these functions. The observed `STATUS_NOT_IMPLEMENTED`
completion is therefore the immediate compatibility boundary after descriptor
enumeration.

The exact `PaeDSPUSB.sys`, SHA-256
`fcd8b46d5af756172cb740386f89373e4129d0baa7f6ecb1ff1a173aed49c7bb`,
contains the UTF-16 strings `Audio Controller initialization failed.` and
`Set Configuration failed.` The 120- and 92-byte error-log allocations match
those respective string lengths under the driver's apparent error-entry
header-plus-UTF-16 sizing. Together with call-order disassembly, this strongly
supports that the first unsupported class request aborts audio-controller
initialization and the later select-interface request aborts configuration;
the unavailable Wine log fields mean this remains a correlation, not a
runtime dump of the actual URBs.

Static analysis also shows that the driver can construct both IN and OUT
class-interface URBs and contains several candidate class-control call sites.
Consequently, the direction, request, value, index, and payload of the first
runtime `0x1b` must be observed rather than guessed. Implementing
`SELECT_INTERFACE` would normally require alternate-setting/interface state
changes and is outside the existing no-claim, no-detach live boundary.

## Observation-only v2 source patch

`../wine-11.15-wineusb-urb-observe-v2.patch` is staged source only. Against
the retained Wine 11.15 plus USB-DI-v1 source, it logs:

- class-interface header length/status, transfer flags and length, request
  type, request, value, and index; and
- select-interface header/configuration handle, interface number, alternate
  setting, class tuple, and pipe count.

Both cases then continue to return `STATUS_NOT_IMPLEMENTED`. The patch adds no
libusb submission path, no buffer dump, no interface claim/detach, and no
alternate-setting call. It passed a zero-fuzz dry application to the retained
source. It has not been compiled, staged as an overlay, or run.

## Checkpoint, resume state, and gate

Every entry in the sealed checkpoint verifies at:

`out/checkpoints/live-read-resolver-v6-20260819T030035PDT/`

Key hashes are:

- `SHA256SUMS`:
  `68af8bf8c80079c756506e3245a39f8a5764b97935c0cb7fc803c9332d33ef6d`;
- `service-install.log`:
  `cda76f9ab7b1cd3836f3b22bfcba5c63d1a0d6f58961dc8834e12e3917681f0c`;
- `run-journal.log`:
  `5590a0fa8578f2c90b36d0ecb70e152f9df7e6b41d5d205e39ed08af976ba14d`;
- `live-service-usb.txt`:
  `f7bb87af84915b94a201d7762af0f2f27c017762981c8387175bf2face56c576`;
- `usbtap.so`:
  `dbce256b328b53866dd13dbe382c28b216a1baf64bdb47fc746b722375e86977`.

The live run changed disposable `prefix/system.reg` as expected; it is
3,745,717 bytes, SHA-256
`9d51781ebdea23718153c94a8e39c2c659a9c5582c9915ce664b780fec8be0f4`,
and timestamp `2026-08-19 03:00:35.729572767 -0700`.

At the 2026-08-19 resume check, the same serial remained at sysfs `1-2`, now
devnum 2 after external re-enumeration, authorized at 480 Mbit/s and
configuration 1. Interfaces 0-4 remained on `snd-usb-audio`; 5-6 remained
unclaimed. No Wine, UC, Xvfb, or io24 service process survived, the checkpoint
still verified in full, and the protected prefix timestamp was unchanged.

The v6 authorization is consumed. Do not rerun it. The next safe work is
offline: build the observation-only patch reproducibly, pass USB-hidden
contracts, hash-pin and stage it, and only then request a new one-run
authorization. A future trace authorization must still exclude semantic class
or select-interface support, device writes, interface claims/detach, timeout
changes, full Universal Control, Voice FX, and the protected prefix.
