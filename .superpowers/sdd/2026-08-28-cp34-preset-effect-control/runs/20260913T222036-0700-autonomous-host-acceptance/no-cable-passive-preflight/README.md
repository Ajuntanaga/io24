# No-cable passive preflight

Timestamp: `2026-09-13T23:20:21-07:00`

- Device: Revelator io24 `194f:0422`, serial `AB7C22200355`.
- Battery: 97 percent, not charging.
- Live PipeWire clock: forced 96000 Hz / 512 frames.
- Physical correction: Main L is not connected to Input 2.
- Native capture probe: six channels, S32_LE, 96000 Hz.
- No playback or device-control write occurred.

`native-6ch-passive.wav` is a five-second direct ALSA capture. SHA-256:
`4745cb53424f3fa42ba48bea6a1339e379271a854e65ccd053b71d0211efce94`.

Measured levels:

| Channel | Role | RMS dBFS | Peak dBFS |
|---:|---|---:|---:|
| 1 | Input 1 | -150.67 | -133.16 |
| 2 | Input 2 | -94.25 | -80.80 |
| 3 | Mix A L | -97.25 | -83.80 |
| 4 | Mix A R | -97.25 | -83.80 |
| 5 | Mix B L | -97.25 | -83.80 |
| 6 | Mix B R | -97.25 | -83.80 |

Zero-lag correlation of Input 2 to channels 3-6 was 0.999999. The signal is
device self-noise, so this establishes an existing passive observation path
but is insufficient to classify DSP Amount without changing the scalar and
estimating transfer at each setting.

The three other files are intentional zero-byte recorder diagnostics. The two
WAV attempts failed before stream creation because the PipeWire/libsndfile
path rejected the three-channel format. The raw attempt opened against a
suspended PipeWire node but produced no frames before being interrupted.

Current blocker: GTK Host PID 160463 owns USB vendor interface 5. Direct
read-only PyUSB state access fails `EBUSY`; AT-SPI exposes no child controls.
Nothing was killed or detached. Wait for the user to close the Host, then
perform a read-only exact-zero/link/permutation/phantom preflight before any
DSP Amount write.
