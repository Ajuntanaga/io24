# VoiceFX Input-2 waveform run

User-authorized physical path: `Main Out L -> Input 2`.

This run plays a deterministic -30 dBFS gated signal on Main L and captures
Input 2 plus Mix A. Before playback, it mutes Input 2 and disables
`line/ch2 -> Main` and `fxreturn/ch1 -> Main`, eliminating the physical
feedback loop. It then opens only the USB playback path to Main and the effect
return to Mix A.

The test performs a shared-reverb off/on/off positive control, followed by two
corrected UC 4.7.2 Delay on/off cycles. Input 2 is the timing/reference signal;
Delay repeats are measured on Mix A. It does not change gain, monitor volume,
DSP Amount, `processingChannel`, slots, phantom, link, firmware, reset, or DFU.

Every write-only mixer route must have an exact Host-shadow prestate before
the device is opened. Restoration runs from `finally`: Input 2 is muted, the
prior VoiceFX/reverb/routes are resent, the readable state is compared, and
Input 2 returns to its prior mute state last. Battery at or below 10 percent
blocks the run.

The run is objective; the user does not need to listen.

## Authorized attempt-3 amendment

Attempts 1 and 2 established that the io24 sink had been muted and, once
unmuted, that the correct physical path carried the gated waveform at only
-116.872 dBFS. The user separately authorized attempt 3 to raise only Input 2
gain from its readable 0 dB prestate to 60 dB after both Main feedback routes
are off. Cleanup re-mutes the PipeWire sink first, restores Input 2 gain to
0 dB while Input 2 is muted, and only then restores either Main route. Output
volume, DSP Amount, `processingChannel`, slots, phantom, link, firmware, reset,
and DFU remain untouched.
