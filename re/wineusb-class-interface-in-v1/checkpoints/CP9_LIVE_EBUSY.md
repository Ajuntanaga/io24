# CP9 — class-IN reached live usbfs and failed closed at interface ownership

Recovered and sealed on 2026-08-21 from the single authorized live-read
launched on 2026-08-19.

## One-run result

Exactly one command ran against the disposable class-IN-v1 clone. Unit
io24-wine-live-read-854561.service, invocation
cb532c4af3a04271bf4c2c4ce92affb3, completed status 1 after 38.982 seconds.
Peak memory was 105.3 MiB and swap was zero.

Containment exposed only one io24 node and no audio, GPU, host home, session
bus, or external network. The registered PreSonus service reached RUNNING,
but the read-only probe received no UCNET DA and produced no synchronize.json.
This is not synchronization.

## Decisive transfer result

The 149,021-byte capture has SHA-256:

    c05811fb8f488a3ae28574792e3951f6e4cf91fedc7a88824e4eb9af774978c5

Counts:

    control-IN submits:       96
    status-zero callbacks:    94
    immediate submit errors:   2
    control-OUT:               0
    bulk:                      0
    interrupt:                 0

The two errors are the exact CP8 class-interface-IN setup:

    a1 02 00 01 00 05 00 01

Both libusb submissions failed immediately with errno 16, EBUSY, and produced
no callback or response bytes. Wine mapped them to Input/Output Error and the
driver emitted the same 120-byte Audio Controller error record twice.
Select-interface remained unimplemented and failed closed twice.

## Root cause

This request is addressed to interface 0 because usbfs uses the low byte of
wIndex 0x0500 as the interface number. Entity ID 5 occupies the high byte.
Linux usbfs implicitly tries to claim interface 0 for an interface-recipient
class request. snd-usb-audio already owns interface 0, so USB core returns
EBUSY. Interface 5 being unclaimed does not help this request.

This advances the blocker from an unimplemented Wine URB to a confirmed Linux
interface-arbitration boundary. CP8 reached its intended native submit call;
the request itself did not reach the device.

## Verification

- CP8 SHA256SUMS still verifies completely.
- The staged WineUSB triplet and harness still match CP8.
- The active capture remains in place, preserving the harness collision gate.
- Delayed postflight found no surviving Wine, Xvfb, UC, or io24 process.
- The same serial AB7C22200355 is present, interfaces 0 through 4 remain on
  snd-usb-audio, and interfaces 5 and 6 remain unclaimed.
- The protected prefix retained inode 3427833 and timestamp
  2026-08-12 00:31:35.825186221 -0700.

Exact evidence verifies at:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.class-in-v1-20260819/out/checkpoints/live-read-class-in-v1-20260819T233401PDT/

The checkpoint SHA256SUMS file hashes to:

    8e7d4ae8dafb22c650abce9abe05a0fdcc18991b6682fcce805087c7f03c0287

## Gate

The live authorization is consumed. Do not retry, clear or move the active
capture, detach snd-usb-audio, claim interface 0, implement select-interface,
change alternate settings or timeouts, issue a USB write, run full Universal
Control or Voice FX, or touch the protected prefix.

The offline retained-evidence and current procfs search found no exact UAC2
RANGE response. Linux snd-usb-audio parses the returned subranges into a rate
table and frees the raw payload
(https://github.com/torvalds/linux/blob/master/sound/usb/format.c), so ALSA's
cached rate list cannot reconstruct the original bytes. The safest next
candidate is a separately authorized passive usbmon capture during a
user-controlled device reconnect. Do not reconnect or start that capture
without a new explicit authorization.
