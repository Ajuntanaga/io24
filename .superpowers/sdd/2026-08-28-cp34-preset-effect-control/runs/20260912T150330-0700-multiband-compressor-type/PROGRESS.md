# Multiband as a compressor type, a flat crossover, a wet reverb

Authority: the user, 2026-09-11/12 — "resume", then "take care of the open
items", and for the insert's return pair, "it should immediately follow the FaT
channel, so that goes to 1+2 first" plus the answer **USB playback 1-2**.

Offline only. No USB/device, audio, Host launch, Wine, firmware, install,
network or cache action occurred in this run. The one `pipewire -c
filter-chain.conf` process on the machine is the user's own
`filter-chain.service`, running since login; nothing here started or touched it.

## 1. The merge the user asked for — done

`git merge --ff-only io24-autogain-memory` in the main checkout:
`fa0d974..5a0018d`, 4 files (Auto gain remembered per input). Codex's
uncommitted CP33 WinUSB files do not intersect that diff and were untouched.
New work is on branch `io24-multiband-insert`, cut from `5a0018d`.

## 2. Multiband is now the fourth compressor Model

The user's ask: the multiband as "just another type of compression that can be
selected, replacing the normal compressor block", and, since the unit's chain
cannot be split, "it can go after the limiter then" / "immediately follow the
Fat channel".

**The open live question is answered offline.** USB capture of an input is
after the whole Fat Channel, limiter included: the io24 manual's Settings
section says the unit "will record audio just as you hear it in your
headphones, complete with the Fat Channel preset", and the switch that changes
that ("Fat Channel on USB Stream Outputs") is in neither of firmware 0128's two
parameter tables (23 + 17 records, PROTOCOL.md §12I) nor UC's scene `global`
object. So the tap point is fixed and processed, and no device probe was
needed.

Design, in `io24_mbc.py` (new: `INSERT_*`, `build_insert_graph`,
`build_insert_return_graph`, `build_insert_conf`, `default_insert_state`,
`validate_insert_state`, `route_insert`, `unroute_insert`, `InsertChain`,
`set_default_input`):

```text
io24 capture 1 -> [in1_ 4-band] -> out1 \  Audio/Source "io24 Input 1+2
io24 capture 2 -> [in2_ 4-band] -> out2 /  Multiband" (left In 1, right In 2)
that source -> [mixer: only channels with Multiband] -> USB playback 1-2
```

One child PipeWire process holds both modules. An input without Multiband
passes through untouched, so the published source stands in for capture 1+2
whichever channels are processed. Both device-facing streams carry
`node.dont-fallback`: an insert that loses the io24 goes quiet rather than
processing the laptop's microphone into its speakers.

In the Host (`io24gtk.py`):

- **Model** gains `Multiband`; selecting it sends the unit `compressor_off`
  and starts the insert. Each input has its own band settings; linked channels
  mirror them. The key-filter rows of the unit's compressors hide under it.
- **The mixer follows.** `route_insert` takes the input's own feed out of every
  bus it was in and makes USB playback 1-2 audible there, recording what it
  changed; `unroute_insert` puts back exactly that, and a return two inputs
  share is restored only after the second one leaves. Faders keep their
  positions.
- **Failure is never a silent input.** The chain starts before any feed moves,
  the feed comes back whenever the processing is not running, a start failure
  switches that Compressor off and says why, and a missing io24 in PipeWire
  waits with the dry feed in place (2-second watchdog).
- **Buffer.** While an insert runs the Host forces `clock.force-quantum` to 128
  unless it is already smaller, and restores the previous value; the user
  changing Buffer takes the setting over.
- **Recording.** The published source becomes the default input while on, and
  the io24's own capture is restored when off.
- **Session.** `host_features.multiband_insert` (version 1) carries both
  inputs' settings, what was rerouted and the borrowed buffer, so a crashed
  session's mixer changes are undone or carried on at the next launch. Snapshot
  *files* get the settings only — `snapshot_host_features()` strips the
  session's routing. A pre-2026-09-11 `host_features.multiband` loads into both
  inputs, switched off, with a completed-load notice.
- **Shutdown** gives every feed, the buffer and the default input back; which
  inputs had Multiband stays in the session.
- The retired playback-sink switch ("io24 Multiband" output device) is gone
  from the UI; `Chain`/`build_conf` stay for the command line. The offline
  banner no longer claims "the multiband compressor still works" without the
  unit, because now it does not.

