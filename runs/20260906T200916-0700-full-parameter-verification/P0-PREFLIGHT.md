# P0 live preflight

Timestamp: 2026-09-06T20:09:16-07:00

Status: PASS for the bounded readable-state and loopback-foundation batch.

## Authorized target

- USB product: `194f:0422` Revelator io24
- Serial: `AB7C22200355`
- `bcdDevice`: `0x0128`
- Control interface: 5, alternate setting 1
- ALSA card: `R24`, device 0, six-channel capture/playback endpoint

## Host and ownership gate

- No `io24gtk`, `io24d`, `io24-mixer`, or `ucnet_shim` controller process was
  running.
- No process owned `/dev/bus/usb/003/004`, the playback PCM, or the capture
  PCM. WirePlumber alone held `/dev/snd/controlC1`; it had no active io24 audio
  stream.
- PipeWire's io24 sink was muted and the user confirmed the monitor outputs
  were down/off.
- The durable Host write mirror was exactly `{}` (2 bytes; SHA-256
  `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a`).
- The predecessor plan checkpoint verified without a checksum error.

## Power gate

- First elevated gate: 31 percent, discharging.
- Serial-pinned read gate: 30 percent, discharging.
- Mandatory stop remains at or below 10 percent. Battery must be reread before
  every live write batch.

## Stable JaSt gate

Two consecutive, serial-pinned `GetP / Appl(0) / JaSt` reads were identical:

- reply bytes: 2040 each
- SHA-256: `1a129121ade834ce76f6f2c2b373edb80cc526d919586bc5234fe265d009a6bd`
- flags: `0x0181`
- stereo link: off
- Channel 1 preset: enabled, slot 0
- Channel 2 preset: enabled, slot 2

No `SetP` was emitted by this preflight.

## Full readable baseline

- Channel 1 gain: 35.00 dB
- Channel 2 gain: 20.29 dB
- headphone volume: 0.584
- Main volume: 0.050
- monitor blend: 0.000
- phantom: Channel 1 off, Channel 2 off
- instantaneous input levels: Channel 1 `1.906e-03`, Channel 2 `8.190e-05`

The physical Main-Left-to-Channel-2 loopback must never be energized until the
write-only `line/ch2 -> main` cell has explicitly received the off sentinel.
Channel 2 phantom must remain off for every loopback capture.

