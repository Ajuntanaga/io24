# DSP amount and Bypass on the Device page

Status: `DSP_AMOUNT_DEVICE_PAGE_OFFLINE_COMPLETE_LIVE_ACCEPTANCE_PENDING`

Source: the user's 2026-09-10 ~18:53 PDT message, queued mid-turn in session
`ce4fcfa9` (so it appears only as a `queue-operation`/`queued_command` record,
not an ordinary user turn): "dsp amount and bypass dsp seem important, at the
very least advanced/settings that beloong in the host/settings tab". The
previous session asked where to put them and was stopped before an answer; this
run builds its recommended option — Device page only, one control per setting.

## What the control is

Wire id 4 (`input1FxMix` / `input2FxMix`) is one processing scalar per channel
(PROTOCOL.md 2026-09-08 controlling correction). Exact zero bypasses the
channel's whole chain — EQ, dynamics and effects, compressor included, by live
isolation — and nonzero is the channel processing and feeding the shared
reverb. A recall on a bypassed channel never runs the `Stat` load, which is why
`recall_device_slot` asserts the enable (1.0). JaSt slot 42 bits 5/6 report
only zero versus nonzero. On the FX return, `fxMix` was measured to crossfade
dry to wet (PROTOCOL.md §12J, -24.56/-24.98 dB); what a partial amount does on
the main path is **not** measured (`native.channelN.processing_mix` stimuli
0.25/0.75 remain `PENDING`).

UC declares `dspAmount` (min 0.00001, "min > 0", default 1, percent) and a
`bypassDSP` toggle, neither with a recovered device binding
(re/UCNET_SHIM_SPEC.md 4f). Composing them onto wire 4 is the Host's reading of
that schema, stated as such in GUIDE.md; the `component.line_chN.{dspamount,
bypassdsp}` matrix rows are left `PENDING` with no API.

## Change (`io24gtk.py`)

- `ProcessingMix` composes an amount slider and a Bypass switch:
  `get_value()` is 0.0 while bypassed and the amount otherwise; `set_value(0)`
  adopts as bypassed and keeps the remembered amount; the amount cannot go
  below `AMOUNT_MIN` = 0.001, so it never reads as bypass by itself. It keeps
  the `processing_mix_controls[ch]` contract every caller already used.
- `_processing_group()` on the Device page (after Output delay): per channel a
  **Channel N bypass** switch ("Skips this channel's EQ, dynamics and
  effects") and a **Channel N DSP amount** slider (0.1-100 %, default 100 %).
  The amount row is greyed out while bypassed. Bypass writes 0; releasing it
  writes the remembered amount; a moved amount is sent only while processing.
- The Effects page's processing slider is gone; the reverb switch subtitle
  points at the Device page. `_push_reverb` reads the processing value only
  when establishing the path, because the Effects page is built before the
  Device page that owns the controls.
- Adoption sends nothing: `_adopt_processing_mix` raises `_adopt_mute`, which
  both the slider (`_srow`, before its `Throttle`) and the Bypass handler
  honour. `_after_load` adopts through it; `_slot_recalled` calls
  `_follow_recall_processing`, which shows 100 %, not bypassed, when the recall
  had to assert the enable.
- Wording: slot-row subtitles, the slot-group docstring and the save dialog
  now name DSP amount/Bypass on the Device page.

`GUIDE.md`: a Device-section paragraph, and the Reverb, Voice FX, custom-firmware
and Device-slots passages re-pointed from "processing/effects mix on the Effects
page". PROTOCOL.md untouched — its "no device binding of their own" stays true.

## Verification

- Baseline: commit `1fc5245` is the previous run carried over byte-for-byte
  (all 15 files in its `CHECKPOINT.sha256` OK, both in the worktree and, at
  19:5x, in the main checkout).
- First focused run: 1 failure, `test_sections_have_no_embedded_descriptions`
  — `Win` forbids `description=`. Fixed in production: the group's paragraph
  became the Bypass row's subtitle.
- Test edits to existing files: `test_io24_host_state_repair.py`, two
  assertions that located the processing control in `_fx_page` now look in
  `_processing_group` (the move is the change).
- First full run in the worktree: 7 failed, 4 skipped. Every failure was
  "input is missing"/`FileNotFoundError` for gitignored UC 4.7.2 binaries a
  fresh worktree does not receive. The six (`dspusbdevice.dll`,
  `studiolivepanel.dll`, `ucnet.dll`, `Universal Control.exe`,
  `PreSonusHardwareAccessService.exe`, the UC installer) were symlinked from the
  main checkout; `git check-ignore` confirms `*.dll`, `*.exe`, `dspusbdevice*`.
- Final: **567 passed, 1 skipped, 127 subtests, exit 0** in 156.98 s with
  `ResourceWarning` elevated. The skip is the baseline's
  (`test_cp34_firmware_package.py:104`). 567 + 1 = the baseline's 555 plus 13
  new tests. The one warning is the baseline's: `re/cp34_current_slot_survey.py:260`
  leaves a temporary `first.wav` open.
- New tests: `tests/test_io24_host_dsp_amount.py` (13).
- Matrix (751 rows, unchanged) regenerated twice, identical: SHA-256
  `cf9a7938089a468563e025cce4efc2c7ded0dfb8d11e066aefdb1d484c4f3354`.
- Adw 1.9 introspection: every widget property used exists.

No USB, device, audio, Host launch, Wine, install, network or firmware action
occurred.

## File evidence

| file | before (`1fc5245`) | after |
|---|---|---|
| `io24gtk.py` | `ec83eb81…886f` | `ee01b21f…b28b` |
| `GUIDE.md` | `46c34eb1…e4b3` | `d03400a5…00a4` |
| `tests/test_io24_host_state_repair.py` | `901b3638…06a5` | `078c4c6a…698f` |
| `tests/test_io24_host_dsp_amount.py` | absent | `c8428336…89aa` |
| `runs/…/PARAMETER-VERIFICATION-MATRIX.json` | `83807012…eb0d` | `cf9a7938…3354` |

Full digests are in `CHECKPOINT.sha256`.

## Open

- Live acceptance needs the device: Bypass and amount audible per channel, and
  a recall on a bypassed channel showing 100 %.
- The Bypass switch shows what the Host sent; it does not follow the unit's
  press-and-hold. JaSt bits 5/6 would allow it, with an edge-triggered sync so
  a poll cannot fight an in-flight write.
- Proposed, not run: one bounded measurement of partial amounts (0/25/75/100 %
  on the main path) and of `dawpostdsp` pre/post. Needs the io24 and an exact go.
- Channel-1 slot-0 MAIN rewrite from `Main.scene` ch1 remains staged (canonical
  SHA-256 `f74cd983…d222`, preamp 30.0 dB); `save_known_device_slot` +
  `recall_device_slot`, never the stage script.
- Merge: branch `worktree-io24-dsp-device-tab`. The main checkout still holds
  the `1fc5245` changes uncommitted and byte-identical, so they must be
  discarded (or stashed) there before merging.
