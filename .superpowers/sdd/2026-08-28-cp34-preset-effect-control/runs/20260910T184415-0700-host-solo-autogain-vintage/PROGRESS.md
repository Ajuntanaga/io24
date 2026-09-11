# Host solo, auto gain and alternate-model EQ view

Status: `HOST_FEATURES_OFFLINE_COMPLETE_LIVE_ACCEPTANCE_PENDING`

Source: Codex's 2026-09-09 parameter audit (thread `01a086bb-3efc-7a30…`),
which listed seven Host gaps. `db39742` closed limiter release, sample-rate
propagation and reverb Host-state persistence. This run builds the three that
remained buildable; the user chose all of them together.

## Mixer solo (`io24.py`, `io24gtk.py`)

Block 100 has no solo and UC's `solo` has no device binding. `set_solo(source,
bus, on)`, `clear_solo(bus=None)` and `soloed(source, bus)` fold solo into
`_push_send`: while any source is soloed in a bus, every other source there is
written off; level, assign and pan are never touched, so release writes the
prior mix back exactly. Solo state lives outside `_send_state` (which a shadow
reload rebuilds) and is never shadowed, so a snapshot saved while soloing holds
the real mix. A never-set route is materialised at the displayed 0 dB on its
bus's first solo, so release has a real level to return to. `line/ch3` is
excluded (`SOLO_SOURCES`) because its io24 applicability is unproven.

GTK: an **S** toggle per routing cell; `_sync_mix_widgets` mirrors driver solo
state; `release_host_solo()` runs in `App.do_shutdown` so no bus is left
silenced after the Host closes.

Matrix: three `mixer.<bus>.solo` rows (748 -> 751) carry `set_solo`,
`clear_solo`, `soloed`; `soloed` added to the generator's explicit API set.

## Auto gain (`io24gtk.py`)

UC's `autogain`/`autogainmode` reach firmware ids with no descriptor
(re/UCNET_SHIM_SPEC.md 4c), so this is Host-side. First built as a one-shot
"listen 3 s, then set" button; the user rejected that ("completely automatic,
no prompting ... how it was in UC"), so it is now a continuous per-input
**Auto** switch like UC's `autogain` toggle.

While on, `AutoGain.step()` runs every 50 ms on the JaSt input meter (slots
4/6): it steers the 95th percentile of a 3 s window toward -12 dBFS, acts only
outside a 3 dB deadband, at most once per second (0.4 s settle, window cleared
after each change), rising at most 2 dB and falling at most 4 dB per step; any
reading >= -0.5 dBFS drops 6 dB at once. It never lifts silence (< -60 dBFS) or
a steady floor (a rise needs a >= 10 dB spread between the 95th and 10th
percentiles). Gain is clamped to 0-60 dB. The gain fader is locked while the
switch is on; linked inputs share one switch state and one controller, and the
louder input sets the single gain for both. No message is ever shown; writes go
through the existing `_set("gain")`. It is session state (UC's `autogain` is
not `storable`) and starts off each launch. `autogainmode`'s two values are
undecoded and not exposed.

## Passive/Vintage EQ view (`io24_presets.py`, `io24gtk.py`)

`alternate_eq_view(record)` returns read-only rows for a Passive/Vintage body:
Vintage switches as positions, with the io24_scene Neve 1073 Hz labelled
unverified. After a recall, `_adopt_recalled_slot` adopts everything except the
EQ, then shows the EQ read-only; the curve and rack say it cannot be drawn and
the Standard band controls are paused on that channel. `current_slot_record`
takes `alternate_eq=` and stores it verbatim, and `_current_slot_record` passes
it, so saving that channel no longer replaces the user's Vintage EQ with four
Standard bands. **Edit with Standard EQ instead** lifts the pause and sends
nothing; linked edits skip a held channel and say so once. Factory load and
Host snapshot load end the view because they write Standard bands.

## Verification

- Baseline before edits: 513 passed, 1 skipped, 124 subtests.
- First full run after edits: 553 passed, **2 failed** — `do_shutdown` read
  `self.ctl` and `_adopt_preset_record` called `_show_alternate_eq` on
  duck-typed test hosts. Fixed in production code (both now touch nothing on
  the common path); tests unchanged.
- After those fixes, with the one-shot auto gain: 555 passed, 1 skipped.
- Final, after the continuous Auto rework: **554 passed, 1 skipped, 127
  subtests, exit 0** in 186.52 s with `ResourceWarning` elevated; the one
  warning is the pre-existing `re/cp34_current_slot_survey.py:260` unclosed
  file seen in the baseline.
- New tests: `test_io24_mixer_solo.py` (15), `test_io24_host_autogain.py` (16,
  3 subtests), `test_io24_vintage_eq_view.py` (10).
- Matrix regenerated twice, identical: SHA-256
  `838070128347dbad2e7670405cfd5738373eea3ed9a40f733ee92ab2fa43eb0d`.
- GTK4 property names used by the new widgets verified by introspection only.

No USB, device, audio, Host launch, Wine, install, network or firmware action
occurred. Nothing is committed.

## File evidence

| file | before (HEAD `3fd72cb`) | after |
|---|---|---|
| `io24.py` | `52e034ed…bfda7` | `3eea5ea9…65e39` |
| `io24_presets.py` | `8beeccc2…c1eb` | `2a7033b4…68a3` |
| `io24gtk.py` | `09702c85…68b8` | `ec83eb81…886f` |
| `GUIDE.md` | `c2e4c974…380c` | `46c34eb1…e4b3` |
| `runs/…/build_parameter_matrix.py` | `613f3be3…affb0` | `82eda857…d94f` |
| `runs/…/PARAMETER-VERIFICATION-MATRIX.json` | `742c55f6…1a63` | `83807012…eb0d` |
| `tests/test_io24_device_slot_recall.py` | `f00ea4a8…6396` | `11e4054c…b245` |
| `tests/test_io24_full_parameter_inventory.py` | `b684a659…921c` | `981dae75…8b75` |
| `tests/test_uc472_standard_highshelf.py` | `d265746f…f1b8` | `436bbf43…be14` |
| `tests/test_io24_mixer_solo.py` | absent | `16ff188f…3464` |
| `tests/test_io24_host_autogain.py` | absent | `379e11e9…6cde` |
| `tests/test_io24_vintage_eq_view.py` | absent | `24edf162…0fa5` |

Full digests are in `CHECKPOINT.sha256`.

## Open

- Live acceptance of all three needs the device: Auto gain against a real
  source, solo audibility per bus, and a recalled Vintage body on screen.
- Channel-1 slot-0 MAIN rewrite from `Main.scene` ch1 is staged (canonical
  SHA-256 `f74cd9837af8fb093ae1260381bf98b21b4549d40cc58cbf531d209910efd222`),
  preamp gain to stay at 30.0 dB per the user. Needs the io24 connected and an
  explicit go; write via `save_known_device_slot` + `recall_device_slot`, not
  the stage script.
