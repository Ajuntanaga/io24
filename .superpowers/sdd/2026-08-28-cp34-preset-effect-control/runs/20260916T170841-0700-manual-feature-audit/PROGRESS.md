# Owner's-manual feature audit: what the io24 documents vs what the Host implements

Status: `MANUAL_AUDIT_COMPLETE_ONE_GAP_CLOSED_FOUR_OPEN`

Raised by the user, 2026-09-16: the manual documents a per-effect power button
for Voice FX, and it is the reference that should be driving the gap list. It
had not been used that way. This is that pass.

## Sources, pinned

| artifact | SHA-256 |
|---|---|
| `~/.cache/io24/re/io24_manual.txt` | `c15a3644fb2ca70205c0118e23652f1013cf93907d632833b4c53de717f40bd8` |
| `~/.cache/io24/re/io24_manual.pdf` | `db879ed87a63dfbb1a6ee6130a9e04b751a5bc2354ed1de17cf74c77e95b1bef` |
| `re/uc_component_model/dsp_fx_params.xml` | `3f5f99bd6efdfd54b65adf15c82d8b9da36116b25b11e3c88a4ad441b9decd89` |
| `re/uc_component_model/dspusb_component_model.xml` | `55388fd3fdcf6d5b466991db886d50a2d8c787afe50390cde554e46d74ff2bfc` |

The io24 manual has been retained since 2026-08-10 and was not being used as the
feature reference. Read-only; no cache mutation.

## What the manual settles about Voice FX

§7.2.13, page 79, verbatim: "while you can use any of these effects with the Fat
Channel and Reverb, you can **only use one effect at a time**" and "To
enable/disable the Voice FX of your choice, use the **power button in the Voice
tab**."

Both halves matter and they point the same way as the vendor component model:

* The per-effect power button is real. `dsp_fx_params.xml` gives each of the six
  modules its own storable `on` toggle and declares no container-level enable.
* Only one runs at a time. `dspusb_component_model.xml` carries exactly one
  *mutable* `voicefx` component per mic strip behind `voicefxopt`
  (`InsertFXSelector`, starttag 450).

So the single `FX active` switch in the Host is a one-at-a-time UI over the same
per-module `on` parameter, not a coarser gate above it. That `on` is the first
word of every model's state blob (`io24_fx.py:310` and the five siblings), every
`set_fx_*` emits `VoFx` selection then that blob (`io24_fx.py:562-585`), and
`io24gtk._push_fx` feeds the switch straight into it (`io24gtk.py:4412,4434`).
The 2026-09-15 ear sweep set `on=True` per model for all six
(`re/io24_fx_listen_sweep.py:113`). The per-module button is therefore already
on the wire and is not the missing gate.

§5.1 also confirms two things the implementation already gets right: "Reverb is
**not** stored with a Preset" — `io24_preset_record.py` stores only Voice FX
model 0's *private* reverb core, never block 202 — and the simple HPF choices
40/80/160 Hz, which `io24gtk.HPF_BASIC_HZ` carries.

§7.1 item 6 and §5.1 both state Voice FX is available on one input at a time,
selectable between Channel 1 and 2 — `Io24.set_voicefx_channel` (`Pari` 12,
`processingChannel`).

## Gaps found

### 1. Channel Mute Sync was decoded but unreachable — CLOSED in this run

Manual §7.1 item 5: "Channel Mute Sync. With this enabled, clicking Mute on a
channel mutes the channel in all outputs: Main, Stream Mix A, and Stream Mix B."

`PROTOCOL.md`'s `'Pari'` table already names it: wire id 8, index ignored,
`muteMode`. `io24.py:2407` names it again in passing, while correcting an old
probe that wrote wire 8 believing it was `presetButtonMode`. But `KNOWN_PARA`/
`KNOWN_PARI` at `io24.py:1046-1059` omits 8 entirely, so `set_param` treats it
as unmapped and refuses without `unsafe=True`, and no setter or UI exists.

