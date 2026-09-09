# io24 libusb native-debug stage v4

Prepared and validated offline on 2026-08-19 PDT after the v3 event-loop
live-read. No live-read or Wine process was started. The isolated libusb
process could not see any USB node, sysfs USB tree, or udev runtime. The
preservation audit only read prefix metadata and the existing capture; both
prefix directory timestamps and the capture's bytes and timestamp remained
unchanged.

This is a harness diagnostic stage, not a new tap binary: the hash-pinned v3
interposer remains unchanged.

## Evidence boundary

V3 proved that two Wine processes each started a dedicated thread in
`libusb_handle_events()`, while another thread submitted two accepted standard
IN `GET_DESCRIPTOR(Device)` requests. Neither process produced an immediate
submit error, callback, or event-handler return before teardown.

That does not distinguish a USB/device request that never completed from a
usbfs/libusb poll, notification, or reap failure. The next observation layer
must therefore be below the interposer callback without altering timeouts,
interrupting the event handler, claiming an interface, detaching a kernel
driver, or sending a control write.

## Selected discriminator

The installed native library is Ubuntu `libusb-1.0-0` 1.0.29-2build1:

- `/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0` SHA-256:
  `e422dc361a501e8175a94e16228704de7ca6376037fc29a0e7272e8fe2c8edc1`.

Its binary exposes the `LIBUSB_DEBUG` switch and diagnostic strings for
`op_submit_transfer`, `op_handle_events`, `reap_for_handle`, `submiturb
failed`, `reap failed`, URB status/length, and completed reaping. Level 4 is
the library's debug level and adds logging only; it does not change transfer
timeout or control flow.

`tests/uc_wine_sandbox.sh` now:

- adds `--setenv LIBUSB_DEBUG 4` only inside the outer `live-read` Bubblewrap
  block;
- fails closed inside `inner_service` unless the live-USB environment sees
  exactly level 4; and
- prints the active level before Wine starts, making the future run output
  self-identifying.

The debug stream will inherit the existing service redirections. Native
libusb diagnostics should therefore appear beside Wine evidence in
`service-install.log` and `service-loader.log`; the v3 tap continues writing
correlated `H`/`S`/`C`/`E` records to `live-service-usb.txt`.

## Empty-device contract

New files:

- `../../tests/libusb_debug_contract.c` SHA-256:
  `864ef65d14593d23bb8e90825dbb61648b2dc0ec5c75c7a5195238e4763b4faf`;
- `../../tests/libusb_debug_contract.sh` SHA-256:
  `01f366a10d61605757ba9042d23d0a2549032b33d9e9f06f6419f1120cec2351`;
- revised `../../tests/uc_wine_sandbox.sh` SHA-256:
  `2c08846757f3ad71e488503d8ac5701a23490206561b58ae0d0c917ad7a8e2bd`.

The contract first statically requires exactly one `LIBUSB_DEBUG` setting,
requires the inner fail-closed assertion, and proves that the setting is
inside a `live-read`-only block. It then compiles a small `dlopen()` lifecycle
probe and runs real libusb inside Bubblewrap with:

- a synthetic minimal `/dev` containing no `/dev/bus/usb`;
- empty `/sys`, `/run`, `/home`, and `/tmp` mounts;
- no udev runtime;
- no network namespace access; and
- only `/usr` plus the test binary mounted read-only.

The C probe independently refuses to continue if a USB node tree, sysfs USB
tree, or `/run/udev` is visible. It calls only `libusb_init()` and
`libusb_exit()`, then the shell contract requires native debug records for
both lifecycle calls.

Before the harness change, the test was observed RED at the intended gate:

```text
FAIL: expected one live-read LIBUSB_DEBUG setting, found 0
```

After the change, real libusb passed in the empty-device namespace:

```text
libusb debug empty-device contract: pass
```

`bash -n` also passes for both shell files.

## Preservation and next gate

Post-validation timestamps remained:

- protected `/home/ajuntanaga/.wine-io24`:
  `2026-08-12 00:31:35.825186221 -0700`;
- disposable prefix:
  `2026-08-19 00:33:48.706786759 -0700`;
- current v3 capture:
  `2026-08-19 00:33:48.184682528 -0700`.

No Wine/UC/Xvfb process was present after validation. The current v3 capture
and its checkpoint remain untouched.

This offline stage does not authorize another `live-read`. Before any future
run, preserve and hash-verify the v3 capture, refresh the exact device/node,
driver ownership, process, artifact, prefix, and capacity gates, then obtain a
new explicit one-run authorization. Do not retry automatically.
