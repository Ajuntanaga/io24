# VoiceFX Input-1 waveform run

User confirmed `Main Out L -> Input 1` and authorized the same guarded Input-1
run.

The probe plays deterministic -30 dBFS gated audio on Main L and captures
physical Input 1 plus Mix A. Before playback it mutes Input 1, disables
`line/ch1 -> Main` and `fxreturn/ch1 -> Main`, raises Input 1 from its readable
prestate to 60 dB, opens only USB playback to Main and the effect return to Mix
A, then restores the prior mute state. It temporarily unmutes only the exact
io24 PipeWire sink without changing its volume.

The measurement is shared reverb off/on/off as a same-path positive control,
then two corrected UC 4.7.2 Delay on/off cycles at 250 ms, feedback 0.65 and
Wet/Dry 1.0. Input 1 is the waveform timing reference; Delay repeats are read
from Mix A.

Cleanup runs from `finally`: re-mute PipeWire first; mute Input 1; restore its
exact gain; restore VoiceFX, reverb and all five shadow-backed write-only
routes; reopen feedback routes last; restore the original Input-1 mute state;
then compare every readable field. DSP Amount, `processingChannel`, slots,
output volumes, phantom, link, firmware, reset and DFU are untouched. Battery
at or below 10 percent blocks the run.

This is an objective test; the user does not need to listen.