Closed here. `Io24.set_mute_mode` emits `'Pari'` 8 with index 0, `KNOWN_PARI`
carries `8: "muteMode"` so the id is no longer unmapped, and the matrix gained
`native.global.mute_mode` under the `write_only_audio_toggle` profile — the
audio-domain oracle, not `presetMode`'s front-panel one, because the observable
is whether a muted channel also drops out of Mix A and Mix B.

What is deliberately NOT claimed: which integer means enabled. UC's naming and
the manual's wording make 1 the sync-on value, but no hardware run has confirmed
it, the parameter is write-only with no slot in the 503-float blob, and SetP is
fire-and-forget. The setter returns `value_mapping:
INFERRED_FROM_VENDOR_NAMING` and `readback: UNAVAILABLE`, and settling it is
exactly what the new matrix row is for. No live action was taken.

Evidence: `io24.py` `set_mute_mode` and `KNOWN_PARI`;
`tests/test_io24_host_parameter_repairs.py::ChannelMuteSyncTests` (3 tests,
including that wire 8 no longer needs `unsafe=True`);
`runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py`.
Matrix before `6e8f936d5b58001a76873d18ba9d57b423d7a341e28f6f9310d2f1b0e9bb7d75`
(709 rows), after `22437ced92100525001a6235fc0f4e98dde849e67292e38a006f6250fbf0f6c5`
(710 rows), from two byte-identical regenerations.

### 2. Fat Channel on USB Stream Outputs is unidentified

Manual §7.1 item 2: by default the USB stream outputs carry the audio "just as
you hear it in your headphones, complete with the Fat Channel preset"; disabling
it records "only the raw unprocessed audio, but still listen to the presets
while you record."

UC's component model has it as `dawpostdsp` ("DAW Send Post DSP", type list,
def 1, `PrePostList`) on `AnalogInputChannel`. No io24 wire id has been
identified for it, and `PROTOCOL.md:1754` only records that the UCNET shim
deliberately does not forward `line/chN/dawpostdsp` because the host binds it to
block 0, where `'Para'` wire 2 is `mainVolume` — it is shadowed host-side
instead. So the *device* control is unmapped, unreadable and unimplemented.

**Hypothesis worth testing, stated as a hypothesis.** Stream Mix A is USB 3/4
and Stream Mix B is USB 5/6 (§7.1 item 3, §6.3.3). Many CP34 block-201 nulls
ratioed `mixa`/`mixb`. If this switch is off and the `JaSt` meter taps for those
buses sit after it, every Voice FX measurement taken on Mix A or Mix B was blind
for a reason unrelated to block 201. This does **not** touch the 2026-09-15 ear
verdict, which was taken on Main through headphones with an in-run positive
control, and it is not a claim that the CP34 nulls were wrong — the last time a
"your bus was wrong" argument was made here it had to be partly withdrawn. It is
a specific, cheap thing to check before any future bus-meter FX run: establish
where the meter tap sits relative to the switch, or run the control on Main.

### 3. Per-mix Mono/Stereo is not implemented

Manual §6.3.3 item 9: "Each mix can be toggled between mono and stereo." UC's
component model has `mono` on `OutputChannel` (starttag 300). Nothing in
`PROTOCOL.md` or the driver addresses it; the word `mono` appears in
`PROTOCOL.md` only in discussions of the pan law. No wire id hunted.

### 4. Per-mix Mute is not implemented

Manual §6.3.3 item 13: "Mute. Mutes the currently selected mix." The only mute
ids decoded are `'Pari'` 7 (`input1/2Mute`, per input) and `'Pari'` 6
(`hpOutputMute`, the software output mute that is distinct from the front-panel
button). Neither is a per-mix mute for Mix A or Mix B.

### 5. Mix names are not implemented

Manual §6.3.3 item 14 and §6.3.2 item 5: mix and mixer-channel names are
user-customizable. The Host reads channel names from the device's `'CHNP'`
table (`io24gtk.py:5320`), but there is no mix naming.

