# Cold-boot direct block-201 test

Status: `BLOCK201_INERT_WITH_GATE_SATISFIED_AND_PATH_OPEN`

Unit `AB7C22200355`, firmware `0128`, battery 98% throughout, Host closed. The
user physically unplugged the io24, waited ten seconds and reconnected it;
`devnum` moved 2 -> 4, confirming the device left the bus.

## Four results

### 1. Cold boot reproduces 12S, but the first run was confounded

Direct `set_fx('delay', on, 0.25 s, feedback 1.0, fully wet)` on the Voice FX
owner, read from the device as Channel 1 rather than assigned. Effect
`+0.512 dB` against a `5.96 dB` threshold: null.

That run was not well conditioned. Its baseline ratio was `-20.894 dB`, meaning
Main sat 21 dB below Input 1 -- Channel 1's own gate was closed. `MAIN` stores
a gate on at `-48.72 dB` and the probe's 60 dB preamp noise sits near
`-61 dBFS`, so the channel gate was shut and everything downstream attenuated.

### 2. The meter does see Channel-1 DSP

Positive control on the same channel, same rig, using the already verified
direct `set_gate`: **-19.475 dB** against a `5.46 dB` threshold, drift
`0.018 dB`. Its `gate_off_before` ratio was `-0.242 dB`, i.e. Main tracking
Input 1 almost exactly once the channel gate is at its power-on state.

### 3. With the path open, block 201 is inert across three models

Channel gate forced to its firmware power-on state first, so the ratio starts
near `-0.25 dB` and nothing is attenuating.

| model | off / on / off ratio dB | delta dB | threshold dB | verdict |
|---|---|---|---|---|
| delay, fully wet, feedback 1.0 | -0.241 / -0.134 / -0.278 | +0.126 | 1.78 | none |
| filters, fully wet | -0.350 / -0.409 / -0.210 | -0.129 | 2.15 | none |
| ringmod 220 Hz, fully wet | -0.261 / -0.328 / -0.293 | -0.051 | 2.18 | none |

Three different models, each fully wet, on an open path, measured by a rig
proven in the same session to resolve a Channel-1 change at 19 dB. This is a
clean negative, not an absence of sensitivity.

### 4. Selection does not re-apply a stored preset, but power-on does

After forcing the power-on gate, `recall_device_slot(1, 0)` left the ratio at
`-0.294 dB`. A genuine re-apply of `MAIN` would have closed the gate to about
`-20 dB`. Repeating the recall moved it `+0.053 dB`. So `Pari` 16 selection
does not cause the firmware to reprogram the chain from the stored body.

The same measurement proves the converse for boot: the cold-boot baseline was
`-20.894 dB`, which is exactly `MAIN`'s gate closing. **The device does hold
`MAIN` in slot 0 and does apply it at power-on.** Re-applying `MAIN`'s stored
gate directly afterwards reproduced `-19.388 dB`, confirming the interpretation
and restoring the channel.

## What this eliminates

- **Gate flags.** Construction satisfies all three, and the writes still do
  nothing.
- **Signal path.** The positive control proves Channel-1 processing reaches
  Main on this routing.

What survives is 13a: the insert-FX slot is a chain *member* that has to be
**installed**. Block 201 is present, addressable, accepts writes, and is not in
the audio chain.

## Corrections owed

- The session's earlier framing -- that a shut gate explains silent Voice FX --
  is now doubly wrong: the gate is satisfied at construction, and the writes are
  inert anyway.
- `recall_device_slot` was described as "the decoded way to run that load". It
  selects the slot index; it does **not** make the firmware reload the body.
  The Host's Presets tab should not imply otherwise.

## Restoration

Channel 1's gate was left at firmware power-on by the probes and was restored by
re-applying `MAIN`'s exact stored gate values, verified at `-19.388 dB`. Preamp
gain returned to 30.00 dB, main volume to 0.7599995732307434, Channel 2
untouched at slot 2 and 24.287769317626953 dB. Slot 0 remains selected and
enabled.

Evidence: `delay-report.json`, `channel1-gate-control.json`,
`open-path-block201.json`, `recall-reprograms-gate.json`.
