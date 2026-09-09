# Live attempt 2 correction

Status: `INVALID_PHYSICAL_CHANNEL_CONTROL_MAPPING`

The raw `LIVE-ATTEMPT-2.json` is retained unchanged. Its `MemP/Stat(3)`
transport remains an observed one-record write to global slot 3, but the
runner then called the physical preset APIs with channel `1`. The readback
confirms that it bypassed, selected, and enabled Channel 1 (`input1SlotIndex`
`2 -> 3`) while Channel 2 stayed bypassed at selector value 0.

`processingChannel=(1,0)` assigns the singleton VoiceFX layer to physical
Input 2. It does not renumber `set_preset_enabled(channel, ...)` or
`set_preset_slot(channel, ...)`; those APIs continue to address the physical
front-panel channels. Therefore this attempt does not establish Channel-2
preset recall or Channel-2 VoiceFX audibility.

No Channel-1 preset record body was written. Only its active selector and
enable state were changed.
