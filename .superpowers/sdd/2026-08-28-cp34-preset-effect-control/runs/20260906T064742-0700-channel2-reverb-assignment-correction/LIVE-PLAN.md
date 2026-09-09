# Exact live plan: Channel-2 slot-3 Reverb

Status: **INVALID PHYSICAL CHANNEL CONTROL MAPPING; DO NOT USE FOR ACCEPTANCE**

Attempt 2 assigned VoiceFX to Input 2 but used physical preset-control channel
1. Its readback proves the intended Channel-2 recall did not occur. The human
acceptance instructions below are cancelled for this run; see
`LIVE-ATTEMPT-2-CLASSIFICATION.md` and the corrected successor run.

Attempt 1 safely stopped at its assignment invariant. The assignment read back
as Channel 2, but firmware 1.28 also exchanged the two active slot indexes.
That behavior is now pinned at firmware offsets `0x2e77a..0x2e7bb`: the
assignment handler reads both slot values and invokes wire id 16 for target
indexes 0 and 1 in exchanged order. No preset record was written. See
`LIVE-ATTEMPT-1.json`.

The renewed attempt completed this corrected automated sequence with exit 0.
Its exact state and transport report are in `LIVE-ATTEMPT-2.json`. Do not run
the command again; perform only the human acceptance below.

## Pass condition

Success is a reproducible audible Reverb/Voice FX difference from Input 2 after
the io24 has been disconnected from the computer, cold-booted from a
non-computer USB supply, and controlled with the Channel-2 preset button.
Connected-host transport or sound alone is not a pass.

## Automated stage

The one authorized command will:

1. refuse at or below 10 percent battery;
2. open only the normal io24 control interface and pin serial
   `AB7C22200355`, `bcdDevice 0x0128`;
3. read and require stereo link off, a valid processing permutation, and each
   physical input's matching slot family, including the already-swapped state
   that attempt 1 may have left;
4. send UC's exact `Assign Voice FX = Ch2` control
   (`line/ch1/processingChannel=1` / `Pari 12`, index 0, value 1);
5. verify the firmware's exact slot-index exchange. After assignment, physical
   Input 2 and its slot-2/3 family are on processing chain 1 (wire index 0);
6. bypass that assigned chain and, if necessary, select global slot 2 through
   it so slot 3 is not active during overwrite;
7. write exactly one complete tagged `MemP/Stat(3)` factory Reverb record;
8. command two preset blocks, select global slot 3 through the processing chain
   serving physical Channel 2, enable it, and verify assignment, slot, enable,
   link, and the untouched other-chain state;
9. close the interface and leave physical Channel-2 slot 3 selected for
   listening.

It will not target or write slot 0, write any other slot, change stereo link, issue a
separate live FX parameter write, capture/play audio, power-cycle the unit,
restore unknown slot content, use Wine, reset, enter DFU, touch firmware,
install, use the network, or perform GitHub work.

The assignment handler may expose slot 0 on the non-target processing chain as
its automatic half of the slot-index exchange; this is not a slot-0 record
write or an explicit slot-0 selection. Slot 3 cannot be read back as a complete
record. The action therefore requires
explicit acceptance that its current content is unreadable and will be
replaced. A transport completion is reported only as sent; it is not called
stored or audible.

## Human acceptance

After `STAGED_FOR_STANDALONE_LISTENING`:

1. Confirm Input 2 is audible while connected; any effect heard here is only a
   diagnostic.
2. Disconnect the io24 from the computer so it fully loses bus power.
3. Cold-boot it from a non-computer USB supply with the Input-2 source and
   headphones or safely lowered analogue monitor still connected.
4. Use only the Channel-2 preset button to compare slot 3 enabled versus
   bypassed/its alternate block more than once.
5. Report a repeatable wet/dry difference as success; otherwise report the
   exact screen and audible behavior and stop without another write.