A device block cannot hold this: saving a preset under Multiband stores the
unit's compressor **off**, which is what the unit is doing.

## 3. The crossover did not sum flat — now it does

The four bands were independent parallel legs (`LP0 | HP0·LP1 | HP1·LP2 |
HP2`), which lack the phase of the splits they do not use. Evaluated over
20 Hz–20 kHz that sums to a **dip of 1.23 dB at 792 Hz** at the default
150/800/4500, and 1.38 dB at 60/250/2000. `CROSSOVER_LEGS` now cascades them
with all-pass compensation (`low = LP0·A1·A2`, `low-mid = HP0·LP1·A2`,
`high-mid = HP0·HP1·LP2`, `high = HP0·HP1·HP2`, summing to `A0·A1·A2`), and Q
is set explicitly to the Butterworth value on every section instead of relying
on the builtin's default. Measured on the graph the code builds: **< 0.01 dB**
at three crossover spreads, which is now a regression test.

## 4. The shared reverb is fully wet

Every Universal Control scene recovered from this unit keeps the reverb
engine's own mix at **1.0** (`Main.scene` size 0.475 / HP 150 / pre-delay
38.8 ms; `B A S E.scene` 0.015 / 305 / 11.3 ms; `Piano Accomany.scene` 0.49 /
150 / 16.3 ms). The Host defaulted to 0.35. The reverb is a send effect, so a
dry share on the FX return doubles the input already in the bus. Wet mix now
starts at 100 %, every character sets it, and the return level is what sets how
much reverb. Not verified by listening.

## 5. A Host snapshot with reverb character or Auto gain could not be saved

`_normalise_host_features` accepted only `multiband` and `pan`, while the GTK
Host has been saving `reverb_character` (and, since 2026-09-11, `autogain`)
with every snapshot — so `save_preset` raised "unknown host feature" and the
save failed. Both are now accepted as the Host's own objects (validated as
objects; the Host already reports values it cannot use), with a regression
test that round-trips a snapshot carrying them.

## 6. Voice FX from a stored block: the closing record

Codex did not answer the 2026-09-11 05:15 OUTBOX question (INBOX unchanged
since 03:55). This is the answer from the retained static evidence, as a
closing record, not a new campaign.

The user's hypothesis — "I dont think that fx are actually stored on the device
itself beyond the Fat channel" — is very close to what the evidence shows, with
one correction: the effect is stored, but the record we and UC write is not
eligible for the loader that would play it.

1. **The gate needs a version-2 record.** Structured-state apply `0x531e0`
   reads four bytes at cursor zero and requires the native word `2`
   (`0x53212 cmp.w fp, #2`; PROTOCOL.md 2026-09-05). Only past it does the
   route reach component 201's state loader `0x5545c`, the one thing that sets
   all three conditions gate `0x50af8` checks (`+0x44 != 0`, `+0x39 != 0`,
   `+0x40 == 0`).
2. **What the firmware's own defaults look like.** The four embedded slot
   records at `0x69230/0x69670/0x69ab0/0x69eb4` begin with little-endian u32
   `2` and hold length-delimited four-byte-keyed chunks.
3. **What we store instead.** UC's active-slot writer and this Host both emit
   a tagged archive whose physical record starts with `0x7b` (`{`);
   `_build_uc_slot_json_frames` is that path, and the retained factory Slap
   Echo archive at `0x6b1c8` begins `7b 69 0b 70`. Read natively that is
   `0x700b697b`, not `2`.
4. **Nothing rewrites it in between.** Ingress, storage and recall are
   byte-preserving: the wrapper's eight-byte CRC/length header never reaches
   the parser, and the parser-visible first word is exactly
   `little_endian_u32(payload[0:4])` (the two sealed 2026-09-05 framing runs).

So a stored block recalled by either path — Host `recall_device_slot` or the
unit's own Preset button — hands `0x531e0` a `{` archive, fails at `0x53212`,
and component 201 is never loaded or armed. That is consistent with every
listening result on this unit, including 2026-09-11's "No tail on either
channel or any block" and "No, Ive never heard it from a stored block", and
with shared reverb (block 202, a different route) being the only effect ever
heard.

**Not established, and the honest gap:** which path applies a `{` archive's
Fat Channel sections — the strip loader at `device+0x5090` that Codex traced
has `filt/gate/comp/eq/lim` and **no** component 201, which would explain "the
Fat Channel loads, the effect does not", but nobody has followed the archive
applier end to end. The stored bytes in the unit cannot be read back, so
"the record we wrote is the record stored" also remains unproved.

