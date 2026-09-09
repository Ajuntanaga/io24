---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: local-checkpoint-sealed-review-pending
workflow: offline-static-analysis
updated: 2026-09-05T18:31:26-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260905T181808-0700-structured-state-input-cursor-provenance
checkpoint_manifest: CHECKPOINT.sha256
tags:
  - project/io24
  - topic/firmware
  - topic/presets
  - practice/recovery
  - status/offline-only
  - status/review-pending
---

# PreSonus Revelator io24 - CP34 Stat input cursor

## Resume first

1. Read task-local `RESUME.md`, this run's `SCOPE.md`, and `PROGRESS.md`.
2. Verify `CHECKPOINT.sha256` from the project root.
3. Treat this dashboard as an index only. It authorizes no image, device,
   audio, Wine, network, or preset/effect action.

## Current source-bound result

- The live `Stat` dispatcher copies input-object bytes at `+0x1d` into the
  accumulation buffer at `device+0x18+fragment_offset`.
- It constructs a non-owning stream over `device+0x18`, resets cursor `+0x1c`
  to zero, and passes that stream at `0x42266`.
- The first four-byte `0x531e0` read goes through reader `0x2cbb4` and therefore
  consumes the caller-supplied accumulation-buffer bytes at offset zero.
- Result:
  `STAT_STREAM_CURSOR_ZERO_SOURCE_BOUND_FIRST_WORD_FROM_ACCUMULATION_BUFFER`.

## Consequence for the current Linux frame

The local Slap Echo `MemP/Stat` frame puts raw archive bytes `7b690b70` at the
firmware-consumed `+0x1d` position. Its first native word is `0x700b697b`, not
the required integer `2`. The direct incoming `Stat` path has no hidden cursor
advance or transform before the gate, so this generated frame is framing-
incompatible with the structured-state entry.

Physical storage, factory-recall representation, correct sender framing,
selected component identity, Voice FX activation, and audibility remain
unresolved. Do not infer that prepending `2` is sufficient.

## Verification

- Intended RED observed after correcting one initial missing-key error.
- Focused GREEN: 1/1 in 16.871s.
- Firmware-static module: 46/46 in 18.210s.
- Linux framing module: 24/24 in 0.182s.
- Complete hardware-free suite: 225 passed, one expected skip, 159.328s,
  exit 0; only the pre-existing unclosed-WAV warning appeared.
- Independent review remains open.

## Next safe action

Trace the retained UC 4.7.2 host serializer offline to source-bind the exact
leading `Stat` representation. Do not modify or replay the local device-slot
writer until that sender-side evidence exists.
