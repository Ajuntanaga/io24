# Autonomous Host acceptance scope

Opened: 2026-09-13T22:20:36-07:00

The user explicitly requested the previously proposed Host acceptance tests and
required objective evaluation without user listening or audio feedback. The
requested evidence targets are:

1. identify the behavior of per-channel DSP Amount at 0, 25, 50, 75 and 100%;
2. detect current global FX on/off and model audibility from captured audio;
3. save a known preset into an inactive block and verify recall/persistence;
4. smoke-test Solo, Auto gain, Multiband and Mix A/B at 96 kHz / 512 frames;
5. submit the collected results to a fresh subagent for independent evaluation.

Permitted for this run: local code/tests/artifacts and the exact io24 USB,
control, PipeWire/ALSA, playback/capture and preset/effect operations required
by the listed tests. Preserve all prestate and restore every reversible setting.
No Wine, network, firmware, DFU, reset, install, git commit/push, or guessed
packet is permitted. A USB reset is not a substitute for a disconnected,
non-computer-powered cold boot.

The device must remain operational. Stop at or below 10% battery, on target
identity mismatch, control ownership conflict, missing restoration evidence,
audio clipping/feedback risk, or any unexpected bootloader enumeration.

