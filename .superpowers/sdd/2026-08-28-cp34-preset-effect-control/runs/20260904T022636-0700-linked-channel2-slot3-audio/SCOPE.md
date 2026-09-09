# CP34 linked Channel-2 slot-3 audible trial

## Authority

The operator accepted the proposed linked positive-slot trial and explicitly
directed the assistant to perform the listening because the operator needed to
rest.  This lifted the preceding Channel-1-untouched restriction only for the
stated risk that a linked slot-3 recall could apply the complete record through
the Channel-1/common path.  The target remained Revelator io24 serial
`AB7C22200355`.

## Exact bounded operation

1. Require battery above 10 percent, exact serial, stereo link off, Channel 1
   disabled on slot 0, and Channel 2 enabled on slot 3.
2. Open one passive six-channel `S32_LE`/48 kHz ALSA capture at
   `hw:CARD=R24,DEV=0`; emit no playback stimulus.
3. Move only Channel 2 from slot 3 to slot 2 while unlinked and retain a
   three-second dry window.
4. Enable stereo link, verify it through `JaSt`, recall Channel-2 slot 3 once,
   and retain a five-second active window.
5. Clear stereo link in a `finally` path, verify link off and final state, close
   the capture, and stop all live actions.

No preset record, gain, gate, routing, output, firmware, reset, DFU, install,
Wine, network, or playback operation was authorized or performed.

## Audible-evidence boundary

The retained physical path was an open cable feeding Input 2.  The assistant
could capture and analyze that path but could not physically excite the cable.
Therefore a negative effect conclusion requires an adequate naturally present
signal.  Below-gate noise cannot establish that Voice FX would remain dry for a
listening-level source.
