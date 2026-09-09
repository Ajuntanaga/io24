# IO24 WinUSB readiness boundary v1

This lineage corrects the former assumption that Wine's USB bus enumerator is
a complete WinUSB function stack. It is an offline scope checkpoint only. No
compatibility implementation is staged or selected.

## Outcome

The CP29 function children are necessary but not sufficient for MI05/MI06.
Universal Control's hardware-access module expects a three-layer Windows
contract that the pinned Wine source does not provide:

1. Microsoft OS 1.0 descriptor translation to `USB\MS_COMP_WINUSB`;
2. a generic WinUSB function binding and device-interface registration; and
3. the fourteen `WinUsb_*` operations imported by `dspusbdevice.dll`.

The retained CP24 registry and setup trace show the direct consequence: MI05
and MI06 have only USB class compatible IDs, no driver, and no service. Wine
11.15 implements zero of the fourteen required API operations. Current Wine
master at release 11.16 has the same boundary.

## Test-first evidence

- `tests/io24_winusb_readiness.py` parses the real PE import table and IO24
  model, retained Wine registry and setup trace, and pinned Wine source.
- `tests/io24_winusb_readiness_contract.py` proves the expected three-blocker
  RED and a synthetic structural GREEN. The audit never claims behavioral
  proof or stageability.
- `logs/synthetic-contract.log` records the self-contained contract result.
- `logs/real-boundary.log` records the exact retained-artifact boundary.
- `logs/real-readiness-red.log` records the deliberate structurally-not-ready
  exit.
- `logs/retained-contracts.log` records the contained CP29 regression matrix.
- `logs/upstream-verification.log` pins the current official Wine comparison.
- `logs/legacy-capture-guard.log` records the CP30 fail-closed capture guard.

The audit does not call Wine, libusb, SetupAPI, a device node, or a prefix.

## Checkpoint

`checkpoints/CP30_WINUSB_READINESS_BOUNDARY.md` records the evidence,
correction, implications for presets/effects and firmware, implementation
order, and stop boundary. `checkpoints/CP30_SHA256SUMS` seals the local inputs.

## Explicit exclusions

There was no Wine build, staging, selector edit, Wine prefix, USB node, driver
or service load, Universal Control, Voice FX, device read, claim/detach,
alternate or configuration change, control transfer, OUT transfer, firmware
image extraction, mode transition, or write.
