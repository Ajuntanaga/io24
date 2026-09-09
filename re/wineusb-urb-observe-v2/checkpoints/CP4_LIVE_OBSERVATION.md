# CP4 — one-run live observation complete

Completed 2026-08-19 PDT under the user's explicit one-run authorization.
The run was not retried.

## Passed gates

- Fresh preflight found exactly one `194f:0422`, serial `AB7C22200355`, at
  sysfs `1-2` and `/dev/bus/usb/001/005`, configuration 1, 480 Mbit/s.
- Interfaces 0-4 remained on `snd-usb-audio`; 5-6 remained unclaimed.
- No competing Wine, Universal Control, Xvfb, or project io24 process existed.
- CP3, the WineUSB overlay triplet, logger v6, harness, NT overlays, driver,
  inherited capture, sealed v6 sandbox, and protected prefix passed their
  integrity gates.
- A separate read-only isolation audit exposed only the exact io24 node and no
  audio, GPU, host home, session bus, or external network.
- The inherited v6 capture was preserved before service launch.

## One authorized run

`io24-wine-live-read-625692.service`, invocation
`2c5ad2102bd24c11bc1e76ed60b844f6`, ran once from
`2026-08-19T19:42:21.114016-07:00` to `19:42:51.266182-07:00`.
It exited status 1 after the bounded probe received no UCNET `DA`; it was not
retried.

The observation overlay remained fail-closed. It logged two identical class
interface requests:

```text
flags=0x3 length=256 reserved=0 request=0x02 value=0x0100 index=0x0500
```

It also logged two select-interface URBs with a null configuration handle and
zeroed interface tuple. Both functions still returned
`STATUS_NOT_IMPLEMENTED`; neither was submitted to the io24.

The capture contains 106 accepted control-IN descriptor requests and 106
status-zero callbacks, with no OUT/bulk/interrupt transfer or submit error. Its
SHA-256 is
`f7ae3a97696dfd1ceff7b511c307d054422250e481deceb7b180167538762a67`.

## Interpretation and postflight

The class tuple plus the device's UAC2 AudioControl/Clock Source descriptor
identifies a high-confidence Clock Source Sampling Frequency `RANGE` read:
`a1 02 00 01 00 05 00 01` as the eight setup-packet bytes on the wire.
This is an inferred setup packet; the fail-closed overlay did not submit it or
capture a response.

Postflight found the same device/configuration and driver ownership, no
surviving process, and unchanged protected prefix and original sealed v6
evidence. The disposable clone changed only as expected from its live service
run.

Full facts and the observed/inferred distinction are in
`../../live-read-observe-v2-20260819/MANIFEST.md`.

All evidence verifies under:

```text
/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.observe-v2-20260819/out/checkpoints/live-read-observe-v2-20260819T194220PDT/
```

Its `SHA256SUMS` file has SHA-256
`45f75278cca8a31fbb70e659efc47849d43f4160ddf0272d99efc6b779f41634`.

## Gate

The live authorization is consumed; do not retry. The next work is offline
class-interface-IN design and fake-libusb contracts. Semantic requests, device
writes, select-interface/alternate-setting behavior, claims/detach, full UC,
Voice FX, and the protected prefix remain outside this checkpoint.
