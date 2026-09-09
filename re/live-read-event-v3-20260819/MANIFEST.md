# io24 v3 event-loop live-read

Performed once on 2026-08-19 PDT under the user's explicit authorization for
one v3 event-loop live-read. The authorization covered this run only. It did
not authorize a retry, device writes, full Universal Control, Voice FX, a
firmware operation, or changes to the protected Wine prefix.

## Preflight

- Exactly one `194f:0422` was present at sysfs `1-2`, serial
  `AB7C22200355`, bus 1 device 3, configuration 1, authorized at 480 Mbit/s.
- Host node `/dev/bus/usb/001/003` was a readable/writable character device.
- Interfaces 0–4 were owned by `snd-usb-audio`; interfaces 5 and 6 were
  unclaimed.
- No Wine, wineserver, Xvfb, PaeDSPUSB, PreSonus service, or UC process was
  present.
- Source-built and exact staged-artifact contracts passed callback success,
  asynchronous STALL, immediate rejection, normal event-handler return, and
  a deliberately blocked event handler.
- Active `out/usbtap.so` and versioned `out/usbtap-event-v3.so` both matched
  SHA-256
  `bfc1a6ff8553c65e207c240eef8fdc59b50ef7ba8e9c7d89961d81ee6f48dd42`.
- The UCNET probe SHA-256 was
  `0e1efdd6b4fc8625120e735a4b58026014d6c12923cd699392df0ddb358f1e3e`;
  source inspection reconfirmed only `UM`, `JM Subscribe`, and `KA`, with no
  `PV` or `PS` control-write path.
- The previous v2 capture was byte-matched to its checkpoint, then preserved
  as `out/live-service-usb-async-v2-20260819T001451PDT.txt`, SHA-256
  `0cbd3983e846eba64b9e1b0a7732408d7c82f80d2c7818f0d20950b91836f0b8`.
- Protected prefix `/home/ajuntanaga/.wine-io24` remained at
  `2026-08-12 00:31:35.825186221 -0700`; disposable prefix mtime was
  `2026-08-19 00:15:12.496283080 -0700`.

The managed diagnostic shell hid `/dev/bus/usb`; the exact node and access
checks were therefore repeated successfully through the authorized host-side
surface before the capture was moved or the run started.

## One authorized run

Exactly this command was executed once and was not retried:

```bash
./tests/uc_wine_sandbox.sh live-read \
  /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.statusprobe-20260816
```

Observed harness result:

- transient unit `io24-wine-live-read-242096.service`, invocation
  `4284822ee4034c42aaac05d6e09360ce`;
- live isolation verified one io24 node and no audio, GPU, host home, session
  bus, or external network;
- installer status 255 and loader diagnostic status 255;
- registered `PreSonus Hardware Access Service` reached `RUNNING` on readiness
  check 1;
- the read-only probe returned status 1 because no UCNET `DA` announcement
  arrived within 8 seconds; no `synchronize.json` was created;
- the transient unit ended with status 1 after 21.378 seconds, using 3.400
  seconds CPU, 102.1 MiB peak memory, and zero swap.

Service `RUNNING` is not synchronization evidence.

## V3 capture

`live-service-usb.txt` is 10 lines, 584 bytes, SHA-256
`4f685e2a74fe94bdac896c025c89cf6a45d9f518a19410ffd422435c1847fdca`:

```text
# usbtap pid=74 tid=86 event=H-enter
# usbtap pid=74 tid=78 transfer=ffff880000000000 event=S
ffff880000000000 8446439402 S Ci:1:004:00 -115 8 = 80060001 00001200
# usbtap pid=74 tid=78 transfer=ffff880000000001 event=S
ffff880000000001 8446644857 S Ci:1:004:00 -115 8 = 80060001 00001200
# usbtap pid=203 tid=215 event=H-enter
# usbtap pid=203 tid=207 transfer=ffff880000000000 event=S
ffff880000000000 8462545120 S Ci:1:004:00 -115 8 = 80060001 00001200
# usbtap pid=203 tid=207 transfer=ffff880000000001 event=S
ffff880000000001 8462839436 S Ci:1:004:00 -115 8 = 80060001 00001200
```

The PIDs are local to the contained process namespace. In each of the two
Wine process lifetimes:

1. a dedicated thread entered the exact `libusb_handle_events()` call;
2. another thread submitted two standard IN `GET_DESCRIPTOR(Device)` requests
   for 18 bytes;
3. libusb accepted both requests (`S`), with no immediate `E` error;
4. no `C` callback occurred; and
5. the event-handler call produced no `H-return` before bounded process
   teardown.

This directly confirms the v2 timing inference: the reset 0/1 transfer IDs
belong to two separate processes. It also proves that Wine did start its
libusb event handler and that the handler remained inside libusb while the
descriptor requests were outstanding. Four accepted transfers produced no
completion event during the observed intervals.

`libusb_handle_events()` is intentionally blocking and Wine gives these
transfers a zero (infinite) libusb timeout. Therefore the evidence does not
yet distinguish a USB/device request that never completed from a usbfs/libusb
notification or reap failure. Calling this a proven Wine event-loop bug would
overstate the result.

The service log again has two 100-byte `IoAllocateErrorLogEntry` attempts,
consistent with PaeDSPUSB's `Get Device Descriptor failed.` path. It has no
immediate submit error, no prior query-interface blocker, and no callback
trace. A read-only kernel-journal check covering the run found no USB, xHCI,
reset, stall, timeout, warning, or error message.

## Postflight and checkpoint

- The same device identity, configuration, authorization, speed, and interface
  ownership remained present.
- `/dev/bus/usb/001/003` remained accessible through the host-side check.
- No relevant Wine/UC/Xvfb process survived.
- The protected real prefix remained unchanged. The disposable prefix changed
  as expected from this run to `2026-08-19 00:33:48.706786759 -0700`.
- Capacity remained healthy and the run consumed zero swap.

Every copied artifact byte-matched its source in:

`out/checkpoints/live-read-event-v3-20260819T003432PDT/`

Key SHA-256 values:

- `live-service-usb.txt`:
  `4f685e2a74fe94bdac896c025c89cf6a45d9f518a19410ffd422435c1847fdca`;
- `service-install.log`:
  `c31741ef122b38ad7264f65c9c150f695940b825fb563717f262c0e8949b5b08`;
- `service-loader.log`:
  `227cd5ae07760606ed6d318fefa2bb4fa7a94e36f035932d08d61de243f7c9c7`;
- `probe.log`:
  `74c9bc89c032995f8c92475ca61ba052cd806169dc592dee76db9a178e3f4018`;
- `usbtap.so`:
  `bfc1a6ff8553c65e207c240eef8fdc59b50ef7ba8e9c7d89961d81ee6f48dd42`.

## Gate

This one-run authorization is consumed. Preserve the new capture and do not
retry live-read without another explicit authorization.

The next investigation should remain offline first. The safest discriminator
is to stage libusb's own debug logging or narrowly instrument usbfs
submit/poll/reap behavior, validate that instrumentation without hardware, and
only then request another bounded live-read. Do not introduce a timeout,
interrupt the event handler, detach kernel drivers, claim an interface, or
send a control write merely to force progress; those would change behavior
rather than observe it.
