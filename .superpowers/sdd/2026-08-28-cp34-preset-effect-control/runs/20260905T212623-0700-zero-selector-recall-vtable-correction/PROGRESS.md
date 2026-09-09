# CP34 zero-selector recall vtable correction - progress

Timestamp: 2026-09-05T23:10:14-07:00
Status: locally verified offline correction; independent review remains open;
no live authority or observable-outcome conclusion follows

## Corrected result

The stored-record callback constructs `SetP | 0 | 0 | nested Stat`. Its exact
zero/zero selector route returns primary device `0x20216660`. Construction at
`0x41580..0x415a2` installs primary vtable `0x6008d3a8`:

- raw slot zero `0x6d3a8 -> 0x420bc` enters the `Stat` dispatcher;
- raw slot `+0x38` `0x6d3e0 -> 0x3ccb4` returns true without reading any
  argument.

Dispatcher `0x420bc` captures the selected receiver in `r5`. Both callback
loads at `0x42262` and `0x4227a` use `[r5] + 0x38`, so calls `0x42266` and
`0x42280` both target `0x3ccb4`. The exact zero-selector route does not reach
structured-state method `0x531e0`.

Result:
`ZERO_SELECTOR_STAT_ROUTE_SOURCE_BOUND_PRIMARY_SLOT_0X38_NOOP_NOT_0X531E0`.

## Root cause

Raw table `0x10cb40` contains compatible entries:

- slot zero `0x10cb40 -> 0x420bc`;
- slot `+0x38` `0x10cb78 -> 0x531e0`.

The prior analysis paired these slots based on their relative position without
binding table base `0x6012cb40` to the selected receiver. That exact base
pointer occurs zero times in the pinned firmware. The constructed primary
table at `0x6008d3a8` is the source-bound table for the zero route.

## Supersession

The following older route conclusions are superseded:

- `0x42266` or `0x42280 -> 0x531e0` on zero-selector recall;
- cursor-zero accumulation bytes being consumed by `0x531e0` on that route;
- paired `r1/r3` values enabling `0x531e0` gates on that route;
- linked/unlinked call sites selecting the independently decoded Voice FX or
  channel-strip component tables without a receiver binding;
- stored recall or ingress/storage byte preservation proving a parser-visible
  first word.

The corrected stored-recall status is
`STORED_STAT_RECALL_ZERO_SELECTOR_SOURCE_BOUND_ACCUMULATION_COPY_THEN_PRIMARY_NOOP_CALLBACKS`.
The corrected ingress/storage status is
`FIRMWARE_STAT_INGRESS_STORAGE_WRAPPER_SOURCE_BOUND_LOGICAL_BYTE_ZERO_PRESERVED`.

The following narrower evidence remains valid:

- accepted `MemP/Stat` payload bytes pass unchanged through record writer
  `0x3092c`, CRC/length wrapper `0x2bfe4`, paired reader `0x2c0a8`, stored-record
  reader `0x30a90`, and the copy into primary accumulation storage;
- `0x531e0` entry/gate/component behavior is independently source-bound as
  function-local semantics;
- current UC5's selected host record begins with physical byte `0x7b`;
- none of those facts binds an actual caller to `0x531e0`.

The older sealed recall-framing and ingress/storage run directories remain
immutable historical evidence. Their route conclusions are superseded by this
run and by the updated authoritative `RESUME.md` and `EVIDENCE.md`.

## TDD and verification

- Intended RED: two failures while the corrective analyzer was absent.
- Corrective analyzer focused GREEN: 2/2.
- Intended stale-contract RED: 2 failures and 2 passes after narrowing recall
  and ingress/storage expectations.
- Corrected framing/ingress/vtable contracts: 6/6 in 0.10 seconds.
- Intended lane integration RED: missing
  `zero_selector_recall_vtable_correction` report key.
- Lane correction focused GREEN: 1/1 in 18.08 seconds.
- Route-sensitive lane contracts: 7/7 in 18.16 seconds.
- Complete firmware-static module: 47/47 in 20.54 seconds.
- Python compilation of all affected analyzers/contracts: PASS.
- Complete hardware-free suite: 235 passed, one expected skip, and 47 subtests
  in 168.44 seconds, exit 0.

The command environment printed its recurring `Failed to create stream fd`
diagnostic before tests; pytest completed successfully with exit 0.

## Boundary and continuation

Boundary:
`NONZERO_APPL_ZERO_SELECTED_RECEIVER_AND_0X531E0_CALLER_REMAIN_UNRESOLVED`.

The next safe offline question is which receiver the host `{Appl,0}` selector
chooses and whether any source-bound object construction or caller reaches
`0x531e0`. Do not infer that receiver from the zero-selector route or the
unreferenced raw table.

Physical backend commit, the exact UC 4.7.2 serializer, device-resident round
trip, selected component, Voice FX activation, and audibility remain
unobserved.

## Safety

The firmware application was recovered from the installed package in memory
only. No firmware image was emitted. No USB/device, interface claim/detach,
transfer, ALSA, preset/effect, Wine, protected-prefix, network, reset, DFU,
install, staging, flash, or REAPER action occurred. Passive sysfs reported BAT0
at 95 percent and charging.
