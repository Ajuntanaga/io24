# Exact live plan: standalone model-0 private reverb

Status: **CANCELLED BY USER; DO NOT EXECUTE**

> The user prohibited slot 0 and requested an actual Channel-2 slot. No write
> occurred. Stock Channel-2 slots 2/3 do not own component 201, so they cannot
> replace this target. See `CHANNEL2-CONSTRAINT.md`. The exact runner now blocks
> all slot-0/1 live execution under the current instruction before opening the
> device.

## Pass condition

The only CP34 completion result is a repeatable audible wet/dry difference from
the saved model-0 private reverb after the io24 has cold-booted from a
non-computer USB power supply. A connected-host readback, transport completion,
screen indication, or sound heard only before disconnection is not a pass.

## Pinned target

- device: Revelator io24 `194f:0422`, serial `AB7C22200355`;
- firmware descriptor: `bcdDevice 0x0128`;
- storage target: native global slot 0, the first Channel-1 preset block;
- physical signal: Input 1, which is the stock/default mapping for the
  Voice-FX-owning processing chain after a cold boot;
- candidate: `slot0-model0-private-reverb.stat`, 1092 bytes, SHA-256
  `da1b3e00463ed6e51139119611ef18ba8b8286d4db41f7d6dac7290e2f041c57`;
- exact `MemP/Stat(0)` payload: one fragment, SHA-256
  `f0d7f0878f8d06cb5c3629ec452e4b688c2bb342a29975d1a26fbdf0d97e6a8c`;
- candidate state: model 0 enabled, lows `0.06`, width `0.405`, mix `0.295`;
- exact available restoration: `slot0-firmware-default.stat`, 1088 bytes,
  SHA-256
  `1cf1d764c48be395c1e5af43d6c37cc0ced2aa27ba4408d2c112b9cf251f4df7`.

The device cannot return the current full slot body. Executing this plan
therefore irreversibly replaces any unknown custom content presently in slot 0.
The project can restore the pinned firmware default, not that unknown content.
No automatic restoration is part of this trial.

## Automated boundary

`re/cp34_native_model0_slot_stage.py` will:

1. require host battery above 10 percent and the explicit unreadable-overwrite
   flag before opening the device;
2. claim only the normal io24 control interface through the existing `Io24`
   constructor, including its endpoint clear and vendor capability reads;
3. pin serial and firmware, then read the exposed `JaSt` baseline;
4. refuse stereo link or a Channel-1 selector outside owning pair 0/1;
5. bypass Channel 1 while staging and, if slot 0 is currently selected, move
   temporarily to slot 1 and verify that state before any record write, creating
   an unambiguous later application edge;
6. send exactly one validated `MemP/Stat(0)` record fragment;
7. route the shared Voice FX processing chain to physical Input 1;
8. command two-block preset mode, select slot 0, and enable Channel 1;
9. read back the exposed slot, enable, routing, and link state, close the
   interface, and leave the candidate selected for listening.

It will not use Wine, Universal Control, ALSA, playback, capture, stereo link,
gain, phantom power, mixer routing, shared block-202 reverb, reset, DFU,
firmware, installation, network, or GitHub. It cannot read back stored slot
bytes and it will not label the write physically committed or audible.

## Human acceptance sequence

Before execution, connect a reliable voice or instrument source to physical
Input 1 and headphones or a safely lowered analogue monitor to the io24.

After the staged result reports `STAGED_FOR_STANDALONE_LISTENING`:

1. With the computer still attached, confirm direct input is present and note
   whether the effect is audible. This is diagnostic only.
2. Disconnect the io24 from the computer so the device loses bus power.
3. Connect it to a non-computer USB supply and allow a complete cold boot. Keep
   the Input-1 source and headphones/analogue output attached.
4. Use the **Channel 1 Preset** control on the unit. A short press moves between
   the two blocks when two-block mode is present; a long press toggles
   enable/bypass. Compare wet and dry states more than once.
5. Report only a reproducible audible difference as success. If the screen has
   one block, the preset cannot be selected, direct audio is absent, or the
   result stays dry, report that observation rather than trying additional
   host or device commands.

No second write, restoration, alternate input, shared-reverb fallback, or
firmware action is authorized by this plan.
