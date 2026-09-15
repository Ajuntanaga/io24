# 'VFxO' in the firmware's own shape is not the insert-FX enable

Status: `NO_VFXO_ENABLE_EFFECT_DETECTED`

Unit `AB7C22200355`, firmware `0128`, Host closed, battery 26 percent.

## Why this was run

12X ranked `'VFxO'` as candidate number one for the missing enable: "the only
candidate that explains 12S -- block 201 accepting model coefficient blobs and
producing no audio. If it is an enable, writing it should make an already-armed
model audible."

12Y tested it and reported a negative, and that negative was then **voided
twice over**: 12Z recovered the real blob layout from the firmware, and 13
showed the metric of the day did not cancel the source. The correction was
written; the retest never happened. Six weeks passed.

## The shape 12Y never sent

At fw `0x3f26e` the firmware builds the message itself, as three words, and
calls the block-201 handler `0x553d4` directly:

```
4f 78 46 56  0c 00 00 00  01 00 00 00
   'VFxO'       size 0x0c    value 1
```

The handler agrees: `ldm r1, {r0, r1, r2}` copies exactly three words to
`object+0x2860`. Contrast `'VoFx'`, which is four words with the model read
from `+0x0c`.

12Y used the parameter shape `[tag][size][index][id][value]` at 0x14 and 0x10,
so its value landed at `+0x10` while the handler reads `+0x08`. The value had
never once reached the field.

## Result

Positive control first:

| window | Main/Input-1 | MAD |
|---|---|---|
| control_gate_off_before | -0.359 dB | 0.365 |
| **control_gate_on** | **-19.912 dB** | 0.669 |
| control_gate_off_after | -0.171 dB | 0.325 |

`DIRECT_GATE_EFFECT_DETECTED`, delta **-19.647 dB** against 4.015 dB.

Ring Mod armed fully wet with `vol = 0`, so an enabled model drives both output
gains to zero. The only variable between the first two windows is one 12-byte
message:

| window | Main/Input-1 | MAD |
|---|---|---|
| armed_vfxo_untouched | -0.211 dB | 0.372 |
| armed_vfxo_1 | -0.305 dB | 0.454 |
| armed_vfxo_0 | -0.135 dB | 0.362 |

Delta **-0.132 dB** against a 2.724 dB threshold, drift +0.076 dB.

## Conclusion

`'VFxO'` is not the insert-FX enable. 12Y's verdict was right; its reasoning was
not, and the void is now properly discharged rather than left open. Candidate
number one is closed with the correct layout and a rig proven in the same
windows at -19.6 dB.

Block 201 now accepts two known tags, `'VFxO'` and `'VoFx'`, and neither
produces audio. The handler `0x553d4` compares against exactly these two before
falling through to the generic handler `0x5079c`, so the block-message space at
this entry point is enumerated and closed.

## Restoration

All probe restores returned. The probe leaves Channel 1's gate at its firmware
power-on state, so `MAIN`'s exact stored gate was re-applied afterwards. Final
readable state: ch1 slot 0 gain 30.00 dB enabled, ch2 slot 2 gain 24.29 dB,
main 0.750000, headphones 0.510000, stereo link off. Routing, preset slots, DSP
Amount and processingChannel untouched.

## Battery note

Battery fell from 59 to 26 percent across this session's runs and is
discharging. Further live work needs mains power or it will hit the 10 percent
floor.

Evidence: `live-report.json`.
