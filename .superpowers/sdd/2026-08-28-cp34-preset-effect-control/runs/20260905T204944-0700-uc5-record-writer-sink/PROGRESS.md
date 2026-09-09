# CP34 UC5 record-writer sink - progress

Timestamp: 2026-09-05T21:01:39-07:00
Status: locally verified offline static result; independent review remains
open; UC5 comparison only; no live authority follows

## Result

The exact installed UC5 serializer's first logical archive byte becomes
physical byte zero of the selected `0x38`-byte record object. The writer does
not reserve, prepend, or synthesize a native little-endian u32 value `2`.

Result:
`UC5_RECORD_WRITER_SOURCE_BOUND_PHYSICAL_BYTE_ZERO_0X7B_NO_PREFIX_INSERTION`.

The empty-name archive opener supplies the single byte `0x7b`. The selected
record starts with cursor and length zero; the writer copies that byte to
`record.data + record.cursor`, then advances both cursor and length to one.

## TDD record

The intended RED produced two assertion failures because
`re/cp34_uc5_record_writer_sink.py` did not exist. The source-bound analyzer
was then added with exact PE identity, code-slice, instruction, call-edge,
RIP-relative vtable, vtable-slot, writer-object, and record-member checks.
Focused GREEN passed 2/2.

The contract checks the complete report and rejects a same-size module whose
final byte is changed.

## Pinned source

- Installed UC5 module:
  `/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll`.
- Size: 4,984,704 bytes.
- SHA-256:
  `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`.
- Image base: `0x180000000`.

This is the currently installed UC5 source. It is not the missing 4,979,672-
byte UC 4.7.2 module.

## Record and writer binding

The controller constructs four record elements at
`controller+0x340`, stores that address at `controller+0x2d8`, and uses stride
`0x38`. Element constructor `0x180030570` installs vtable `0x18043b828` and
initializes data `+0x10`, allocation `+0x18`, cursor `+0x2c`, and length
`+0x30` as an empty record.

Serializer `0x18002e9e0` captures the selected output record in `r14`. At
`0x18002ebba`, record vtable slot `+0x8` resolves to reset function
`0x1800643b0`; with zero arguments it puts zero at cursor `+0x2c`.
Instruction `0x18002ebbd` separately clears length `+0x30`.

The serializer then builds a stack writer with primary vtable
`0x18043bbd8`, secondary vtable `0x18043bc20`, and `writer+0x18 = r14`.
The secondary receiver therefore starts at `writer+8`.

## First physical byte

Archive call `0x180069dae` invokes secondary writer slot `+0x8` with source
byte `0x7b` and size one. That slot resolves to adapter `0x180065d30`:

```text
writer+8 receiver +0x10
  -> writer+0x18
  -> r14 selected record
  -> record vtable slot +0x18
  -> append 0x1800643f0
```

Append `0x1800643f0` reads cursor zero, computes destination
`record.data(+0x10) + record.cursor(+0x2c)`, and calls the PE import `memcpy`
at `0x180064470` for exactly one byte. It then advances cursor to one and
length to one. There is no destination offset, headroom reservation, or
prefix write before the copy.

Thus physical record byte zero is `0x7b`. It is not eligible to be the first
byte of native little-endian u32 `0x00000002`.

## Post-serializer path

Snapshot returns success immediately after the serializer call at
`0x180042893`. Its caller uses the same `r14d` slot for snapshot
`0x18004239c` and send `0x1800423b3`, with no intervening record mutation.
The source-bound predecessor resolves fragmenter `0x180052270`, which reads
the same record's data `+0x10` and length `+0x30`, copies it, and queues it.

## Reconciliation and boundary

The firmware recall stage proves that
`little_endian_u32(stored_record[0:4])` reaches structured-state gate
`0x531e0` unchanged and that the gate requires `0x00000002`. This UC5 stage
proves current UC5's outbound record begins with `0x7b`, not `02 00 00 00`.

Boundary:
`UC5_ONLY_UC472_AND_FIRMWARE_INGRESS_STORAGE_TRANSFORM_UNRESOLVED`.

This does not prove UC 4.7.2 emits the same record. It also does not yet prove
whether firmware `MemP/Stat` ingress writes incoming record bytes unchanged,
adds storage framing, or otherwise transforms them before recall. The
connected unit's physical record bytes, persistence, recall result, selected
component, Voice FX activation, and audibility remain unobserved.

## Verification

- Intended RED: 2 expected missing-analyzer failures, exit 1.
- Focused GREEN: 2 passed in 0.07 seconds, exit 0.
- Writer-sink, serializer, and firmware-recall contracts: 6 passed in 0.10
  seconds, exit 0.
- Direct analyzer execution on the pinned UC5 module: PASS, exit 0.
- Python compilation: analyzer and contract passed, exit 0.
- Complete hardware-free suite: 231 tests passed, one expected skip, 160.888
  seconds, exit 0.
- The suite's only diagnostic was the pre-existing unclosed-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.

## Safety

The vendor module was read as data only and never loaded or executed. No
firmware image was written. No USB/device, interface claim/detach, transfer,
ALSA, preset/effect, Wine, protected-prefix, network, reset, DFU, install,
staging, flash, or REAPER action occurred. Device presence was not treated as
authority. Passive sysfs reported BAT0 at 99 percent and not charging after
verification.
