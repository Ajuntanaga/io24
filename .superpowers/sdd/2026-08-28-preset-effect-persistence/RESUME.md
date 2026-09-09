# io24 preset and effect persistence continuation

Timestamp: 2026-08-28T17:52:38-07:00

## Authoritative continuation

This is the default continuation point for `resume io24`.

The objective is narrow: make user presets and effect state saveable,
inspectable, and reliably restorable, then determine the real Universal Control
sequence for device-resident user slots and audible Voice FX. Keep the work in
audio-device interoperability, preset persistence, effect state, protocol
evidence, and executable regression testing.

The CP33 WinUSB Task 9 lane is separate and frozen. R148 and R149 remain rejected
and unapplied. Nothing in this lane accepts, modifies, supersedes, or resumes
those proposals.

## Completed offline phase

- `Io24.save_preset()` writes a same-directory temporary JSON file, syncs it,
  atomically replaces the destination, and syncs the containing directory. A
  serialization failure leaves the last good preset byte-for-byte intact and
  removes its temporary file.
- `Io24.load_preset()` replays the saved live values and durable write mirror.
  A hardware-free save-load-save regression exercises the real reverb, Voice FX
  intent, per-channel FX mix, FX-return fader, assignment, and bus-master paths.
- `io24.py presetinfo FILE.json` is file-only. It reports reverb, stored Voice FX
  intent, FX sends, and for every saved FX return its fader, assignment, master,
  and effective/off/unknown state. An assignment without a saved fader is
  reported as unknown rather than falsely reported as off. It constructs no
  `Io24` device object.
- The broad historical wording about preset storage has been reconciled. The
  current distinction is: host JSON persistence works; factory content exists;
  the custom device-slot writer is not reachable through the decoded direct
  route; and the native Universal Control sequence remains uncaptured.
- `tests/normalize_io24_capture.py` requires the declared USB bus/device,
  deterministically filters a six-column supported-host TSV export to interface
  5 and endpoints 0x01/0x81, and writes normalized JSONL atomically.
- The normalizer and `tests/usbmon_decode.py` share one validator for endpoint,
  direction/type, outer header/message code, and inner blob length. Malformed,
  contradictory, or structurally truncated rows cannot silently disappear.
- The prepared live matrix and exact offline conversion steps are in
  `CAPTURE-MANIFEST.md`. Preparation grants no live execution authority.

## Current evidence state

- Ten focused hardware-free regressions currently pass and cover preset durability, real
  save-load-save effect replay, file-only inspection, complete-frame decoding,
  strict rejection, coherent novel-command preservation/reporting, and
  deterministic native-capture normalization.
- `VERIFICATION.md` records the latest full commands and results.
- The final independent adjudication found no remaining material issue and
  explicitly supports sealing. `SHA256SUMS` seals the current offline lane.

## Confirmed versus unresolved

Confirmed:

1. Host JSON is a dependable persistence path for every currently shadowed
   setting, including working reverb and recorded Voice FX intent.
2. Factory preset content exists in the device.
3. Direct Voice FX payloads are byte-defined and saved, but their audible native
   activation sequence has not been established on this unit.
4. Selecting a device slot is implemented; writing custom content into a slot is
   not.

Unresolved:

1. The exact Universal Control transaction that stores or assigns a custom
   device-resident preset.
2. The prerequisite/state sequence that makes Voice FX audible.
3. Whether those two operations share one native transaction boundary.

## Live boundary

Remain offline and hardware-free by default. Do not start Wine, access
`/home/ajuntanaga/.wine-io24`, access USB/device nodes, claim or detach an
interface, send a transfer, run Universal Control, operate a preset/effect on the
device, touch firmware, stage a driver, use the network, or perform live hardware
work without separate exact authorization. Stop at or below 10 percent battery.

## Exact next step

Verify `SHA256SUMS` and rerun the commands in `VERIFICATION.md`. If either fails,
stop and treat the lane as unsealed. If both pass and no separate exact live
authorization has been granted, stop: the offline phase is complete and no
additional probing is justified.

If the user separately authorizes the named device, supported native host,
Universal Control session, exact preset/effect actions, capture, and restoration,
execute only `CAPTURE-MANIFEST.md` C00-C07. Preserve the native captures, run the
tested normalizer, and return to offline decoding. Do not reproduce any newly
decoded transaction on the device without another separate authorization.
