# CP34 firmware ingress/storage framing - progress

Timestamp: 2026-09-05T21:19:17-07:00
Status: locally verified offline static result; independent review remains
open; no physical-commit conclusion or live authority follows

## Result

Firmware 1.28 preserves logical `Stat` payload byte zero from accepted
`MemP/Stat` ingress through the storage wrapper and back through selected-
record recall. It does not insert, replace, skip, or expose a native little-
endian u32 value `2` before the incoming payload.

Result:
`FIRMWARE_STAT_INGRESS_RECALL_SOURCE_BOUND_LOGICAL_BYTE_ZERO_UNCHANGED_NO_PREFIX_INSERTION`.

The storage wrapper does add an eight-byte backend-address header containing
CRC32 and payload length. That header is outside the logical payload and is
consumed by the paired reader; it never reaches `message+0x1d` or structured-
state gate `0x531e0`.

## TDD record

The intended RED produced two assertion failures because
`re/cp34_firmware_ingress_storage_framing.py` did not exist. The source-bound
analyzer was then added with exact firmware identity, code-slice, instruction,
literal/vtable, direct-branch, construction/binding, argument-flow, CRC32, and
paired read/write checks. Focused GREEN passed 2/2.

The contract checks the complete report and rejects a same-size firmware image
whose final byte is changed.

## Pinned source

- Firmware application size: 1,104,448 bytes.
- SHA-256:
  `65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.
- Load base: `0x60020000`.
- Recovery source: the package span inside the hash-verified installed UC5
  module, recovered in memory only. No firmware image was emitted.

## Ingress dispatch

The root constructor retains the component at
`root+0x70 = root+0x1240`. The root vtable entry at raw `0x6d288` targets
handler `0x2f210`; that handler loads `root+0x70`, preserves the original
message argument, and dispatches through component vtable `0x600874f8` slot
`+0x18`, exact target `0x3099c`.

Handler `0x3099c` recognizes `Stat`, accepts the four normal global slots, and
calls record writer `0x3092c` at `0x30a06` after its capacity check.

## Record writer

Record writer `0x3092c` retains the incoming message in `r8`. Its fields are:

- fragment offset: u32 at message `+0x12`;
- fragment length: u16 at message `+0x17`;
- total record length: u32 at message `+0x19`;
- fragment payload: bytes at message `+0x1d`.

For fragment offset zero, `0x3093e..0x30948` first passes a pointer to the
four-byte total record length to wrapper write `0x2bfe4`. This is a separate
wrapped storage entry. The writer then advances past those four logical bytes
and the wrapper's eight-byte header.

For the payload, `0x30980` loads the exact u16 fragment length and `0x30984`
forms the exact source pointer `message+0x1d`; call
`0x30988 -> 0x2bfe4` passes both without a prefix or source transformation.

## Storage wrapper

Component constructor `0x306bc` builds its wrapper at component `+8` with
vtable `0x60086994`. That vtable binds write slot 0 to `0x2bfe4`, read slot
`+4` to `0x2c0a8`, and reports overhead eight through `0x2bf40`.

For each wrapper entry, `0x2bfe4` preserves the caller's payload pointer and
length, computes CRC32 over exactly those bytes, and emits through the backend
interface at these addresses:

```text
storage_address + 0: CRC32
storage_address + 4: payload length
storage_address + 8: payload bytes
```

This is a backend-address layout, not a claim about physical flash placement.

Paired reader `0x2c0a8` reads CRC32 and length into its own stack, verifies
the caller's capacity, reads exactly the stored length from
`storage_address+8` into the caller destination, recomputes CRC32 over the
destination, and returns the payload length only after the checks pass. The
eight-byte wrapper header is not returned to the caller.

## Backend binding and forwarding

Constructor `0x31a34` creates the backend interface subobject at object
`+0x2c` with vtable `0x600876ec`. The startup route

```text
0x31ad2 -> 0x2d660 -> 0x300ac -> 0x306b4 -> 0x2c1c0
```

binds that interface at the component wrapper's backend pointer.

Vtable slot 0 reaches `0x316dc/0x316b0`, which forwards the same storage
address, source pointer, and length to the underlying write operation and adds
only a separate flag value one. Slot `+4` reaches `0x3170c/0x316e4`, which
forwards the same address, destination, and length to read. Slot `+0xc`
reaches `0x3198c/0x3196c`; its call to `0x3665c` is a bytewise CRC32 update.

## Paired record reader and parser-visible bytes

Stored-record reader `0x30a90` uses `0x2c0a8` twice for a first fragment:

1. `0x30ab8` reads the separate four-byte total record length into message
   `+0x19`.
2. It advances by four logical bytes plus the wrapper's eight-byte overhead.
3. `0x30b16` reads the payload into message `+0x1d`.

The sealed recall stage then copies `message+0x1d` unchanged and starts the
structured-state reader at cursor zero. Therefore the parser-visible first
word is exactly `little_endian_u32(incoming_payload[0:4])`.

Conditionally, incoming bytes `7b690b70` remain those bytes and reach the gate
as native word `0x700b697b`, not required word `0x00000002`.

## Reconciliation and boundary

This closes the previous firmware ingress/storage-transform uncertainty. The
separately sealed UC5 comparison establishes that current UC5's selected host
record begins with physical byte `0x7b`; firmware supplies no hidden parser-
visible prefix that could turn that into native u32 `2`.

Boundary:
`PHYSICAL_BACKEND_COMMIT_AND_UC472_SERIALIZER_REMAIN_UNOBSERVED`.

The exact UC 4.7.2 serializer output remains unavailable, so current UC5
behavior cannot be substituted for it. The connected unit's actual backend
contents, physical commit, power-cycle persistence, selected component,
Voice FX activation, and audibility remain unobserved. No framing change is
authorized or justified by this result.

## Verification

- Intended RED: 2 expected missing-analyzer failures, exit 1.
- Focused GREEN: 2 passed in 0.06 seconds, exit 0.
- Ingress/storage, recall, UC5 writer/serializer, and persistence contracts:
  32 tests and 6 subtests passed in 0.34 seconds, exit 0.
- Python compilation: analyzer and contract passed, exit 0.
- Complete hardware-free suite: 233 tests passed, one expected skip, 160.306
  seconds, exit 0.
- The suite's only diagnostic was the pre-existing unclosed-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.

## Safety

No vendor binary or firmware was loaded or executed. No firmware image was
written. No USB/device, interface claim/detach, transfer, ALSA, preset/effect,
Wine, protected-prefix, network, reset, DFU, install, staging, flash, or REAPER
action occurred. Device presence was not treated as authority. Passive sysfs
reported BAT0 at 99 percent and not charging after verification.
