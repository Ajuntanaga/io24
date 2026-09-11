# Presets tab, A/B removal, and resuming the last session

Status: `PRESETS_AND_RESUME_OFFLINE_COMPLETE_LIVE_ACCEPTANCE_PENDING`

Base: `956b7ae` (Bypass follows the unit). Three commits on worktree branch
`worktree-io24-dsp-device-tab`: `2bf9e78` (A/B removed), `3b703e6` (Presets
tab), and the resume commit that carries this record.

## A/B preview removed (`2bf9e78`)

The user called the Host's hold-to-preview "Temporary A/B previews" unplayable
and unnecessary. Removed: the Presets section and its three handlers,
`io24.HostHotKeySession` and `_HotKeyPreflightIo24`, the three Host Hot Key
matrix rows (751 → 748), `tests/test_io24_host_hotkey.py`, and two tests in
`test_io24_host_parameter_repairs.py`. `PARAMETER-INVENTORY.json` lists
`line/ch1|2/presetHotKey` as unimplemented again and drops `host_hot_key`
(this file is hand-maintained; its run's old `CHECKPOINT.sha256` was already
stale for the matrix and is read by no test). The user later clarified that
UC's own Hot Key was a quick loader they liked; that was never implemented in
this Host, and they were asked what it did.

## Presets tab (`3b703e6`)

`_presets_page` is one group: **Load into**, a search box, **Preset name** with
**Save**, and two `Adw.ExpanderRow` drop-downs, **User Presets** (expanded) and
**Factory Presets**.

- User Presets: the Host-known unit blocks from the slot registry, tagged
  "On the unit · Channel N, block M" with "· playing" on each channel's
  selected block (`_mark_playing_unit_blocks`, from `_tick`), then presets saved
  on the computer.
- Double-click (`_on_double_click`, `n_press == 2`) loads. A unit preset on its
  own channel is recalled by the unit (`_load_device_entry` →
  `_recall_host_preset`); on the other channel, or the other half of a linked
  pair, its record is applied (`_load_factory(record=…, channels=…)`). Factory
  and saved presets load with Voice FX for the target channel.
- Save: `io24_presets.save_user_preset` into `~/.config/io24/user-presets.json`
  (the factory list-of-records format; `load_user_presets`, `delete_…`,
  `rename_…`; a damaged file is refused, never read as empty or overwritten).
  Saving over a name confirms. `_record_voicefx(strict=False)` stores the
  non-owning channel's Voice FX switched off instead of refusing.
- Each row's ⋯ menu: **Put on the unit's button, block 1/2**
  (`_prepare_record_slot_store` → confirm naming what it replaces →
  `_queue_factory_slot_store`, activate=True); saved presets also **Delete**
  (confirmed). `_prepare_slot_store_target(relative_slot=)` keeps refusing the
  block the channel is playing.
- Removed: the Device slots and Host presets sections, the help row,
  **Complete-body base** (now `_slot_base_name`: Broadcast, else the first
  factory name), Save only / Save and activate, Load strip / Load + Voice FX,
  `SlotBlocks`. **Preset blocks on the unit** moved to the Device page
  (`_preset_button_group`).

## Resume where it left off (this commit)

- `io24.Io24.reapply_shadow(skip=())` skips named setters and reports
  `skipped_by_request`; its docstring records the user's reversal of the earlier
  "never automatically" rule.
- `io24gtk`: `LAST_SESSION_PATH`, `RESUME_SKIP` = mute, headphone mute, stereo
  link (the unit reports them), `load_last_session`.
- `_host_features_state` (shared with the snapshot dialog), `_save_last_session`
  (writes only on change; every 5 s via `_autosave_session` and in
  `App.do_shutdown`, guarded for a half-built window).
- `_maybe_resume` from `_tick` after the alive gate, once per
  `attach_generation`; only the first restores Host-only features.
- `_resume_session`: when the mirror has Voice FX on, recall the owner's
  selected block first (opens the gate), then `reapply_shadow(skip=RESUME_SKIP)`,
  then re-send the owner's saved DSP amount (a recall on a bypassed channel
  enables it), then `_after_load` onto the controls.

## Verification

- Affected-file runs: A/B removal 209 passed + 54 subtests; Presets 1 failure
  (`test_preset_frontends_distinguish_host_files_from_device_slots` expected the
  removed section title; retargeted to the new unit tag); resume 1 failure
  (`test_application_shutdown_stops_both_bus_sources`, a duck-typed window
  without `_save_last_session`; fixed in production with a guard).
- Full suites: after A/B 559 passed; after Presets 581 passed; final **597
  passed, 1 skipped, 125 subtests, exit 0** in 165.15 s with `ResourceWarning`
  elevated. The skip and the one warning are the baseline's.
- New tests: `test_io24_presets_page.py` (22), `test_io24_host_resume.py` (16).
- Matrix 748 rows, regenerated twice, identical: SHA-256
  `7b4a9590798f382bd0759db83d44bb2aec3e2ee6456405bd6909e9b3e765142e`.
