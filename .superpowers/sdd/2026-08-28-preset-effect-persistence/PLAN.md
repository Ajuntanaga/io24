# Offline preset and effect persistence plan

Status: offline gates 1-4 complete and independently reviewed; gate 5 awaits evidence

## Goal

Give the user a dependable way to save, inspect, and restore all currently
controllable io24 settings and effect state, while isolating the unknown
device-resident save/Voice FX sequence for one clean future capture.

## Gate 1: host preset durability — complete

- A failed serialization leaves an existing preset byte-for-byte intact.
- Successful saves use a same-directory temporary file, file sync, atomic
  replacement, and directory sync.
- Failure cleanup and version-1 JSON load/replay are executable regressions.

## Gate 2: effect round-trip visibility — complete

- A hardware-free save-load-save test exercises the real setters and replay.
- Pure inspection reports reverb, Voice FX intent, per-channel FX sends, and
  FX-return fader/assignment/master/effective state.
- `presetinfo` exposes that result without constructing a device object.
- Explicit off, default assignment/master, and bus aliases are covered.

## Gate 3: wording reconciliation — complete

Current user-facing text distinguishes working host persistence, device factory
content, the unresolved custom-slot writer, and the uncaptured native sequence.

## Gate 4: native capture preparation — complete, not execution authority

- C00-C07 isolate baseline sync, reverb, Voice FX model, Voice FX parameter,
  save, assignment, standalone recall, and complete restoration/deletion.
- Exact bus/device-scoped TSV columns, interface/endpoint filtering, a separate
  endpoint-zero export, deterministic normalization, strict shared framing
  validation, immutable originals, and required hashes are specified.
- No firmware, reset, blind write, unrelated driver work, or Linux/Wine route is
  part of the matrix.

## Gate 5: decode and reproduce — pending external evidence

After separate exact authorization, capture the C00-C07 matrix on a supported
native host. Decode offline, identify the smallest new message/state transition,
and add a fake-boundary executable regression. A bounded device reproduction is
a later, separately authorized gate; capture authority does not imply it.
