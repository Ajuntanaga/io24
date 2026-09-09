# io24 WineUSB observation v2 live-read

Performed exactly once on 2026-08-19 PDT after the user explicitly authorized
the already staged observation-only overlay and then reported the io24
connected. The authorization covered this run only. It was not retried.

## Outcome

The run stayed fail-closed and resolved the first unknown URB tuple without
submitting that request to the device. PaeDSPUSB twice constructed this exact
`URB_FUNCTION_CLASS_INTERFACE` request:

```text
header length     0x88
initial status    0xffffffff
transfer flags    0x00000003
transfer length   256
reserved bits     0x00
request           0x02
value             0x0100
index             0x0500
```

The overlay logged each instance and returned `STATUS_NOT_IMPLEMENTED`, exactly
as its offline contract requires. It also twice observed a
`URB_FUNCTION_SELECT_INTERFACE` whose configuration handle was null and whose
embedded interface fields were all zero, then returned the same failure.

The service reached `RUNNING`, but no UCNET `DA` announcement arrived. This is
protocol-boundary evidence, not Universal Control synchronization or general
driver-compatibility evidence.

## Fresh preflight and isolation audit

No live-read began until a fresh preflight passed:

- exactly one `194f:0422`, serial `AB7C22200355`, was present at sysfs `1-2`
  and `/dev/bus/usb/001/005`, configuration 1, at 480 Mbit/s;
- interfaces 0 through 4 remained owned by `snd-usb-audio`; interfaces 5 and 6
  were unclaimed;
- no Wine, Universal Control, Xvfb, or project io24 process was running;
- the staged WineUSB triplet, v6 logger, NT overlays, harness, official driver,
  prior capture, sealed v6 sandbox, and CP3 checkpoint matched their pinned
  hashes;
- the protected `/home/ajuntanaga/.wine-io24` inode and timestamp were still
  unchanged; and
- 134 GiB was free on the containing filesystem.

The read-only live isolation audit ran separately as
`io24-wine-live-audit-624016.service`, invocation
`62619805a197439ba97d2ee343ffd705`, and exited status 0 after 671 ms. Its
namespace exposed only the exact io24 node and reported no host audio, GPU,
home, session bus, or external network. The audit did not open Wine or the
candidate driver.

Before the authorized run, the inherited 224,247-byte v6 capture was moved
within the disposable clone to
`out/live-service-usb-observe-v2-source-v6-20260819T030035PDT.txt`. It retained
inode `8917623`, its original timestamp, and SHA-256
`f7bb87af84915b94a201d7762af0f2f27c017762981c8387175bf2face56c576`.
The original sealed v6 sandbox was not modified.

## Exact one-run record

The sole authorized live-read was transient unit
`io24-wine-live-read-625692.service`, invocation
`2c5ad2102bd24c11bc1e76ed60b844f6`. It started at
`2026-08-19T19:42:21.114016-07:00`, ended at
`19:42:51.266182-07:00`, and was not retried. It exited status 1 after 30.151
seconds wall time, 5.758 seconds CPU, 110.6 MiB peak memory, and zero swap.

The namespace again exposed only `/dev/bus/usb/001/005`, with the project,
driver input, and WineUSB overlay mounted read-only. The protected prefix,
host audio/GPU/home/session bus, and external network were unavailable. The
registered `PreSonus Hardware Access Service` reported `RUNNING` with only the
io24 exposed; the bounded probe then exited because no UCNET `DA` arrived.

## Sealed descriptor traffic

The new logger capture is 1,723 lines and 179,452 bytes, timestamp
`2026-08-19 19:42:50.749419575 -0700`, SHA-256
`f7ae3a97696dfd1ceff7b511c307d054422250e481deceb7b180167538762a67`.
It records two contained Wine processes:

| PID | init/global/resolve | submits | callbacks | errors | event enter/return |
| --- | ---: | ---: | ---: | ---: | ---: |
| 74 | 1 / 1 / 1 | 94 | 94 | 0 | 96 / 95 |
| 204 | 1 / 1 / 1 | 12 | 12 | 0 | 13 / 13 |

All 106 accepted submissions produced status-zero callbacks. Every captured
transfer is a control-IN descriptor request on endpoint zero. There is no
control OUT, bulk, interrupt, immediate-submit error, class request, or
select-interface operation in the logger capture.

The standard `GET_DESCRIPTOR` setup-packet census is:

```text
  3  8006000100001200
  6  8006000200000900
  6  8006000200008801
 10  8006000300000001
  5  each of string indices 0x01, 0x02, and 0x03
  3  string index 0x10
  6  each of string indices 0x13 and 0x16
  3  string index 0x19
  4  each of string indices 0x21 through 0x2c
```

Callback lengths were 4 bytes x10, 9 x6, 16 x3, 18 x8, 22 x16, 26 x17,
30 x16, 32 x8, 38 x16, and 392 x6. As in the prior v6 capture, logger text
`Ci:1:004:00` is a hard-coded display identifier, not the live node identity;
preflight and the transient unit independently establish `/001/005`.

## URB observations

The 1,043,443-byte `service-install.log`, SHA-256
`f7b480645e1cb2febc9dd85626f7d219b8debaf184c4306037fd1bb8b8b2fa74`,
contains two identical cycles:

