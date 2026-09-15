# Corrected zero-output Ring-Mod discriminator

Status: `EXECUTED; HOST_SEQUENCE_SUPERSEDED`

The later authorized run is recorded at
`../20260914T152132-0700-corrected-ringmod-live/`. Its valid gate control and
flat Ring-Mod result resolve the sequence used here, but primary-handler tracing
then proved that a state frame cannot trigger deferred rebuild. Current Host
code replays the selector after bypass before sending state.

This continuation performed firmware analysis, probe implementation, tests,
and documentation only. It did not open USB, write the device, start audio or
Wine, alter system state, or execute the probe's live path.

## Why this test is decisive

Pinned firmware SHA-256:
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.

Model 3 follows installer call `0x5f1cc` to constructor `0x58920`, primary
handler `0x58db0`, and process `0x4ff6c`. The handler stores on, volume, and
mix at model offsets `+0x14`, `+0x20`, and `+0x2c`. The process computes dry
gain `volume*(1-mix)` and wet gain `2*volume*mix`; off uses dry 1 / wet 0.

The proposed active Ring-Mod call is fully wet with `vol=0`, so both active
gains are exactly zero. It should strongly collapse the normalized Main/Input-1
meter. A stable flat result, provided the same-process Channel-1 direct-gate
control fires, resolves the Host sequence used by this run. It does not rely on
the user listening and is not limited by Delay's
1.249 dB stationary-noise expectation.

## Guarded sequence

1. Validate phantom off, stereo link off, physical processing permutation 0/1,
   and Input-1 processing already enabled.
2. Save readable state and load complete Host-known Voice FX and Channel-1 gate
   restoration calls before opening USB.
3. Set safe Main/headphone volumes and Input-1 gain; run gate off/on/off control.
4. Run Ring Mod off/on/off using the then-current selector, 60 ms wait, state,
   60 ms wait, and state-replay sequence.
5. In `finally`, resend Host-known FX/gate intent and restore gain and both
   output volumes; require exact readable before/after state.

Routes, preset slots, DSP Amount, and `processingChannel` are untouched.
The live path also requires `--execute` and a new empty output directory.

## Verification

- focused static/probe contracts: 8/8 passed;
- complete hardware-free discovery: 869 passed, 1 skipped (870 total);
- only the two pre-existing ResourceWarnings appeared;
- `STATIC-ANALYSIS.json` records schema
  `cp34-ringmod-zero-output-discriminator-v1`.

Files:

- `re/cp34_ringmod_discriminator_static.py`
- `re/io24_corrected_ringmod_probe.py`
- `tests/test_cp34_ringmod_discriminator_static.py`
- `tests/test_io24_corrected_ringmod_probe.py`

## Next boundary

If the user separately authorizes exactly this live test, create a new empty
run directory and execute:

```text
python3 re/io24_corrected_ringmod_probe.py --execute --output-dir <new-empty-run-dir>
```

Without that new exact authorization, stop here.
