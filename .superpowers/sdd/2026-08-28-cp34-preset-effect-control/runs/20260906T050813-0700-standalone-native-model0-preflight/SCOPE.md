# Standalone native model-0 acceptance preflight

Timestamp: 2026-09-06T05:08:13-07:00
Status: offline preparation only

Update: the user prohibited slot 0 and requested an actual Channel-2 slot. The
slot-0 trial is cancelled without execution. Exact stock slots 2/3 lack
component 201 and are therefore not eligible model-0 targets. See
`CHANNEL2-CONSTRAINT.md`.

## Stopping criterion

Success requires a human-audible effect/private-reverb result recalled from
device-resident state while the io24 is no longer connected to a computer. For
the bus-powered unit, the strongest form is: disconnect it from the computer,
power it from a non-computer USB supply, recall the saved preset from the unit,
and hear the expected effect from a physical input through the unit's analogue
output or headphones.

A transport reply, connected-host audio, a selected-slot readback, or survival
after merely closing the Linux process is not sufficient.

## Offline preparation

- Build candidates only from the exact firmware 1.28 native defaults in the
  pinned UC 4.7.2 DSP module.
- Produce one candidate and one byte-exact firmware-default restoration record
  for each component-201-owning slot, 0 and 1.
- Preserve every byte of the native Fat Channel chunk and replace only the
  component-201 state with model 0 and the mapped
  `on/lows/width/lows-mirror/mix` words.
- Keep runtime input routing distinct from slot storage ownership. Voice FX can
  be directed to either physical input. The first acceptance trial uses Input 1
  because that mapping survives a stock/default cold boot without host help.
  Simultaneous two-input behavior is not required by the stopping criterion.

## Live boundary

This preflight does not enumerate, open, read, write, select, recall, capture,
power-cycle, or otherwise act on the io24. It performs no Wine, Universal
Control, ALSA, network, firmware-image, DFU, install, or GitHub action.

Before a live write, the user must explicitly accept that the current full body
of slot 0 is unreadable and cannot be backed up. Restoration can return that
slot to its exact firmware default, not to unknown current custom content. The
exact serial, battery floor, slot-0 record, Input-1 route, no-link boundary,
human audio path, standalone power transition, and saved-state disposition are
listed in `LIVE-PLAN.md` and must be authorized as one bounded trial.

## Project order after the result

1. Reach the standalone audible stopping criterion on stock firmware.
2. Clean the Linux host and prepare the public GitHub package.
3. Continue custom-firmware work privately and exclude it from the public host
   package unless the user later changes that boundary.
