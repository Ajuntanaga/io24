# Native device save repair and FX closure attempt

## Device-resident preset save repaired

The Host no longer offers a device action that is guaranteed to refuse. It
builds a complete firmware-native version-2 `Stat` body from the selected Host
scene, sends that body through the existing device-slot transport, and commits
the exact native SHA-256 to the per-device registry only after transport
returns. The menu wording is now `Save to device, block 1/2`.

The live production path wrote the existing user preset `MAIN` to inactive
Channel 1 Block 2 (global slot 1) on serial `AB7C22200355`, firmware `0128`.
One native frame was sent, the fire-and-forget transport returned zero replies,
and active slots stayed `[0, 2]`; the working sound was not selected or
recalled. Native body SHA-256:
`71d59077628129ef991464c9486d8372cbad9fe4eb9f9e46aae558a0d36630cd`.
Exact receipt: `NATIVE-SLOT-SAVE-LIVE.json`.

The native body covers HPF, gate, compressor, Standard/Passive/Vintage EQ,
limiter, and Transformer when that decoded FX model is on. Passive/Vintage
generation currently depends on the retained source-tree UC designer and DLL.
The firmware-native slot body does not contain the tagged scene's
`opt.swapcompeq` field, so this action does not prove chain-order persistence.
Firmware also provides no slot-body readback; cold-boot/front-panel recall is
the remaining persistence oracle.

## Verification

- Full hardware-free run: 881 passed and one deterministic matrix mismatch.
  The mismatch was the expected stale source hash after the source edits.
- The matrix was regenerated; its SHA-256 is
  `1d0ba2ad1fa798f8bfcd08be56fd37433ebfe510c0f38600843f165a995fd187`.
- Final affected save/FX-UI/inventory set: 167 passed plus 22 subtests.
- `git diff --check` passed.
- Stub-device paint smoke completed for every page. Presets, Routing, and Fat
  Channel were visually inspected; Routing keeps 16 px side margins and the
  rack tile reads `HPF`.

## FX remains open

The authorized `--transformer-repeatability` run passed its quiet preflight and
its direct Channel-1 gate control moved the selected bus by 19.593 dB with
0.117 dB Input-1 drift. Both Transformer cycles were stable nulls
(-0.119 dB and -0.070 dB), so repeatability was invalid and the classification
is `NO_DIRECT_BLOCK201_METER_EFFECT_DETECTED`. The report's top-level
`RESTORATION_FAILED` is solely flags `385 -> 897`; every other readable value
matched, no restoration call failed, and write-only Host FX/gate intent was
resent. Raw report: `transformer-repeatability-live/live-report.json`.

Do not call Host-side FX activation fixed. The remaining decisive experiment is
a cold boot with a stored native Transformer-on slot and no Host attached.
