# CP34 Channel-2 VoiceFX materialization progress

Timestamp: 2026-09-06T14:54:07-07:00

Status: `TERMINAL_STOCK_FIRMWARE_NO_AUDIBLE_CHANGE_AFTER_POWER_CYCLE`

## Controlling result

The retained `LIVE-ATTEMPT-2.json` did send the four block-201 model/state
messages and one `MemP/Stat(3)` record, but the runner then called both physical
preset APIs with channel 1. Readback shows Channel 1 changed from selector 0,
bypassed, to selector 3, enabled, while Channel 2 was not recalled. VoiceFX
assignment is separate and does not renumber these APIs. This attempt and its
dry listening result are classified
`INVALID_PHYSICAL_CHANNEL_CONTROL_MAPPING`.

The requested restoration then returned Channel 1 to selector 0 while keeping
it bypassed. It preserved both gains, stereo-link-off, the `(1,0)` Input-2
VoiceFX assignment, and Channel-2 state. No record body was written during
restoration, and neither earlier test wrote a Channel-1 record body. Exact
readback is in `CHANNEL1-RESTORATION.json`.

## Corrected host and runner

Exact UC 4.7.2 code evaluates `processingChannel == 0` to choose which channel
object owns `voicefxopt/fxmodel`. The owner activates/selects parameter 450;
the non-owner deactivates it and selects `-1`. `voicefx.on` is a separate saved
model enable. The stock Linux host now mirrors the full order for explicit
VoiceFX loads: assign the requested physical input, select the saved model,
then apply `voicefx.on` and the model fields.

`re/cp34_channel2_reverb_slot_stage.py` now requires the exposed VoiceFX
assignment already be Input 2, reasserts the same value without permitting an
exposed state change, and sends every preset bypass/slot/enable operation to
physical Channel 2. The materialization wrapper still inserts the pinned
model-before-state sequence immediately before the one slot-3 record write. A
model/state failure leaves the record write unattempted.

The final target is no longer the quiet 29.5%-wet factory value. It is a
factory-derived 100%-wet private-reverb record, still 842 bytes, with record
SHA-256
`191a5048c4995355932609e9d5ae225f37c50d8f112966f685a11b3f2a08e79c`
and one-fragment frame SHA-256
`d8ea35050b33484444e48c3d54cf1716bce35265a0b2b92f26939ea7bdf92c1f`.

Focused verification passes 28/28 across the host apply path, corrected base
runner, materialization runner, and exact UC analyzer; the corrected Slap
wrapper passes 4/4. Two disjoint commands cover the complete suite: 254 passed,
one expected skip, and 44 subtests outside the slow survey; the survey passed
41 tests and 11 subtests. Total: 295 passed, one expected skip, 55 subtests.
The separately authorized corrected sequence ran once on serial
`AB7C22200355` at 45 percent battery and exited 0. It sent the four pinned
model-before-state writes and one maximum-wet `MemP/Stat(3)` frame. Exposed
post-state retained Channel 1 at selector 0 and bypassed, placed Channel 2 at
selector 3 and enabled, retained gains 37/24, retained the `(1,0)` Input-2
VoiceFX assignment, and retained stereo link off. The exact result is
`LIVE-ATTEMPT-3-CORRECTED-MAX-WET.json` with status
`STAGED_FOR_STANDALONE_LISTENING`.

The user then unplugged and reconnected the interface and reported no noticed
change. Because the target was deliberately 100 percent wet, that is the
terminal stock-firmware negative under the corrected Channel-2 sequence: the
user-defined audible standalone acceptance condition was not met. Exact human
evidence and its limits are in `STANDALONE-LISTENING-RESULT.md`.

The transport returned no readable reply, so the negative does not identify
whether the missing boundary is physical commit, nonvolatile persistence,
parsing, model activation, the processing gate, or recall. The one live
authorization is consumed; no retry or other device action is authorized.
Next is Linux-host cleanup and initial GitHub publication. Custom firmware
remains deferred until after that publication.
