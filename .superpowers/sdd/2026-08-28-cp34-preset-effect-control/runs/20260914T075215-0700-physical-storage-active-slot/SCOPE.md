# CP34 physical storage and active-slot discriminator - scope

Timestamp: 2026-09-14T07:52:15-07:00

## Goal

Close the firmware storage completion boundary beneath the known
`MemP/Stat` writer, then test the one source-bound live condition absent from
the two prior native negatives: exact UC 4.7.2 writes the currently selected
slot, whereas those probes wrote inactive slot 3.

## Exact live action

- physical Channel 2 only; global slot 3 only;
- select slot 3 before every native record write;
- write native gate off / on / off, forcing a 2 -> 3 recall edge after each;
- measure existing Input-2/Main `JaSt` meters with no playback;
- write the pinned native Piano restoration while slot 3 is active;
- restore every readable control exactly.

The test does not change routing, DSP Amount, `processingChannel`, playback,
firmware, reset/DFU, Wine, network state, or any unknown command. Stop at or
below 10% battery. The user explicitly authorized this connected-device
continuation.

## Sources

- firmware 1.28 application SHA-256:
  `65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`;
- active-slot probe: `re/io24_native_gate_active_slot_probe.py`;
- physical-backend analyzer:
  `re/cp34_firmware_physical_storage_commit.py`.

