# Device-slot recall and the Voice FX gate

Status: `RECALL_PATH_IMPLEMENTED_OFFLINE_LISTENING_PENDING`

## The defect

The Host had no recall. `_slot_changed` sent `set_preset_slot` alone, and the
`Host presets` list rendered each entry as inert text. Nothing anywhere in the
Host ran the device's own `Stat` load.

That is the same defect as the inaudible Voice FX. Block 201's handler at fw
`0x50af8` checks `+0x44 != 0`, `+0x39 != 0` and `+0x40 == 0` and returns having
done nothing when any of them fails — no error, no reply difference. Only the
native `Stat` structured-state loader `0x5545c` sets all three (`[+0x40]=0`,
`[+0x38]=0x0101` so byte `+0x39`=1, then `[+0x44]=1` after a valid model
selection 0..5). See PROTOCOL.md §13c and the 2026-08-31 controlling
correction.

Every direct `SetP | 201 | 'VoFx'` model and parameter write the Host sends is
therefore accepted, stored and silently discarded while that gate is shut. This
explains the whole run of negatives without needing a routing theory: the
2026-07-30 rig measuring nothing from block 201 while block 202 responded on
the same routing; the fully wet 240 ms Delay reported inaudible on 2026-09-09;
and the Detuner neutral-default correction, which was a real defect but could
not have been the reason the insert was silent.

The registry already held the record that opens the gate. Global slot 0 `MAIN`
is a Detuner body with `on=1`, `detune=1`, `mix=0.8` — the same factory Detuned
Vocal values that were being pushed directly — and the Host listed it without
offering any way to recall it.

## What changed

`io24.Io24.recall_device_slot(channel, slot)` is the new transport primitive.
It refuses a cross-channel slot and a non-integer slot before any write, fails
closed when the channel's processing state is unreadable, selects the slot,
and asserts the channel enable only when the device reports that channel
bypassed. An already-processing channel keeps its exact mix, because wire id 4
is a float whose nonzero value is write-only and re-asserting it would force a
partial mix to full. Selection precedes enable so a channel asked to process
never briefly runs the previously selected slot. `device_slot_pair()` exposes
the pairing from the single `DEVICE_SLOT_PAIRS` source.

In the Host: selecting a slot block is now a recall; each `Host presets` row
carries `Recall on device` and says whether that body's Voice FX is on; the
Voice FX section carries a `Device activation` row reading Not opened / Opened
/ Closed / Unknown; and `_observe_device_slot_recalls` notices a recall the
Host did not perform, because the unit's own Preset button runs the same load.
A first sighting of a slot index is the resting value, not a load, so only a
change counts.

## Evidence

Offline only. 17 new hardware-free contracts in
`tests/test_io24_device_slot_recall.py` cover the write order, the mix-
preserving enable, both refusals, the fail-closed read, all four gate-row
states, target following, the failed-recall path, and front-panel observation.
The 748-row parameter matrix was regenerated and two independent generations
are byte-identical.

## Boundary

No device write, recall, audio, Host launch, USB, Wine, install, network, or
firmware action occurred. `recall_device_slot` has never been executed against
hardware. Its report deliberately claims only `SENT_UNVERIFIED` selection and
`STAT_LOAD_REQUESTED`; audibility stays `UNPROVED`.

The live acceptance test this makes available, and which remains a separate
explicit authorization: recall global slot 0 `MAIN` on Channel 1 and listen. If
the gate reading is right, the Detuner becomes audible, and direct model edits
become effective afterwards. A negative there would be a real result about the
gate rather than another parameter-tuning round.
