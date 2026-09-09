# Task 2 — source-bound Host Hot Key

Implement the missing Linux Host Hot Key as the smallest faithful, hardware-free feature.

## Binding behavior

- UC 4.7.2 establishes `presetHotKey` as a **momentary Host state transition**, not a seventh device slot, not a second effect instance, and not a new USB command.
- While held, it applies a complete known snapshot for exactly one physical channel. On release, it restores that channel's complete normal Host snapshot.
- Channel 1 and Channel 2 must be independent. A Hot Key operation for one channel must not replay or mutate the other channel's gain, phantom, Fat Channel, sends, slot selector, or preset-enable state.
- The normal state must be captured before the first press and replayed on release. Repeated press events while already active and repeated release events while inactive are idempotent and emit no duplicate replay.
- A Hot Key snapshot must use the established Host preset/shadow normalization and safe ordering. It must preserve supported Fat Channel state, mixer routes belonging to the selected physical channel, selected VoiceFX class/model/state when that channel owns VoiceFX, and readable channel-local values. It must not silently claim or infer unknown write-only attached-device state.
- Reject incomplete, malformed, cross-channel, unknown-setter, and unsupported alternate-EQ snapshots before the first device-facing setter call. Passive/Vintage direct-live state remains fail-closed until its exact builder exists.
- Do **not** write `Pari/151`, invent a Hot Key wire command, access USB, launch the Host, access Wine, or use the network in tests or implementation work.

## Host surface

- Provide a clear backend/session abstraction that can be tested with instrumented fake devices.
- Add a GTK momentary control for each physical channel and a deliberate way to capture/assign the complete known Hot Key snapshot. Programmatic GTK synchronization must not trigger a press, capture, or device write.
- Display that this is a Host snapshot and that device readback/standalone persistence is unavailable; do not label it a device slot.
- Update the 750-row matrix so `state.hotkey_ch1`, `state.hotkey_ch2`, and `state.hotkey_release` become supported Host behavior with no `not_exposed_by_current_linux_host` blocker. Total rows remain exactly 750 and deterministic.

## Verification

- Add focused tests proving per-channel filtering, press/release ordering, idempotence, failure atomicity, VoiceFX ownership handling, other-channel isolation, and silent GTK adoption.
- Re-run the new focused tests plus `tests/test_io24_host_parameter_repairs.py`, `tests/test_io24_host_state_repair.py`, `tests/test_io24_preset_persistence.py`, `tests/test_io24_voicefx_preset_apply.py`, and `tests/test_io24_full_parameter_inventory.py`.
- Rebuild the matrix to a temporary path and prove it is byte-identical to the checked-in/generated matrix.

## Owned files

The implementer owns only the minimal Host/backend, GTK, focused-test, matrix-builder, and generated-matrix files needed for this task. Preserve other users' and agents' edits; do not revert unrelated changes.

