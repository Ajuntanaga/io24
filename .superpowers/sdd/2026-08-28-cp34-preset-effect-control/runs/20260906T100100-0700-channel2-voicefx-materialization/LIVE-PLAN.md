# Separately gated live plan

Status: completed with terminal stock-firmware negative after disconnected
power-cycle listening. The retained prior attempt remains invalid because it
used physical Channel 1 preset controls.

This stage is the final stock-firmware discriminator, not custom firmware. Its
default invocation performs no device operation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_channel2_voicefx_materialization_stage.py
```

The consumed one-run authorization covered:

- serial `AB7C22200355`, firmware descriptor `0x0128`;
- reading the exposed io24 state and claiming its existing control interface;
- requiring VoiceFX already assigned to physical Input 2, then reasserting that
  same assignment without accepting any exposed state change;
- bypass/select/enable operations only on physical preset-control Channel 2;
- four pinned block-201 writes in model-before-state order;
- replacement of unreadable global slot 3 with the pinned 842-byte,
  factory-derived Reverb record whose private Wet/Dry is 100%;
- recall/enable of Channel-2 slot 3;
- no slot-0 write, no stereo-link change, no firmware operation, no audio
  capture, and no Wine access;
- a battery reading above 10 percent.

The unreadable-overwrite acknowledgement remains exact:

`current Channel-2 slot 3 content is unreadable and will be replaced`

## Corrected live result

At 45 percent battery, the serial-pinned corrected runner exited 0 after four
model-before-state writes and one 842-byte maximum-wet `MemP/Stat(3)` write.
Readback retained Channel 1 at selector 0 and bypassed and left Channel 2 at
selector 3 and enabled, with VoiceFX assigned to Input 2 and stereo link off.
The device did not return a readable write reply, so this proves the intended
host sequence and exposed post-state, not physical commit or persistence. See
`LIVE-ATTEMPT-3-CORRECTED-MAX-WET.json`.

The prescribed human check was:

1. Confirm the Reverb/VoiceFX character is identifiable on Channel 2 while the
   computer is still present.
2. Disconnect the computer completely.
3. Cold-boot the io24 from a non-computer USB power source.
4. Use only the physical Channel-2 preset control to compare bypass and both
   blocks.
5. Report the exact audible result.

The user unplugged and reconnected the interface and reported no noticed
change. The maximum-wet effect was therefore not audibly present after the
power cycle, so the standalone acceptance condition failed and the terminal
stock-firmware outcome is sealed. See `STANDALONE-LISTENING-RESULT.md`. This
does not identify which internal commit/persistence/parser/activation/recall
boundary failed and does not authorize custom firmware before publication.
The completed one-run authorization does not authorize a retry or any other
device operation.
