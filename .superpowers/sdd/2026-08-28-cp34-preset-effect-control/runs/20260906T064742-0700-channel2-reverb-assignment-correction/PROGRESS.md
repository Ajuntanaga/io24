# Channel-2 Reverb assignment correction

Timestamp: 2026-09-06T06:47:42-07:00
Status: **INVALID PHYSICAL CHANNEL CONTROL MAPPING; SUPERSEDED**

Controlling correction: VoiceFX assignment is an independent ownership layer;
it does not renumber `set_preset_enabled()` or `set_preset_slot()`. Attempt 2
used channel 1 for both calls and its readback shows Channel 1 moved while
Channel 2 did not complete the intended recall. Its slot-3 transport remains
observed, but all Channel-2 recall/audibility conclusions below are withdrawn.
See `LIVE-ATTEMPT-2-CLASSIFICATION.md`.

## SUPERSEDED interpretation of live attempt 2

The renewed authorized run completed with exit 0 and status
`STAGED_FOR_STANDALONE_LISTENING`. Battery was 100 percent; serial
`AB7C22200355` and `bcdDevice 0x0128` matched. The baseline already retained
the corrected assignment, so `assignment_changed=false`: physical Input 2 was
served by processing chain 1 with global slot 2, while the other chain exposed
slot 0. The runner bypassed only the target assigned chain before transport.

Exactly one 842-byte tagged UC factory Reverb record was sent to
`MemP/Stat(3)`, frame SHA-256
`e9154a66a7691ae8e415b891eab299310a3899df9b6cb2658ebb94d99ccf4306`.
No slot-0 record write occurred. Post-state verified stereo link off, Voice FX
assigned to physical Input 2, global slot 3 selected on processing chain 1,
that chain enabled, and the other chain's slot/enable/gain/processing state
unchanged. The interface closed normally.

Transport proves only that the frame was sent. Physical commit, cold-boot
survival, front-panel Channel-2 recall, and audible effect remain pending the
user's disconnected non-computer-powered listening comparison. Exact output is
retained in `LIVE-ATTEMPT-2.json`.

## Live attempt 1 and exact correction

The authorized first run matched serial `AB7C22200355` / `bcdDevice 0x0128`
and passed the battery gate. `Assign Voice FX = Ch2` read back successfully,
but the runner stopped at `voicefx_assignment` because the physical Channel-2
slot state did not remain at the same JaSt index. It re-sent bypass and closed.
Crucially, `record_write_attempted=false`: slot 3 was not replaced and slot 0
was never a record target.

The cause is now exact rather than speculative. Firmware 1.28 code at
`0x2e77a..0x2e7bb` reads both current active slot indexes and replays wire id 16
twice in exchanged order whenever `Pari/12` changes the processing assignment.
That preserves the physical input's slot family while moving physical Input 2
onto Voice-FX-owning processing chain 1. The original runner's fake device did
not model this side effect and therefore validated the wrong invariant.

This was the mistaken correction: it treated processing chain 1 as though it
renumbered the physical Channel-2 preset API. That premise is withdrawn. The
successor runner keeps `set_preset_enabled` and `set_preset_slot` on physical
channel 2 while treating `processingChannel` only as VoiceFX ownership.

The second device action is retained in `LIVE-ATTEMPT-2.json` as invalid
historical evidence, not a completed Channel-2 stage.

## Corrected interpretation

The four version-2 records embedded in firmware are startup/default records.
Their contents show what those four defaults contain; they do not establish a
schema rule that component 201 is illegal in slots 2/3.

Three independent retained sources resolve the mistake:

1. Exact UC 4.7.2 `DEFAULT.SKIN`, member `uceasy/settings.xml`, lines 207-215,
   exposes `Assign Voice FX` as radio values on
   `line/ch1/processingChannel`: `Ch1=0`, `Ch2=1`.
2. The author's retained UC scenes have four `presets.slots` entries and all
   four contain `voicefx`, including Channel-2 slots 2/3. Their active channel
   state uses `line.ch1.processingChannel=0` and
   `line.ch2.processingChannel=1` in the ordinary Channel-1 assignment.
3. The exact UC active-slot writer emits the tagged scene-shaped record through
   `MemP/Stat`; the physical record starts with `0x7b`, not native u32 `2`.

The 2026-09-03 Channel-2 Slap Echo result retained the baseline processing map
`input1ProcessingChannel=0`, `input2ProcessingChannel=1`. It therefore never
performed `Assign Voice FX = Ch2`. Its dry observation cannot answer the
corrected workflow.

## Prepared discriminator

`re/cp34_channel2_reverb_slot_stage.py` is hardware-free by default and pins:

- Channel 2, global slot 3, Channel-2 front-panel control;
- exact serial and firmware descriptor;
- exact local factory collection SHA-256
  `89b0572dd760b77831d012e2db0568b4f4eeb158985a4ca86126be28e934c73d`;
- exact encoded Reverb record: 842 bytes, SHA-256
  `c85119953bef5fd41f83f4b60e207519e9d57c6bf174f9d8a8e7ce6a88ed65c4`;
- exact one-fragment `MemP/Stat(3)` frame SHA-256
  `e9154a66a7691ae8e415b891eab299310a3899df9b6cb2658ebb94d99ccf4306`;
- `line/ch1/processingChannel=1`, the exact UC `Ch2` assignment;
- battery above 10 percent, unreadable-overwrite acknowledgement, identity,
  firmware, stereo-link-off, slot-pair and exposed post-state gates.

Historical implementation note: this version followed the assignment exchange
but then wrongly used physical preset-control channel 1. The current successor
keeps every preset bypass, slot, and enable call on physical Channel 2.

`io24.py` now exposes UC's tagged complete-record path as
`save_device_slot()`/`save_uc_device_slot()`. Firmware-default chunk framing is
retained only as an offline structural fixture. `io24_native_stat.py` no longer
turns the four default shapes into slot ownership validation.

## Verification

Focused hardware-free verification passed 61 tests and 12 subtests. The exact
default command returns `OFFLINE_READY`, targets Channel 2 slot 3, reports
`slot_zero_targeted=false`, and makes no device access. The complete
hardware-free suite then passed 272 tests and 47 subtests with one expected
skip in 713.06 seconds, exit 0.

Physical commit, front-panel recall, power-cycle survival, and audibility remain
unproved. Apart from the bounded first attempt recorded above, no additional
USB/device action occurred; no audio, Wine, firmware, network, install, or
GitHub action occurred.
