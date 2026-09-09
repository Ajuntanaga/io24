# CP34 official UC 4.7.2 serializer reconciliation - progress

Timestamp: 2026-09-06T00:33:00-07:00
Status: exact offline host serializer locally verified; independent review and
all physical-device outcomes remain open

## Source recovery

The official PreSonus/FMIC asset returned HTTP 200 in the one authorized
download. The retained 186,792,552-byte Universal Control 4.7.2.108537
installer has SHA-256
`1b5ddd6fd3ad4b93529caf8e5933bcd52b13194bdfa62652292b46ddcd980b95`,
exactly matching the historical pin.

The Nullsoft payload was decompressed as data without running the installer.
The retained 4,979,672-byte `hwaccess/dspusbdevice.dll` has SHA-256
`de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`,
also exactly matching the historical pin.

## Exact writer result

One caller passes the same `r14d` slot to snapshot
`0x180041c1c -> 0x1800420c0` and then send
`0x180041c33 -> 0x1800421c0`. Snapshot resolves the selected record and calls
serializer `0x18002e270`; the serializer returns success immediately after
that call.

Serializer `0x18002e270` resets the selected record cursor and length, installs
writer vtables `0x18043aa08/0x18043aa50`, and binds the selected record at
writer `+0x18`. Its null-name archive call reaches the zero-length branch in
`0x1800688b0`, whose first output operation supplies exactly one byte `0x7b`
through secondary writer slot `+0x8`.

That slot resolves to adapter `0x1800649a0`. It obtains the bound record and
tailcalls record append `0x180063060`. Append copies the source directly to
`record.data(+0x10) + record.cursor(+0x2c)` through the imported `memcpy`, then
advances cursor and length from zero to one. It reserves no headroom and
inserts no prefix.

The sender selects the same four-element, `0x38`-stride record collection,
passes the selected record to fragmenter `0x180050f10`, and that fragmenter
reads record data `+0x10` and length `+0x30` before queueing the `MemP/Stat`
envelope. The controlling result is
`UC472_SAVE_SERIALIZER_SOURCE_BOUND_RECORD_BYTE_ZERO_0X7B_NO_NATIVE_U32_TWO_PREFIX`.

## Firmware reconciliation

The sealed firmware ingress/storage and recall analyses show that incoming
record byte zero remains record byte zero through storage and reaches
structured-state method `0x531e0` unchanged. That method requires native
little-endian u32 value `2`, whose first byte would be `0x02`.

The exact UC 4.7.2 save record instead starts with `0x7b`. It is therefore not
eligible for that native-u32-two gate as serialized. This is source-bound host
and firmware evidence, not a claim that a physical device accepted, stored,
recalled, or applied the record.

## Verification

- TDD RED failed 2/2 on the deliberately missing analyzer.
- Focused GREEN passed 2/2.
- UC 4.7.2/UC5 writer plus firmware ingress/recall reconciliation passed 8/8.
- Direct analyzer execution and Python compilation passed.
- Complete hardware-free suite passed 238 tests, one expected skip, in
  189.613 seconds, exit 0.

The complete run emitted the pre-existing unclosed-WAV `ResourceWarning` at
`re/cp34_current_slot_survey.py:260`; it did not affect the successful exit.

## Boundary and continuation

Boundary:
`UC472_SERIALIZER_RESOLVED_DEVICE_COMMIT_RUNTIME_COMPONENT_SELECTION_AND_AUDIBILITY_REMAIN_UNOBSERVED`.

The exact host-format question is closed. Backend commit, device-resident
bytes, preset round trip, runtime component selection, Voice FX activation,
and audibility remain unobserved. Any physical read/write, preset/effect
operation, audio capture, USB action, or framing change requires its own exact
authorization; this result supplies none.

## Safety

No vendor executable or DLL was loaded. No install, Wine, access to
`/home/ajuntanaga/.wine-io24`, USB/device, interface claim/detach, transfer,
ALSA/audio, preset/effect, firmware-image, reset, DFU, flash, staging, or
REAPER action occurred. Network use was limited to the one authorized official
installer acquisition.
