# Ring-Mod live result and selector-replay correction

Status: `LIVE_V1_NEGATIVE; HOST_V2_OFFLINE_VERIFIED; FRESH_LIVE_AUTH_REQUIRED`

## Authorized live result

The one authorized zero-output Ring-Mod A/B/A ran on serial `AB7C22200355`,
firmware `0128`, at the declared 96 kHz / 512 quantum. Battery was 55 percent
before and after. The Host and UC were closed, ALSA endpoints were closed, and
one process owned the USB writer.

The same-process Channel-1 direct-gate control changed the normalized
Main/Input-1 ratio by `-19.277711 dB` against an `11.794912 dB` threshold, with
`-0.030664 dB` drift. The observation path was sensitive.

Fully wet Ring Mod at `vol=0`, whose source-bound active dry and wet output
gains are both zero, changed the ratio by only `-0.098927 dB` against a
`2.813849 dB` threshold. Off-state drift was `+0.054058 dB`. This is a resolved
negative for the exact Host sequence transmitted by the run.

Raw immutable report: `live-report.json`, SHA-256
`9157dd84bc6d3e9f91db6870a7eeb7de484f2b5565ccb6ee085b904dc519f001`.

## Restoration correction

The raw runner reported restoration failure because readable flags changed
from 385 to 897, exactly XOR 512 (bit 9). Existing power-cycle evidence
identifies bit 9 as an unmapped session/stream flag, not user, preset, gate, or
DSP state. Every other readable field matched exactly. Host-known
Transformer-off and the exact Channel-1 gate intent were resent; no restoration
call failed. No additional corrective USB write was appropriate or performed.

The corrected classification is `USER_AND_DEVICE_CONTROL_STATE_RESTORED` in
`POSTANALYSIS.json`. Routes, preset slots, DSP Amount, and `processingChannel`
were untouched.

## Static follow-up: why the sequence failed

The run sent selector -> wait -> model state -> wait -> model-state replay.
That sequence was based on the auxiliary handler at `0x50af8`. The actual
block-201 primary message handler at `0x553d4` separates the routes:

- `VoFx` selects model 0..5 through selector `0x55388`;
- every ordinary model-state tag tail-calls generic handler `0x5079c`, which
  forwards directly to the currently installed delegate.

Therefore a model-state frame cannot revisit the selector's deferred rebuild
check. After the nominal 40 ms bypass transition, `VoFx` itself must be
replayed. The second selector call sees `block+0x39=1` and `block+0x40=0`, calls
work virtual `+0x34`, and installs the requested model synchronously.

`Io24.send_fx` now emits selector -> 60 ms -> selector replay -> model state.
`BLOCK201-STATIC-ANALYSIS.json` records schema
`cp34-block201-delegate-lifecycle-v4` and pins the primary-handler slice and
critical branches.

## Verification and next boundary

- focused sequence, preset-apply, analyzer, and probe contracts: 31 passed;
- complete hardware-free suite: 871 passed, one expected skip;
- deterministic parameter matrix regenerated for the new Host source;
- no device, firmware, USB, audio, Wine, network, commit, or push occurred
  after the authorized live process exited.

The selector-replay correction is not live-proven. Any next device operation
requires fresh exact authorization.
