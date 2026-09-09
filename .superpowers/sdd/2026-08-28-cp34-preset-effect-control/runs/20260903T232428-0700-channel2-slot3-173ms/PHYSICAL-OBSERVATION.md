# Requested physical observation

Channel 2 now selects global slot 3. The submitted complete record is a
factory-compatible compressed Slap Echo variant with `voicefx.on = 1` and a
deliberately distinctive 173 ms delay.

When ready, feed a safe short transient or spoken syllable into **Input 2** and
report whether a repeat is audible about 0.17 seconds later. Do not operate
channel 1. The host readback shows Input 2 gain at 0 dB, so use the normal safe
source/level arrangement needed for that input; the run did not change gain,
phantom, monitor, main, or headphone settings.

Report only what you observe (for example: no signal, dry only, one repeat,
multiple repeats, or another effect). A panel icon does not identify the stored
record, so audio observation is the discriminating evidence.

## Recorded first observation

The operator reported **dry only** when touching the free patch-cable end with
a finger while it fed Input 2; no distinct repeat about 0.17 seconds later was
heard. That establishes direct monitoring for this arrangement, but not the
absence of the configured effect: finger hum/taps are not a calibrated,
isolated line-level transient. The retained result is
`PHYSICAL-OBSERVATION-RESULT.json`.

The operator later added that there may have been one delay-like moment shortly
after the native host restarted, but it occurred only once. This is retained as
`UNCONFIRMED_SINGLE_EVENT`, not promoted to audible-effect proof. The host action
was then repeated once with its final UI result captured. The operator reported
**no audible difference; dry**, so the earlier possible moment did not reproduce.
The retained result is in `HOST-ACTION-RESULT.json`.

A subsequent controlled Channel-2 selector edge moved global slot
`3 -> 2 -> 3` through the open host. The operator reported **dry only** after
the final return to slot 3. Direct audio remained audible, so the observation
does not indicate a mute or lost monitoring route; it indicates that this
native recall attempt did not make Voice FX audible. See
`RECALL-EDGE-RESULT.json`.

## Exact factory control observation

The open native host was restarted to load a test-covered action, then wrote
the byte-exact recovered factory `Slap Echo` record to Channel-2 global slot 3
and forced another `3 -> 2 -> 3` selector edge. The record is 850 bytes with
wire SHA-256
`a6c3294b62cfb3a46122a82c93514ea2aeb836280fb5d1e458707a78634f87eb`;
its Voice FX is enabled with 150 ms time, 25% feedback, and 50% wet/dry. The
host guarded Channel 1 and left output controls unchanged. The operator's
time-correlated report was **"dry all dry everytime"**: direct signal remained,
but no distinct 150 ms repeat was heard. This makes the custom 173 ms value,
title, and compressor-threshold differences poor explanations. It does not yet
separate failed record uptake from recall dispatch that never reaches the
block-201 Voice FX loader. The operator then explicitly ruled out the headphone
channel as the cause. That attestation is retained without changing any output
routing or headphone control. See `FACTORY-SLAP-ECHO-RESULT.json`.
