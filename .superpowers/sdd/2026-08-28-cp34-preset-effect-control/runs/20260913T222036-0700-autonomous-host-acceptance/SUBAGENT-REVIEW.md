# Independent result evaluation

The user-requested fresh read-only subagent reviewed the run artifacts,
classifier, acquisition runner, tests, and evidence claims after the actual
`BLOCKED_DEVICE_ABSENT` invocation.

## Findings returned

1. **High:** the initial future-live runner neither proved the anti-feedback
   route nor rejected stereo link, so its low Main/gain guard did not make
   playback safe enough.
2. **High:** it hardcoded capture channel 3 although the established Mix A
   pair is channels 3–4 and the correlated member must be calibrated.
3. **High:** a positive Host-shadow scalar plus a zero/nonzero device bit is
   not exact restoration evidence; the shadow may be stale.
4. **Medium:** linear waveform interpolation cannot by itself distinguish an
   internal parallel dry/wet implementation from a nonzero-floor gain law.
5. **Low:** the docs needed to distinguish the first unreachable PipeWire
   preflight from the healthy second one, and the 681-test run from the later
   focused status-label check.

Verdict before correction: the absent-device result and hashes were accurate,
and no live state changed, but the acquisition path was not ready for a device
and DSP Amount remained unknown. The Host was near implementation stop, not UC
functionality acceptance stop.

## One correction pass

The runner now requires exact-zero DSP Amount readback; rejects stereo link;
requires a fresh, identity-pinned, calibrated foundation that began and ended
at zero and left the exact parked anti-feedback route; uses the foundation's
measured Mix A channel; and restores the one playback-return cell it opens.
The manifest now uses valid local capture names. Classifications are renamed to
describe acoustic endpoint behavior, with dry/wet explicitly only a compatible
interpretation. The focused result after these changes is 19 passing tests.

Final verification after the correction and one time-dependent fixture repair:
687 tests passed with one expected skip in 178.624 seconds.

No second review was commissioned. No device/audio action accompanied the
correction.
