# CP34 firmware stored-record recall framing - progress

Timestamp: 2026-09-05T20:42:52-07:00
Status: locally verified offline static result; independent review remains
open; no physical-device conclusion or live authority follows

## Result

The pinned firmware's selected `Stat` recall route is byte-preserving from its
record reader to the cursor-zero structured-state parser. It does not prepend,
strip, skip, reverse, or otherwise transform the stored archive payload before
the first native-u32 read at `0x531e0`.

Result:
`STORED_STAT_RECALL_SOURCE_BOUND_BYTE_PRESERVING_NO_PREFIX_INSERTION`.

Consequently, the first word consumed at `0x531e0` is exactly
`little_endian_u32(stored_record[0:4])`. If the stored record begins with the
known Linux tagged-map bytes `7b690b70`, the consumed word is `0x700b697b`,
not the required value `2`.

This does not reveal the bytes actually stored in the connected unit and does
not establish the missing UC 4.7.2 serializer's physical record output.

## TDD record

The intended RED produced two assertion failures because
`re/cp34_firmware_recall_framing.py` did not exist. The source-bound analyzer
was then added with exact firmware identity, code-slice, instruction, literal,
vtable, and direct-branch checks. Focused GREEN passed 2/2.

The contract checks the complete report and rejects a same-size firmware image
whose final byte is changed.

## Pinned source

- Firmware application size: 1,104,448 bytes.
- SHA-256:
  `65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.
- Load base: `0x60020000`.
- Recovery source: the package span inside the hash-verified installed UC5
  module, recovered in memory only. No firmware image was emitted.

## Record reader

1. Reader `0x30be0` requires nested tag `Stat` and slot 0..3.
2. Storage reader `0x30a90` reads the four-byte stored length directly into
   message `+0x19`. Its call at `0x30b16 -> 0x2c0a8` reads payload bytes
   directly into message `+0x1d`; there is no intermediate transform.
3. When stored length is nonzero, `0x30c0c..0x30c12` returns that message.
4. The zero-length fallback selects the slot descriptor at
   `0x30c1a..0x30c26` and calls `0x30c2a -> 0x30708`. That helper likewise
   copies descriptor bytes plus fragment offset directly to message `+0x1d`.

Both storage and descriptor-fallback paths preserve the payload byte order.

## Recall wrapper and forwarding

Recall driver `0x2f0d0` passes the complete `Stat` message to callback
`0x2f8ac` with two zero metadata words. The callback constructs exactly:

```text
SetP | 0 | 0 | nested Stat message
```

The nested message starts at packet offset 12. The copy at
`0x2f8ea -> memcpy` uses the message's own length from `+0x4`.

Manager bridge `0x31674/0x3163c` preserves packet data pointer and length.
Application router `0x20790/0x20754` reaches singleton lookup `0x34cb8`, then
vtable projection `0x6d40c -> 0x3cc08` and secondary forwarder
`0x6d434 -> 0x3cc40`.

The formerly indirect edge is now source-bound:

- lazy binding `0x3d4f0` makes singleton primary `+0x13c` point to global cell
  `0x20216664`;
- initializer `0x41580` places device subobject vtable `0x6008d3f0` in that
  cell;
- its slot 0 is adjustor `0x41b6c`, which enters packet router `0x419a0`.

## Packet router and live dispatcher

Router `0x419a0` receives the packet descriptor built by `0x3cc40`. For the
recall wrapper's zero second word it takes the branch at `0x419c0`:

1. It calls the selector through device `+8`, vtable `0x6008d3fc`, adjustor
   `0x3cf20`, and selector `0x3ce98`.
2. Query word zero takes `0x3cebe -> 0x3ceec`, returning the primary live
   device unchanged.
3. Router register `r1` remains packet `+0xc`. The `SetP` comparison at
   `0x41aaa` reaches `0x41b44`, which calls primary vtable slot 0.
4. Primary vtable `0x6008d3a8` resolves slot 0 to live dispatcher `0x420bc`.

The exact route replacing the older shorthand is therefore:

```text
0x3cc40
  -> 0x41b6c/0x419a0
  -> 0x3cf20/0x3ce98
  -> 0x420bc
```

The old route's ultimate dispatcher was correct; the shorthand omitted the
source-bound packet router and selector.

## Cursor-zero handoff

Dispatcher `0x420bc` receives `r1 = packet+0xc`, so its `Stat` branch at
`0x42200` sees the original nested message. It advances only past the message
header to `Stat+0x1d` and copies those payload bytes into
`device+0x18+fragment_offset`. On completion it constructs the non-owning
reader, explicitly keeps cursor zero, and calls the source-bound `+0x38`
vtable target `0x531e0` at `0x42266`.

At `0x531e0`, the first four-byte read uses the underlying cursor reader
`0x2cbb4`; `0x53212` requires the resulting native word to equal `2`.
No recall-side step inserts that word.

## Boundary and next question

Boundary:
`PHYSICAL_STORED_BYTES_AND_UC472_SERIALIZER_REMAIN_UNOBSERVED`.

The connected unit's stored bytes, physical commit, power-cycle persistence,
selected component semantics, Voice FX activation, and audibility remain
unobserved. The exact UC 4.7.2 source remains unavailable.

The sealed UC5 comparison proves that archive opener `0x180069c40` presents
logical byte `0x7b` to writer slot `+0x8`; it did not follow that writer slot
to the record buffer. Because recall adds no framing, the next safe static
question is whether the UC5 record writer itself inserts a leading native u32
`2` before its first logical archive byte. UC5 remains comparison evidence,
not UC 4.7.2 proof.

## Verification

- Intended RED: 2 expected missing-analyzer failures, exit 1.
- Focused GREEN: 2 passed in 0.05 seconds, exit 0.
- Recall, UC5, cursor-provenance, and new framing contracts: 55 passed in
  19.66 seconds, exit 0.
- Python compilation: analyzer and contract passed, exit 0.
- Complete hardware-free suite: 229 tests passed, one expected skip, 156.897
  seconds, exit 0.
- The complete suite's only diagnostic was the pre-existing unclosed-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.

## Safety

No vendor binary or firmware was loaded or executed. No firmware image was
written. No USB/device, interface claim/detach, transfer, ALSA, preset/effect,
Wine, protected-prefix, network, reset, DFU, install, staging, flash, or REAPER
action occurred. Device presence was not treated as authority.
Passive sysfs reported BAT0 at 100 percent and full after verification.
