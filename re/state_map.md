# io24 `JaSt` state-blob map (work in progress)

Read with `GetP / block 'Appl' idx 0 / blob 'JaSt' blobSize 0x7ec`.
Reply payload: floats begin at payload offset `0x1c` (slot 0). 503 slots total.
`slot N` ↔ payload offset `0x1c + N*4`.

Integer-typed parameters are stored as **raw int bits reinterpreted as float**
(they appear as denormals, e.g. `5.42e-43` = int 387).

## Confirmed by physical correlation

| slot | offset | value/range | meaning | evidence |
|------|--------|-------------|---------|----------|
| 46 | 0x0d4 | float 0–60 dB | **Mic/Inst ch1 preamp gain** | knob→max gave 32→60; later 60→56→48. Matches `preampgain` max=60 from descriptor tables |
| 47 | 0x0d8 | float 0–60 dB | **Mic/Inst ch2 preamp gain** | 26.8→27.8→60, identical range/behaviour to ch1 |

## Live meters (volatile every read — never treat as parameters)

slots **4,5,6,7,8,9,12,13,14,15,16,17,24,27**
(input pairs, bus meters; values ~1e-7…1e-3 at near-silence)

## Normalized knobs (0.0–1.0) — identified as a group, individual assignment TENTATIVE

| slot | offset | observed | likely |
|------|--------|----------|--------|
| 43 | 0x0c8 | 0.47 → 0.59 → 0.99 | one of headphone / main / blend |
| 44 | 0x0cc | 0.44 → 0.30 → 0.78 | one of headphone / main / blend (moved in 3 separate episodes) |
| 45 | 0x0d0 | 0.02 → 0.32 → 1.00 | one of headphone / main / blend |

Needs a one-knob-at-a-time pass to assign definitively.

## Button / enum ints — TENTATIVE

| slot | offset | observed | note |
|------|--------|----------|------|
| 40 | 0x0bc | int 0 ↔ 1 | toggled twice by a button |
| 41 | 0x0c0 | int 2 ↔ 3 | steps between 2 and 3 |
| 42 | 0x0c4 | int 387 ↔ 385 | toggles ±2 (NOT firmware version — it moves with a button) |
| 50 | 0x0e4 | int 0 ↔ 1, later 0 ↔ 256 | two distinct values seen |

## Always-1.0 slots (unity / enabled)

slots 18–35 (16 slots) all read `1.0` and never moved during panel exercise.

## Firmware-side parameter ids (different id space, for `SetP`)

From the embedded io24 firmware's flat table (ids 0..49):
`input1Gain=13`, `hpVolume=10`, plus `input1Mute`, `input1PhantomPower`,
`input1LevelMeter`, …  — these are the ids to use in a `SetP`/`'Para'` blob,
NOT the slot indices above.