**Lead, recorded not acted on:** the native version-2 chunk representation is
already implemented offline (`io24_native_stat.py`,
`_build_native_slot_memp_frames`), and it is the shape `0x531e0` accepts. Any
test of it is a device write and needs a separate exact authorization; the user
has de-scoped unit-only effects ("I guess its just for when connected to a
host, thats all").

## 7. Verification

- Focused: 176 passed + 52 subtests across `test_io24_multiband_insert.py`,
  `test_io24_host_parameter_repairs.py`, `test_io24_vintage_eq_view.py`,
  `test_io24_host_resume.py`, `test_io24_host_rate_and_effects.py`,
  `test_io24_host_dsp_amount.py`.
- Matrix: two regenerations byte-identical, checked in at SHA-256
  `61be8f93e8156585553ead28acf641325964b5f48f655ca0efbcc3e4eafa9144`
  (was `16b1ea67…e96f`); `test_io24_full_parameter_inventory.py` 28 passed.
- Full hardware-free suite: running at the time of writing; the previous run of
  this branch was 648 passed / 1 skipped / 141 subtests with exactly the two
  failures fixed here (stale matrix, and `_multiband_selected` on a fixture
  with no Model row).
- New tests: `tests/test_io24_multiband_insert.py` (graph, config, state
  validation, mixer routing on the driver's real send model, process owner,
  reconcile start/stop/give-up/waiting, crossover flatness, shutdown order).

## 8. What is not verified

Nothing here has been heard. Specifically: the insert's level match against an
input's own feed, its round-trip delay while playing, whether the six-channel
capture and playback positions link as written on this machine, and the fully
wet reverb. All are first-run acceptance items, and the insert has never been
started.

## 9. The UI sizing pass

The user asked for "the sizing of the program, the sizing of everything, and
the visible layout of everything", then chose **use more of the window** and
named Routing/Device/Presets, Mixer and Effects as the pages that bother them.

**How it was seen.** A headless harness renders the real window with the
project's own stub device (`tests/paint_smoke.py`'s `FakeDev`/`FakeInner`, the
real `Ctl`, `FakeSpectrum`) and PipeWire stubbed out, under a `gtk4-broadwayd`
display on a private unix socket: no USB, no ALSA, no PipeWire, nothing on the
user's screen and nothing on the network. Four of six pages render that way;
Mixer and Fat channel produce no render node offscreen at all (the project's
own `capture_window` raises "GTK produced no render node"), so with the user's
explicit go the window was opened briefly on the desktop with the same stubs
and all six pages captured at 1040x800 and 1440x900.

**What was wrong.** Effects, Device and Presets are `Adw.PreferencesPage`,
which clamps its content at 600sp; Fat channel clamped at 580 and Routing at
760. At the size the Host opens at, that left roughly a third of the width
empty on either side — the pages sat in a centre strip while the window was
1090 px wide.

**The change.** One `PAGE_WIDTH` (900sp) and `PAGE_TIGHTEN` (640sp) for every
page. `Adw.PreferencesPage` exposes no width API, so `widen_page()` walks a
built page and widens every clamp inside it (anything taking both a maximum
size and a tightening threshold), and `wide_preferences_page()` is what the
three preference pages are built from. The two pages that clamp themselves use
the same constants. Verified by re-rendering: Device, Effects, Presets, Fat
channel and Routing now span the window; Mixer was already full width.

Tests: `tests/test_io24_host_layout.py` (the helper against a fake widget tree,
and source contracts that every page goes through it).

**Still open on the Mixer**, the one page the width change does not touch: each
input strip ends with an explicit `Gtk.Box(vexpand=True)` spacer above a fixed
260 px meter/fader row, so the bottom third of the strip is empty and the
meters stay short however tall the window is.

**The Mixer, vertically.** The width change does not touch it — it was already
full width — but each input strip fixed its meter/fader row at 260 px and then
pushed everything up with a `Gtk.Box(vexpand=True)` spacer, leaving the bottom
third of the card empty however tall the window was; the bus strip did the
same. Both now treat 260 px as a floor and expand, so the meters and faders use
the window's height (visibly taller at 1440x900), with a fixed 8 px pad keeping
the Gain reduction rows off the card's edge. The Monitoring strip is unchanged:
its content is buttons, which should not stretch.
