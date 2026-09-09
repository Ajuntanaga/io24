# CP25 — WineUSB immediate-submit cleanup development

Reached offline on 2026-08-22.  CP24's complete seal first reverified.  No
Wine process or service was launched, and the live authorization consumed by
CP24 was not reused.

## Test-first evidence

The new contract was kept separate from every sealed predecessor test.  Its
first run loaded the exact CP21 Unix library through a fake libusb SONAME in a
bubblewrap namespace with unshared networking, minimal `/dev`, empty `/sys`,
private `/tmp` and `/run`, and no USB or user-runtime path.  The isolation
audit positively verified that `/dev/bus/usb`, `/sys/bus/usb`, and `/run/user`
were absent.

The first RED reproduced CP24's defect across all three asynchronous submit
families: bulk, GET_DESCRIPTOR, and vendor-interface each returned
`STATUS_PENDING`, retained `DriverContext[0]`, and failed to free the transfer;
the two control paths also failed to free their buffers.  Fourteen assertions
failed for those exact reasons.

Two further RED/GREEN cycles covered adjacent lifetime branches discovered by
the sibling audit:

- an invalid bulk pipe freed its transfer but left the pointer in
  `DriverContext[0]`; and
- deterministic, real `malloc` failure on descriptor and vendor control-buffer
  allocation freed the transfer but left the same stale cancellation handle.

The allocation test derives an address-space ceiling from `/proc/self/statm`,
leaves eight MiB of headroom for small real allocations, and requests a 64 MiB
control buffer.  It exercises the production allocator branch without
allocating physical payload memory or mocking WineUSB.

## Minimal implementation

The patch changes only `dlls/wineusb.sys/unixlib.c`.  On an immediate libusb
submission error it now:

1. clears `irp->Tail.Overlay.DriverContext[0]`;
2. sets the URB status to `USBD_STATUS_REQUEST_FAILED`;
3. frees the libusb transfer, its control buffer when present, and the transfer
   context; and
4. returns `STATUS_UNSUCCESSFUL` rather than a pending status that can never
   receive a callback.

Bulk telemetry now records the actual returned NTSTATUS.  Invalid-pipe and
control-buffer-allocation exits clear the cancellation handle before freeing
their transfer.  No new libusb API, device action, claim, detach, alternate
setting, configuration request, control transfer, or OUT path was added.

The patch applies to the CP21 source with fuzz zero.  A fresh patch-check tree
matches the development source exactly across all 12,445 regular files, with
no symlinks, `.orig`, or `.rej` files.

## Development validation

The changed translation unit built without warnings.  The new contract and
the predecessor multi-interface, pipe-observe, captured-RANGE, USB-DI, and
CP15 analyzer contracts all passed in hardware-free containment.

Development artifacts:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    93a30fce04fc59fb034d9c88b6becd9931c56892cf97f5eca7f27db99aa68264  wineusb.so

No artifact was staged or selected at CP25.