- Widget API by introspection (Adw 1.9): ExpanderRow `expanded`/`add_row`/
  `remove`, MenuButton `popover`, Popover `child`/`popdown`, EntryRow
  `add_suffix`. GestureClick `pressed` is the signal the removed A/B used.

No USB, device, audio, Host launch, Wine, install, network or firmware action
occurred.

## File evidence

| file | before (`956b7ae`) | after |
|---|---|---|
| `io24.py` | `3eea5ea9…5e39` | `8635f9d7…d950` |
| `io24gtk.py` | `c97c5baa…fc82` | `6b612c39…92b4` |
| `io24_presets.py` | `2a7033b4…68a3` | `12ddfa07…f147` |
| `GUIDE.md` | `da712469…8fbc` | `8a127455…361a` |
| `README.md` | `a82b120f…54ed8` | `05a9b3c2…48c0` |
| `runs/…/PARAMETER-VERIFICATION-MATRIX.json` | `24bf6ad3…88fe` | `7b4a9590…142e` |
| `runs/…/PARAMETER-INVENTORY.json` | `d6084618…8e45` | `413ef4fa…7924` |
| `runs/…/build_parameter_matrix.py` | `82eda857…d94f` | `051242fd…9d19` |
| `tests/test_io24_full_parameter_inventory.py` | `981dae75…8b75` | `f3dd0711…cade` |
| `tests/test_io24_host_parameter_repairs.py` | `633c5fa7…1a4f` | `013e28fd…eed7` |
| `tests/test_uc472_standard_highshelf.py` | `436bbf43…be14` | `d265746f…f1b8` |
| `tests/test_io24_device_slot_recall.py` | `11e4054c…b245` | `f49f284b…1d1b` |
| `tests/test_io24_host_state_repair.py` | `078c4c6a…698f` | `9a41f938…f4fa` |
| `tests/test_io24_preset_persistence.py` | `f8c4fe81…312a` | `c732e96c…5f42` |
| `tests/test_io24_host_hotkey.py` | `cd3fa1d9…5cb0` | removed |
| `tests/test_io24_presets_page.py` | absent | `adfff5d9…8175` |
| `tests/test_io24_host_resume.py` | absent | `6cbc3573…59a8` |

Full digests of the present files are in `CHECKPOINT.sha256`.

## Open

- Live acceptance, each needing the io24 and the user's go: double-click
  loading on both channels and linked; a Save round trip; Put on the unit's
  button (writes and loads a block); resume after a Host restart and after a
  power cycle, including a Voice FX session.
- Ask the user what UC's Hot Key quick loader did, if they want it rebuilt.
- The user's stated goals needing a separate plan and explicit authorization:
  Doubler private-reverb shaping (trace `0x5c06c`'s mapping first, offline), a
  multiband compressor on the unit, and new effects; all require custom
  firmware because the stock firmware has no crossover or multiband code.
- Channel-1 slot-0 MAIN rewrite from `Main.scene` ch1 remains staged.

## Post-merge fix: the resume job reached the USB handle

Found after the user fast-forwarded `main` to `98539ab`, while reading
`Ctl._loop` for live work: the worker passes each job the Io24 driver itself
(`fn(self.dev.dev)`), and the driver's own `.dev` is the raw pyusb handle. The
resume job unwrapped `getattr(dev, "dev", dev)`, so on hardware it would have
reached the USB handle, failed on `reapply_shadow`, and restored nothing. The
tests missed it because their stand-in driver had no `.dev`. Fixed by using the
job's argument directly; the stand-in now carries a `.dev` like the real driver,
so the old code fails the resume tests.

- Resume tests 16 passed; full suite **597 passed, 1 skipped, 125 subtests,
  exit 0**; matrix `1fdb73c7…8a9d`, regenerated twice, identical.
- The merged `main` (`98539ab`) was also run in the user's own checkout with
  the real UC binaries: 597 passed, 1 skipped, exit 0.

## Read-only device probe (2026-09-11 ~01:45, user-cleared)

`Io24(shadow=False)`, GetP/JaSt reads only, then closed. Serial `AB7C22200355`,
firmware `0128`; Channel 1 on global slot 0, Channel 2 on slot 2, neither
bypassed; gains 30.0 / 24.2878 dB; link, mutes and phantom off; main 0.75,
headphones 0.50; Voice FX owned by input 1; flags 385. Battery 96 %.

## MAIN restore, prepared and not run

Offline proof: rebuilding B A S E from `B A S E.scene` `line/ch1` (the seven
sections, name set) reproduces registry slot 1 exactly (`135a93f1…`), and the
same rule on `Main.scene` `line/ch1` (identical to its `presets/slots/0`) with
name `MAIN` reproduces the pinned `f74cd983…d222`. The scene's separate user
preset "Main" is a different body (`23e76d01…`); the user was asked which they
meant. The live script (job tmp `io24_main_restore.py`) recalls block 2 first
because Channel 1 is playing block 1, writes slot 0, recalls it, and checks
Channel 2, gains, link and ownership unchanged. It waits for the user's go.