## A documented behavior worth carrying into any future FX probe

Manual §7.2.3, on the compressor: "The compressor will turn off whenever a new
model is loaded and must be re-enabled for you to hear its effect on your
voice."

`comp` and `voicefx` are both `mutable` components in the same strip template,
so the same load-clears-enable behavior plausibly applies to a `VoFx` model
change. The current send order already handles the simple case — `set_fx_*`
sends selection first and the state blob carrying `on` second, 20 ms apart
(`FX_FRAME_INTERVAL_S`), and the Host v2 experiment used selector -> 60 ms ->
selector -> state. So an enable that is cleared *synchronously* by the selector
is already covered.

What is not covered is an enable cleared *after* the state blob, by a lazy
rebuild on a later audio buffer. Any future block-201 probe should re-send the
model's state with `on=1` a second time after a settle delay; it costs one frame
and closes the ordering off. This is a cheap addition to an already-authorized
probe shape, not a new hypothesis about how the block works, and it does not
reopen the 2026-09-15 ear verdict.

## The oddbear repository

`oddbear/Revelator.io24.Api` is cited in `PROTOCOL.md:1323` and is already used
where it is authoritative: `io24_mixer.py:219-233` reproduces its
`VolumeValue.cs` fader taper bit-for-bit across a 1001-point sweep to under
2e-4 dB, `io24_meters.py:319,378` pins the metering trailer constants against
it, and `re/UCNET_SHIM_SPEC.md` implements a shim its clients can drive.

It is not the primary reference for a reason recorded in `PROTOCOL.md:1323-1330`:
it documents UCNET, which is TCP to `127.0.0.1` and a Windows service acting as
a USB-to-TCP bridge. The device does not speak UCNET over USB, so it is the
wrong layer for the native protocol this project implements.

For the feature-inventory question it would still be a useful cross-check —
its route list would confirm names and value encodings for `muteMode`,
`dawpostdsp` and the per-mix controls above. No copy is retained locally
(searched the tree and `~/.cache/io24`), and fetching one needs network access,
which is outside the standing boundary. It needs the user's authorization or a
local clone.

## Not gaps — deliberate omissions, recorded so they are not re-reported

* **Reset All** (§7.1 item 1). `'FRst'` is decoded and the driver refuses to
  send it by design: `io24.py:23,57` and `PROTOCOL.md:1699`. `PROTOCOL.md:1678`
  notes it is a parameter-defaults reset rather than a destructive factory
  erase, but it stays unsent without explicit authorization.
* **Hot Key** (§4.1 item 1). Implemented in Task 2, then removed at the user's
  request on 2026-09-11; `tests/test_io24_host_parameter_repairs.py:462-465`
  pins `line/ch1,2/presetHotKey` as intentionally unresolved.
* **Per-mix output fader** (§6.3.3 item 11) exists as `Io24.set_bus_master`,
  honestly documented as a host-side emulation because block 100 holds
  per-source levels with nothing above them.

## Already correct, confirmed against the manual

Output delay with bus selection (§7.1 item 3) — `set_output_delay`, `'Para'` 14
and `'Pari'` 13. Preset Button Mode one/two/none (§7.1 item 4) —
`set_preset_mode`, `'Pari'` 17. Voice FX channel assignment (§7.1 item 6) —
`'Pari'` 12. Monitor blend (§2.1.7) — `'Para'` 10. Phones Listen (§6.3.3 item 7)
— `'Pari'` 11, `PHONE_SOURCES`. Solo (§6.3.1 item 10) — host-side, as UC does it,
because block 100 has no solo. Stereo link (§6.3.1 item 11) — `'Pari'` 9. Six
mixer sources by three buses (§6.3.2) — `MIXER_SOURCES`/`MIXER_BUSES`.

## Boundary

Static reading only: the retained manual text, the retained UC component model,
and the project's own source. No device, USB, audio, Host, Wine, network, cache
mutation or Obsidian action. No live claim is made or revised by this document.
