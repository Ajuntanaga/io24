# CP34 MemP/Stat writer reconciliation - progress

Timestamp: 2026-09-14T01:18:19-07:00
Status: offline implementation complete; live native acceptance not authorized

## Result

The Linux slot writer now accepts only a complete firmware-native version-2
`Stat` body. The old tagged JSON/scene writer and its JSON registry convenience
path refuse before transport.

Result:
`NATIVE_V2_STAT_WRITER_FRAMED_OFFLINE_TAGGED_SLOT_WRITER_RETIRED`.

## Why the representation changed

- Exact UC 4.7.2 `dspusbdevice.dll`: 4,979,672 bytes, SHA-256
  `de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.
- The call site at `0x180041bac..0x180041c38` waits more than 500 ms after a
  dirty active-slot edit, snapshots the current controller into the selected
  record at `0x1800420c0`, then sends it at `0x1800421c0`. This is the
  settled-state synchronizer.
- The explicit UI Store route is distinct: `StorePreset` serializes a library
  record and calls the `MemP/PrsM` sender at `0x180037250`.
- UC's settled-state serializer starts its record at physical byte `0x7b` with
  no version prefix or later mutation before fragmentation.
- Firmware 1.28 `MemP/Stat` ingress writes payload bytes unchanged, and recall
  presents them unchanged to `0x531e0`. That consumer requires the first
  little-endian word to equal `2`; tagged bytes `7b 69 0b 70` become
  `0x700b697b` and fail the gate.
- The objective 2026-09-14 inactive-slot A/B/A test independently observed the
  expected failure: selection changed, but the high-shelf body did not apply.

## Implementation

- `_build_native_slot_memp_frames()` validates the full native version-2 chunk
  record, then uses the exact existing `SetP/Appl/MemP/Stat` fragment envelope.
- `Io24.save_device_slot()` is the byte-oriented native writer.
- `Io24.save_uc_device_slot()` refuses tagged scene records before `_exec()`.
- `Io24.save_known_device_slot()` refuses before transport or registry update;
  existing JSON receipts remain historical tagged-transport evidence only.
- The specialized model-0 helper still refuses implicit construction because
  the device's current native body cannot be backed up.
- The deterministic parameter matrix and user/protocol/resume documentation now
  carry the native representation and live overwrite boundary.

## Verification

- Exact UC 4.7.2 writer-sink analyzer: passed against the pinned DLL and now
  executable-checks the 500 ms/same-slot/dirty-bit settled-state gate.
- Exact firmware-native slot analyzer: passed; all four native records retain
  version `2`, expected sizes, component directories, and hashes.
- Writer/preset/native/matrix/Host focused suite: 125 tests passed.
- Post-review writer/analyzer regression set: 80 tests passed.
- Complete hardware-free suite: 709 tests passed, one expected skip, in
  358.035 seconds. Its only diagnostic was the pre-existing unclosed-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- Python compilation and `git diff --check`: passed.

No USB/device, Wine, audio, firmware, network, or external action occurred.

## Remaining boundary

The writer is not accepted on hardware. The connected device cannot return its
current native slot body. A future live test must explicitly name the inactive
slot, exact candidate hash, pinned firmware-default restoration record, and
objective effect measurement; transport completion alone is insufficient.
