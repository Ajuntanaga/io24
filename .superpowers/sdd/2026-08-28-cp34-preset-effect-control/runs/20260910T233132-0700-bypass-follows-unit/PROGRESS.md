# Bypass follows the unit's press-and-hold

Status: `BYPASS_FOLLOW_OFFLINE_COMPLETE_LIVE_ACCEPTANCE_PENDING`

Base: `main` = `0f2dc41` (the user fast-forwarded it before this run); the main
checkout's sources were compared byte-for-byte with the worktree first — no
other agent was editing.

## Change (`io24gtk.py`)

`_follow_device_bypass(poff, now=None)` runs from `_tick`, after its
`alive` gate, on the JaSt bypass flags the poll already parses
(`s["preset_off"]`, slot 42 bits 5/6):

- **Debounced.** A device state counts once it has held for
  `DEVICE_BYPASS_HOLD_S` = 0.5 s. The poll's own comment records that a short
  Preset press only blips the bits while press-and-hold latches them.
- **Edge-triggered.** Only a change in the accepted device state moves a
  switch, never a disagreement. A poll taken before a Host write lands shows the
  old state unchanged, so it cannot undo that write; after the write lands the
  new state already matches the switch and nothing moves.
- **Adopted, never sent**, through `_adopt_processing_mix`. A channel the unit
  re-enables shows 100 %, because press-and-hold writes the Boolean form of
  wire 4; the remembered amount is kept when the unit bypasses.
- The first steady reading after start is treated as an edge, so a channel
  already bypassed on the unit shows bypassed.

`GUIDE.md` Device section: the switch now follows the unit's press-and-hold.

## Verification

- Focused `tests/test_io24_host_dsp_amount.py`: 19 passed (13 existing + 6 new:
  held bypass followed without sending; short-press blip ignored; stale poll
  never undoes a Host write; unit re-enable shows 100 %; startup bypass shown;
  `_tick` follows only after the `alive` gate).
- Full hardware-free suite: **573 passed, 1 skipped, 127 subtests, exit 0** in
  160.04 s with `ResourceWarning` elevated. The skip
  (`test_cp34_firmware_package.py:104`) and the one warning
  (`re/cp34_current_slot_survey.py:260` temp wav) are the baseline's. The six
  gitignored UC 4.7.2 binaries remain symlinked in the worktree.
- Matrix (751 rows) regenerated twice, identical: SHA-256
  `24bf6ad399074c2141219aa8ab0c0dbad90dfdfe3c5a3435c95bcbe46bd988fe`.

No USB, device, audio, Host launch, Wine, install, network or firmware action
occurred.

## File evidence

| file | before (`0f2dc41`) | after |
|---|---|---|
| `io24gtk.py` | `ee01b21f…b28b` | `c97c5baa…fc82` |
| `GUIDE.md` | `d03400a5…00a4` | `da712469…8fbc` |
| `tests/test_io24_host_dsp_amount.py` | `c8428336…89aa` | `302ead90…d2aa` |
| `runs/…/PARAMETER-VERIFICATION-MATRIX.json` | `cf9a7938…3354` | `24bf6ad3…88fe` |

Full digests are in `CHECKPOINT.sha256`.

## Open

- Live acceptance: press-and-hold on each channel moves its switch within about
  half a second; a short Preset press does not.
- Everything else in the 2026-09-10 Codex handoff stands, including the
  Presets-tab reorganization (Codex's), the MAIN slot-0 rewrite and the
  proposed partial-amount / `dawpostdsp` measurement (both need the device and
  the user's go).
