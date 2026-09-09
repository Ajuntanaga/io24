# User observation and automatic stop

The runner sent the authorized Channel-1 Fat Channel HPF value `40 Hz`. The
user reported that the physical io24 display showed `80Hz`.

This observation arrived after the runner's 300-second human-response timeout,
so it is not present in the generated `REPORT.json` observation array. It is
retained here as user-reported front-panel evidence and is not represented as
device readback.

The runner's cleanup sent the exact 24 Hz bypass command. Post-cleanup readable
state retained Channel-1 slot 0 enabled, Channel-2 slot 2 enabled, stereo link
off, the same processing-channel permutation, and unchanged Channel-2 gain.
Channel-1 gain changed from the guarded 30 dB baseline to 33 dB during the
human-observation window. The runner has no gain-write path. Execution stopped
before the 80, 160, or 55 Hz steps; the cause of the gain change is unresolved.
