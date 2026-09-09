# io24 v4 native-libusb live-read

Performed exactly once on 2026-08-19 PDT after the user explicitly authorized
the v4 live-read procedure. The authorization covered this run only. It did
not authorize a retry, a control write, an interface claim or detach, a
timeout change, full Universal Control, Voice FX, firmware work, or use of the
protected Wine prefix.

## Fresh preflight

- `tests/libusb_debug_contract.sh` passed against the installed real libusb in
  a hardware-empty Bubblewrap namespace.
- The source-built and exact staged-artifact asynchronous tap contracts both
  passed callback success, STALL, immediate rejection, normal event return,
  and deliberately blocked event-handler cases.
- Active and versioned v3 tap artifacts both matched SHA-256
  `bfc1a6ff8553c65e207c240eef8fdc59b50ef7ba8e9c7d89961d81ee6f48dd42`.
- The v3 capture was still 584 bytes with SHA-256
  `4f685e2a74fe94bdac896c025c89cf6a45d9f518a19410ffd422435c1847fdca`
  and byte-matched its complete v3 checkpoint.
- Exactly one `194f:0422`, serial `AB7C22200355`, was present at sysfs `1-2`
  and `/dev/bus/usb/001/003`, configuration 1, authorized at 480 Mbit/s.
- Interfaces 0 through 4 were owned by `snd-usb-audio`; interfaces 5 and 6
  were unclaimed. No Wine, UC, Xvfb, or project io24 process was running.
- The protected prefix remained at
  `2026-08-12 00:31:35.825186221 -0700`; the disposable prefix was at
  `2026-08-19 00:33:48.706786759 -0700`.
- The filesystem had 139 GiB and more than 29 million inodes free.

The host-side identity check completed at `2026-08-19T00:55:02-07:00`.
The non-opening isolation gate then passed as transient unit
`io24-wine-live-audit-275500.service`, invocation
`d3405d9ac3e3435dbde21aa3ed28a994`: one io24 node was visible, while audio,
GPU, host home, session bus, udev control, and external network remained
inaccessible. It used 5.5 MiB peak memory and zero swap.

Every current v3 output byte-matched the existing checkpoint before the
capture was preserved as:

`out/live-service-usb-event-v3-20260819T003432PDT.txt`

That archive retains the v3 capture hash above.

## One authorized run

Exactly this command was executed once and was not retried:

```bash
./tests/uc_wine_sandbox.sh live-read \
  /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.statusprobe-20260816
```

Observed result:

- transient unit `io24-wine-live-read-276864.service`, invocation
  `ecec6039bf7a47469653600460105d2a`;
- containment again exposed only the io24 USB node and printed
  `libusb debug level: 4` before Wine started;
- installer and loader diagnostic status 255;
- registered `PreSonus Hardware Access Service` reached `RUNNING` on readiness
  check 1;
- no UCNET `DA` arrived within 8 seconds and `synchronize.json` was absent;
- final status 1 after 21.455 seconds, 3.422 seconds CPU, 103.4 MiB peak
  memory, and zero swap.

Service `RUNNING` is not synchronization evidence.

## Tap capture

The v4 capture is 10 lines, 584 bytes, SHA-256
`d1a0faa893c348a53bfe4ef4160c8ecbaf9e90c84f8547fb974929d4100e8885`:

```text
# usbtap pid=74 tid=86 event=H-enter
# usbtap pid=74 tid=78 transfer=ffff880000000000 event=S
ffff880000000000 9814291273 S Ci:1:004:00 -115 8 = 80060001 00001200
# usbtap pid=74 tid=78 transfer=ffff880000000001 event=S
ffff880000000001 9814593845 S Ci:1:004:00 -115 8 = 80060001 00001200
# usbtap pid=203 tid=215 event=H-enter
# usbtap pid=203 tid=207 transfer=ffff880000000000 event=S
ffff880000000000 9830493658 S Ci:1:004:00 -115 8 = 80060001 00001200
# usbtap pid=203 tid=207 transfer=ffff880000000001 event=S
ffff880000000001 9830788703 S Ci:1:004:00 -115 8 = 80060001 00001200
```

