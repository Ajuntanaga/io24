# CP34 zero-selector recall vtable correction

Timestamp: 2026-09-05T21:26:23-07:00
Status: bounded offline corrective analysis; no live authority

## Objective

Reconcile the exact receiver and vtable used by the stored-`Stat` callback's
zero/zero selector route at dispatcher calls `0x42266` and `0x42280`.
Determine whether primary device slot `+0x38` actually targets structured-
state method `0x531e0` or the primary-table target `0x3ccb4`.

Audit the older inference that combined dispatcher slot zero from raw table
`0x10cb40` with slot `+0x38` from that table without source-binding the table
to the zero-selector receiver. Supersede downstream prefix-gate conclusions
for this exact route if the object identity disproves the edge.

## Allowed

- Read-only static analysis of the exact hash-pinned firmware application,
  recovered from the installed package in memory only.
- Hardware-free corrective analyzer/tests and task-local documentation.
- Corrections to affected analyzers, tests, and authoritative handoffs.

## Forbidden

- Inferring that an unreferenced or differently bound vtable belongs to the
  primary zero-selector receiver merely because slot zero matches.
- Inferring behavior of the nonzero `{Appl,0}` selector route from the zero
  route.
- Emitting, staging, patching, flashing, or executing firmware.
- USB/device, interface claim/detach, transfer, ALSA, preset/effect, Wine or
  protected-prefix, network, install, reset, DFU, or REAPER action.

## Stop condition

Stop with a source-bound receiver-to-vtable-to-slot target for both direct
calls in the zero-selector stored-record route, plus a precise supersession
boundary for the nonzero `{Appl,0}` path and any earlier claims that depended
on `0x42266 -> 0x531e0`.