```text
3269  class-interface: length 0x88, status 0xffffffff, flags 0x3,
      transfer-length 256, request-type 0, request 0x2, value 0x100,
      index 0x500; returning STATUS_NOT_IMPLEMENTED
3277  IoAllocateErrorLogEntry size 120

4665  select-interface: length 0x38, status 0xffffffff,
      configuration-handle NULL, interface-length 0x18, interface 0,
      alternate 0, class/subclass/protocol 0/0/0, pipes 0;
      returning STATUS_NOT_IMPLEMENTED
4683  IoAllocateErrorLogEntry size 92
```

The same class/error and select/error sequence repeats at lines 7011/7019 and
9339/9357. The 120-byte allocation correlates with the driver's retained
`Audio Controller initialization failed.` path, and the 92-byte allocation
with `Set Configuration failed.` This remains correlation based on exact size
and call order; the runtime did not print either driver string.

## Interpretation: observed versus inferred

The following is directly observed:

- `URB_FUNCTION_CLASS_INTERFACE`, flags `0x3`, request `0x02`, value `0x0100`,
  index `0x0500`, requested length 256;
- reserved request-type bits zero;
- the device's returned 392-byte configuration descriptor declares interface
  0 as AudioControl using protocol `0x20` and contains the bytes
  `08 24 0a 05 03 07 00 19`, a class-specific Clock Source descriptor with
  entity/clock ID 5; and
- the overlay returned `STATUS_NOT_IMPLEMENTED`, so no setup packet or response
  payload for this class request appears in the USB capture.

The high-confidence interpretation is a USB Audio Class 2 Clock Source
Sampling Frequency `RANGE` read:

```text
bmRequestType  0xa1  device-to-host | class | interface
bRequest       0x02  RANGE
wValue         0x0100  Sampling Frequency selector 1, channel 0
wIndex         0x0500  clock/entity ID 5, AudioControl interface 0
wLength        0x0100  256-byte receive capacity
```

The evidence chain is independently checkable. Microsoft's URB documentation
defines `URB_FUNCTION_CLASS_INTERFACE` as a class command to an interface and
documents the request structure and transfer-direction flags:

- [URB header and function meaning](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usb/ns-usb-_urb_header)
- [vendor/class request construction and flags](https://learn.microsoft.com/en-us/previous-versions/ff538986%28v%3Dvs.85%29)

The upstream Linux UAC2 definitions assign request `0x02` to `RANGE` and
Clock Source selector `0x01` to Sampling Frequency. Its audio driver constructs
the same field layout: selector in the high byte of `wValue`, clock ID in the
high byte of `wIndex`, and control-interface number in the low byte:

- [UAC2 request and control-selector definitions](https://github.com/torvalds/linux/blob/master/include/linux/usb/audio-v2.h)
- [upstream UAC2 clock-range request construction](https://github.com/torvalds/linux/blob/master/sound/usb/format.c)

This is a semantic identification, not a captured class transfer. No response
bytes, supported sample-rate ranges, or device behavior under this request have
yet been observed.

The select-interface observation remains deliberately uninterpreted beyond its
raw zero/null fields. Implementing it could change alternate-setting and
interface state and therefore crosses the current safety boundary.

## Postflight and sealed checkpoint

Postflight passed at `2026-08-19T19:44:12-07:00`:

- the same serial remained at sysfs `1-2`, `/dev/bus/usb/001/005`,
  configuration 1, 480 Mbit/s;
- interfaces 0 through 4 remained with `snd-usb-audio`, and 5/6 remained
  unclaimed;
- the transient unit was inactive/collected and no Wine, UC, Xvfb, or project
  io24 process survived;
- the protected prefix inode/timestamp were unchanged;
- the original sealed v6 sandbox retained SHA-256
  `9d51781ebdea23718153c94a8e39c2c659a9c5582c9915ce664b780fec8be0f4`
  for `system.reg` and
  `f7bb87af84915b94a201d7762af0f2f27c017762981c8387175bf2face56c576`
  for its capture; and
- the disposable clone's registry changed as expected during the run and now
  has SHA-256
  `adecbb1610a9d6024bae3c8397f783c3e70cd10ec1d7a4212787cc40673720f5`.

Every evidence entry verifies under:

```text
/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.observe-v2-20260819/out/checkpoints/live-read-observe-v2-20260819T194220PDT/
```

The checkpoint's `SHA256SUMS` file has SHA-256
`45f75278cca8a31fbb70e659efc47849d43f4160ddf0272d99efc6b779f41634`.
It contains the preflight, isolation audit, immediate pre-run gate, console,
systemd journal, bounded kernel-journal slice, analysis, postflight, new and
prior captures, service logs, exact overlays, logger, harness, probe, and
observation patch.

## Current gate

The one-run live-read authorization is consumed. Do not archive the new active
capture or retry this run. No semantic URB support, control write, interface
claim/detach, alternate-setting operation, timeout change, full Universal
Control, Voice FX, or protected-prefix use was authorized or performed.

The next safe checkpoint is offline and does not require the device: design a
narrow, fail-closed implementation for the identified class-interface IN
request; first prove request construction, `USBD_SHORT_TRANSFER_OK`, bounded
receive-copy semantics, completion/cancellation, and rejected OUT/unknown cases
against fake libusb; then reproduce and hash-pin the overlay. A later hardware
test would require a new explicit one-run authorization. Select-interface
support remains a separate, prohibited boundary until its semantics and state
effects are resolved offline.
