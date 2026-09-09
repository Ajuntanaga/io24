# CP34 linked gate-transition progress

Timestamp: 2026-09-04T03:15:28-07:00
Status: one live trial completed and restored; the gate-observable linked path
contains no factory 150 ms repeat.

## Result

The run removed the earlier below-gate ambiguity without playback or a gain
change. On the pinned target, Channel 2 moved from slot 3 to slot 2 while
unlinked, stereo link was confirmed, Channel-2 slot 3 was recalled, the exact
factory gate was toggled on then off, its exact on-state was restored by write,
and stereo link was cleared. The action's final readable Channel-1 guard matched
baseline. Independent postflight confirmed flags `0x1a1`, Channel 1 disabled
on slot 0, and Channel 2 enabled on slot 3.

Every captured monitor channel changed by approximately 48.142 dB between the
gate-on and gate-off windows. The capture path therefore observes the gate.
During the gate-off window each monitor channel was an approximately -3 dB,
correlation-`0.99999542` copy of Input 2, while its fitted 150 ms/direct ratio
was only approximately `0.00001426`. The fixed positive threshold was `0.05`.
The classification is `NO_REPEAT_DOWNSTREAM_GATE_OFF`.

This is strong waveform evidence against active factory Slap Echo in the
linked recalled path. It is not proof that the complete `Stat` record is or is
not physically resident, and it does not resolve the remaining record-driven
component selection or activation condition.

## Verification

- TDD RED: 4 action, 5 analyzer, and 6 runner contracts failed before their
  implementations existed.
- Eligibility GREEN: 26/26.
- Final focused GREEN: 18/18 in 1.880 seconds.
- Full hardware-free suite: 223 tests passed, one expected skip, 176.921
  seconds, exit 0.
- Raw capture: 14 seconds, six-channel S32_LE/48 kHz, exit 0, SHA-256
  `9f2307056e44b909668deb4226ec2b191d1e23ade12d641996fc9669e4beafda`.

## Safety and next boundary

No playback, gain, routing, output, preset-content, firmware, reset, DFU,
install, Wine, or network operation occurred. The only gate writes were the
explicitly authorized factory on/off/on discriminator. Live work stopped after
the independent postflight. Continue offline by resolving the record-driven
normal-table index or another missing activation condition. Any further device
or audio action requires new exact authorization.

An unrelated REAPER process started after the live work at 03:16:54 -0700 and
now owns the io24 ALSA capture and playback nodes. It was not started or touched
by this run. Future work must recheck ownership and must not disturb it.
