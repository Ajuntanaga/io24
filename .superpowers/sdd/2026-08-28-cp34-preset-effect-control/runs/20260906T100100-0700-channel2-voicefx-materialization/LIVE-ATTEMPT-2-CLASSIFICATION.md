# Live attempt 2 correction

Status: `INVALID_PHYSICAL_CHANNEL_CONTROL_MAPPING`

The raw `LIVE-ATTEMPT-2.json` is retained unchanged. Its direct block-201
model/state writes and one `MemP/Stat(3)` transport remain observed. However,
the runner called both physical preset-control APIs with channel `1` after
VoiceFX had been assigned to Input 2. Readback proves the result: Channel 1
moved from selector 0/bypassed to selector 3/enabled, while Channel 2 stayed
on selector value 1/enabled.

VoiceFX assignment is an independent selection layer. It does not turn
physical preset-control channel 1 into Channel 2. Consequently the user's dry
listening result is contaminated as a Channel-2 slot-recall test and cannot be
used as the terminal stock-firmware result.

The `Stat(3)` record write may still have replaced global slot 3. It did not
replace either Channel-1 preset body; only Channel 1's active selector and
enable state were displaced.
