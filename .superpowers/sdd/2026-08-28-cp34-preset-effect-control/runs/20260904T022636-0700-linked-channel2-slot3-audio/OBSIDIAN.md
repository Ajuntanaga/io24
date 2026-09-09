# io24 CP34 - Linked recall executed, audible source absent

Updated: 2026-09-04T02:41:59-07:00

Live result: target `AB7C22200355` completed Channel 2 `3 -> 2`, stereo link
on, Channel 2 `2 -> 3`, then stereo link off.  The action's Channel-1 readable
guard remained unchanged.  Independent postflight at 93 percent battery
confirmed flags `0x1a1`, Channel 1 slot 0 disabled, and Channel 2 slot 3
enabled.

Audio result: the 14-second six-channel capture completed and linked capture
channels 3-6 tracked Input 2 directly at -3 dB with no fitted 150 ms component.
Input 2 was only -97.15 dBFS RMS / -83.66 dBFS peak, while factory Slap Echo's
gate is on at -47.5 dBFS.  Therefore the result is
`UNPROVED_NO_ABOVE_GATE_STIMULUS`, not an audible dry verdict.

Verification: 208 hardware-free tests passed with one expected skip in
196.907 seconds.  No playback, routing, gain, gate, preset-record, firmware,
reset, DFU, install, Wine, or network action occurred.

Next boundary: a known safe physical source into Input 2, or separately
authorized/restorable gain or gate changes.  Do not infer either authority from
this completed run.

Authoritative recovery: `../../RESUME.md`; detailed evidence is in this
directory's `SCOPE.md`, `LIVE-TRIAL.json`, `AUDIO-ANALYSIS.json`, `RESULT.md`,
`PROGRESS.md`, and `CHECKPOINT.sha256`.

The read-back canonical dashboard at
`Documents/Obsidian/ResearchOS/Projects/PreSonus Revelator io24 — CP34 custom-firmware recovery.md`
has SHA-256
`0784c8bb90cf0bdb42514b9246c74054c546eeac3c666d7e5ef587bf9683bd0a`.
