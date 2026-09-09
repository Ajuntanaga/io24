# Passive usbmon reconnect window v2 — exact UAC2 RANGE captured

## Authorization and scope

The user explicitly confirmed physical readiness and renewed the one-run
authorization for the bounded passive capture. The wrapper observed only
control URBs on bus 3 with a 512-byte snap length. It did not open the io24
device node, detach or claim an interface, write USB or sysfs state, start
Universal Control, or touch the protected Wine prefix.

## Capture timeline

    capture ready:    2026-08-21 02:36:41.990 PDT
    disconnect seen:  2026-08-21 02:36:53.981 PDT
    reconnect seen:   2026-08-21 02:37:03.272 PDT at sysfs 3-1
    capture finished: 2026-08-21 02:37:15.397 PDT

The reconnected device was bus 3 device 4, VID:PID `194f:0422`, serial
`AB7C22200355`. tcpdump captured 316 control-URB events, received all 316
through the filter, and reported zero kernel drops.

## Exact Clock Source RANGE evidence

During snd-usb-audio enumeration, the device completed this count request
twice with status zero:

    setup:    a1 02 00 01 00 05 02 00
    response: 04 00

It then completed this full RANGE request twice with status zero:

    setup: a1 02 00 01 00 05 32 00

Both 50-byte responses were byte-identical:

    04 00
    44 ac 00 00 44 ac 00 00 00 00 00 00
    80 bb 00 00 80 bb 00 00 00 00 00 00
    88 58 01 00 88 58 01 00 00 00 00 00
    00 77 01 00 00 77 01 00 00 00 00 00

Decoded as UAC2 `wNumSubRanges=4`, the triplets are:

| Minimum Hz | Maximum Hz | Resolution Hz |
|---:|---:|---:|
| 44100 | 44100 | 0 |
| 48000 | 48000 | 0 |
| 88200 | 88200 | 0 |
| 96000 | 96000 | 0 |

The project parser found four matching requests total: two 2-byte count
requests and two complete 50-byte requests. An independent `tcpdump -XX`
inspection confirmed both setup packets, both status-zero completions, and
both complete byte-identical payloads directly in the pcap.

The pcap SHA-256 is
`194a4b2619e0bddcdeef2108b0969cf13c029b3d2516309123c6567437b2922d`.
The wrapper-generated `SHA256SUMS` hashes to
`0d7c71804766cc200ec1ccc238f0bdd27c924b49e3c2605936986b35f5246707`.

## Postflight

- The target is present at sysfs `3-1`, bus 3 device 4, with the expected
  serial.
- Interfaces 0 through 4 are bound to `snd-usb-audio`; interfaces 5 and 6 are
  unclaimed.
- The usbmon module was restored to its prior absent state.
- No tcpdump, udev monitor, Wine, UC, Xvfb, or io24 process remains.
- The protected prefix retained inode 3427833 and timestamp
  `2026-08-12 00:31:35.825186221 -0700`.

## Interpretation and gate

This is the exact device response that was previously unavailable from ALSA's
parsed rate list. It supports an offline, exact-tuple captured-response design
for the WineUSB `GET_RANGE` blocker without detaching snd-usb-audio. It does
not prove Wine driver progression, synchronization, or safety of any broader
operation.

No new live Wine run, interface detach or claim, select-interface behavior,
alternate-setting change, USB write, Universal Control run, Voice FX action,
or protected-prefix access is authorized by this capture. The safest next
step is offline-only: add a contract for this exact request and response while
failing closed for every other tuple and operation.
