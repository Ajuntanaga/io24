# Host feature smoke conclusion

The bounded smoke completed on serial `AB7C22200355` with PipeWire forced to
96 kHz / 512 frames before, during, and after the run.

- Auto Gain's real controller produced its immediate clip correction from
  30.0 to 24.0 dB, the device read back 24.0 dB, and 30.0 dB was restored.
- The passive `io24 Host Mix A` and `io24 Host Mix B` sources both reached
  `ready` against the Revelator capture node and disappeared on stop.
- The Input-1 Multiband graph published all three required nodes against the
  Revelator capture/playback pair, accepted a live ratio move, stopped, and
  removed every temporary node. The device mixer was deliberately not
  rerouted.
- Solo passed its hardware-free contracts but was not exercised against the
  device. Its first live toggle rewrites every source in a bus, while the
  current Host shadow lacks an exact value for every write-only cell; exact
  restoration would therefore be impossible.

Before PipeWire playback existed, Main and headphones were attenuated to 0.01.
Readable flags, gains, outputs, phantom/link state, and processing order 0/1
restored exactly. Mixer routes, preset slots, DSP Amount, and
`processingChannel` were untouched. No temporary node or child process
remained, and battery was 100 percent before/after.

The live run first exposed and then followed a correction to io24 PipeWire
node discovery: real `pw-cli` id lines are tab-indented, so the former parser
could return the laptop's first ALSA sink once it saw a later io24 marker. A
regression fixture reproduces the real formatting; the corrected selector
returns the exact Revelator input and output. The focused Host smoke suite
passes 168 tests plus 55 subtests.

Controlling report SHA-256:
`7713875f492c3125078fc2bd1ae607c57e5d3977e5da2be24d1055f00d57e8fd`.
