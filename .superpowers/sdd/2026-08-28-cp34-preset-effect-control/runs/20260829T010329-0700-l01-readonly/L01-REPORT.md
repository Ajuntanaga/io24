# CP34 L01 read-only discovery report

Run ID: `20260829T010329-0700-l01-readonly`

Authority: the user authorized USB identity, one interface-5 PRESTATE read
sequence, and ALSA identity/mapping on the single connected io24. No audio
playback/capture, mapped setting write, preset/effect action, Wine access,
firmware action, reset, detach, or network action was authorized or performed.

## Target identity

- Device: PreSonus Revelator IO 24, USB `194f:0422`
- Serial: `AB7C22200355`
- USB node/topology: bus 001 device 003, sysfs `1-2`
- Speed/configuration: 480 Mbit/s, configuration 1
- USB device release descriptor: `bcdDevice 1.28`
- Control path: interface 5, alternate 1, bulk OUT `0x01`, bulk IN `0x81`
- State protocol: version 1, maximum command 2048 bytes, maximum response
  2048 bytes
- Post-read interface state: alternate 0, authorized, driver unbound

## ALSA identity

- Card/device: `R24`, card 2, device 0
- Playback and capture were both `Stop`
- Kernel stream map: six channels, S32_LE container, 24 valid bits,
  44100/48000/88200/96000 Hz
- Logical channel map: `FL FR FC LFE RL RR`
- The required physical capture-channel A/B map was not exercised because L01
  did not authorize playback or capture.

## JaSt PRESTATE

`io24.py` made one interface claim and saved four state reads, all containing
503 slots. The relevant stable raw values were identical across all four reads:

- slots 38/39: raw `3`/`4`, processing chains 1/2 fed by inputs 1/2
- slots 40/41: raw `0`/`2`, channel 1 slot 0 and channel 2 slot 2
- slot 42: raw flags `385`; preset-disable bits 5 and 6 are both clear, so both
  channel presets read enabled
- slots 43/44/45: headphone `0.9800000191`, main `0.5462135673`, monitor blend
  `0.2717857361`
- slots 46/47: input gains `37.0` dB and `0.0` dB
- slot 50: raw zero; phantom power is off for both inputs

Snapshot:

- Path: `jast-snapshot.json`
- Size: 12,507 bytes
- SHA-256:
  `4f114b8a4e215e2345b196543bfa7ce020b4de9ccba6a21b4365a9432c3182e4`
- Native reader: `io24.py`, SHA-256
  `af5472545139711aa8a3ca305851888cb9af20513fd16c16e34a8b8bbe9ebfac`

## Unresolved L01 fields

- The operator has not transcribed the currently visible device-screen preset
  title or declared preset mode.
- Neither selected numeric slot is evidence that its title is `Slap Echo`.
- The physical six-channel capture map lacks an A/B proof.
- The August 23 driver shadow remains stale/unattested and incomplete for
  restoration; L02-L07 therefore remain ineligible.

Battery was 76% charging before discovery and 77% charging after the interface
read. No setting, preset, effect, audio, firmware, or restoration action
occurred.
