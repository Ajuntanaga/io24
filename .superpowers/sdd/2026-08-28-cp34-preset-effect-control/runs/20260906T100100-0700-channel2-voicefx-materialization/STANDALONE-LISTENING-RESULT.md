# CP34 corrected standalone listening result

Timestamp: 2026-09-06T14:54:07-07:00

Status: `TERMINAL_STOCK_FIRMWARE_NO_AUDIBLE_CHANGE_AFTER_POWER_CYCLE`

## Preconditions

The immediately preceding live stage was the corrected physical-Channel-2
sequence recorded in `LIVE-ATTEMPT-3-CORRECTED-MAX-WET.json`. It sent the
pinned model-before-state transition and one 842-byte factory-derived Reverb
record with `voicefx.mix=1.0` to global slot 3. Exposed post-state left physical
Channel 2 on its second visible block, global slot 3, enabled; VoiceFX remained
assigned to Input 2. Channel 1 remained at selector 0 and bypassed.

## Human observation

After the instructed disconnection/power-cycle check, the user reported:

> I unplugged the interface and plugged it back in. I didnt notice any changes.

No audio capture or automated classifier was used. The user-observed result is
therefore no identifiable audible change after the power cycle, despite the
deliberately maximum-wet target.

## Conclusion and boundary

The user-defined standalone acceptance condition was not met. This is the
terminal result for the stock-firmware CP34 preset/VoiceFX investigation: the
corrected Linux-host sequence did not yield audible saved VoiceFX/private
reverb after power cycling the interface.

This observation does not distinguish among failed physical record commit,
nonvolatile persistence, record parsing, VoiceFX model activation, processing
gate restoration, or another stock-firmware recall boundary. It also does not
invalidate the separately observed persistence of ordinary Fat Channel state.
No retry or additional device operation is authorized by this result.

Next project stage: clean and package the Linux host for its initial GitHub
publication. Custom-firmware implementation remains deferred until after that
publication.
