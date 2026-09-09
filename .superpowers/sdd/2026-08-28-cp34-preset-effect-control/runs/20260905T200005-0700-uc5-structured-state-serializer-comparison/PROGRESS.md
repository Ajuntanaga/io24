# CP34 UC 5.0 structured-state serializer comparison - progress

Timestamp: 2026-09-05T20:17:07-07:00
Status: locally verified offline static comparison; independent review remains
open; no UC 4.7.2 or live-device conclusion follows

## TDD record

The initial focused run produced two assertion failures for the intended
reason: `re/cp34_uc5_serializer_comparison.py` did not exist. The first
implementation made the same-size hash-rejection test pass and exposed one
incorrect LEA instruction-id check in the main path. Correcting that check and
adding explicit zero-state anchors produced focused GREEN at 2/2.

The regression rejects a same-size unpinned image and checks the exact report
for the snapshot/send call pair, selected-record arithmetic, sender vtable,
serializer output binding, empty-name archive opener, first emitted byte,
record-copy import, and queue handoff.

## Pinned source

- Installed comparison module:
  `/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll`
- Size: 4,984,704 bytes.
- SHA-256:
  `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`.
- PE32+ image base: `0x180000000`.

This is the installed UC 5.0 comparison module. It is not the missing
4,979,672-byte UC 4.7.2 source.

## Source-bound path

1. One host path passes the same slot in `r14d` to snapshot call
   `0x18004239c -> 0x180042840`, checks success, and then calls
   `0x1800423b3 -> 0x180042940` to send it.
2. Snapshot function `0x180042840` resolves the selected record through
   `0x180042888 -> 0x1800427e0`. The returned record moves from `rax` to
   serializer output argument `rcx`, while the controller becomes source
   argument `rdx`, at `0x180042893 -> 0x18002e9e0`.
3. Sender `0x180042940` validates the slot, selects
   `[controller+0x2d8] + slot*0x38`, passes that record in `r9`, constructs
   `{Stat,slot}` and `{Appl,0}`, and invokes virtual slot `+0x10` on
   `controller+0x308`.
4. The controller constructor forms `+0x308` as `+0x2d0+0x38` and installs
   vtable `0x18043a5b0`. Its `+0x10` word is exact target `0x180052270`.
5. Serializer `0x18002e9e0` captures output record `rcx` in `r14`, resets the
   record, explicitly clears `[r14+0x30]`, binds `r14` as the archive writer's
   output, zeros the name arguments, and makes direct call
   `0x18002ec07 -> 0x180069c40`.
6. Archive opener `0x180069c40` resolves the null name to a pinned empty
   string. Its zero-length branch at `0x180069c76` lands at `0x180069d96`,
   writes byte `0x7b` (`{`), sets length one, and invokes writer slot `+0x8`
   at `0x180069dae`.
7. Sender `0x180052270` builds `MemP` length `0x7ec`, captures the selected
   record from `r9`, reads record length `+0x30` and data pointer `+0x10`, and
   copies the first fragment through a thunk whose PE import resolves to
   `memcpy`. It queues the envelope at
   `0x18005238e -> 0x1800546b0`.

Result:
`UC5_SAVE_SERIALIZER_SOURCE_BOUND_TAGGED_MAP_OPENER_NOT_NATIVE_U32_TWO`.

The first byte of the current UC5 host save-record serialization is therefore
`0x7b`, not the leading `0x02` required by a native little-endian u32 value of
two. Current UC5 does not prepend native u32 `2` in this save serializer.

## Boundary

The controlling boundary is
`UC5_ONLY_UC472_AND_FIRMWARE_RECALL_TO_LIVE_STAT_BRIDGE_UNRESOLVED`.

This result does not establish UC 4.7.2 byte behavior, because that exact
source is unavailable. It also does not prove that a stored `MemP/Stat` record
enters firmware live dispatcher `0x420bc` unchanged, that the live dispatcher
is the preset-recall consumer, or that adding a u32 prefix is correct. Physical
storage, firmware recall transformation, selected component semantics, Voice
FX activation, audibility, and custom-firmware readiness remain unresolved.

## Verification

- Intended RED: 2 failures for the missing analyzer, exit 1.
- Focused GREEN: 2 passed in 0.05 seconds, exit 0.
- Serializer plus queue-inventory contracts: 5 passed in 0.29 seconds,
  exit 0.
- Python compilation: analyzer and contract passed, exit 0.
- Complete hardware-free suite: 226 passed, one expected skip, 47 subtests
  passed in 155.19 seconds, exit 0.

## Safety and next boundary

No vendor binary was loaded or executed. No USB/device, ALSA, preset/effect,
Wine, protected-prefix, network, firmware image, reset, DFU, install, staging,
flash, or REAPER action occurred. Passive sysfs reported BAT0 at 99 percent and
charging after verification. Device presence was not treated as authority.

The exact UC 4.7.2 serializer still requires reacquisition under separate
network authority. A separate offline stage may instead trace the pinned
firmware's stored-record recall output toward the live structured-state
dispatcher. Neither route authorizes changing or replaying the Linux writer.
