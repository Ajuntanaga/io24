# CP34 Linux factory Voice FX PRESTATE

Status: L01 read-only discovery partial; no L02-L07 action authorized or started

The current Ubuntu host is the project environment. On 2026-08-29 the user
authorized USB identity, interface-5 PRESTATE reads, and ALSA identity/mapping
on the single connected io24. L01 performed only those reads. No preset,
effect, audio stream, setting write, Wine, firmware, reset, detach, or network
action occurred. A field that was not established remains `UNRECORDED`; do not
infer it.

## Target

- Device model: PreSonus Revelator IO 24 (`194f:0422`); LIVE OBSERVED
- Serial: `AB7C22200355`; LIVE OBSERVED
- Firmware version: USB device release descriptor `bcdDevice 1.28`; LIVE
  OBSERVED, NOT INFERRED AS A SEPARATE APPLICATION-FIRMWARE REPORT
- Host OS/version: Ubuntu 26.04 LTS (Resolute Raccoon); OFFLINE RECORDED
- Host identifier: `CipherPixy`; LIVE-RUN HOST OBSERVED
- Kernel: 7.0.0-30-generic; OFFLINE RECORDED
- USB topology/node: sysfs `1-2`, bus 001 device 003, 480 Mbit/s,
  configuration 1; LIVE OBSERVED
- Control interface/alternate setting: 5/1, bulk OUT `0x01`, bulk IN `0x81`;
  LIVE VERIFIED FOR L01
- Native state-read tool/version/hash: `io24.py`, SHA-256
  `af5472545139711aa8a3ca305851888cb9af20513fd16c16e34a8b8bbe9ebfac`;
  OFFLINE PIN VERIFIED AND USED FOR L01
- Native state run: protocol 1, max command/response 2048/2048;
  `runs/20260829T010329-0700-l01-readonly/jast-snapshot.json`, 4 reads,
  503 slots, SHA-256
  `4f114b8a4e215e2345b196543bfa7ce020b4de9ccba6a21b4365a9432c3182e4`
- Audio capture tool/version: `arecord` 1.2.15.2; OFFLINE RECORDED
- ALSA card/device identity: `R24`, card 2, device 0, playback/capture both
  stopped during inventory; LIVE OBSERVED
- Sample format/rate/channel count: kernel reports S32_LE, 24 valid bits,
  44100/48000/88200/96000 Hz, 6 channels; required S32_LE/48000/6 is
  CAPABILITY VERIFIED, NOT STREAM-EXERCISED
- Capture-channel map and its A/B proof: logical ALSA map
  `FL FR FC LFE RL RR`; PHYSICAL MAP/A-B PROOF UNRECORDED
- Battery capacity/status immediately before/after L01: 76%/77%, charging

## Preset state

- Preset mode: UNRECORDED; device does not report it
- Channel 1 enabled/slot: enabled, slot 0; JaSt slot 40 raw 0 and flags bit 5
  clear in all four reads; LIVE OBSERVED
- Channel 2 enabled/slot: enabled, slot 2; JaSt slot 41 raw 2 and flags bit 6
  clear in all four reads; LIVE OBSERVED
- Processing-chain map: chain 1 <- input 1 and chain 2 <- input 2; JaSt slots
  38/39 raw 3/4 in all four reads; LIVE OBSERVED
- Declared processing channel: UNRECORDED
- Declared test slot and device-screen title: UNRECORDED
- Target title is exactly `Slap Echo`: UNRECORDED
- Target record provenance: factory JSON record 4, source SHA-256
  `89b0572dd760b77831d012e2db0568b4f4eeb158985a4ca86126be28e934c73d`;
  VERIFIED OFFLINE, UNVERIFIED ON DEVICE
- Original selected slot and enabled state: channel 1 slot 0 enabled; channel 2
  slot 2 enabled; L01 BASELINE RECORDED
- Confirmation that no slot assignment/store occurred in L01: VERIFIED BY
  PROCEDURE; READ COMMANDS ONLY

## Voice FX and audible-reference state

- Target model: Slap Echo; UNVERIFIED ON DEVICE
- Target serialized state: on=1, time=0.15, feedback=0.25, mix=0.5
- Initial target on/bypass state: both currently selected channel presets read
  enabled, but the target title is still UNRECORDED
- Input connector/source/cable: UNRECORDED
- Phantom power off confirmation: both inputs off in JaSt slot 50; LIVE OBSERVED
- Source peak level and current/level limit: UNRECORDED
- Monitor path/level and safe-start confirmation: readable controls were
  headphone 0.9800000191, main 0.5462135673, monitor blend 0.2717857361,
  input gains 37.0/0.0 dB; PHYSICAL PATH/SAFE LEVEL UNRECORDED
- Fixed impulse stimulus generator: `re/cp34_live_matrix.py`; output SHA-256
  `318786a6af910736dbe8f96d152753884dac6fe360b8ad1e8a685b3077d68142`;
  run path UNRECORDED
- Dry fixture/analyzer result/hash: hardware-free contract suite passed;
  live dry captures UNRECORDED
- Reverb positive-control parameters: UNRECORDED
- Reverb baseline and restoration provenance: UNRECORDED

## Write-only restoration ledger

- Driver shadow path/hash: `/home/ajuntanaga/.cache/io24/shadow.json`,
  SHA-256 `36f6ef20c89d2dbb7625689d002bafd9bcde18576398f8dfde9a0e9208a0fc98`,
  mtime 2026-08-23T00:58:28.962800758-07:00; OFFLINE OBSERVED
- Shadow current since last power cycle/editor use: NOT ATTESTED; INELIGIBLE
- Complete Mix A send/assign/master/pan baseline: all seven `set_send_db` rows
  present; no explicit assign/master rows; NOT CURRENT-ATTESTED
- Channel FX-mix baseline: shadow says channel 1=0.0, channel 2=0.0;
  NOT CURRENT-ATTESTED
- Reverb on/size/mix/high-pass/predelay baseline: shadow says
  false/0.1/0.0/200.0/0.02 at 48 kHz; NOT CURRENT-ATTESTED
- Any gain or monitor value to be changed and its inverse: UNRECORDED
- Forward actions paired one-to-one with inverse calls: UNRECORDED
- Ledger validator result/hash: hardware-free contract suite passed; real
  target ledger UNRECORDED

If any changed write-only value lacks an exact, current inverse, the live matrix
is ineligible. Defaults are not restoration evidence.

## Restoration check

- Original selected slot and enabled state restored: UNRECORDED
- Every mapped write replayed to its exact baseline: UNRECORDED
- Readable state equals PRESTATE: UNRECORDED
- Write-only replay limitation recorded: UNRECORDED
- Physical connection and monitor level restored: UNRECORDED
- L07 capture/log/hash: UNRECORDED
- No slot assignment, preset store, reset, or power cycle occurred: UNRECORDED