After normalizing only the monotonic timestamps, this is identical to the v3
capture: two event-handler entries, four accepted standard IN
`GET_DESCRIPTOR(Device)` submissions for 18 bytes, zero immediate submit
errors, zero callbacks, and zero event-handler returns before teardown.

## Native libusb evidence

Native level-4 logging produced two 94-record sequences:

- `service-install.log` used libusb thread `0x56` (decimal 86), which matches
  the first tap `H-enter` thread;
- `service-stop.log` used libusb thread `0xd7` (decimal 215), which matches the
  second tap `H-enter` thread.

After normalizing timestamps, thread IDs, and pointer values, the two native
sequences were identical. Each sequence:

1. created the default libusb context and reported libusb 1.0.29.11953;
2. found usbfs and sysfs;
3. enumerated sysfs `1-2` as bus 1, address 3, session 259, root-hub port 2;
4. failed with expected `ENOENT` while trying USB nodes hidden by containment;
5. successfully opened the sole exposed node as `1.3`, added its event source,
   and parsed its configuration.

No native record named `libusb_submit_transfer`, `op_submit_transfer`,
`op_handle_events`, or `reap_for_handle` appeared. There was also no
`submiturb` error, reap error, URB status, completion, or libusb exit record.
`service-loader.log` contained no native libusb record.

This absence is not evidence that submission was skipped. The tap calls the
real `libusb_submit_transfer()` and would emit `E` on a nonzero return; all
four real calls returned zero. The installed library's exported submit
function also contains a level-4 `transfer %p` entry record, yet that record
did not reach these redirected logs. Therefore v4 exposed a logging coverage
gap after enumeration/open. Whether the context log level changed or the
native log sink stopped receiving output is unresolved.

The native log does establish successful libusb enumeration and opening of
the exact io24 node. It does not distinguish a device/usbfs request that never
completed from a missing poll/reap notification, because the intended
submit/reap observation layer was not captured at transfer time.

## Postflight and checkpoint

At `2026-08-19T00:57:25-07:00`, the exact device remained at the same node,
configuration, authorization, and speed. Interfaces 5 and 6 remained
unclaimed and no Wine, UC, Xvfb, or project io24 process survived. The
protected prefix timestamp was unchanged; the disposable prefix changed as
expected to `2026-08-19 00:56:36.730245956 -0700`.

No USB, xHCI, reset, stall, timeout, warning, or error appeared in the kernel
journal for `00:55:50` through `00:57:05` PDT. The two 100-byte
`IoAllocateErrorLogEntry` attempts remained present in the installer trace.

Every copied artifact byte-matched its source at:

`out/checkpoints/live-read-libusb-v4-20260819T005725PDT/`

Key SHA-256 values:

- `live-service-usb.txt`:
  `d1a0faa893c348a53bfe4ef4160c8ecbaf9e90c84f8547fb974929d4100e8885`;
- `service-install.log`:
  `1d0b58edfe93222f138033a88f79c8fbff376c76528919c33062cbeafba36c53`;
- `service-stop.log`:
  `d2d227e78fe56e503f0e8f9d477c8202e938b4f738e57c523cd5a959bc8e2273`;
- `service-loader.log`:
  `2a17ee542e4c37bd45a80f768652b1bf9e41de0f7ea92d31777e7332657d55a0`;
- `probe.log`:
  `74c9bc89c032995f8c92475ca61ba052cd806169dc592dee76db9a178e3f4018`;
- `usbtap.so`:
  `bfc1a6ff8553c65e207c240eef8fdc59b50ef7ba8e9c7d89961d81ee6f48dd42`;
- native `libusb-1.0.so.0`:
  `e422dc361a501e8175a94e16228704de7ca6376037fc29a0e7272e8fe2c8edc1`.

## Gate

This one-run authorization is consumed. Keep the current v4 capture in place
and do not retry live-read automatically.

The safest next step is offline: make native debug delivery durable with a
dedicated file callback or equivalently narrow logging interposer, prove its
submit/event/reap coverage without hardware, and only then request another
one-run authorization. If that still cannot observe backend progress, stage a
narrow usbfs submit/poll/reap interposer offline. Do not change transfer
timeouts, interrupt the event handler, claim or detach interfaces, or send a
control write merely to force progress.
