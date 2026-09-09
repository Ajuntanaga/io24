# Preset and effect persistence evidence

## Current executable behavior

- `io24.py:153-181` keeps the durable host write mirror used across CLI
  processes.
- `io24.py:184-242` performs device-free effect inspection and distinguishes a
  missing FX-return fader from explicit off while accounting for assignment and
  bus master.
- `io24.py:1070-1162` snapshots readable values plus mirrored calls, durably
  writes version-1 preset JSON, and replays recognized setters on load.
- `io24.py:1192-1201` records Voice FX model intent; the comments preserve the
  unresolved audible-path qualification.
- `io24.py:1307-1319` implements the hardware-verified reverb path.
- `io24.py:1570-1589` includes reverb, Voice FX, FX mix, mixer routing, output
  delay, processing, and preset selectors in the write mirror.
- `io24.py:1864-1913` exposes file-only `presetinfo` before device construction.

## Executable regression evidence

- `tests/test_io24_preset_persistence.py` covers failed-save preservation and
  cleanup, file and directory sync, real hardware-free save-load-save replay,
  complete effect/route inspection, and a CLI guard against device construction.
- `tests/test_io24_capture_decode.py` supplies structurally complete paesdk
  request/response fixtures, asserts decoded tuples, and requires malformed,
  contradictory, outer-truncated, or inner-truncated JSONL to fail.
- `tests/test_normalize_io24_capture.py` verifies exact interface-5 and endpoint
  filtering for one declared bus/device, deterministic JSONL, colon-separated
  payload handling, strict rejection of damaged native exports, and preservation
  plus visible decoder flagging of a coherent novel command.
- `tests/io24_capture_format.py:8-65` is the shared frame validator;
  `tests/normalize_io24_capture.py:64-131` is the tested device-scoped
  normalizer; and `tests/usbmon_decode.py:64-118` is the strict reader.

## Existing protocol and scene evidence

- `PROTOCOL.md:5011-5060` records a controlled negative: device preset recall did
  not open the Voice FX gate, while reverb was the positive control.
- `PROTOCOL.md:5122-5190` records the recovered Universal Control component model
  and why a genuine UC-to-device capture is the remaining non-guessing route.
- `PROTOCOL.md:5194-5227` identifies the Universal Control WinUSB call surface but
  does not itself reveal the preset/effect sequence.
- `io24_scene.py:288-311` shows that Universal Control scene JSON retains Voice FX
  fields and enumerates the saved slot records and host user-preset library.
- `README.md:432-525` documents scene import, firmware factory presets, host
  startup persistence, and the unresolved custom device-slot write path.

## Confirmed

- Host JSON persists and replays driver-known state.
- Reverb is directly controllable and survives the host preset round trip.
- Voice FX model intent and parameters survive the host preset round trip even
  though direct audible playback is not established.
- FX-return visibility includes the values that actually determine route state.
- Strict validation preserves coherent unknown commands for discovery while
  applying the established inner-TLV contract to known GetP/SetP/Rply frames.
- Factory preset content exists, but the known direct resolver cannot name the
  internal preset component.

## Unresolved and decisive future evidence

The missing evidence is a supported-host Universal Control capture with one
variable changed at a time: baseline synchronization, known reverb change, known
Voice FX change, user-preset save, slot assignment, hardware-only recall, and
restoration. `CAPTURE-MANIFEST.md` makes the conversion and validation path
deterministic. It remains a future live gate and is not current authorization.
