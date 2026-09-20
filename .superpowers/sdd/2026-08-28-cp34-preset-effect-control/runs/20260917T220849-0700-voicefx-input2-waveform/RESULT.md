# Attempt 1 result

Status: `BLOCKED_PHYSICAL_INPUT2_STIMULUS_UNUSABLE`.

The authorized capture completed and restored exactly, but it did not test
VoiceFX. Input 2 measured about -160.4 dBFS during the nominal bursts with only
0.45 dB burst/gap contrast. The reverb positive control therefore failed on
the same silent source. This is an invalid rig result, not a VoiceFX null.

The direct cause is now identified: the exact io24 PipeWire sink was volume
0.40 and `MUTED`. `pw-play` completed successfully, but the sink emitted
silence. The device was not the cause of that silence.

Restoration passed:

- battery: 64% before, 63% after;
- all readable prestate fields matched exactly after the run;
- Host-known VoiceFX, reverb, and five write-only routes were resent;
- no gain, volume, DSP Amount, `processingChannel`, slot, phantom, link,
  firmware, reset, or DFU operation occurred.

Evidence: `attempt-1/live-report.json`, SHA-256
`fbfe60db79f98d5dbc2ac547dba61ef5c6d99c375791a40adf3782779c147f4d`.

The corrected probe now detects the exact sink mute bit and can temporarily
unmute only that sink, then re-mute it before restoring device routes. That
host system-state change needs explicit authorization before attempt 2.

## Attempt 2

Status: `BLOCKED_PHYSICAL_INPUT2_STIMULUS_UNUSABLE`.

The authorized temporary sink unmute worked and proved the physical route:
Input 2 contained all five gated bursts with 33.286 dB burst/gap contrast and
only 0.060 dB maximum inter-stage drift. Its burst level was nevertheless only
-116.872 dBFS, below the preregistered -75 dBFS floor and too low to excite the
reverb positive control. This again makes the VoiceFX result invalid, not
negative.

The PipeWire sink returned to muted with the same channel volumes. Every
readable device field matched exactly; the prior VoiceFX, reverb and write-only
routes were resent. Battery was 60% before and 59% after.

Evidence: `attempt-2/live-report.json`, SHA-256
`bc3c6565425d364a900b185393f0b511f4ec66895e5960f93e5966161c5fb256`.

The smallest correction is a temporary Input 2 gain of 60 dB after both Main
feedback routes are off. The measured source should then be about -57 dBFS.
Gain is readable and will be restored to the exact 0 dB prestate before either
feedback route is reopened. This newly added device write needs authorization.

## Attempt 3

Status: `NO_VOICEFX_DELAY_PROCESSING_DETECTED` in a valid Input-2 run.

The separately authorized Input 2 gain stage produced a strong, stable source:
-20.604 dBFS bursts, 31.299 dB burst/gap contrast, 0.004 dB maximum drift. The
shared-reverb positive control fired by +23.305 dB on the same Mix A capture,
and all three off-state gaps held within 0.159 dB.

Delay then produced no repeat at 250, 500 or 750 ms in either cycle. Cycle 1's
largest change was -0.023 dB; cycle 2's was +0.577 dB, both far below the 6 dB
detector. This is a decisive null for corrected Host Delay on the Input-2 lane,
not a rig failure and not a claim about the separately proven Input-1 model-0
lane.

Restoration passed completely: PipeWire returned to muted at the same channel
volumes, Input 2 returned from 60 to 0 dB, every readable device field matched,
and the exact Host-known VoiceFX, reverb, and five write-only routes were
resent. Battery was 57% before and 56% after.

Evidence: `attempt-3/live-report.json`, SHA-256
`cc1266fef8df88106641ca0f8d1d32b7b312b40e2462ed929fcd00123b2df504`.

The next non-redundant discriminator is the same waveform test on physical
Input 1, whose Transformer lane previously produced a live response. It needs
the cable moved from Input 2 to Input 1; no `processingChannel` mutation is
needed.
