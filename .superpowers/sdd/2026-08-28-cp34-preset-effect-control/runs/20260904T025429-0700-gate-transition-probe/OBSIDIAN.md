# io24 CP34 - Gate-observable linked path has no factory repeat

Updated: 2026-09-04T03:15:28-07:00

Live result: target `AB7C22200355` completed the one bounded linked recall and
factory gate on/off/on sequence, then restored link off. The action's readable
Channel-1 guard remained unchanged. Independent postflight confirmed flags
`0x1a1`, Channel 1 slot 0 disabled, and Channel 2 slot 3 enabled. The gate is
not readable; restoration is retained only as the exact factory write sent.

Audio result: all four monitor channels changed by approximately 48.142 dB
when the gate opened, so the capture path positively observes the gate. Each
then tracked Input 2 directly at approximately -3 dB and correlation
`0.99999542`, but its 150 ms/direct ratio was only approximately `0.00001426`
against the fixed `0.05` threshold. The result is
`NO_REPEAT_DOWNSTREAM_GATE_OFF`, strong linked-path waveform evidence without
a physical-storage or stored-record-equality claim.

Verification: eligibility passed 26/26; focused regression passed 18/18; and
the complete hardware-free suite passed 223 tests with one expected skip in
176.921 seconds. The 14-second six-channel capture has SHA-256
`9f2307056e44b909668deb4226ec2b191d1e23ade12d641996fc9669e4beafda`.

Next boundary: resolve the record-driven normal-table index or another missing
activation condition offline. No further USB/audio, gain/gate/routing,
preset/effect, firmware, Wine, install, or network authority is implied.
An unrelated REAPER process acquired the io24 ALSA capture and playback nodes
after the live work; this run did not start or touch it, and it must not be
disturbed.

Authoritative recovery: `../../RESUME.md`; detailed evidence is in this
directory's `SCOPE.md`, `LIVE-TRIAL.json`, `AUDIO-ANALYSIS.json`, `RESULT.md`,
`PROGRESS.md`, and `CHECKPOINT.sha256`.

The read-back canonical dashboard at
`Documents/Obsidian/ResearchOS/Projects/PreSonus Revelator io24 — CP34 custom-firmware recovery.md`
has SHA-256
`f12e44d5a45d939eadb2bc458b90fd8c594e0feba766fbcab5c014e027090aaf`.
