# CP34 device preset and Voice FX continuation

## 2026-09-10 controlling checkpoint: DSP amount and Bypass on the Device page

The user asked (2026-09-10 ~18:53 PDT, a message queued mid-turn) for UC's
`dspAmount`/`bypassDSP` as settings in the Host's settings tab. Built offline on
worktree branch `worktree-io24-dsp-device-tab`: per channel a Bypass switch and
a DSP amount slider on the Device page, composed onto the one wire-4 processing
scalar — zero while bypassed, the amount otherwise, the amount never below
0.1 % so it cannot read as bypass. The Effects-page processing slider is gone.
A recall that had to assert the enable now shows 100 %, not bypassed. The
pairing is the Host's reading of UC's schema, not a recovered UC binding; the
matrix component rows stay `PENDING`, and partial amounts are unmeasured on the
main path. Full suite 567 passed, 1 skipped, 127 subtests, exit 0; matrix 751
rows, deterministic at `cf9a7938…3354`. No device action.

Worktrees: a fresh one lacks six gitignored UC 4.7.2 binaries under `runs/`,
and 7 UC-analysis tests then fail on missing inputs; symlink them from the main
checkout. Commit `1fc5245` carries the solo/auto gain/Vintage EQ run
byte-for-byte; the main checkout still holds those changes uncommitted.

The Channel-1 slot-0 MAIN rewrite from `Main.scene` ch1 is still staged (see
the correction in the next section).

Resume from
`runs/20260910T193341-0700-dsp-amount-device-page/PROGRESS.md`.


## 2026-09-10 controlling checkpoint: Host solo, auto gain, Vintage EQ view

Built offline the three Host gaps from Codex's 2026-09-09 audit that remained
after `db39742`: a Host-side mixer solo (`set_solo`/`clear_solo`/`soloed`,
never shadowed, released on Host shutdown), a continuous per-input Host-side
Auto gain switch (95th-percentile JaSt level held near -12 dBFS, silent, fader
locked while on; the user rejected a one-shot prompt design), and a view of
recalled Passive/Vintage EQ bodies whose save now carries the stored EQ through
verbatim. Full hardware-free suite 554 passed, 1 skipped, 127 subtests, exit 0;
matrix 751 rows, deterministic at `83807012…eb0d`. No device action; nothing
committed. Open with the user: `dspAmount`/`bypassDSP` are UC's two-control
face of the one wire-4 processing scalar the Effects page already drives; the
user wants them in the settings (Device) tab.

**Correction carried forward:** the section below claims the authorized MAIN
was restored. Commit `3fd72cb` withdrew that — `build_main_record()` is a
fabricated guitar preset, not the user's MAIN. The user then chose
`~/.cache/io24/re/scenes/Main.scene` ch1 (name set to MAIN, canonical SHA-256
`f74cd983…d222`) and to leave preamp gain at 30.0 dB. That rewrite is staged
and needs the io24 connected plus an explicit go.

Resume from
`runs/20260910T184415-0700-host-solo-autogain-vintage/PROGRESS.md`.


## 2026-09-10 controlling checkpoint: MAIN restored, and it survives a power cycle

The authorized `MAIN` profile was written back to Channel-1 slot 0 through
`re/cp34_channel1_main_slot_stage.py` at 99 percent battery on serial
`AB7C22200355`, firmware `0128`. Result `MAIN_ACTIVE_WRITE_SENT`, record
SHA-256 `fdd1c3def78bd774f49eccb34ae85c1f1e60906337723b06e847aee6e63b2404`,
one `MemP/Stat(0)` fragment and zero replies. The stage verified Channel 2,
both gains, stereo link and the Voice FX assignment unchanged before and after.
Channel 1 had been sitting on slot 1 and bypassed (flags 417); it is now on
slot 0 and processing. The identity-bound registry entry, which still held the
`voicefx-arm:MAIN` Detuner body, was corrected to the authorized record under
source `restored-authorized:MAIN`.

A real power cycle then followed — physically unplugged by the user, because
the unit is on a root-hub port with no per-port power switching and every
software reset would have left VBUS applied and returned a false positive. The
Host was closed across the whole window so no cached shadow could be re-pushed
on reattachment. `devnum` moved 5 -> 6, confirming the device left the bus.

Every readable preset-relevant field survived identically: slot 0 selected,
Channel 1 preset enabled, gains 30.0 and 24.287769317626953, stereo link off,
processing channels (0, 1), Channel 2 on slot 2 and enabled. The only change is
`flags` 897 -> 385, bit 9, which is absent from the recovered slot-42 table and
matches the value recorded immediately after the stage write, so it tracks
session/stream state rather than preset state.

This establishes device-slot **selection and enable** survival across power
loss. It does **not** establish the stored body. Slot bodies have no readback
on firmware 0128, so listening is the only remaining test of whether slot 0
really contains MAIN — and it is now a valid test, because the power loss wiped
the Fat Channel values the stage had applied directly.

Resume from
`runs/20260910T013611-0700-main-power-cycle-survival/PROGRESS.md`.


## 2026-09-10 controlling checkpoint: MAIN correction, preset saving, effect clock

**Correction, controlling.** The previous checkpoint's claim that slot 0 `MAIN`
holds a Detuner body with `on=1` is withdrawn. The authorized `MAIN` pinned in
`re/cp34_channel1_main_slot_stage.py` is **Delay, `on=0`**, Standard EQ. The
Detuner body is a registry entry written `2026-09-09T22:47:32Z` under source
`voicefx-arm:MAIN` — a receipt, read as if it were the user's preset. The
user's `MAIN` body was therefore very likely overwritten on the device by that
write; it is `WRITE_SENT_UNVERIFIED` and slots have no readback, so it cannot
be confirmed either way. It is recoverable from `build_main_record()`. Slot 1
`B A S E` is untouched. Restoring `MAIN` is a separate authorized device write
and has not been done.

"Recall MAIN and listen" is consequently not a valid acceptance test; the
authorized MAIN would produce a false negative. The acceptance test is **Save
and activate**, which authors a body of known contents into the channel's
inactive block and recalls it. The block-201 gate finding is unaffected — it
rests on the firmware disassembly and the 2026-08-31 report, not on slot
contents.

Preset saving is repaired: presets can be named (refused when empty or over the
record's 127-byte form), **Save and activate** writes then recalls while **Save
only** leaves selection alone, a failed recall is never reported as a failed
save, and a newly saved body is listed without restarting. A recalled body is
adopted onto the controls; a Passive/Vintage body is not shown at all and says
why, because it has no Standard-band form.

Effects are repaired at the clock: no device write passed a sample rate, so
every biquad, time constant, reverb and rate-dependent Voice FX payload was
built for 48 kHz whatever the device was running — at 96 kHz a 1 kHz band
landed at 2 kHz. The Host now tracks the real rate, passes it everywhere, and
recomputes and re-sends on a change. The limiter's release is a control at last
(every prior write used the 0.4 s default); it stays out of the slot record
because UC's `limit` section has no such field. The Host-only reverb character,
movement and movement depth now travel in `host_features` instead of resetting
to Custom on every load.

Offline implementation evidence only. No device write, recall, audio, Host
launch, USB, Wine, install, network or firmware action occurred.

Resume from
`runs/20260910T000000-0700-save-presets-and-effects/PROGRESS.md`.


## 2026-09-09 controlling checkpoint: MAIN recalled; Voice FX gate opened

The missing action identified by the prior checkpoint has now run on the live
Host. The process that had been open since before the patch still rendered the
old inert `MAIN` / `B A S E` rows and owned USB interface 5, so it was closed
normally and the installed `io24-mixer` launcher reopened the current worktree.
The patched Host's `MAIN` row then invoked `recall_device_slot(1, 0)`. The
Effects page reports `Opened` and: `MAIN was recalled on Channel 1, so model
and parameter edits reach the engine`.

This was one Channel-1 slot-0 recall. It did not rewrite either slot body,
change `B A S E`, start Wine, touch firmware/DFU, reset the unit, or use the
network. Battery was 37 percent and `lsusb` showed `194f:0422` before the
action. The Host remains open on Effects with MAIN's stored Detuner body
adopted. Human listening is the remaining audibility observation; the Host's
transport/gate path is no longer pending.

Claude's interrupted save-path refactor left two stale test fixtures and the
generated matrix behind current source hashes. The fixtures now describe the
new `Save only` / `Save and activate` UI and exercise the extracted adoption
helper. Two independent matrix generations were byte-identical at SHA-256
`e2294b839c7be884e10f8991d8a723954d86c49e2affd2a34fc1711f4f79c540`.
Focused result: 112 passed plus 36 subtests. Definitive result: 495 passed,
1 skipped, 0 failed, plus 124 subtests, with `ResourceWarning` elevated to
error. See
`runs/20260909T184211-0700-main-recall-live/PROGRESS.md`.

## 2026-09-09 controlling checkpoint: the Host had no recall, and that is the gate

The Voice FX defect and the presets defect are one defect. Block 201's handler
at fw `0x50af8` returns having done nothing unless `+0x44 != 0`, `+0x39 != 0`
and `+0x40 == 0`, and only the native `Stat` structured-state loader `0x5545c`
sets all three. Recalling a device slot is the decoded way to run that load,
and the Host had no recall anywhere: `_slot_changed` sent `set_preset_slot`
alone and the `Host presets` list was inert text. Every direct block-201 write
was therefore accepted, stored and silently discarded.

This supersedes the reading that the isolated Delay negative pointed at
routing, wet/dry, or a model-specific default. The Detuner neutral-default
correction was a genuine defect and is kept, but it was not why the insert was
silent. Slot 0 `MAIN` already holds a Detuner body with `on=1`, `detune=1`,
`mix=0.8` — the very values that were being pushed directly — and the Host
offered no way to recall it.

`recall_device_slot()` is the new primitive: cross-channel and non-integer
slots are refused before any write, an unreadable processing state fails
closed, selection precedes enable, and the enable is asserted only for a
channel the device reports bypassed so an existing partial mix is never forced
to full. Slot blocks now recall, `Host presets` rows carry `Recall on device`
and show each body's Voice FX state, the Voice FX section carries a
`Device activation` row (Not opened / Opened / Closed / Unknown), and the Host
notices recalls made from the unit's own Preset button.

This is offline implementation evidence. No device write, recall, audio, Host
launch, USB, Wine, install, network, or firmware action occurred, and
`recall_device_slot` has never run against hardware. The separately authorized
live acceptance is: recall slot 0 `MAIN` on Channel 1 and listen.

Resume from
`runs/20260909T170000-0700-device-slot-recall-gate/PROGRESS.md`.


## 2026-09-09 controlling checkpoint: Detuner neutral-default correction

The user reported that the isolated 240 ms, 75-percent-feedback,
100-percent-wet Delay remained inaudible while shared reverb worked. This
rejects the candidate that the visible reverb processing-mix control should be
resent before block 201; that write was removed from the Host path.

The concrete Detuner defect was simpler: the Host initialized Tune to index 8,
which the builder defines as zero semitones, so selecting Detuner started
audibly dry. UC's factory Detuned Vocal record instead uses index 1, 80-percent
wet, and `on=1`. Those values are now the Host defaults and were sent directly
to Channel 1 at 95 percent battery on serial `AB7C22200355`. The Host is open;
human confirmation of the pitch drop remains pending.

Resume from
`runs/20260909T150313-0700-voicefx-activation/PROGRESS.md`.

## 2026-09-09 controlling checkpoint: live Host effects repair

The shared-reverb switch now establishes the Channel-1 processing mix and Main
return before arming block 202, matching the sequence with prior positive
listening evidence. A bounded live write armed Plate at 35 percent Channel-1
mix and a 0 dB Main return on serial `AB7C22200355`; the control connection was
then closed. This is a completed device write, not fresh listening confirmation.

The multiband switch now makes its public PipeWire sink the system default when
the chain becomes ready, restores the physical io24 output when switched off or
when the Host exits, and fails closed if routing cannot be established. A live
round trip started node 138, selected it, restored the physical io24 output,
and stopped cleanly. The physical io24 output was found muted at 40 percent and
was unmuted without changing its volume. There were no active playback streams.

The source launcher was restarted on the patched worktree. The affected suite
passes 142/142 with `ResourceWarning` elevated to error, including release
packaging, and the regenerated 748-row matrix is deterministic at SHA-256
`aa9e26fd432110d6ea3d96aafe3a353a8fa43d2070efc60d80881a2d5a675643`.
No peer review was requested. Direct block-201 Voice FX activation remains
unestablished and was not falsely presented as repaired.

## 2026-09-09 predecessor checkpoint: MAIN/B A S E restored and Host paths repaired

The user identified `MAIN` and `B A S E` as their two Channel-1 device presets
that an earlier Codex run accidentally removed, explicitly authorized restoring
both physical blocks, and required both names in the Host preset list.

At 98 percent battery, exact io24 serial `AB7C22200355`, USB ID `194f:0422`,
firmware `0128`, stereo link off, and with no running io24 Host or active
PipeWire server, the bounded restoration sent the pinned complete `MAIN` record
to global slot 0 and the retained `B A S E.scene` Channel-1 record to global
slot 1. `MAIN` was left selected and enabled. Both gains, Channel 2's slot and
enable state, stereo link, and the processing-channel pair matched before and
after. The identity-bound registry contains slot 0 `MAIN` and slot 1
`B A S E`, both honestly marked `WRITE_SENT_UNVERIFIED`; stored-body readback
is unavailable on this device.

The Host now lists those registry-backed user presets separately from factory
sounds and includes their names in Channel 1's slot row. Multiband startup no
longer treats `Popen` as success: the public `io24 Multiband` node must appear
within the readiness deadline or the process is stopped and the switch remains
off. Shared reverb enable now serializes the visible Channel-1 processing mix,
engine parameters, Main return level, and Main return assignment as one worker
action; disabling preserves the path and turns off only the engine.

At the user's direction, the Main/Mix A/Mix B bus-pan controls were then
removed completely. The bus strip is meters only. The passive Mix A/B sources
retain exact left/right capture selection at fixed unity, and Host snapshots no
longer persist or restore bus pan. Old `host_features.pan` data is accepted only
to discard it with a completed-load notice, so it cannot recreate a control or
alter a source.

The Channel preset-block dots now breathe through opacity only, from 0.25 to
1.0, on faster 1.8-second and 0.9-second cycles; their animated radius is fixed
so the dots never grow spatially. All embedded
`Adw.PreferencesGroup` descriptions were removed from the Host; explanatory
material remains in README.md and GUIDE.md while operational row state remains
beside its control.

The existing source launcher points directly at this worktree, so no install
was needed. The stale orphaned filter-chain process was terminated and the
repaired Host was restarted in the desktop session after the final UI edits.
The focused Host suite passes 63/63; the affected source, persistence,
inventory, and hot-key suite passes 140/140 with `ResourceWarning` elevated to
error; release-package verification passes 1/1 without installation. Two
independent 748-row matrix generations were byte-identical; the checked-in
matrix SHA-256 is
`94c1d5af78ee652b22c98893d7dd619edc84af84b379f079e3e1c0832978b23e`.

Claude received only a tool-less textual plan, not the old 53-file snapshot or
the user's personal scene. Its one useful finding—require the write window to
be free of Host/audio activity—was applied. Its suggestion to back up stored
slot bodies was inapplicable because the firmware exposes no body readback. A
final behavior-only sanity request was refused by Claude at its session limit
and was not retried, rather than delaying the agreed implementation; no repeat
snapshot review was made.

## 2026-09-09 superseded checkpoint: passive Mix A/B Host sources

The previous per-input pan monitor is retired. The GTK bus strip now keeps Main
centered and disabled because the io24 exposes no complete Main USB capture
pair. It publishes `io24 Host Mix A` from USB capture 3-4 and
`io24 Host Mix B` from 5-6 as separate passive, non-remixing PipeWire sources.
They have no playback target and route nowhere by default. Their processes,
readiness deadlines, controls, and failures are independently owned; a balance
knob enables only when its exact source node appears.

Host snapshot `host_features.pan` version 2 stores only the two center-unity
stereo balances. It never crosses channels. Valid version 1 input-pan data is
strictly checked, then migrates to centered Mix A/B values with the explicit
completed-load notice `legacy input pan was not applied; Mix A/B balances
centered`. Snapshot adoption itself does not launch or alter PipeWire.

Offline gates are GREEN: 123 focused source/persistence tests plus 46 subtests;
183 affected tests plus 81 subtests with `ResourceWarning` elevated to error;
release-package verification 1/1 without installation; and two byte-identical
748-row matrices matching the checked-in artifact at SHA-256
`e3b4b378dd3cd0701415e4af9499dad29c60b6299f9c65d80aa8a7a1f8cae037`.
Claude's authorized 53-file architecture review agreed and required the two
non-remixing flags and separate chain owners; both are implemented. The
separately authorized final review refreshed the same 53-path boundary at
`2026-09-09T11:14:02-07:00`; all 53 entries verify. Dedicated UUID
`15978222-d591-4549-9876-21c04f741e14` returned success with nonzero token use,
zero permission denials, no substantive defect, and agreement that the
implementation is sound. No further review turn was requested.

This remains offline implementation evidence. Do not claim live source
publication, exact channel selection, visual acceptance, balance control feel,
audibility, or routing. No Host, USB/device/audio, Wine, install, firmware,
publication, or Obsidian action occurred. Resume from the newest run at
`.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260909T103619-0700-host-bus-source-balance/`.

## 2026-09-08 controlling checkpoint: Mixer, pan, and notification refinement

The GTK Host no longer emits bottom toasts for routine parameter changes across
its tabs. Continuous controls and ordinary toggles/selectors report in place;
toasts remain for connection transitions, faults/constraints, and discrete
completion of file, factory-load, capture, mirror, or device-slot operations.
Factory-load success is now posted only after its worker returns. The entire
GTK cached-control reapply banner, handlers, and state machine are removed;
explicit Host snapshot save/load remains, as do useful connect/disconnect
notices.

Mixer input strips now display `S1`/`S2` with a blue active dot: S1 breathes
slowly, S2 twice as quickly, bypass is an empty ring, and reduced-motion makes
the dot steady. The bus section has one consolidated footer and narrower
meters. The fixed preamp control is labelled `HPF`.

The two input pan knobs are independent regardless of stereo link and persist
as strict Host-only JSON. The opt-in `Host input pan` route is a separate
PipeWire physical-capture-to-io24-playback filter chain with equal-power gains,
not the app-playback multiband sink. It defaults off, never changes Monitoring
Blend automatically, warns about direct-path doubling/latency, stops on Host
shutdown or device disconnect, and skips redundant identical starts.

This is offline implementation evidence, not a live-function claim. The
interface was unplugged and no Host, USB/device/audio, Wine, install,
publication, Git, or Obsidian operation occurred. A later live acceptance must
verify node selection, audible left/center/right travel for each channel,
round-trip latency, direct-monitor blend behavior, and visual layout before
calling the pan path operational on this workstation.

Dedicated Claude UUID `15978222-d591-4549-9876-21c04f741e14` reviewed the
same approved 53-file boundary. Two findings were corrected (fully remove the
hidden reapply state machine; make identical pan starts idempotent). Its slot-
speed finding was a zero-based-index misread; the peer explicitly withdrew it
after the mapping and directional regression were provided. The correction
turn used snapshot `2026-09-08T16:26:40-07:00`, had zero permission denials,
and found no remaining defect.

The terminal handoff-text turn on that UUID used the refreshed 53-entry
snapshot created `2026-09-08T16:42:06-07:00`, returned with zero permission
denials, confirmed the older recovery paragraphs now match the removed GTK
reapply UI and current `HPF` label, and found no new substantive defect.

Fresh gates pass: release package 1/1; affected Host suite 172/172 with
`ResourceWarning` elevated to error; uninstalled 236508-byte wheel SHA-256
`58719a27dd9b2505ff0baad081042fca2a24da5007fee29399e630d85365a77f`
with 15/15 modules, 7/7 entry points, isolated imports, and
`python -m io24_scene`; two byte-identical 748-row regenerations and the
checked-in matrix at SHA-256
`84e0b3fbe7e9aa6ee736a8f52db6da50732013e5a482e33fcc0c01443d967f28`;
and a verified five-entry Task 5 checkpoint. Task 5 is complete for offline
Host correctness/package readiness only. Private Reverb activation/audibility,
device persistence, and live pan acceptance remain separate unresolved gates.

## 2026-09-08 controlling checkpoint: effects lifecycle cleanup started

The user has redirected the active work to functional effect behavior with and
without the Linux Host: the shared reverb, the distinct Voice FX/private
reverb, device-resident operation, and cleanup of the Host's effect controls.
The current run is
`runs/20260908T070000-0700-effects-lifecycle-host-cleanup/`.

The first offline correction is complete. The production Effects page now
names `Shared reverb` separately from the `Voice FX insert`. The shared engine
switch says that a channel send and FX return are also required; it no longer
implies that one on bit makes an audible path. The Voice FX switch is labelled
`Model parameters enabled` and says that standalone activation requires a
device-slot save and recall. The stale structural/private-lane explanation,
the unused `fx_save_both` branch, and the two unregistered Channel-2 Delay/Slap
Echo helper methods are removed from `io24gtk.py` entirely.

This is presentation and containment, not device evidence. Shared block-202
reverb can continue onboard after the Host closes once its engine, input send,
and audible return have been configured, but power-cycle survival remains
unproved. Direct block-201 owner/model writes do not prove the separate native
Voice FX activation gate. The source-bound standalone candidate remains a
complete channel record written to a device-resident slot, then explicitly
selected/enabled/recalled and verified by listening. Shared reverb is not part
of the modeled per-channel slot record; do not conflate these two paths.

A crash-safe `DeviceSlotRegistry` and `save_known_device_slot` now accept only
a complete body, validate before transport, record only Host-written
provenance after the write call returns, and never select, enable, recall, or
directly apply the slot. Schema v2 binds every entry to the connected unit's
serial, VID/PID, and firmware `bcdDevice`; identity failure stops before a
write. Zero replies remain `WRITE_SENT_UNVERIFIED`, never device readback or
commit.

The GTK Factory presets group now exposes the matching product workflow. Pick
the physical target channel and one of its two device slots, then choose
`Store in device slot…` on any complete factory record. The Host refuses the
currently selected destination, requires an overwrite confirmation, and queues
only the complete body write plus registry commit. It does not select, enable,
recall, or directly apply that slot. Passive/Vintage EQ and record-resident
Voice FX therefore have an exact device-store route even when direct-live apply
is unavailable.

Claude's first successful fresh-UUID review found two defects before this UI
was exposed. `_push_fx` used to resend the permutation-sensitive Voice FX owner
assignment on every slider/model edit; it now assigns once per connected
device/target, while still sending every model edit, and the UI discloses that
a real owner change can exchange the device's two exposed slot indicators. The
registry also lacked device identity; schema v2 closes that gap. Source review
retracted the earlier unsupported claim that the disclosed Channel-2 stages
directly call Channel-1 selector/enable APIs. A Voice FX assignment change is a
credible slot-exchange mechanism, but the exact incident cause remains
unproved.

The expanded Host/effects/stage suite passes 176/176. The deterministic
750-row matrix includes the registry-aware API and matches two independent
outputs byte-for-byte at SHA-256
`de1ff7fd14b1555e081c0beccd23490bd0c3a518a39d7759be5ee068cedc1ec7`.

Every decision and result is appended to Claude's durable inbox. The successful
52-file review used only fresh dedicated UUID
`a764bfc8-6fec-453f-9289-92ace5f16ce5`, consumed nonzero tokens, and had zero
permission denials. The immediate correction-review resume returned an
explicit Anthropic 429 with zero tokens: the session limit resets at 10:00 AM
Pacific. Resume this UUID after that time and review the corrections plus GTK
workflow; do not resume either retired or unrelated session.

No USB/device/audio action, Host launch, slot write/select/enable, effect write,
Wine access, firmware action, publication, installation, or Obsidian write
occurred in this run. Do not perform a live effects stage without a new exact
authorization naming the channel, slot, intended effect states, protected
other-channel state, rollback/restoration behavior, and listening steps.

## 2026-09-08 controlling checkpoint: physical HPF display resolved

The user authorized the bounded Channel-1 display probe recorded at
`runs/20260908T061654-0700-channel1-hpf-display-probe/`. Preflight passed at
100% battery on exact serial `AB7C22200355`, firmware `0x0128`, with link off,
MAIN slot 0 enabled, Channel 2 slot 2 enabled, and duplicate byte-identical
JaSt replies. Only the 40 Hz digital Fat Channel write ran. The user reported
that the physical screen still displayed `80Hz`; cleanup sent MAIN's exact
24 Hz digital bypass. Channel 2 remained unchanged and no slot/preset action
occurred. The user confirmed that they intentionally changed Channel-1 gain
from 30 to 33 dB while observing the display; retain 33 dB unless they request
another value.

The official io24 manual resolves the display semantics: the Channel screen's
`80Hz` field is the separate fixed preamp HPF and the encoder toggles it on/off.
The manual separately defines the Fat Channel HPF as adjustable from 24 Hz to
1 kHz in Universal Control. Therefore arbitrary digital cutoff numbers are not
documented as physical-screen content, and the remaining 80/160/55 writes were
not run. The probe has no gain command and the user-confirmed 33 dB change is
not a Host/probe defect.

## 2026-09-08 controlling checkpoint: Host preset quarantine and HPF UI

The current offline implementation record is
`runs/20260908T054619-0700-host-preset-quarantine-hpf-ui/`. Ordinary Host
snapshot save/load, startup save/apply, and explicit backend cached-state
reapply quarantine device preset mode, slot selection, and enable calls by
default. An explicit backend opt-in remains, but normal GTK paths neither expose
cache reapply nor move or disable MAIN or Channel 2 through stale selector
state. Backend reapply reports disclose the quarantined count. The production
Effects page no longer
contains the Channel-2 Delay/Slap Echo experiment actions or deferred private-
reverb/custom-firmware controls; the later effects-lifecycle cleanup above also
removes their dead GTK helpers.

The Mixer page labels its separate boolean switch `HPF`. The
Fat Channel uses one synchronized digital HPF surface: Off, 40 Hz, 80 Hz,
160 Hz, or Advanced 24 Hz..1 kHz. This is Host-written state, not device
readback. The user explicitly expects the physical io24 screen to show the
selected number. Static firmware evidence is insufficient to confirm or deny
that behavior. A separately authorized, human-paced Channel-1 display probe is
the next live gate; do not run it without explicit permission. It must touch
only live `filt` state and restore MAIN's exact 24 Hz bypass in `finally`; it
must not save, select, enable, or overwrite any slot.

The focused suite passes 62/62 and the expanded affected Host suite passes
121/121. The matrix remains 750 rows and regenerated three times byte-
identically at SHA-256
`4fae0d3d338a00a9ce1892a20109a43381530131d28914f174cbeed851beedac`.
Peer work used dedicated UUID `288f3639-1f23-4309-bd76-168255b7644e` with
zero permission denials; Claude independently verified the quarantine and HPF
UI and found one dead-helper defect that is now removed.

Claude's last successful turn reviewed the executable quarantine/HPF work and
closed it without a remaining finding. Two subsequent same-UUID requests for
the final comment-only source digest and refreshed Task 5 checkpoint returned
`Request timed out` with zero input/output tokens and zero permission denials;
do not count those two unavailable responses as review. Codex independently
reran the expanded suite (121 passed plus 64 subtests), regenerated the matrix
twice at the digest above, reran the release-package regression, and verified
the refreshed five-entry Task 5 checkpoint.

## 2026-09-08 controlling checkpoint: Channel 1 MAIN active, slot-0 write sent

At the user's explicit request, Channel 1 now has a new complete preset named
`MAIN` selected and enabled on the first device slot (global slot 0). The exact
record and live result are in
`runs/20260908T043900-0700-channel1-main-slot0/`.

The profile uses the Standard compressor active at -24 dB, 2:1, 30 ms attack,
120 ms release, +2 dB makeup, soft knee, manual timing; limiter active at
-0.6 dBFS; a four-band Standard EQ starting curve for the Strandberg Boden 8
(90 Hz +1 dB shelf, 300 Hz -2 dB, 1.8 kHz +1.25 dB, 7 kHz +1 dB shelf); gate
off; Voice FX off; and no HPF. No HPF was implemented on both relevant layers:
the `filt` record/direct path uses its documented 24 Hz bypass encoding and the
separate preamp `Pari/5` HPF switch received an explicit off write.

The new guarded runner never calls the global preset-mode setter or changes
Voice FX assignment. It bypassed Channel 1, moved its selector from slot 0 to
slot 1 before overwriting slot 0, sent one hash-pinned complete
`MemP/Stat(0)` frame, selected slot 0, enabled Channel 1, and directly applied
the identical strip values so immediate function does not depend on unproved
slot-recall semantics. Exposed baseline and post-state match for Channel 2:
gain `24.287769317626953`, slot 2, preset enabled, processing index 1. Channel 1
gain remained 30 dB; stereo link remained off; battery was 95 percent.

Transport completed with one fragment and zero replies. Therefore the slot
body's durable/nonvolatile commit remains unproved until a later disconnected
recall or power-cycle check, and sound quality remains subject to the user's
listening judgment. The focused new and neighboring suite passes 61/61.
Do not rerun the live stage unless the user explicitly asks to overwrite slot
0 again.

The user clarified the audible incident chronology: before returning to the
computer and asking for the compressor to be turned back on, Channel 1 sounded
as though compression was disabled. That matches the displaced/off effect
state and explains the marked sound change better than an unsupported claim
that the recovered curve alone caused it. The later MAIN transaction sent the
compressor-on state and directly applied the active compressor profile. Because
DSP parameter readback is unavailable, the send is transport evidence and the
user's listening remains the audibility authority.

## 2026-09-08 controlling checkpoint: Task 5 offline Host publication readiness complete

Task 5 is closed at
`.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260908T021022-0700-host-publication-readiness/`.
The Python wheel metadata now includes all 15 local runtime modules needed by
the advertised Host surfaces and all seven console entry points, including
`io24-scene`. The recovered PreSonus factory-preset data remains source-tree
evidence and is not redistributed by the wheel.

The approved 40-file Claude peer boundary review used only the dedicated
serialized UUID `4aa42435-e87a-4ba1-befe-5571013b4cc1`, not the retired consult
session. All three Task 5 turns completed with zero permission denials. The first
turn found one real regression-coverage gap: archive membership did not prove
runtime importability. A staged missing-dependency mutation produced the
required RED without changing expected wheel membership. The permanent GREEN
test now imports all 15 modules directly from the built wheel in an empty
working directory, verifies their wheel origins, and executes
`python -m io24_scene`. The refreshed same-40-file fix review closed that
finding. A final same-boundary turn confirmed the Python 3.8-compatible module-
name derivation and reported no new defect, stale claim, or authority expansion.
Claude's responses remain peer feedback rather than approval authority.

The affected Host suite passes 114/114. A fresh disposable wheel contains
15/15 required modules and 7/7 console entry points, imports every module from
its own bytes, and runs the hardware-free `io24_scene` usage path without
installation. Two regenerated 750-row matrices are byte-identical to the
checked-in artifact at SHA-256
`9b220c0c2b8224a1452c11cf9b79b336f5e369253503aa4387ffc968a8ba577e`.
The five-entry Task 5 checkpoint verifies.

No USB, audio, Wine, firmware, Host launch, installation, network publication,
Git initialization, or Obsidian write occurred. A repaired live Host preset
round trip, Passive/Vintage source reacquisition, Git setup, publication, and
Obsidian dashboard synchronization remain separately authorized actions.

## 2026-09-06 controlling checkpoint: exhaustive campaign live gate

The 750-row exhaustive plan remains authoritative at
`runs/20260906T165749-0700-host-live-routing-repair/`. Live campaign evidence is
now in `runs/20260906T200916-0700-full-parameter-verification/`.

P0 passed on the exact io24 (`194f:0422`, serial `AB7C22200355`, bcdDevice
`0x0128`): exclusive control ownership, six-channel ALSA topology, empty Host
shadow, phantom off, link off, stable duplicate JaSt reads, Channel 1 slot 0 and
Channel 2 slot 2 at the first gate. Before any P2 write, front-panel/external
state had independently changed Channel 1 to slot 1 and headphone volume from
`0.5841094255` to `0.5541094542`; the P2 immediate baseline therefore correctly
uses those later values.

P2 attempt 1 aborted before audio and before any mixer write. Two input-mute
frames were accepted; the following Channel-2 gain frame timed out. Bounded
recovery and an independent duplicate postflight confirmed flags `0x0181`, both
input mutes off, link off, both presets enabled, Channel 1 slot 1 and Channel 2
slot 2. Raw failure evidence remains failure-labelled in `P2-REPORT.json` and
`MUTE-RECOVERY.json`; `P2-POSTFLIGHT.md` explains the successful final recovery.
No route, DSP, slot-body, playback, capture, Wine, firmware, DFU, reset, or
network action occurred.

No kernel USB reset/disconnect accompanied the timeout. The first P2 runner had
omitted the established Host's 400 ms EP_IN service interval after SetP; it now
preserves that cadence and raises on write failure. The bounded recovery reader
now reassembles fragmented JaSt replies. Eleven focused tests pass. Per the
predeclared stop gate, do not resume live writes as part of that failed batch.
The last battery reading was 19 percent and discharging. A later P2 retry needs
a fresh battery/identity/ownership preflight and a new batch; stop at or below
10 percent. Current row-level observations are in `RESULTS-OVERLAY.json`; both
input-mute rows remain incomplete rather than being rounded up to PASS.

Timestamp: 2026-09-06T17:59:00-07:00
Status: exhaustive atomic verification plan generated and hardware-free
validated; full bounded live authorization recorded; Host remains closed and
live execution has not begun

## 2026-09-06 controlling checkpoint: exhaustive parameter campaign

The user authorized a complete live audit of every Linux Host parameter after
the routing/state repair, with the requirement that no control be accepted on
USB-write success alone. The authoritative plan artifacts are now in
`runs/20260906T165749-0700-host-live-routing-repair/`:

- `FULL-PARAMETER-VERIFICATION-PLAN.md` defines the evidence standard, fixed
  objective tolerances, batch order, stop gates, disconnected acceptance, and
  reverse-order restoration;
- `PARAMETER-VERIFICATION-MATRIX.json` is a 750-row atomic ledger; every row is
  still `PENDING` and `restored=false`;
- `build_parameter_matrix.py` deterministically rebuilds and validates it; and
- `PARAMETER-INVENTORY.json` is the compact human-readable dimension list.

Coverage is explicit: 142 Fat Channel rows, 60 VoiceFX user-parameter rows for
both possible physical owners, 42 generic mixer level/assignment rows, 52
Host-owned multiband rows, all 117 retained vendor descriptor records, all 211
relevant component-model routes, plus native control, reverb, telemetry, Host
state, serializer, and persistence rows. The generic backend's `line/ch3`
entries remain visible applicability gates because the exact Michael/io24 model
has two analog inputs; they are not silently counted as working routes.

P1 also records the blockers that must be resolved rather than papered over:
`phonesSrc` is known but not exposed, Hot Key is source-confirmed but absent from
the Linux Host, Passive/Vintage factory EQ is currently flattened into Standard,
the high-shelf implementation is not bit-exact to UC, and the Passive `bfreq`
list contains a vendor-literal `20kHz` anomaly. Unknown or guessed writes remain
forbidden.

The focused completeness suite passes 21/21. Plan artifact SHA-256 values:

```text
FULL-PARAMETER-VERIFICATION-PLAN.md  4d144cb160f8b311de941530ce8defea15928b21b440e5d9b9168f93677766eb
PARAMETER-INVENTORY.json             5421f6791e421f77b4f8e482fe31f145372a553afe71dfa37c538889d91af2c7
PARAMETER-VERIFICATION-MATRIX.json   9c321e09ca083135405e20ae3008db6132c9ce7dd02b490ea072e104585212a3
build_parameter_matrix.py            652a81518251f28e87e8e167f09e7edb13b9d5d5af9944088409b15cf9a893fb
tests/test_io24_full_parameter_inventory.py
                                     d2bc8e35dbb7da9f0695e9e916ee59c3e324259072fd44f27e9fe1dd40ec0211
```

No USB access, audio stream, Host launch, device write, Wine action, firmware
action, reset, DFU, network action, or publication occurred while building the
plan. The cache remains empty and the Host remains closed. The next live audio
gate requires explicit physical confirmation that Main Left is connected to the
open cable in Channel 2 with monitors down/off; Channel 2 must remain removed
from Main to prevent feedback. Static P1 work may continue before that physical
confirmation.

## 2026-09-06 controlling checkpoint: the Host state was mangled

The later listening/meter observations supersede the earlier terminal-device
interpretation below. The user confirmed that both Fat Channels still work,
while Channel 2 disappeared at L100 and returned at R100; Mix A metered signal
that was not audible; and Mix B showed no signal. Those symptoms isolate Linux
Host bookkeeping and presentation defects:

1. GTK exposed one `set_pan()` knob per independent mono input even though the
   decoded mixer has only one scalar per source/bus. On the right leg, L100
   therefore computes zero gain. This was stereo-pair balance presented as
   independent mono panning.
2. A send could be saved as assigned without any saved fader level.
   `_push_send()` then deliberately emitted no write, so Mix B could look active
   while remaining absent on the device.
3. Mix A and Mix B are USB capture buses (3-4 and 5-6), not automatic Main or
   headphone monitoring paths. Their meters can move without local audio.
4. On a new USB attachment GTK reopened `shadow.json`, but neither replayed it
   nor marked it as unconfirmed. The visible Host and write-only hardware could
   silently describe different states.
5. Unlinked factory-preset loading hard-coded Channel 1. A Channel-2 user could
   therefore click **Load strip** or **Load + Voice FX** and command the wrong
   physical strip/VoiceFX owner.
6. Raising a reverb input send did not materialize the visually displayed 0 dB
   Main FX return when that return had never been written.

The local-only repair is implemented in `io24.py` and `io24gtk.py`:

- assigning an unknown route now materializes a 0 dB send and records both
  level and assignment; explicit off remains distinguishable from unknown;
- pair-balance migration materializes both backend legs; the later Mixer
  refinement supersedes its GTK control with independent Host-input pan;
- old one-leg-pan shadow/preset entries are discarded, and deprecated preset
  enable aliases are canonicalized before restore;
- device-slot recall precedes DSP/effect replay, while mixer levels precede
  masters, balance, and assignment;
- nothing is silently replayed merely because USB reappeared. The later Mixer
  refinement removes the GTK cached-reapply/forget controls entirely and keeps
  explicit Host snapshot save/load as the user-facing recovery path;
- unknown routing cells now appear parked instead of falsely active at 0 dB;
- the factory page has an explicit Channel 1/Channel 2 target. When linked, the
  Fat Channel loads to both strips and the chosen channel remains the singleton
  Voice FX owner;
- Mix A/B are labelled as USB capture, and moving a nonzero reverb input send
  initializes an unknown Main FX return without overriding an explicit mute.

A read-only dry migration of the actual cache found 63 old entries and 57
coherent entries: two deprecated preset aliases and four unlinked balance
entries are removed. A hardware-free replay of those 57 entries completed with
57/57 Host calls and no exception, but it also confirmed that the cache itself
currently requests Channel-2 Main/Mix-A/Mix-B unassignment and an unassigned
Main FX return at -60 dB. That is internally executable but not the audible
state the user wants. The cache has deliberately not been changed. The original
repair exposed GTK reapply/forget controls, but the newer controlling checkpoint
removes that UI and state machine; a future recovery must use an explicit Host
snapshot or a separately authorized backend operation rather than replay this
known-unwanted routing by accident.

`tests/test_io24_host_state_repair.py` contains the new hardware-free
regressions. The final complete suite passes 308 tests, one expected skip, and
55 subtests in 160.06 seconds. The final focused preset/Host compatibility run
passes 57 tests and 12 subtests; changed Python sources also pass AST parsing
and GTK import. `tests/paint_smoke.py` was deliberately not run because it is
explicitly restricted to an unplugged interface and the device is connected.

Final source hashes before this checkpoint update:

```text
io24.py                                 fbb67c0ae6bf5cce66c014951a7f10a75b173e47213d6cfcad9cafa437888753
io24gtk.py                              87a985c6c7bc09a88789d43229f464b65d2515a7017b3b30723201854a45fd2a
tests/test_io24_host_state_repair.py    9d6884ead0a15aad89ea37fc78e0ceca4d2696f0eee275d11a15c386988450a7
GUIDE.md                                c9322d0a01d4a38a219195e44874a28bd24266c852d1ee1335d65cefca6fef7d
README.md                               f264634062353a85c1068991955395440de41e7e31809b7ddcf79a8752d972e0
```

No USB access, audio stream, Host launch, preset/effect command, cache mutation,
firmware action, Wine action, network action, or publication occurred in this
repair. The installed desktop launcher already points at this source tree, so a
future launch will use the repaired code. Live validation remains a separate
exact gate: launch the Host, explicitly choose whether to reapply the old cache,
select Channel 2 on the factory page, establish Channel-2 Main and reverb
send/return routing, then perform one audible test with full restoration. The
disconnected device-resident acceptance condition remains open.

## HISTORICAL CP34 mapping checkpoint; terminal interpretation superseded

The user's layered model is correct. There are three independent controls:

1. `set_preset_enabled(1|2)` bypasses/enables the corresponding physical
   front-panel channel.
2. `set_preset_slot(1|2, slot)` selects the corresponding physical channel's
   block. VoiceFX assignment never renumbers this API.
3. `processingChannel` parameter 149 assigns the singleton VoiceFX model to an
   input. Parameter 450 selects the algorithm; `voicefx.on` is a separate saved
   enable within the selected model state.

Exact UC 4.7.2 code confirms the branch. Initial apply
`0x180040729 -> 0x18003e6c0` and change refresh
`0x18004193f -> 0x18003e6c0` evaluate `processingChannel == 0`. The owning
channel object activates `voicefxopt/fxmodel` and selects its current model;
the non-owner deactivates it and selects host sentinel `-1`. Parameter-149
changes use handler `0x18004145e`. Evidence is in
`runs/20260906T090317-0700-hotkey-voicefx-state-route/`.

Both previous `LIVE-ATTEMPT-2.json` runs used channel 1 for preset bypass,
selection, and enable after assigning VoiceFX to Input 2. Their own readback
shows that they moved Channel 1, not Channel 2. Both are classified
`INVALID_PHYSICAL_CHANNEL_CONTROL_MAPPING`. Their `Stat(3)` writes remain
observed, but neither result proves Channel-2 recall or audibility.

Channel 1 has been restored without a record write. Exact exposed state after
restoration:

```text
Channel 1: selector 0, bypassed, gain 37
Channel 2: selector 0, enabled, gain 24
processingChannel tuple: (1,0), VoiceFX assigned to Input 2
stereo link: off
```

The faulty tests never wrote a Channel-1 slot body; only its active selector
and enable were displaced. `CHANNEL1-RESTORATION.json` records serial
`AB7C22200355`, firmware `0x0128`, battery 20 percent, selector `3 -> 0`, and
`channel1_preset_body_written=false`.

The corrected runners now require the retained Input-2 VoiceFX assignment,
reassert it without changing exposed state, and use physical Channel 2 for
every preset bypass/slot/enable operation. The explicit Linux-host
`with_fx=True` path now performs:

```text
set_voicefx_channel(requested physical input)
select/instantiate the saved model
apply voicefx.on and the selected model fields
```

The final Reverb target is factory-derived but deliberately changes
`voicefx.mix` from the factory 0.295 to 1.0, as requested, so the private-reverb
result is maximally obvious. It remains 842 bytes; record SHA-256 is
`191a5048c4995355932609e9d5ae225f37c50d8f112966f685a11b3f2a08e79c`
and the one-fragment `Stat(3)` frame SHA-256 is
`d8ea35050b33484444e48c3d54cf1716bce35265a0b2b92f26939ea7bdf92c1f`.

Focused verification passes 28/28 across the host apply path, both Channel-2
runners, and the exact UC analyzer; the corrected Slap wrapper passes 4/4. The
complete suite was run in two disjoint commands: 254 passed with one expected
skip and 44 subtests outside the slow survey, then 41 passed and 11 subtests in
the survey, for 295 passed, one expected skip, and 55 subtests total. This is
the hardware-free verification baseline.

The separately authorized corrected physical Channel-2 sequence then ran once
on serial `AB7C22200355` at 45 percent battery and exited 0. It sent four
pinned model-before-state writes and one maximum-wet `MemP/Stat(3)` frame.
Exposed post-state retained Channel 1 at selector 0/bypassed and gains 37/24,
placed Channel 2 at selector 3/enabled, retained `(1,0)` Input-2 VoiceFX
assignment, and retained stereo link off. Exact output is
`runs/20260906T100100-0700-channel2-voicefx-materialization/LIVE-ATTEMPT-3-CORRECTED-MAX-WET.json`.
There was no readable record-write reply. The user then unplugged and
reconnected the interface and reported no noticed change. Since the target was
deliberately 100 percent wet, the identifiable saved VoiceFX/private-reverb
acceptance condition was not met. This is the terminal stock-firmware result;
exact human evidence is
`runs/20260906T100100-0700-channel2-voicefx-materialization/STANDALONE-LISTENING-RESULT.md`.
It does not distinguish physical commit, nonvolatile persistence, record
parsing, model activation, processing-gate restoration, or recall as the failed
internal boundary. No retry or other device action is authorized now. Cleanup
and initial GitHub packaging are next; custom firmware stays deferred until
after publication.

## SUPERSEDED: pre-mapping-correction offline checkpoint

The stock-compatible Linux-host correction is implemented. `io24_fx.py` maps
all six exact UC VoiceFX class IDs to their model-specific saved fields and
refuses incomplete, unknown, non-finite, or mistyped state rather than filling
in silent defaults. `Io24.apply_voicefx_snapshot()` selects the model first and
then sends only its state, reporting activation and audibility as `UNPROVED`.
`io24_presets.apply_preset(..., with_fx=True)`, CLI `--voicefx`, and GTK
`Load + Voice FX` expose that route explicitly; the default remains the prior
non-VoiceFX Fat Channel load.

The current run is
`runs/20260906T100100-0700-channel2-voicefx-materialization/`. Its default dry
invocation returns `OFFLINE_READY`. The successor runner wraps rather than
modifies the completed historical Channel-2 stage and retains its exact serial,
firmware, battery, link, assignment, slot-index-exchange, Channel-1 guard,
unreadable-overwrite, failure-bypass, and slot-3-only constraints. After the
target chain is bypassed and dislodged if needed, it sends four pinned
model-before-state block-201 messages, then writes the same pinned 842-byte
Reverb record to `Stat(3)`, recalls it, and verifies exposed state. If model
application fails, no slot record write is attempted.

The final integrated focused verification passes 38/38. The complete
hardware-free suite passes 293 tests with one expected skip in 185.344
seconds; all ten relevant implementation, runner, and contract Python files
also pass AST parsing. No USB/device, audio, Wine, network, firmware, or
GitHub action occurred.

Do not execute the live stage without a new exact authorization. The eventual
human acceptance remains Channel 2 after complete computer disconnection and a
non-computer-powered cold boot. Identifiable saved private reverb is success; a
repeatable dry result under this corrected sequence is the terminal stock-
firmware negative. Either closes the preset investigation. Host cleanup and
initial GitHub publication follow. Independent-instance custom firmware remains
deferred until after that publication.

## RETAINED SOURCE RESULT; LIVE INTERPRETATION SUPERSEDED

The previously skipped Hot Key path is now resolved from exact UC 4.7.2
sources. It is not a seventh device preset or a second effect. Parameter 151
momentarily replaces the active normal slot with a cached complete-channel
snapshot at channel-object offset `+0x180`; release restores the normal slot
selected by parameter 150. Channel load/save uses the nested `hotkey` record,
and both Hot Key and `StorePreset` use the same channel-state serializer.

The VoiceFX algorithm is not detected from a readable DSP register. UC retains
it in host component state as `voicefx.__classid` and parameter 450
(`voicefxopt/fxmodel`). Restore maps that class to model `-1` or `0..5`,
selects/instantiates the model by sending block 201 `VoFx`, and then applies
`voicefx.on` plus that selected model's fields. The Linux host must preserve
and replay that same ordering. If it does not already own a complete known
snapshot, it cannot infer unknown VoiceFX state from device readback.

The nominal Channel-2 slot-3 stage explicitly recorded
`direct_voicefx_parameter_write=false`. The user's later closed-host listening
heard dry pops and a thinner second block, but no identifiable effect. Later
readback analysis invalidated that observation as a Channel-2 test because the
runner recalled physical Channel 1. The user-defined disconnected,
non-computer-powered audible pass has not been achieved.

Per-channel slot objects can serialize different VoiceFX models, but recall
still targets one singleton block-201 model/state object. Its two audio lanes
make shared same-state processing structurally possible, not proved
simultaneous stock behavior. Two different simultaneous effects require a
second firmware model instance.

Per user direction, all custom-firmware implementation is deferred until after
the first GitHub publication. The order is now: seal this finding; implement
and test the stock-compatible host apply/save behavior; obtain the Channel-2
standalone audible result or exact terminal negative; clean/package/publish the
Linux host; then resume custom firmware privately. No firmware work or new
device action is authorized by this continuation.

Exact evidence is in
`runs/20260906T090317-0700-hotkey-voicefx-state-route/`. The focused analyzer
contract passes 2/2. Its boundary is static host-state routing only: runtime
propagation, storage, standalone recall, simultaneous VoiceFX lanes, and
audibility remain unobserved.

## INVALIDATED: live stage used physical Channel 1 controls

The separately authorized run exited 0 only because its assertions encoded the
wrong mapping. It assigned VoiceFX to physical Input 2 and sent exactly one
pinned 842-byte Reverb record to global `Stat(3)`, but its preset calls used
channel 1. The raw readback shows physical Channel 1 moved to slot 3 and became
enabled. It did not verify a Channel-2 recall. The raw JSON is retained, and
the controlling classification is
`runs/20260906T100100-0700-channel2-voicefx-materialization/LIVE-ATTEMPT-2-CLASSIFICATION.md`.

Do not perform disconnected acceptance from that state. Channel 1 was restored
and the corrected runner requires a new exact live authorization.

## HISTORICAL: live attempt 1 and slot-value exchange

The authorized run matched serial `AB7C22200355` / `bcdDevice 0x0128`, passed
the battery gate, and confirmed `Assign Voice FX = Ch2`. It then stopped at its
old same-index slot invariant. `record_write_attempted=false`: neither slot 3
nor slot 0 received a record write. Failure cleanup re-sent bypass and closed;
its readback is unavailable. The exact result is
`runs/20260906T064742-0700-channel2-reverb-assignment-correction/LIVE-ATTEMPT-1.json`.

The stopped run exposed an omitted firmware behavior. Pinned firmware 1.28 at
`0x2e77a..0x2e7bb` reads both active slot indexes after a `Pari/12` assignment
change and replays `Pari/16` for indexes 0 and 1 with their values exchanged.
Thus `Assign Voice FX = Ch2` maps physical Input 2 and its slot-2/3 family onto
Voice-FX-owning processing chain 1. The old fake did not model that exchange.

The old correction incorrectly treated processing-chain ownership as physical
preset addressing. The corrected runner instead requires/reasserts the Input-2
VoiceFX assignment, then bypasses/selects/enables with physical channel 2. It
never selects or writes slot 0. The later authorized retry described in this
historical section is invalid; a subsequent corrected run and its terminal
standalone negative are the controlling result above.

## SUPERSEDED: assignment was correct but preset-control mapping was not

The user corrected the core assumption: Voice FX is traditionally assignable
to either channel, one at a time. UC's effect/preset selector and confirmation
identify that channel; the four firmware default records cannot override the
product workflow.

The correction is source-bound. Exact UC 4.7.2
`uceasy/settings.xml` exposes `Assign Voice FX` on
`line/ch1/processingChannel` with `Ch1=0` and `Ch2=1`. Retained UC scene JSON
has a `voicefx` member in all four slot objects, including Channel-2 slots 2/3.
The exact UC active-slot writer emits a tagged mapping beginning with `0x7b`
through `MemP/Stat`; the version-2 records embedded in firmware are
startup/default implementation data, not a host record schema or a legal slot
content limit.

The earlier Channel-2 Slap Echo trial never changed the baseline processing map
from `input1ProcessingChannel=0`, so it never reproduced
`Assign Voice FX = Ch2`. Its dry result is not a test of this corrected path.
The later claim that slots 2/3 categorically cannot store Voice FX is retracted;
the cancelled slot-0 plan remains cancelled.

The current run is
`runs/20260906T064742-0700-channel2-reverb-assignment-correction/`.
`re/cp34_channel2_reverb_slot_stage.py` is hardware-free by default and pins:

- serial `AB7C22200355`, firmware descriptor `0x0128`;
- Channel 2, global slot 3, never slot 0;
- `Assign Voice FX = Ch2` via `Pari/12`, index 0, value 1;
- exact 842-byte UC factory Reverb record, SHA-256
  `c85119953bef5fd41f83f4b60e207519e9d57c6bf174f9d8a8e7ce6a88ed65c4`;
- exact one-fragment `MemP/Stat(3)` frame, SHA-256
  `e9154a66a7691ae8e415b891eab299310a3899df9b6cb2658ebb94d99ccf4306`;
- battery, unreadable-overwrite, identity, firmware, link, pair, ordering, and
  exposed post-state gates.

Historical implementation note: this version set the assignment, then wrongly
used the VoiceFX-owning processing-object index for preset control. It did not
recall physical Channel 2. The current runner instead uses physical channel 2
for every bypass, slot, and enable call.

`io24.py` now uses the exact tagged complete-record route for
`save_device_slot()`; native firmware-default chunk framing is retained only as
an offline analysis fixture. The validator no longer converts four observed
default shapes into slot-ownership rules. Focused verification passes 61 tests
and 12 subtests; the exact dry run returns `OFFLINE_READY` and
`slot_zero_targeted=false`. The complete hardware-free suite passes 272 tests
and 47 subtests with one expected skip, exit 0.

Physical commit, standalone recall, power-cycle survival, and audibility remain
unproved. The automated stage has completed and must not be repeated. The user
now performs the disconnected non-computer-power cold boot and listens on Input
2. A
repeatable wet/dry difference is the CP34 stopping point.

The two older sections immediately below are superseded conclusions retained
as chronology. Do not execute their native slot-0/1 runner or their Channel-2
constraint.

## 2026-09-06 user correction: require Channel-2 storage

The user prohibited slot 0 because it belongs to Channel 1 and requested a slot
on the second channel. No device write occurred. The earlier slot-0 live plan is
cancelled and must not be executed.

The exact native records make a direct substitution impossible: Channel-1
slots 0/1 contain `opt ` plus component 201, while Channel-2 slots 2/3 contain
only `opt `. Shared block-202 reverb is also absent from these slot records.
The validator therefore correctly rejects model-0 Voice FX in slot 2 or 3.

If the requirement is sound from physical Input 2, the remaining stock path is
owning slot 1 routed to Input 2; storage and the physical preset button would
still belong to Channel 1, and routing survival would need the standalone test.
If the requirement is actual Channel-2 slot/button ownership, it is not
available in the decoded stock format and belongs in the later private firmware
lane. `runs/20260906T050813-0700-standalone-native-model0-preflight/CHANNEL2-CONSTRAINT.md`
is the controlling decision.

`re/cp34_native_model0_slot_stage.py` now enforces the current prohibition on
both owning slots before device open. Focused tests pass 21/21. No USB/device,
Wine, ALSA, preset/effect, network, firmware, or GitHub action occurred.

## 2026-09-06 standalone stopping criterion and exact next action

The user-defined CP34 stopping point is now exact: hear a reproducible saved
effect/private-reverb result after the io24 has been disconnected from the
computer, cold-booted on a non-computer USB supply, and controlled from the
unit. Connected-host transport, readback, or audio is insufficient.

The active run is
`runs/20260906T050813-0700-standalone-native-model0-preflight/`. It contains
pinned native candidates/restoration defaults, the no-I/O analysis and dry run,
the exact live plan, progress, and test record. The chosen first trial uses
physical Input 1 and native slot 0 so standalone boot does not depend on the
host-only processing swap or reaching a second preset block.

The slot-0 candidate is 1092 bytes, SHA-256
`da1b3e00463ed6e51139119611ef18ba8b8286d4db41f7d6dac7290e2f041c57`.
It preserves the exact firmware-default Fat Channel and replaces only component
201 with enabled model 0 at `lows=0.06`, `width=0.405`, and `mix=0.295`. The
only available restoration is the 1088-byte firmware slot-0 default, SHA-256
`1cf1d764c48be395c1e5af43d6c37cc0ced2aa27ba4408d2c112b9cf251f4df7`;
the device cannot return the unknown current full slot body.

`re/cp34_native_model0_slot_stage.py` is fail-closed and defaults to a hardware-
free plan. Live mode separately requires the execution and unreadable-overwrite
flags, battery above 10 percent, exact serial/firmware, link off, and a valid
Channel-1 slot-pair baseline. It bypasses the owning preset family during
staging, creates an application edge if slot 0 is already active, writes the one
pinned native record, routes Voice FX to Input 1, commands dual preset blocks,
selects slot 0, enables Channel 1, and verifies only exposed state. It cannot
prove stored bytes or audibility and leaves the candidate selected.

Focused hardware-free verification passes 20/20, the exact slot-0/Input-1 dry
run returns `OFFLINE_READY`, and the final complete suite passes 261 tests with
one expected skip and no failures. No USB/device, Wine, ALSA, network, firmware,
power, preset/effect, installation, or GitHub action occurred. Before live use,
the user must explicitly accept replacement of unreadable slot-0 content and
authorize the exact interface/read/write scope in `LIVE-PLAN.md`.

After a standalone audible pass, CP34 stops. Clean and package the Linux host
for GitHub next; continue custom-firmware work privately afterward.

## 2026-09-06 native Stat and library separation

The latest run is
`runs/20260906T044958-0700-native-stat-slot-family/`. It reads only the exact
retained UC 4.7.2 DSP module and its byte-identical firmware 1.28 application.

The missed attribution is now explicit. Firmware startup binds four contiguous
native `Stat` defaults at raw `0x69230`, `0x69670`, `0x69ab0`, and `0x69eb4`,
with exact lengths `0x440`, `0x440`, `0x404`, and `0x404`. All four start with
native little-endian version `2`. They end exactly at raw `0x6a2b8`, where a
separate sixteen-record tagged factory/library collection begins with the
`Broadcast` archive and byte `0x7b`.

The storage ownership is equally direct:

- slots 0/1 contain channel strip `opt ` plus component 201/Voice FX;
- slots 2/3 contain the channel strip only and do not own component 201.

This does not make Voice FX input-1-only. The host processing-channel control
can route the singleton Voice FX processor to either physical input,
traditionally one at a time. Storage ownership and runtime input selection are
separate.

This retracts the paired JSON model and the idea that the same `voicefx` object
should be written into one slot from each family. The Channel-2 Slap Echo trial
combined a tagged library archive with a slot family that does not own Voice
FX. Its dry result therefore does not expose another hidden activation switch.

The native container and the required model-0 leaf are now executable. The two
component-201-owning defaults select model 5 and contain a 16-byte native leaf exactly equal
to the already mapped Delay state words. Model-0 serializer `0x53680` declares
and copies exactly 20 bytes from `model+0x340`; those five words are the mapped
`godv` state `on/lows/width/lows-mirror/mix`. `io24_native_stat.py` now parses,
validates, round-trips, and constructs that record. `io24.py` exposes the
hardware-free builder and a native-only save API. Tagged JSON and the obsolete
paired operation fail before transport.

There is no remaining model-0 format transformation to derive. The next
meaningful step is a separately authorized physical slot-0/1 trial using a
complete native base, followed by recall and a two-input routing/audio capture.
Model 0's separate private reverb core binds two lane indexes, but static
structure does not prove stock firmware opens both concurrently. A transport reply
would show only receipt; nonvolatile persistence still requires an independent
recall/power-cycle observation, and audibility still requires audio evidence.
No device, USB, audio, Wine, network, firmware-image, or preset/effect action
occurred in this stage.

The exact UC Save/Assign analysis below remains useful for distinguishing its
tagged host/library workflow, but any statement that tagged JSON is the native
slot representation or that a hidden prefix transformation remains is
superseded by this section.

## 2026-09-06 exact UC 4.7.2 Save/Assign UI route

The latest run is
`runs/20260906T010449-0700-uc472-save-assign-ui-route/`. It uses the retained,
hash-pinned UC 4.7.2.108537 modules only. The predecessor checkpoint verified
14/14 entries before the shared handoff was advanced.

The panel's exact `DEFAULT.SKIN/PACKAGEF` resource contains 275 members.
Member `uceasy/uceasy.xml` binds `presetSlot` values 1..4, a remote list
labeled `Device Presets`, `storeNamedRemotePreset`, and `sendToMixer` between
the local and remote lists.

The panel registers `sendToMixer` as action `0x452`; its event reaches helper
`0x1800fe080` and transfer helper `0x180113ba0`, which validates a
`MixerPreset`, temporarily installs a capture dispatcher, creates `ZStr`
items, and inserts them into the remote model. It registers
`storeNamedRemotePreset` as action `0x45f`; helper `0x180103ba0` calls the
exact UCNet `UCGetNetworkManager` and `UCGetFileTransferManager` imports.

Jackson's browser vtable maps `+0x220` to `0x18006ef10`. That function builds
the high-level `StorePreset` message with `presets`, `presetFile`, and
`presetTarget`, then dispatches through object `+0x298`, vtable `+0x80`. It
does not itself build low-level `MemP/Stat` bytes.

The exact DSP receiver at `0x18003aef0` handles `RestorePreset` and
`StorePreset`. Its Store branch calls serializer `0x18002e270`, updates the
selected user-library record, then calls `0x180037250`, which constructs
`PrsM` plus `Appl` and reaches existing `MemP` fragmenter `0x180050f10`.
This is the twelve-record `Device Presets` library, indexed 16..27. It is
distinct from the four fast-access slots, which the existing settled-state
path maintains as `MemP/Stat` indexes 0..3. No separate Assign frame was
located.

The controlling result is
`UC472_SAVE_ASSIGN_UI_ROUTE_SOURCE_BOUND_TO_EXISTING_DEVICE_LIBRARY_AND_SLOT_STATE_PATHS`.
It rules out a newly discovered simple DLL/syscall or one-packet Wine
workaround within the exact traced route. A strictly Linux-native replacement
remains plausible, but the smallest source-bound direction is to reproduce the
high-level preset/state-machine behavior after resolving the remaining runtime
format boundary; a guessed packet is not eligible.

The boundary is
`STATIC_UI_AND_HOST_MESSAGE_ROUTE_RESOLVED_RUNTIME_UCNET_DELIVERY_FORMAT_TRANSFORMATION_PHYSICAL_COMMIT_RECALL_AND_AUDIBILITY_UNOBSERVED`.
The panel and DSP endpoints are statically source-bound; their runtime UCNet
delivery was not observed, and no native-u32-two transformation was located.
Device acceptance, physical storage, recall, power-cycle survival, selected
component, Voice FX activation, and audibility remain unobserved.

TDD recorded the intended absent-analyzer RED, then focused GREEN 2/2. The
related route/serializer/firmware suite passed 12/12. The complete
hardware-free suite passed 240 tests with one expected skip in 199.013
seconds, exit 0. No Wine prefix, vendor execution, USB/device, audio,
front-panel, preset/effect, firmware-image, install, network, or REAPER action
occurred.

## 2026-09-06 exact UC 4.7.2 save serializer

The latest run is
`runs/20260906T001130-0700-uc472-official-reacquisition/`. The one authorized
official download recovered the exact 186,792,552-byte Universal Control
4.7.2.108537 installer, SHA-256
`1b5ddd6fd3ad4b93529caf8e5933bcd52b13194bdfa62652292b46ddcd980b95`.
Offline Nullsoft/zlib extraction recovered the exact 4,979,672-byte
`hwaccess/dspusbdevice.dll`, SHA-256
`de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.
Neither artifact was executed or installed.

One caller snapshots and sends the same `r14d` slot. Serializer
`0x18002e270` clears the selected record, binds it at writer `+0x18`, and its
null-name archive branch emits one byte `0x7b`. Writer adapter `0x1800649a0`
tailcalls record append `0x180063060`, which copies that byte through `memcpy`
directly to `record.data(+0x10) + record.cursor(+0x2c)` at cursor zero. It then
sets cursor and length to one. No prefix or headroom is inserted before the
same-slot record reaches fragmenter `0x180050f10`.

The controlling result is
`UC472_SAVE_SERIALIZER_SOURCE_BOUND_RECORD_BYTE_ZERO_0X7B_NO_NATIVE_U32_TWO_PREFIX`.
Combined with the sealed firmware path, UC 4.7.2 record byte zero reaches
structured-state method `0x531e0` unchanged if that route is taken. The method
requires native little-endian u32 `2`, whose first byte is `0x02`; a record
starting `0x7b` is not eligible for that gate as serialized.

This closes the exact host-format question but not a physical outcome. The
boundary is
`UC472_SERIALIZER_RESOLVED_DEVICE_COMMIT_RUNTIME_COMPONENT_SELECTION_AND_AUDIBILITY_REMAIN_UNOBSERVED`.
Backend commit, actual device-resident bytes, preset round trip, runtime
component selection, Voice FX activation, and audibility remain unobserved.

TDD recorded two intended missing-analyzer failures, then focused GREEN 2/2.
The UC 4.7.2/UC5 writer and firmware ingress/recall contracts passed 8/8;
direct analyzer execution and compilation passed. The complete hardware-free
suite passed 238 tests with one expected skip in 189.613 seconds, exit 0. Its
only diagnostic was the pre-existing unclosed-WAV `ResourceWarning` at
`re/cp34_current_slot_survey.py:260`. Independent review remains open. No
device, USB, audio, Wine, install, firmware-image, preset/effect, or REAPER
action occurred; network use was limited to the authorized official download.

## 2026-09-05 final derived zero-selector receiver correction

The stored-record callback builds `SetP | 0 | 0 | nested Stat`. Its exact
`{0,0}` selector returns device global `0x20216660`. Lazy initializer `0x3d4f0`
calls derived constructor `0x5e014` at `0x3d52a`. That constructor first calls
base constructor `0x5d990` at `0x5e018`, which temporarily installs primary
vtable `0x6008d3a8`. The derived body then loads header `0x6012cb38` from the
literal at `0x5e08c`, forms header plus eight at `0x5e02a`, and stores the final
primary vtable `0x6012cb40` at `0x5e036`.

The final table's slot zero at raw `0x10cb40` targets dispatcher `0x420bc`; its
slot `+0x38` at raw `0x10cb78` targets structured-state method `0x531e0`.
Dispatcher calls `0x42266` and `0x42280` therefore both reach `0x531e0`. The
exact final pointer occurs zero times as a literal because construction forms it
as `0x6012cb38 + 8`; the header literal occurs exactly once. Function `0x41580`
is registered after construction through the call at `0x3d536 -> 0x5fc04` and
restores base tables during teardown. Treating its base-table writes as final
live construction state caused the provisional no-op conclusion.

The controlling results are:

- `ZERO_SELECTOR_STAT_ROUTE_SOURCE_BOUND_FINAL_DERIVED_SLOT_0X38_0X531E0`;
- `STAT_STREAM_CURSOR_ZERO_SOURCE_BOUND_FIRST_WORD_FROM_ACCUMULATION_BUFFER`;
- `STORED_STAT_RECALL_SOURCE_BOUND_BYTE_PRESERVING_NO_PREFIX_INSERTION`;
- `FIRMWARE_STAT_INGRESS_RECALL_SOURCE_BOUND_LOGICAL_BYTE_ZERO_UNCHANGED_NO_PREFIX_INSERTION`.

The current superseding run is
`runs/20260905T231733-0700-appl-zero-selector-receiver/`. Its initial
`{Appl,0}` premise was narrowed: the outer host envelope is not passed literally
as the firmware selector query on this stored-recall path. Final constructor
provenance resolves the actual `{0,0}` receiver seam.

Run `runs/20260905T212623-0700-zero-selector-recall-vtable-correction/` remains
unchanged, but its `PRIMARY_SLOT_0X38_NOOP_NOT_0X531E0` conclusion is retracted.
It confused transient base-construction and registered-teardown writes with the
final derived vtable. Its checkpoint now has ten expected stale shared-file
rows because this superseding stage replaced those analyzers, contracts, and
active handoffs; seven immutable/task-local predecessor rows still verify. Do
not use that stale manifest to restore active files.

Fresh verification passed all 53 affected contracts, including the complete
47-test firmware-static module. Python compilation passed. The complete
hardware-free suite passed 235 tests, one expected skip, and 47 subtests in
158.89 seconds, exit 0. The recurring `Failed to create stream fd` diagnostic
preceded the tests but did not affect their successful exit. No USB/device,
interface claim/detach, transfer, ALSA, preset/effect, Wine, network,
firmware-image, reset, DFU, install, staging, flash, or REAPER action occurred.

The exact boundary is
`0X531E0_RUNTIME_COMPLETION_SELECTED_COMPONENT_AND_PHYSICAL_OUTCOMES_REMAIN_UNRESOLVED`.
The actual device-resident bytes, backend commit, preset round trip, selected
component at runtime, Voice FX activation, and audibility remain unobserved.
Reacquiring the pinned UC 4.7.2 host artifact requires separate network
authority; connection of the device supplied no live-action authority.

## 2026-09-05 firmware ingress/storage framing

The latest offline run is
`runs/20260905T210639-0700-firmware-ingress-storage-framing/`. It pins firmware
size 1,104,448 and SHA-256
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.
The application was recovered from the installed package in memory only; no
firmware image was emitted.

Root handler `0x2f210` preserves the incoming message and reaches component
vtable `0x600874f8` slot `+0x18`, exact handler `0x3099c`. Its accepted `Stat`
path calls record writer `0x3092c`. For a first fragment, that writer stores
the separate four-byte total record length, then passes the exact payload
pointer `message+0x1d` and exact u16 fragment length to wrapper write
`0x2bfe4`.

Wrapper vtable `0x60086994` binds write `0x2bfe4`, read `0x2c0a8`, and eight
bytes of overhead. The write-side backend-address layout is
`CRC32@+0 | payload length@+4 | payload@+8`. The paired reader consumes CRC32
and length internally, reads only the payload to the caller destination, and
validates CRC32. Stored-record reader `0x30a90` therefore places the separate
total length at message `+0x19` and serialized payload at `+0x1d`, without
exposing wrapper metadata.

The controlling result is
`FIRMWARE_STAT_INGRESS_RECALL_SOURCE_BOUND_LOGICAL_BYTE_ZERO_UNCHANGED_NO_PREFIX_INSERTION`.
Combined with the sealed recall stage, the parser-visible first word is exactly
`little_endian_u32(incoming_payload[0:4])`. Incoming `7b690b70` reaches
`0x531e0` as `0x700b697b`, not required value `2`.

The boundary is
`PHYSICAL_BACKEND_COMMIT_AND_UC472_SERIALIZER_REMAIN_UNOBSERVED`.
The next exact source question is the missing UC 4.7.2 serializer. No current
UC5 inference may substitute for it. Physical device contents, commit,
persistence, component selection, Voice FX activation, and audibility remain
unobserved, and this static result authorizes no live validation.

TDD recorded two intended missing-analyzer failures, then focused GREEN 2/2.
Related ingress, recall, UC5 writer/serializer, and persistence contracts
passed 32 tests and 6 subtests; compilation passed. Complete hardware-free
reproduction passed 233 tests with one expected skip in 160.306 seconds, exit
0. Its only diagnostic was the pre-existing unclosed-WAV `ResourceWarning` at
`re/cp34_current_slot_survey.py:260`. Independent review remains open. Passive
sysfs reported BAT0 at 99 percent and not charging. No device, audio, Wine,
network, firmware-image, or REAPER action occurred.

## 2026-09-05 UC5 record-writer sink

The latest offline run is
`runs/20260905T204944-0700-uc5-record-writer-sink/`. It pins installed UC5
module size 4,984,704 and SHA-256
`567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`.

Serializer `0x18002e9e0` resets the selected record cursor and length to zero,
then binds that record at stack writer `+0x18`. Archive call `0x180069dae`
sends one logical byte `0x7b` through secondary writer slot `+0x8`. That slot
resolves to adapter `0x180065d30`, which obtains the selected record and
tailcalls append `0x1800643f0`.

Append computes `record.data(+0x10) + record.cursor(+0x2c)` and copies exactly
one byte through `memcpy`; it then advances cursor and length to one. It does
not reserve or insert a prefix. Snapshot returns immediately after
serialization, and the caller sends the same slot without an intervening
record mutation. The controlling result is
`UC5_RECORD_WRITER_SOURCE_BOUND_PHYSICAL_BYTE_ZERO_0X7B_NO_PREFIX_INSERTION`.

The boundary is
`UC5_ONLY_UC472_AND_FIRMWARE_INGRESS_STORAGE_TRANSFORM_UNRESOLVED`.
Current UC5 is not exact UC 4.7.2 evidence. The next safe static question is
whether firmware `MemP/Stat` ingress preserves or transforms the incoming
record before storage. That question must remain separate from physical
device state and supplies no authority for a live write or framing change.

TDD recorded two intended missing-analyzer failures, then focused GREEN 2/2.
The writer-sink, serializer, and recall contracts passed 6/6; direct analyzer
execution and compilation passed. Complete hardware-free reproduction passed
231 tests with one expected skip in 160.888 seconds, exit 0. Its only
diagnostic was the pre-existing unclosed-WAV `ResourceWarning` at
`re/cp34_current_slot_survey.py:260`. Independent review remains open. Passive
sysfs reported BAT0 at 99 percent and not charging. No device, audio, Wine,
network, firmware-image, or REAPER action occurred.

## 2026-09-05 firmware stored-record recall framing

The latest offline run is
`runs/20260905T202119-0700-firmware-stored-record-recall-framing/`. It pins
firmware size 1,104,448 and SHA-256
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.
The application was recovered from the installed package in memory only; no
firmware image was emitted.

Reader `0x30be0` validates `Stat` slot 0..3. Storage reader `0x30a90` places
the stored length at message `+0x19` and reads payload directly into
message `+0x1d`; its descriptor fallback `0x30c2a -> 0x30708` also copies
payload bytes directly to `+0x1d`. Recall callback `0x2f8ac` then constructs
exactly `SetP | 0 | 0 | nested Stat message`.

The formerly indirect seam is now resolved. Singleton forwarder `0x3cc40`
uses the source-bound global device cell and enters adjustor/router
`0x41b6c/0x419a0`. The zero/zero selector route
`0x3cf20/0x3ce98` returns the final derived device global. The `SetP` branch
preserves `r1 = packet+0xc` and invokes final primary vtable `0x6012cb40` slot
zero, exact target `0x420bc`.
Thus the precise replacement for the old shorthand is:

```text
0x3cc40
  -> 0x41b6c/0x419a0
  -> 0x3cf20/0x3ce98
  -> 0x420bc
```

Dispatcher branch `0x42200` copies `Stat+0x1d` unchanged to the device
accumulation buffer. The non-owning stream retains cursor zero, and
`0x42266 -> 0x531e0` consumes its first four bytes. The controlling result is
`STORED_STAT_RECALL_SOURCE_BOUND_BYTE_PRESERVING_NO_PREFIX_INSERTION`.

If stored bytes begin `7b690b70`, the exact gate word is `0x700b697b`, not
`2`. This is conditional; actual physical stored bytes were not read. The
boundary is
`PHYSICAL_STORED_BYTES_AND_UC472_SERIALIZER_REMAIN_UNOBSERVED`.

TDD recorded two intended missing-analyzer failures, then focused GREEN 2/2.
The new framing, prior recall, UC5 serializer, and cursor-provenance contracts
passed 55/55 in 19.66 seconds; Python compilation passed. Complete
hardware-free reproduction passed 229 tests with one expected skip in 156.897
seconds, exit 0. Its only diagnostic was the pre-existing unclosed-WAV
`ResourceWarning` at `re/cp34_current_slot_survey.py:260`. Independent review
remains open. Passive sysfs reported BAT0 at 100 percent and full. No device,
audio, Wine, network, firmware-image, or REAPER action occurred.

The next safe offline question is the current UC5 writer sink reached at
`0x180069dae`: determine whether writer slot `+0x8` inserts native u32 `2`
before logical archive byte `0x7b`. This remains UC5 comparison evidence and
cannot substitute for the missing UC 4.7.2 source.

## 2026-09-05 UC 5.0 structured-state serializer comparison

The latest offline run is
`runs/20260905T200005-0700-uc5-structured-state-serializer-comparison/`.
It pins installed UC5 module size 4,984,704 and SHA-256
`567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`.

One host caller passes the same slot register to snapshot
`0x18004239c -> 0x180042840` and send
`0x1800423b3 -> 0x180042940`. Snapshot resolves the selected record and invokes
serializer `0x18002e9e0`. The serializer clears and binds that record as its
archive-writer output, then calls `0x180069c40` with a null/empty name. The
empty-name branch passes one logical byte `0x7b` (`{`) to writer slot `+0x8`.

The sender selects `[controller+0x2d8] + slot*0x38`, constructs
`{Appl,0}/{Stat,slot}`, and invokes the source-bound `+0x10` vtable target
`0x180052270`. That fragmenter reads record length `+0x30` and data pointer
`+0x10`, copies through the PE import `memcpy`, and queues at `0x1800546b0`.
The controlling result is
`UC5_SAVE_SERIALIZER_SOURCE_BOUND_TAGGED_MAP_OPENER_NOT_NATIVE_U32_TWO`.

The sealed stage's boundary was
`UC5_ONLY_UC472_AND_FIRMWARE_RECALL_TO_LIVE_STAT_BRIDGE_UNRESOLVED`. The later
firmware-framing stage resolves the recall bridge and narrows interpretation
of this UC5 evidence: the opener-to-writer input is known, but the writer-slot
implementation and therefore physical record-buffer byte zero are not. UC5
still does not answer the missing UC 4.7.2 byte question and supplies no
authority to alter framing or touch the device.

TDD recorded the intended two-test RED for the absent analyzer. Focused GREEN
passed 2/2, the serializer plus queue-inventory contracts passed 5/5, and the
complete hardware-free suite passed 226 tests with one expected skip and 47
subtests in 155.19 seconds, exit 0. Independent review remains open. Passive
sysfs reported BAT0 at 99 percent and charging. No vendor binary was loaded or
executed; no device, audio, Wine, network, firmware-image, or REAPER action
occurred.

The next separately named offline route may trace the current UC5 writer slot
from `0x180069dae` to the record buffer. Alternatively, reacquire the exact UC
4.7.2 installer only under separate network authority. Neither route
authorizes changing or replaying the Linux writer.

## 2026-09-05 UC 4.7.2 host-source retention audit

The current checkpoint is
`runs/20260905T183725-0700-uc472-host-source-retention-audit/`. It reconciles
the predecessor's phrase "retained UC 4.7.2 host serializer" with the older
independently reviewed artifact report, which explicitly made retention
temporary under `/tmp`.

The historical source manifest now reports its four `/tmp` source rows missing
while its six durable/current rows still verify. Bounded exact-name and
exact-size searches of accessible `/tmp`, ordinary user-data roots, the
project/development roots, and a shallow `Archive` pass that pruned
`Windows.old` found no matching source. The result is
`UC472_HOST_SERIALIZER_SOURCE_UNAVAILABLE_IN_BOUNDED_LOCAL_ROOTS`.

The missing source identities remain pinned: installer SHA-256
`1b5ddd6fd3ad4b93529caf8e5933bcd52b13194bdfa62652292b46ddcd980b95`
and UC 4.7.2 `dspusbdevice.dll` SHA-256
`de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.
The installed DLL is 4,984,704 bytes with SHA-256
`567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`,
not the missing 4,979,672-byte UC 4.7.2 module.

The old report and JSON inventories preserve source-bound topology but not the
newly required byte-level serializer slice. The exact leading representation
therefore remains unresolved. The next exact action is reacquisition of the
pinned installer under separate network authority, followed by offline
extraction, hash validation, and serializer tracing. No network, Wine, device,
audio, image, or REAPER action was performed by this audit.

## 2026-09-05 structured-state input cursor provenance

The current checkpoint is
`runs/20260905T181808-0700-structured-state-input-cursor-provenance/`. It binds
the `Stat` fragment source and device accumulation buffer, the non-owning stack
stream's data/length/cursor fields, the explicit caller-side cursor reset, the
`0x42266 -> 0x531e0` handoff, and the underlying `0x2cbb4` reader that supplies
the first four bytes.

The controlling result is
`STAT_STREAM_CURSOR_ZERO_SOURCE_BOUND_FIRST_WORD_FROM_ACCUMULATION_BUFFER`.
It proves that any caller supplying raw archive prefix `7b690b70` on this live
`Stat` path presents native word `0x700b697b` at the exact consumed position
and cannot pass the required-word gate. It does not yet bind the stored
`MemP/Stat` frame to that live-dispatcher input unchanged; the valid sender- or
recall-side leading representation remains unresolved.

The intended focused contract passed 1/1 after an observed RED, the complete
firmware-static module passed 46/46, the existing Linux framing module passed
24/24, and the complete hardware-free suite passed 225 tests with one expected
skip in 159.328 seconds, exit 0. Independent review remains open. No image,
device, audio, preset/effect, Wine, network, or REAPER action occurred.

The next useful work is reacquisition of the exact UC 4.7.2 source under
separate explicit network authority, then a bounded offline/static serializer
trace. Do not modify or replay the local writer until that sender-side
representation is proved.

## 2026-09-05 structured-state record-prefix gate

The current checkpoint is
`runs/20260905T172026-0700-structured-state-record-prefix-gate/`. It binds the
stack wrapper construction and specialized read slot, the exact four-byte read
at `0x2ce10`, the disabled byte-reverse flag, the required value and accepted
branch at `0x53212..0x53216`, and the retained factory archive prefix at raw
`0x6b1c8`.

The controlling result is
`STRUCTURED_STATE_PREFIX_GATE_SOURCE_BOUND_RAW_FACTORY_ARCHIVE_NOT_DIRECTLY_ELIGIBLE`.
It means only that the raw archive cannot enter this method unchanged at byte
zero and pass the gate. It does not prove failed storage or record inequality:
the caller's actual stream position and any storage/recall transformation are
still unresolved.

The intended focused contract passed 1/1 after an observed RED, the complete
firmware-static module passed 45/45, and the complete hardware-free suite passed
224 tests with one expected skip in 233.126 seconds, exit 0. Independent review
is open. No image, device, audio, preset/effect, Wine, network, or REAPER action
occurred.

Resume reconciliation found that the interrupted run had created a zero-byte
`CHECKPOINT.sha256`. The focused contract reproduced 1/1 in 16.609 seconds, the
firmware-static module reproduced 45/45 in 18.427 seconds, and the complete
hardware-free suite reproduced 224 tests with one expected skip in 158.624
seconds, exit 0. The six-row checkpoint was then rebuilt from the exact current
files and verified 6/6. This seals the local result; independent review remains
open.

The next useful work is a new bounded offline/static scope that traces the
incoming record stream or cursor at the `0x42266` handoff far enough to identify
the first word actually presented to `0x531e0`. Do not infer transformation,
physical commit, component selection, parser semantics, safe placement, or
image readiness from the current prefix mismatch.

## 2026-09-04 linked gate-transition result

The current checkpoint is
`runs/20260904T025429-0700-gate-transition-probe/`. Test-first implementation
added an exact factory-gate action, a runner that is non-mutating without
`--execute`, and a strict six-channel analyzer. The one live execution ran at
53 percent battery after serial-pinned preflight. It made no playback, gain,
routing, output, or preset-content change. The action reported Channel 1's
readable guard unchanged, restored the factory gate by exact write, and
finished unlinked on Channel-2 slot 3.

The independent postflight passed with flags `0x1a1`, Channel 1 slot 0
disabled, Channel 2 slot 3 enabled, and two identical 2040-byte `JaSt` replies.
The gate itself is not readable, so restoration remains
`WRITE_SENT_NOT_READABLE`. The 14-second six-channel S32_LE/48 kHz capture has
SHA-256
`9f2307056e44b909668deb4226ec2b191d1e23ade12d641996fc9669e4beafda`.
Every monitor channel was approximately a -3 dB direct copy of Input 2 with
model correlation approximately `0.99999542`; no 150 ms repeat met the fixed
criterion. Focused regression passed 18/18 and the complete hardware-free
suite passed 223 tests with one expected skip in 176.921 seconds.

The next useful work is offline: resolve the record-driven normal-table index
or another missing activation condition while keeping physical `Stat` storage
separate. Any additional USB/audio operation, gain/gate/routing change,
preset/effect write, or firmware action requires new exact authorization.

After this run's live work and postflight had ended, an external REAPER process
started at 2026-09-04 03:16:54 -0700 and acquired the io24 ALSA capture and
playback nodes. This run did not start, configure, or stop it. Treat the audio
endpoint as currently owned until a future continuation rechecks process state;
do not disturb REAPER or infer new device authority from its presence.

## 2026-09-04 linked positive-slot live result

The current checkpoint is
`runs/20260904T022636-0700-linked-channel2-slot3-audio/`. A test-first bounded
host action requires the exact starting state, moves only Channel 2 to slot 2,
confirms link on before recalling Channel-2 slot 3 once, and clears link in a
`finally` path. The live action passed at 94 percent battery; its final state
reported Channel 1's gain, processing source, slot, and enable state unchanged.
A separate no-write read passed at 93 percent battery with two identical
2040-byte replies.

The 14-second six-channel S32_LE/48 kHz capture completed at SHA-256
`e587d9a7cbf78312eabcb4b2b4ee5e2f806d88335d3c812dd4d7372b1120aa14`.
Across the clean linked slot-3 window, capture channels 3-6 each tracked Input 2
at correlation `0.99999668` and direct coefficient `0.70797731` (-3 dB). A
joint current/150 ms/300 ms fit assigned only `0.00000642` to the 150 ms term.
That establishes no repeat in the captured noise. It does not establish that
the recalled Voice FX would be inaudible for a valid source: the exact factory
record enables its gate at -47.5 dBFS, while the strongest captured Input-2
sample was -83.66 dBFS.

The new action tests passed 3/3, the linked plus existing host-action set passed
7/7, and the complete hardware-free suite passed 208 tests with one expected
historical-artifact skip in 196.907 seconds. No live action followed the final
postflight. A further audible trial requires a known safe source physically
feeding Input 2, or separate authority plus a complete inverse for any gain or
gate change.

## 2026-09-04 channel-pair routing resolution

The current checkpoint is
`runs/20260904T015915-0700-unlinked-channel2-stat-routing/`. The bounded live
preflight used only identity, interface 5/alternate 1, and two
`GetP | Appl(0) | JaSt` reads. At 98% battery it matched serial
`AB7C22200355`, descriptor `1.28`, and returned two identical 2040-byte replies
with SHA-256
`086ca18f0f9dd095d25a046d5d2ceddf0d22e693a554a9c4b38081088702576e`.
The decoded state was:

```text
flags_word             0x1a1
stereo link bit 12     clear
Channel 1              slot 0, disabled
Channel 2              slot 3, enabled
```

The static route is now source-bound end to end for that state:

1. `0x42248..0x42250` tests flags bit 12 and branches to the unlinked path when
   clear.
2. `0x424d6..0x424ec` collapses valid `Stat` slots with `slot >> 1` while
   passing selector argument `r3=0`; slots 2/3 therefore enter `0x531e0` with
   `r1=1`.
3. `0x53222..0x53224` diverts nonzero `r1` to alternate table slot 2 at
   `device+0x5e88`, not Voice FX slot 1 at `device+0x5e80`.
4. The two-instance constructor loop places the second channel-strip owner at
   `device+0x508c`; its `+4` interface is exactly the slot-2 object at
   `device+0x5090`.
5. Vtable word `0x10cb1c` reaches adjustor `0x52aec` and state apply `0x52978`.
   Its five keys are `filt`, `gate`, `comp`, `eq  `, and `lim `; Voice FX 201
   is absent.

The linked candidate is also source-bound without making a device change. With
bit 12 set and slot greater than zero, `0x42266` enters the normal indexed table
with `r1=0, r3=1`, then `0x42280` enters slot 2 with `r1=1, r3=0`. The first
table contains the Voice FX state interface at slot 1, but its selected index
remains data-dependent. Thus linking is a credible discriminating trial, not
proof that Voice FX will be selected.

TDD retained the expected RED failures and current GREEN contracts. The
dedicated preflight module passes 4/4; the firmware-static module passes 44/44
in 53.332 seconds. The first full-suite invocation reached its 420-second
wrapper and remains `INCOMPLETE_TIMEOUT`, not PASS. After the final routing and
documentation changes, a longer complete hardware-free run passed 205 tests
with one expected historical-artifact skip in 482.698 seconds, exit 0. Its only
diagnostic was the pre-existing unclosed-WAV `ResourceWarning` in
`re/cp34_current_slot_survey.py:260`.

This result supersedes the older unresolved-slot-two boundary and any blanket
claim below that selected `Stat` recall always reaches block 201. Historical
sections remain useful provenance for their narrower source facts.

## Current live channel-2 result

At `2026-09-03T23:39:47-07:00`, the bounded run
`runs/20260903T232428-0700-channel2-slot3-173ms/` submitted the complete
860-byte `CP34 Ch2 173ms Echo` `MemP/Stat` archive to inactive global slot 3
(channel 2), then selected channel-2 slot 3. The final result is
`WRITE_SENT_AND_SELECTED`: its two SetP operations returned valid empty
transport acknowledgements, post-state reports channel 2 slot 3, and the
guarded channel-1 processing-channel, slot, enable, and gain values were
unchanged across the trial. The record's wire SHA-256 is
`b609139abc514c67171f047252c554529287bd679cb5df416e391397fc49c3ed`.

The first submission was not retried blindly: it reached the `Stat` write but
the original runner classified its eight-byte empty SetP acknowledgement as a
short reply and stopped before the selector. A read-only health check then
confirmed the unit was responsive and still on channel-2 slot 2. The repaired,
test-covered runner drains this valid acknowledgement; its final retry is
idempotent for the same slot-3 record. Slot 3's preceding record cannot be
recovered because the device does not provide full Stat readback, and the
operator expressly permitted channel-2 block changes.

This is strong transport-and-selection evidence only. Physical nonvolatile
commit, front-panel recall, decoded-record equality, and audible 173 ms Voice
FX remain `UNPROVED` after the requested Input-2 physical observation. The
trial did not write channel 1, gain, phantom, routing, monitor, main, or
headphone controls; it did not use Wine, network, firmware, reset, DFU, or
installation.

After the operator connected the physical patch and headphones, a fresh
read-only preflight passed at 96% battery: channel 2 still selects enabled slot
3 and channel 1 remains slot 0 disabled. A three-second, six-channel
`hw:CARD=R24,DEV=0` passive ALSA capture was then retained without playback or
any device-setting change. Input 2 reached -24.14 dBFS, establishing only that
the captured interval contained a signal. It did not contain the required five
isolated impulses, so no routing map, 173 ms signature, physical commit, or
audibility conclusion follows. Its retained evidence is
`runs/20260903T232428-0700-channel2-slot3-173ms/PASSIVE-AUDIO-BASELINE.json`.
Before emitting a stimulus, identify the external patch source/output; do not
blindly send audio through the headphone path.

The first human audible check is now retained, not discarded: the operator
touched the free patch-cable end feeding Input 2 and reported **dry only**—the
direct tap/hum was audible in headphones, with no distinct 173 ms repeat. A
fresh read-only post-check passed at 98% battery with channel 2 still enabled
on slot 3; it performed no channel-1 write. This is an inconclusive negative,
not proof that Voice FX is absent, because a finger/cable contact is not a
calibrated isolated line-level transient. See
`runs/20260903T232428-0700-channel2-slot3-173ms/PHYSICAL-OBSERVATION-RESULT.json`.
The next safest discriminating test is the same headphones arrangement with a
known, brief external line-level transient fed into Input 2.

The operator subsequently recalled one possible delay-like moment shortly after
the native GTK host restarted, but it occurred only once; this is retained as
`UNCONFIRMED_SINGLE_EVENT`. The host was left open as the sole USB owner and its
bounded `arm-channel2-delay` action was repeated once while the transient UI
result was captured through accessibility. The action's final readback reported
Channel 1's guard unchanged, Channel 2 enabled on slot 3, and two parameter
writes for the exact Delay request (`on=true`, 173 ms, 25% feedback, 50%
wet/dry). This confirms host execution, not audible processing. The operator
reported **no audible difference; dry** during or after that controlled repeat,
so the earlier possible moment did not reproduce. The retained result is
`runs/20260903T232428-0700-channel2-slot3-173ms/HOST-ACTION-RESULT.json`.

The root-cause comparison then identified a flaw in that action: it required
Channel 2 to already report slot 3 and reselected slot 3, while firmware's
native selected-`Stat` application is reached on a changed selector. The open
GTK host was therefore used for one isolated Channel-2 recall edge, global slot
`3 -> 2 -> 3`. Its UI reflected both transitions and the final return to slot 3
after one-second settle intervals; no Channel-1 control, preset content, direct
block-201 parameter, Wine, firmware, network, or audio stream was touched. The
operator reported **dry only** after the edge; direct audio remained present,
so this was not a mute or routing loss, but no Voice FX became audible. The
retained result is
`runs/20260903T232428-0700-channel2-slot3-173ms/RECALL-EDGE-RESULT.json`.

A stronger stock-record control is now active. After 28 focused tests passed,
the native GTK host was cleanly restarted and its
`load-channel2-factory-slap-echo` action accepted only the recovered factory
record at `re/uc_factory_presets.json` index 4: 850 encoded bytes, wire SHA-256
`a6c3294b62cfb3a46122a82c93514ea2aeb836280fb5d1e458707a78634f87eb`,
`voicefx.on=1`, 150 ms, 25% feedback, and 50% wet/dry. At 99% host battery it
sent one `MemP/Stat(3)` fragment, then forced Channel 2 through global slots
`3 -> 2 -> 3`. The action's final read verified Channel 2 enabled on slot 3 and
the guarded Channel-1 state unchanged. The host exposed no semantic transport
payload after its transport-header handling; that does not prove packet
non-reception or physical commit. The
time-correlated headphone report was **"dry all dry everytime"**; no distinct
150 ms repeat was heard. This rules out the custom title, 173 ms value, and
compressor-threshold change as the leading cause. At the time it did not
separate storage from recall dispatch. The 2026-09-04 routing resolution above
now proves that the actual unlinked Channel-2 path selects the second channel
strip rather than Voice FX; physical storage remains independently unresolved.
The result is retained in
`runs/20260903T232428-0700-channel2-slot3-173ms/FACTORY-SLAP-ECHO-RESULT.json`.

At `2026-09-04T00:45:50-07:00`, the operator explicitly ruled out the headphone
channel as the cause. That is retained as an operator attestation, not inferred
from `JaSt`. No output routing or headphone control will be changed. The later
routing checkpoint identifies slot two as the second channel strip and removes
that static ambiguity. That linked positive-slot experiment has now run under
a one-trial lift of the Channel-1 restriction; its caller transition completed,
but the passive capture had no above-gate source and therefore did not resolve
audibility. Independent proof of physical slot-record storage also remains
unavailable without a full record readback or a successful observable recall.

A final read-only snapshot at 95% battery reproduced channel-2 slot 3 enabled
with identical JaSt replies. It also showed channel 1 slot 0 **disabled**.
Channel 1 had been enabled in the 89% pre-trial snapshot, but was already
disabled before the final trial's guarded write window. No retained final-trial
frame addresses channel 1; attribution is unresolved, and no restore write was
sent because the operator instructed that channel 1 be left alone.

The same current-state summary is prepared as the task-local
`runs/20260903T230102-0700-readonly-preflight/OBSIDIAN.md`
dashboard mirror. The task-local `RESUME.md`, `PROGRESS.md`, and checksum
manifest remain authoritative; the Obsidian note is an intentionally redundant
fast-entry index, not a substitute for their verification.

At `2026-09-03T22:52:22-07:00`, the device-slot comparison checkpoint added
`compare_device_slot_records()` and four hardware-free regression cases. The
function requires an explicit complete expected record and a complete decoded
observed record; it strips only extraction metadata, reports canonical hashes
and stable mismatch paths, and keeps physical commit, front-panel recall, and
audibility `UNPROVED`. Baseline tests were 20/20, the deliberate RED import
failure established the missing comparator, related focused tests passed 41/41,
and the full suite passed 190 tests with one expected skip in 152.830 seconds.
No USB, device, audio, preset/effect, Wine, network, firmware, or other live
action occurred. A later live comparison needs exact scoped authorization,
current PRESTATE, a restoration plan, and a provenance-bound decoded readback;
a transport reply or selected slot remains insufficient.

At `2026-09-03T23:04:39-07:00`, an exact authorization permitted only identity
and battery reading, interface 5/alternate-1 claim, and `GetP | Appl(0) | JaSt`
state reads on serial `AB7C22200355`. The dedicated client avoided the broader
host class's endpoint-clear/vendor-query behavior, sent exactly two reads, and
returned two identical 2040-byte `Rply` payload hashes:
`d3862c071142d1ff2c02931917779817b553977fc65ff97e896576d130b62039`.
Host battery was 84%; readable state showed channel 1 selected slot 0 and
channel 2 selected slot 2, both enabled. No stored `Stat` record, preset title,
or full restoration baseline was read. No SetP, audio, preset/effect, Wine,
firmware, detach, network, or other follow-on live action occurred.
The complete hardware-free suite after the dedicated preflight client was added
passed 193 tests with one expected local-artifact skip in 151.298 seconds.

At `2026-09-03T23:10:32-07:00`, the operator clarified that the device shows
preset-block icons rather than names, and that every currently onboard preset
has compression. This rules out a display-title transcription route and confirms
that compressor presence is not a distinguishing slot fingerprint. It does not
identify stored `Stat` content, compressor parameters, Voice FX state, user
assignment, recall, or audibility; no device command accompanied the report.

At `2026-09-03T21:32:42-07:00`, the resumed local checkpoint reconciled the
checksum-valid entry-route evidence against later unsealed source/test drift.
The recovered linear inventory found only the known `0x5e26c -> 0x5e0ec`
adjustor branch and no immediate `BL` candidate in its linear decode. It does
not prove that the executable has no other caller. The focused contract passed
1/1 in 17.99 seconds, the firmware-static module passed 41/41 in 17.84 seconds,
and the complete hardware-free suite passed 185 tests with one expected
local-artifact skip and 47 subtests in 215.55 seconds. Dynamic and
interprocedural callers, optional-field lookup/default behavior, parser
semantics, safe placement, image emission, and all hardware actions remain
unresolved or blocked; independent review of this local checkpoint is open.

At `2026-09-01T01:40:19-07:00`, that dashboard mirror was copied to
`Documents/Obsidian/ResearchOS/Projects/PreSonus Revelator io24 — CP34 custom-firmware recovery.md`
and its SHA-256 matched the task-local `OBSIDIAN.md`. The Obsidian application
was not running; this was a direct Markdown update.

At `2026-09-01T09:41:33-07:00`, the current sealed receiver-type dashboard
was refreshed at that same vault path. Its SHA-256 matches task-local
`runs/20260901T093320-0700-state-receiver-type/OBSIDIAN.md`:
`96fdcb5ea147e0ee1270f9355b67f0bf8f2fb4089441954674da8e651bfd8953`.

At `2026-09-01T09:54:06-07:00`, the sealed owner-construction dashboard was
refreshed at that same vault path. Its SHA-256 matches task-local
`runs/20260901T094641-0700-state-apply-caller-construction/OBSIDIAN.md`:
`6599c51c7e0157941ae05398bd7ceaa8ee3b3c63a6ffab7286a5580732be57be`.

At `2026-09-01T11:08:13-07:00`, the sealed secondary-interface dashboard was
refreshed at that same vault path. Its SHA-256 matches task-local
`runs/20260901T110029-0700-secondary-state-interface-caller/OBSIDIAN.md`:
`b6f4c162b3e9cf1678c566f250d2e4fe78635940f580bfc2aa57ec2496b40533`.

At `2026-09-01T11:22:55-07:00`, the sealed primary-caller dashboard was
refreshed at that same vault path. Its SHA-256 matches task-local
`runs/20260901T111327-0700-primary-apply-caller-provenance/OBSIDIAN.md`:
`c3b55bc79a8a72874f7fe7e876a105cd3696a1172c4d661222b2787e16273015`.

At `2026-09-01T11:35:56-07:00`, the sealed structured-state dispatcher
dashboard was refreshed at that same vault path. Its SHA-256 matches task-local
`runs/20260901T112502-0700-structured-state-dispatcher/OBSIDIAN.md`:
`b5e1a3168b819dcd9e996d7fb6ff27627a8f4eeea61b1077e2ed9d610e19fb26`.

At `2026-09-01T11:49:43-07:00`, the sealed `Stat` dispatcher first-handoff
dashboard was refreshed at that same vault path. Its SHA-256 matches task-local
`runs/20260901T114228-0700-stat-dispatcher-handoff/OBSIDIAN.md`:
`a13044cf1bc847cb67cede3b41f9bdeeeb43dfda3ace6a209790effcff2c39b9`.

At `2026-09-01T12:00:36-07:00`, the sealed indexed component-dispatch dashboard
was refreshed at that same vault path. Its SHA-256 matches task-local
`runs/20260901T115344-0700-state-component-indexed-dispatch/OBSIDIAN.md`:
`0233454611a7c258fa9a91c67220e658e45b440e4b0489cd53c66fe71da699be`.

At `2026-09-01T12:15:57-07:00`, the sealed component-key comparison dashboard
was refreshed at that same vault path. Its SHA-256 matches task-local
`runs/20260901T121005-0700-state-component-key-compare/OBSIDIAN.md`:
`e42a0b0de365ac5db28c896e3067a5889c36492029c2fd7457a2d408e031de38`.

At `2026-09-01T12:31:20-07:00`, the sealed direct `Stat` selector-enable
dashboard was corrected to make the selector gate conditional on reaching it
after prior helpers, then refreshed at that same vault path. Its SHA-256
matches task-local `runs/20260901T121655-0700-stat-selector-enable/OBSIDIAN.md`:
`afa46849acbb14bd474bea8189da9bffbc855d0e82a5dd688c0d99512c47f4d4`.

At `2026-09-01T12:39:44-07:00`, the sealed paired direct `Stat` handoff
entry-gate dashboard was refreshed at that same vault path. Its SHA-256 matches
task-local `runs/20260901T123148-0700-paired-stat-handoff-gates/OBSIDIAN.md`:
`95baa248d35a01d936c006e09c1ff7ccaed7f463e1b68c92bbf39ae9690cfba6`.

At `2026-09-01T12:51:12-07:00`, the sealed alternate constructed-cursor
callback dashboard was refreshed at that same vault path. Its SHA-256 matches
task-local `runs/20260901T124125-0700-alternate-cursor-callback/OBSIDIAN.md`:
`35ab91a203bce53b96559bb9bb53c22d229b02f6002dd6a9641b1ff24483f774`.

At `2026-09-01T13:01:42-07:00`, the sealed alternate cursor-adjust dashboard
was refreshed at that same vault path. Its SHA-256 matches task-local
`runs/20260901T125130-0700-alternate-cursor-adjust/OBSIDIAN.md`:
`d215f62daf41ef2315519b7e814b5c7e6eac14cd1010b6bd0249fadd86708caf`.

At `2026-09-01T13:11:11-07:00`, the sealed alternate static key-comparison
dashboard was refreshed at that same vault path. Its SHA-256 matches task-local
`runs/20260901T130219-0700-alternate-key-compare/OBSIDIAN.md`:
`e0431fe881a2c0eb469d99391a74a9ae177e1aff285b11e8c147ebd2a9451af3`.

At `2026-09-01T13:20:18-07:00`, the sealed alternate slot-two dispatch
dashboard was refreshed at that same vault path. Its SHA-256 matches task-local
`runs/20260901T131149-0700-alternate-slot-two-dispatch/OBSIDIAN.md`:
`117378df42c6b1d2becf8b303a46e06491792a16f64d4ac0e822533ac567896c`.

At `2026-09-01T23:12:18-07:00`, the sealed slot-two base-initializer vtable
boundary established that direct call `0x5e018 -> 0x5d990` carries the
unadjusted outer receiver and writes two static base tables at outer offsets
`+0` and `+4`; it does not bind the later `device +0x5090` slot-two vtable.
The focused contract passed 1/1, the firmware-static module passed 32/32, and
the full hardware-free suite passed 177 tests with one expected skip in
211.171 seconds. Slot-two virtual target/semantics, parser behavior, placement,
image emission, and all hardware actions remain blocked. The direct Markdown
dashboard mirror at the canonical vault path matches task-local
`runs/20260901T230307-0700-slot-two-base-initializer-vtable/OBSIDIAN.md` at
SHA-256 `5a2d33ad31ea2f28279b6d1a7a3c706c74aa4ca8101af7e8f93eee731d155648`.

At `2026-09-01T23:21:17-07:00`, the sealed slot-two local-construction-route
boundary established that constructor `0x5e014` retains `device +0x5090` only
in table slot two and returns without a direct subconstructor call in its
straight-line tail. The focused contract passed 1/1, the firmware-static module
passed 33/33, and the full hardware-free suite passed 178 tests with one
expected skip in 227.406 seconds. This is not a global no-construction result:
an embedded-object construction route elsewhere, the slot-two vtable, virtual
target, semantics, parser behavior, placement, image emission, and all hardware
actions remain blocked. The direct Markdown dashboard mirror at the canonical
vault path matches task-local
`runs/20260901T231454-0700-slot-two-local-construction-route/OBSIDIAN.md` at
SHA-256 `e15c78f6c8d950e822005bb108409bf3acf448fcf537712343488139aec11741`.

At `2026-09-01T23:30:38-07:00`, the sealed slot-two
immediate-materialization inventory decoded the pinned application at every
halfword-aligned raw offset for exact immediate `0x5090`. It found only the
already source-bound component-table site `0x5e03e`; no additional immediate
route was source-bound. The focused contract passed 1/1, the firmware-static
module passed 34/34, and the full hardware-free suite passed 179 tests with one
expected skip in 244.182 seconds. Split, non-immediate, or dynamic construction
remains unresolved, as do the slot-two vtable/target/semantics, parser behavior,
placement, image emission, and all hardware actions. The corresponding dashboard
mirror at the canonical vault path matches task-local
`runs/20260901T232334-0700-slot-two-immediate-materialization-inventory/OBSIDIAN.md`
at SHA-256 `b1d9ad874034df8035fb74e415e228d039ff83b22c1008e5689a513fac641cec`.

At `2026-09-01T23:42:40-07:00`, the sealed base-initializer member-call map
recovered direct initializer `0x5d990`'s normal static return at `0x5df6a`.
Its entry prologue source-binds four direct outer-member calls at offsets
`+0xc38`, `+0xc5c`, `+0x11e0`, and `+0x3a70`, but not slot two `+0x5090`. The
focused contract passed 1/1, the firmware-static module passed 35/35, and the
full hardware-free suite passed 180 tests with one expected skip in 254.657
seconds. Later initializer calls and nonlocal construction remain unresolved,
as do the slot-two vtable/target/semantics, parser behavior, placement, image
emission, and all hardware actions. The direct Markdown dashboard mirror at the
canonical vault path matches task-local
`runs/20260901T233334-0700-base-initializer-member-call-map/OBSIDIAN.md` at
SHA-256 `723ba56611fc9b288c883dc1f4bd84e4e6f37c7ac83f819b6992708908f150c0`.

At `2026-09-01T23:52:54-07:00`, the sealed adjacent pre-slot-two receiver
boundary source-bounded a later direct base-initializer call to receiver
`device +0x508c`: a caller-local `sp+0x4` value first constructed as
`device +0x5074` is reloaded and adjusted by `+0x18` before `0x5df3e` calls
`0x5d2cc`. That receiver is four bytes before unresolved slot two `+0x5090`.
The focused contract passed 1/1, the firmware-static module passed 36/36, and
the full hardware-free suite passed 181 tests with one expected skip in 239.985
seconds. This adjacency alone does not bind type, interface, vtable, target, or
semantics; the target was not entered. Parser behavior, placement, image
emission, and all hardware actions remain blocked. The corresponding dashboard
mirror at the canonical vault path matches task-local
`runs/20260901T234519-0700-adjacent-pre-slot-two-receiver/OBSIDIAN.md` at
SHA-256 `d85a6936a11b4513d936ca092f66822529eaa9fd53307faabd979b976a3a8e5e`.

At `2026-09-02T00:02:35-07:00`, the sealed pre-slot-two target-prologue
boundary entered only target `0x5d2cc`'s first basic block. It captures the
source-bound `device +0x508c` receiver unchanged into `r4` before its first
conditional branch and makes no receiver-relative store or adjustment first.
The focused contract passed 1/1, the firmware-static module passed 37/37, and
the full hardware-free suite passed 182 tests with one expected skip in 240.250
seconds. No later target block, call, or virtual entry was followed; type,
interface, vtable, target behavior, parser behavior, placement, image emission,
and all hardware actions remain blocked. The corresponding dashboard SHA-256
mirror at the canonical vault path matches task-local
`runs/20260901T235453-0700-pre-slot-two-target-prologue/OBSIDIAN.md` at
SHA-256 `e37dd7659bd9d42b3d7f2084290815d673c4f9883929eb3c5ec13b350936a614`.

At `2026-09-02T00:17:23-07:00`, the sealed model-0 decoder first-helper
boundary source-bounded direct call `0x5e192 -> 0x5e094`. Its two arguments are
decoder-local descriptors at `sp+0x2c` and `sp+0x4`, initialized from local
heads at `sp+0x34` and `sp+0xc`; the helper prefix proves only count handling.
The focused contract passed 1/1, the firmware-static module passed 38/38, and
the full hardware-free suite passed 183 tests with one expected skip in
256.479 seconds. This deliberately preserves
`OPTIONAL_FIELD_LOOKUP_UNRESOLVED`: local descriptor/count mechanics do not
identify serialized field names, optional defaults, parser behavior, placement,
image emission, or hardware readiness. The direct Markdown dashboard mirror at
the canonical vault path matches task-local
`runs/20260902T001723-0700-doubler-decoder-first-helper/OBSIDIAN.md` at
SHA-256 `22803ebc507cdb0f60c47f8ca8532b6d6c1eacdc4443b7ae915b361797c9dca1`.

At `2026-09-02T00:26:06-07:00`, the sealed model-0 decoder input-iteration
boundary bound `r1` captured in `r6`, endpoint setup `r7 = r1 + (r2 << 2)`,
and four-byte `vldmia r6!, {s15}` iteration. It also bound a model-local
candidate sequence from `sl +0x1c8`, with a count at `sl +0x1cc`, `s14` at
candidate `+4`, a `0x58` stride, and an FP-register mismatch loop. The focused
contract passed 1/1, the firmware-static module passed 39/39, and the full
hardware-free suite passed 184 tests with one expected skip in 223.686 seconds.
This is word-iteration/comparison evidence only and preserves
`OPTIONAL_FIELD_LOOKUP_UNRESOLVED`: it does not identify a serialized record,
field names, parser/default behavior, placement, image emission, or hardware
readiness. The direct Markdown dashboard mirror at the canonical vault path
matches task-local
`runs/20260902T002606-0700-doubler-decoder-input-iteration/OBSIDIAN.md` at
SHA-256 `333068a4949c4b4f39c188d35c7b479c0bcdade58dbcf0b4eaba10f1acfdd5b0`.

At `2026-09-02T00:38:36-07:00`, the sealed model-0 decoder entry-route
boundary bound two static paths into `0x5e0ec`: primary vtable `0x10c890` slot
`+0x34` at `0x10c8c4`, and vtable slot `0x10c8e0` through adjustor `0x5e268`,
which subtracts `0x1c0` from `r0` and tail-branches at `0x5e26c`. The focused
contract passed 1/1, the firmware-static module passed 40/40, and the full
hardware-free suite passed 185 tests with one expected skip in 319.470 seconds.
This binds static entry ABI only and preserves `OPTIONAL_FIELD_LOOKUP_UNRESOLVED`:
it does not identify a dynamic caller, input record, field names, parser/default
behavior, placement, image emission, or hardware readiness. The direct Markdown
dashboard mirror at the canonical vault path matches task-local
`runs/20260902T003836-0700-model-zero-decoder-entry-routes/OBSIDIAN.md` at
SHA-256 `db74382bffa6a7489fd741bb74f89fa3ea18066ebf8ed833599268d6a17b234e`.

At `2026-09-01T01:42:53-07:00`, the active analyzer gained a test-validated
top-level structured-state entry proof: its primary Voice FX vtable slot
`0x10c6e4` points directly to `0x5545c`; its secondary state-interface slot
`0x10c704` points to adjustor `0x555b8`, which adjusts `this` by `-4` then
branches to the same target. Focused hardware-free contracts pass 13/13.
This is not an optional-field parser/default implementation and does not alter
the `NO_SAFE_HOME` placement result or image-emission block.

The full hardware-free regression suite was then re-run from that checkpoint:
158 tests passed, one expected local-artifact test was skipped, and it finished
in 132.191 seconds. The only warning was the pre-existing unclosed temporary
WAV read in `re/cp34_current_slot_survey.py:260`; no firmware, device, Wine,
network, or image action occurred.

At `2026-09-01T01:49:59-07:00`, the selected model's own state-apply ABI was
also source-bound. The parent loader indirect call at `0x5559a` calls
`model+4` vtable slot `+4`; model-0 construction installs static vtable
`0x10c8d0`, whose `+4` slot points to adjustor `0x548dc`, which adjusts `this`
by `-4` and branches to `0x546ec`. Focused contracts pass 14/14. This proves
the nested model-state route, not that `0x546ec` is the stock `godv` payload
reader or that optional extension fields can be parsed.

The corresponding full hardware-free regression suite passed: 159 tests,
one expected local-artifact skip, in 148.614 seconds. The same pre-existing
temporary-WAV `ResourceWarning` appeared; there was no image, device, Wine,
network, or other live action.

At `2026-09-01T01:55:28-07:00`, static contracts separately bound the stock
model-0 primary tagged callback: primary vtable `0x10c890` enters `0x5bb6c`,
compares the `godv` literal at `0x5bd38`, then writes the five existing state
values at model offsets `+0x340..+0x350` and derives shared mix at `+0x358`.
That callback is not aliased to the model state-apply target `0x546ec`, but no
call relationship between the two has been established. Focused contracts pass
15/15; optional-field lookup and safe extension placement remain unresolved.

The corresponding full hardware-free regression suite passed: 160 tests,
one expected local-artifact skip, in 151.034 seconds. The pre-existing
temporary-WAV `ResourceWarning` was unchanged; no live action occurred.

At `2026-09-01T02:01:23-07:00`, both complete, hash-validated function bodies
were checked for direct immediate control flow. There is no immediate
`B`/`BL` cross-edge between model state-apply `0x546ec..0x548cb` and the tagged
`godv` handler `0x5bb6c..0x5bd2f`; the first body instead has six indirect
`blx` sites. This is deliberately only a two-slice direct-edge result. It does
not prove that the paths have no indirect or interprocedural relationship.
Focused contracts pass 16/16, while optional-field lookup and safe extension
placement remain unresolved.

The corresponding full hardware-free regression suite passed: 161 tests, one
expected local-artifact skip, in 153.314 seconds. The pre-existing
temporary-WAV `ResourceWarning` was unchanged; no image, device, Wine, network,
or other live action occurred. The next static-only action is bounded to the
state-apply indirect call at raw `0x54730`; trace its receiver and vtable
provenance before assigning any parser or tagged-callback semantics. If that
target cannot be source-bound, preserve the unresolved bridge rather than
inferring it.

At `2026-09-01T02:10:15-07:00`, one named model state-apply indirect call was
traced under TDD. The new contract first failed because
`state_apply_indirect_call_0x54730` did not exist; after the minimal verifier,
17 focused hardware-free contracts pass. The state receiver is captured by the
top-level loader at `0x55462`, forwarded at `0x55592`, saved/reloaded through
`0x546f0/0x54708/0x54726`, and dispatched via that caller-supplied receiver's
vtable slot `+8` at `0x5472c/0x5472e/0x54730`. The output argument is
`model+0x340`; the return is compared with raw `0x14`. The concrete vtable
target, parser semantics, and any relationship to tagged `godv` remain
unresolved. The next action is only the broad hardware-free regression run;
after it, preserve this boundary and close the static pass rather than tracing
another indirect call without a new bounded scope.

The corresponding full hardware-free regression suite passed: 162 tests, one
expected local-artifact skip, in 163.340 seconds. The only warning was the
pre-existing temporary-WAV `ResourceWarning` in
`re/cp34_current_slot_survey.py:260`; no image, device, USB, audio, Wine,
network, or other live action occurred. This static pass is sealed with
`CALLER_SUPPLIED_RECEIVER_VTABLE_TARGET_UNRESOLVED`; preserve that boundary
until a new bounded scope is explicitly recorded.

## 2026-09-01 receiver-type boundary continuation

The new bounded static stage examined only the existing state receiver that
reaches model-0's indirect call at `0x54730`; it did not follow another
indirect call. The top-level apply entry `0x5545c` has exactly two static
entry literals at raw `0x10c520` and `0x10c6e4`, but those entries do not bind
the incoming receiver's concrete type. The receiver is captured from `r1` into
`r4`, dynamically dispatched through slots `+0` and `+4`, then forwarded
unchanged to model 0 for dynamic slot `+8` dispatch at `0x54730`.

The source-bound result is
`NO_CONCRETE_RECEIVER_TYPE_IN_VALIDATED_TOP_LEVEL_FLOW`; both the receiver
type and concrete target remain unresolved. This does not recover a parser,
optional-field defaults, a `godv` bridge, or executable placement. The focused
contract passed 1/1, and the full hardware-free suite passed 163 tests with one
expected skip in 219.202 seconds. The only warning was the pre-existing
temporary-WAV `ResourceWarning`. No image, device, USB, audio, Wine, network,
or other live action occurred.

The continuation is sealed at
`runs/20260901T093320-0700-state-receiver-type/`. Any further caller-
construction investigation needs a new bounded scope and checkpoint; it may
not treat entry literals as receiver-type proof, trace a second indirect call,
or emit an image.

## 2026-09-01 owner-construction boundary continuation

The next bounded static stage traced only the two owner tables that contain the
shared top-level state-apply entry `0x5545c`. The table at raw `0x10c4e8`
contains it at `+0x38` (`0x10c520`) and is installed twice at `r8+0x22c` from
literals `0x3d708` and `0x3d868`; that owner remains semantically unresolved.
The distinct table at raw `0x10c6bc` contains it at `+0x28` (`0x10c6e4`) and
is installed from `0x418fc` at `r4+0x11e0` as the source-bound Voice FX owner
entry.

Neither owner installation constructs or types the input state receiver. The
shared apply method separately captures `r1` at `0x55462` before forwarding it
to the existing dynamic `+8` dispatch at `0x54730`. The source-bound result is
`OWNER_INSTALLATIONS_DO_NOT_BIND_INPUT_RECEIVER_TYPE`; it does not recover a
parser, optional-field defaults, the concrete dynamic target, a `godv` bridge,
or executable placement. The focused contract passed 1/1 and the complete
hardware-free suite passed 164 tests with one expected skip in 205.779 seconds.
The only warning was the pre-existing temporary-WAV `ResourceWarning`. No
image, device, USB, audio, Wine, network, or other live action occurred.

The continuation is sealed at
`runs/20260901T094641-0700-state-apply-caller-construction/`. Any further
caller-construction trace must start with a new exact scope and checkpoint; it
may not infer the input receiver type from owner tables, follow another
model-state indirect call, or emit an image.

## 2026-09-01 secondary state-interface caller boundary continuation

The next bounded static stage tied the Voice FX embedded-owner secondary state
interface to the shared top-level apply entry without conflating it with the
separate `r1` record. The constructor loads primary vtable `0x10c6bc` from
literal `0x418fc`, stores it at embedded-owner `+0x11e0`, derives secondary
vtable `0x10c700` as `+0x44`, and stores it at `+0x11e4`. Its secondary slot
`0x10c704` (`+0x4`) invokes adjustor `0x555b8`, which subtracts four from `r0`
and branches to top-level apply `0x5545c`.

This source-binds the `r0` ownership route only. No direct static caller was
source-bound, and the caller does not materialize a construction or concrete
type for the independent `r1` record. The sealed result is
`SECONDARY_INTERFACE_ROUTE_SOURCE_BOUND_CALLER_AND_R1_UNRESOLVED`; it does not
recover a parser, optional-field defaults, the model-state dynamic target, a
`godv` bridge, or executable placement. The focused contract passed 1/1 and
the complete hardware-free suite passed 165 tests with one expected skip in
193.787 seconds. The only warning was the pre-existing temporary-WAV
`ResourceWarning`. No image, device, USB, audio, Wine, network, or other live
action occurred.

The continuation is sealed at
`runs/20260901T110029-0700-secondary-state-interface-caller/`. Any future
caller investigation must start with a new exact scope and checkpoint that
identifies a concrete dispatcher or record-construction boundary. It may not
infer `r1` type from the secondary table, follow a model-state indirect call,
or emit an image.

## 2026-09-01 primary state-apply caller provenance continuation

The next bounded static stage surveyed only local straight-line primary-vtable
`+0x28` dispatches. The required Voice FX table remains `0x10c6bc`, whose
`+0x28` slot at raw `0x10c6e4` points to `0x5545c`. Ten generic dispatches have
the vtable-load/slot-load/`blx` shape, but none locally constructs embedded
owner `+0x11e0` or preserves that owner in `r0` at the call boundary.

Those are syntactic slot matches, not source-bound Voice FX calls: none proves
vtable `0x10c6bc`, target `0x5545c`, or the independent `r1` record. The sealed
result is `NO_LOCAL_STRAIGHT_LINE_EMBEDDED_OWNER_PRIMARY_APPLY_CALLER`; it does
not recover a parser, optional-field defaults, a model-state target, a `godv`
bridge, or executable placement. The focused contract passed 1/1 and the
complete hardware-free suite passed 166 tests with one expected skip in
222.125 seconds. The only warning was the pre-existing temporary-WAV
`ResourceWarning`. No image, device, USB, audio, Wine, network, or other live
action occurred.

The continuation is sealed at
`runs/20260901T111327-0700-primary-apply-caller-provenance/`. Any future
caller investigation must start with a new exact scope and checkpoint naming a
concrete dispatcher or object-transfer boundary into a generic virtual call. It
may not promote a slot match to a receiver/target proof, follow a model-state
indirect call, or emit an image.

## 2026-09-01 structured-state dispatcher boundary continuation

The next bounded static stage examined the retained application's `Stat`
FourCC evidence without treating a byte string or host JSON field as parser
proof. Seven little-endian `tatS` literals (conventional FourCC
`0x53746174`) were source-bound to PC-relative loads, tagged-record `+0x8`
loads, and compare instructions at raw literal offsets `0x2f278`, `0x30a10`,
`0x30a60`, `0x30bdc`, `0x30c30`, `0x41ea0`, and `0x423d4`.

A full-image linear immediate-edge inventory finds exactly one edge into
top-level apply `0x5545c`: the already-established secondary state-interface
adjustor tail branch `0x555bc -> 0x5545c`. None of the verified `Stat`
literal-load, record-tag-load, or compare instructions is that branch source.
This is not a full control-flow graph: dynamic and interprocedural routing,
the direct caller, and independent `r1` record provenance remain unresolved.
The sealed result is
`STRUCTURED_STATE_TAG_SITES_SOURCE_BOUND_DIRECT_APPLY_ROUTE_UNRESOLVED`.
It does not recover parser/default semantics, optional-field lookup, a model
state target, a `godv` bridge, or executable placement.

The focused contract passed 1/1 and the complete hardware-free suite passed
167 tests with one expected skip in 231.293 seconds. The only warning was the
pre-existing temporary-WAV `ResourceWarning`. No image, device, USB, audio,
Wine, network, or other live action occurred. The continuation is sealed at
`runs/20260901T112502-0700-structured-state-dispatcher/`; any later
investigation must create a new exact dispatcher-to-apply transfer scope. It
must not promote a tag comparison to parser/default proof, follow the excluded
model-state indirect call, invent a code cave, or emit an image.

## 2026-09-01 `Stat` dispatcher first-handoff continuation

The next bounded static stage source-bound the first transfer after the live
`Stat` branch, without traversing the later component loop. Pinned vtable word
`0x10cb40` targets dispatcher `0x420bc`; `r1` is captured into `r4`, checked
for the `Stat` tag at `+0x8`, and conditionally branches at `0x420ea` to
`0x42200`. The same live vtable's `+0x38` slot at `0x10cb78` targets structured
state method `0x531e0`.

At the exact `+0x38` virtual call at `0x42266`, the receiver is retained in
`r5`, `r2` is set to local stack address `sp+0xc`, and `r1` is set from `r6`.
`0x531e0` immediately captures its incoming `r1` and `r2` separately. This
source-binds the first handoff ABI, but it does not traverse component selection
or identify the later top-level apply `0x5545c` `r1`. The sealed result is
`STAT_DISPATCHER_FIRST_VTABLE_HANDOFF_SOURCE_BOUND_TOP_LEVEL_R1_UNRESOLVED`.
It does not recover parser/default semantics, optional-field lookup, a model
state target, a `godv` bridge, or executable placement.

The focused contract passed 1/1 and the complete hardware-free suite passed
168 tests with one expected skip in 219.485 seconds. The only warning was the
pre-existing temporary-WAV `ResourceWarning`. No image, device, USB, audio,
Wine, network, or other live action occurred. The continuation is sealed at
`runs/20260901T114228-0700-stat-dispatcher-handoff/`; any later investigation
must create a new exact component-selection-to-state-interface transfer scope.
It must not infer parser/default behavior, follow the excluded model-state
indirect call, invent a code cave, or emit an image.

## 2026-09-01 indexed component-dispatch continuation

The next bounded static stage source-bound the indexed dispatch inside
structured-state method `0x531e0`. The method builds table base
`device+0x5e78` and calls `[table_base + r7 * 8]` through that object's vtable
`+0x4` slot at `0x53374..0x5337c`. Its `r7` index is initialized to `-1`,
derived from incrementing loop counter `r6`, and captured after a data-dependent
comparison; no bounded instruction fixes it to a specific component.

Device construction stores Voice FX state interface `device+0x11e4` at table
slot one (`device+0x5e80`). That interface's vtable `+0x4` word is adjustor
`0x555b8`, which subtracts four from `r0` and branches to top-level apply
`0x5545c`. This establishes the indexed mechanism and a valid slot-one route,
not that a particular `Stat` record selected slot one/component 201 or supplied
top-level apply's `r1`. The sealed result is
`INDEXED_COMPONENT_DISPATCH_SOURCE_BOUND_VOICEFX_SLOT_ONE_ROUTE_SELECTED_INDEX_UNRESOLVED`.
It does not recover parser/default semantics, optional-field lookup, a model
state target, a `godv` bridge, or executable placement.

The focused contract passed 1/1 and the complete hardware-free suite passed
169 tests with one expected skip in 225.742 seconds. The only warning was the
pre-existing temporary-WAV `ResourceWarning`. No image, device, USB, audio,
Wine, network, or other live action occurred. The continuation is sealed at
`runs/20260901T115344-0700-state-component-indexed-dispatch/`; the next exact
scope begins with the two local values compared at `0x53326` to select `r7`.
It must not infer a component identity from the route alone, follow model-state
call `0x54730`, invent a code cave, or emit an image.

## 2026-09-01 runtime-storage/placement checkpoint

The active static analyzer now proves the parent-owned sidecar lifetime from
the exact retained UC 4.7.2 DLL, without writing an extraction: the complete
package SHA-256 is
`790f668608448b7c9f244c360ad72e3c51f71b4e8a3d828eab0e08cd03b35de1` and
the in-memory application span SHA-256 is
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.

- Parent construction is called at raw `0x5da12` for `device+0x11e0`; the
  next sibling begins at `device+0x3a70`, giving an exact `0x2890`-byte parent
  extent. The stock constructor and reset zero existing `+0x2884`; the four
  proposed extension values fit only in `+0x2885..+0x288f`.
- The former `0x10d948..0x10da3f` trailing-cave claim was false. The first 156
  bytes are zero-filled; only the final 92-byte all-FF tail
  (`0x10d9e4..0x10da3f`) remains an unproven candidate. The 36-byte ITCM FF
  span is trampoline-only. Model 5 is proved stock-dispatchable and cannot be
  reclaimed.
- Focused analyzer contracts pass 12/12; the broad hardware-free suite passes
  157 tests in 132.626 seconds with one expected skip. The temporary-WAV
  `ResourceWarning` is pre-existing and unrelated.

No structured-`Stat` parser interception or safe executable extension-body
home is established. Preserve this checkpoint and continue only static,
in-memory investigation; do not emit an image or reinterpret either span as a
safe code cave.

## 2026-09-01 recovery mirror and parser-entry recheck

The pinned image was re-read in memory only after the checkpoint. Its primary
Voice FX vtable slot at raw `0x10c6e4` still points to structured-state apply
`0x5545c`; the secondary state-interface slot at raw `0x10c704` points to
adjustor `0x555b8`, which subtracts four from `this` and branches to `0x5545c`.
This is a source-bound top-level structured-state entry, not proof that the
four new optional fields have a recovered lookup/default implementation.

For fast crash recovery, save task-local evidence before and after each bounded
analysis or verification stage, refresh the active run's checksum manifest, and
mirror the state to its Obsidian Markdown note. Do not treat a successful
mirror copy as proof of the artifact, firmware, or any hardware outcome.

## 2026-09-01 saved continuation: custom per-lane private-reverb controls

The requested capability is a custom firmware extension for block 201/model 0
(Doubler/Transformer's private reverb), not a reinterpretation of block 202.
The public host schema is backward compatible in the firmware direction: an
old record omits the optional fields and the future parser supplies defaults.
The host does **not** assume stock firmware accepts unknown fields: normal
saves emit the exact legacy object and extension serialization requires an
explicit custom-firmware capability.

- `voicefx.wet_ch1`, `voicefx.wet_ch2`: finite gain values clamped to `0.0..1.0`;
- `voicefx.bypass_ch1`, `voicefx.bypass_ch2`: boolean per-lane wet bypasses;
- absent fields retain stock behavior (`wet=1.0`, `bypass=false`);
- existing `voicefx.on` remains the global Voice FX enable, and `mix` remains
  the private algorithm's existing shared parameter.

When that explicit capability is selected, both paired device-slot records
carry the same complete four-field lane state because either record enters the
one shared block-201 state instance. This is the smallest deterministic recall
rule: recalling either paired slot restores both lane controls together. The
two `Stat` writes are sequential—not atomic—and return completed/failed slot
details. A future split-record rule would require a separate
channel-context-aware parser and is not part of this fork.

The original firmware package is a 0x12a694-byte vendor image with metadata and
a standard CRC32 trailer. The project tool now accepts a recovery source only
when its target, image id, Cortex-M vector, full length, and pinned SHA-256 all
match UC 4.7.2. The historical 0x10da40 extraction is truncated and must not
be flashed. The current work may inspect and verify the original package, but
may not emit a modified binary or run an updater.

The reset copy table and model-0 process path are now source-bound: raw
`0x1e1a8` selects a lane from model `+0x338`, loads shared mix from `+0x358` at
raw `0x1e2be`, and calls the private core at raw `0x1c408`, whose final dry/wet
blend is verified. The future hook is
`bypass[lane] ? 0 : clamp(shared_mix * wet[lane], 0, 1)`. It remains blocked
from image emission because no newly owned parser/default storage or safe code
placement is proven; nearby model fields/coefficient arrays and all models 0–5
are live.

Durable current handoff:
`runs/20260901T001259-0700-custom-firmware-lane-controls/`. It contains the
scope, report, checksum manifest, field contract, and stop boundary.

## Outcomes

CP34 has exactly two completion outcomes:

1. Save a custom preset into device-resident storage, assign it to a front-panel
   slot, recall it without an editor driving the state, and prove that it
   survives the declared recall boundary.
2. Select and control Voice FX so the effect is audibly present, then preserve
   and restore that state through the same preset workflow.

Host-only JSON persistence is useful predecessor work, but it does not satisfy
either outcome.

## Current result: both hardware inputs, one shared private-reverb state

This is the controlling continuation state. Block 201/model 0 is one settings
instance, but it is not one audio lane:

- audio-root code loads both physical-input mappings at `device+0x5d74` and
  `device+0x5d78`, using stride `0xcec` to select two processing objects;
- block-201 setup writes count 2 into both adjacent input/output setup fields,
  then configures singleton `device+0x11e0`;
- Doubler's private-core setup calls indexed helper `0x56cc8` once with lane 0
  and once with lane 1.

Therefore the same Doubler private-reverb state can run on both physical inputs
simultaneously. The device does not provide two independently parameterized
instances: `on/lows/width/mix` is shared between the lanes.

The device-resident save contract is now implemented rather than merely
described:

- `io24_preset_record.py` builds two complete channel records and enforces one
  channel-1 slot from 0/1 plus one channel-2 slot from 2/3;
- both records receive an identical Doubler class-id + `on/lows/width/mix`
  mapping and no block-202/send state;
- `io24.py` builds both complete frame sets before the first write and exposes
  `save_device_slot()`, `save_paired_doubler_private_reverb()`, and CLI command
  `saveprivatereverb`;
- `io24gtk.py` now stages those private-reverb values and provides an explicit
  **Overwrite both selected blocks** action using the complete recovered
  Reverb channel-strip record; slider motion performs no ineffective direct FX
  write;
- the save does not select, recall, enable, or change `processingChannel`.

Publishable documentation in `README.md`, `GUIDE.md`, and `PROTOCOL.md` now
states this two-lane/shared-settings contract and removes the stale current
claims that the slot writer is unreachable or that a singleton implies only one
input.

Durable source-bound and implementation result:
`runs/20260831T053346-0700-dual-private-reverb-host/`. Analyzer schema is
`cp34-doubler-private-reverb-v2`; focused verification is 39/39 and the complete
hardware-free suite is 127/127. This stage performed no USB, audio, preset,
Wine, network, firmware, or other live device action.

Physical commit, front-panel recall, audible two-input operation, power-cycle
survival, and restoration remain unproved. A live closure now requires exact
authorization for the target unit, the two slots to overwrite, a pre-write
backup/restoration plan, the paired Stat write, bounded recalls/audio capture,
and any declared power-cycle boundary. Device presence alone is not that
authority; stop at or below 10% battery.

## Current correction: Doubler reverb is private and record-resident

The factory preset titled `Reverb` does not save shared reverb block 202 or a
reverb send. It selects Voice FX model 0 (UC `VoiceOfGod`,
`{66A10093-D461-4CAC-A80C-91F6A1BB37E5}`) and stores only `on`, `lows`,
`width`, and `mix` inside the slot's `voicefx` object.

Firmware establishes why that is sufficient:

- block 202 constructs its reverb core at block+`0x10` by calling `0x5af14`;
- Doubler constructs a private core at model+`0x384` by calling the same
  `0x5af14`;
- block 202 configures its core through `0x5a6a8` at `0x5ade6`;
- Doubler configures its private core through the same `0x5a6a8` at `0x5ae0e`;
- the resulting objects are distinct: `device+0x3a80` for shared block 202 and
  `device+0x1574` for model-0's private member.

All 41 extracted UC factory records were recursively checked. None contains
`reverb`, `vrvb`, `FXA`, `size`, `predelay`, or `hp_freq`. UC's component model
also declares Doubler's storable fields separately from `VocalReverb`'s shared
block-202 fields. Sample rate is runtime configuration rather than a `Stat`
field; saving at 96 kHz uses the same JSON/tagged record.

Predecessor implementation-identity result:
`runs/20260831T040258-0700-doubler-private-reverb/`. The controlling two-lane
and host result is the v2 run named above. Do not add a block-202
write, reverb-send value, or synthesized 96 kHz coefficients to a Doubler slot
record. This resolves the representation and routing question, but not physical
commit, front-panel recall, audibility, survival, or restoration.

## Current correction: the scene JSON drives save, native recall, and Voice FX state

This is the controlling resume state. It supersedes later historical statements
in this file that call `Stat` enumeration-only, claim no host slot-update sender
exists, or say static analysis is exhausted.

- `presets.slots` contains four independent, complete channel/effect records:
  slots 0/1 are the two device blocks for channel 1 and slots 2/3 are the two
  device blocks for channel 2.
- `presets.userpresets` is a separate twelve-record library, indexed 16..27.
- After an eligible processing/effect edit settles for 500 ms, UC 4.7.2 copies
  the current channel object into its active slot and sends the serialized
  record as `SetP -> Appl(0) -> MemP -> Stat(slot 0..3)`.
- A user-library update uses the same outer sender with `PrsM(index 16..27)`.
  There is no second save opcode and no sample-rate branch.
- `io24_preset_record.py` now converts the scene-shaped JSON object into UC's
  tagged binary record. `io24.py` composes that record into the exact
  hardware-free `MemP/Stat` frames; it exposes no live write.
- Forty-seven preset records embedded in UC 4.7.2's source-bound device module
  decoded and re-encoded byte-for-byte. All twelve recovered scene slots also
  passed local encode/decode and frame construction.
- Firmware 1.28 closes the incoming-record handoff. The device-root vtable
  starts at `0x6d208`; its `MemP` slot `+0x80` is `0x2f210`, not `0x3c064`.
  Constructor path `0x3c890 -> 0x30260 -> 0x2fca8` places the preset component
  at `device+0x1240` and stores that address at `device+0x70`. Handler `0x2f210`
  calls the component's `+0x18` entry, `0x3099c`, with the original record.
- `0x3099c` accepts `Stat` 0..3 and `PrsM` 16..27, and `0x3092c` writes the
  record length and fragments through the component's startup-bound storage
  backend. This establishes the static host-message-to-firmware-storage path.
  Power-cycle/nonvolatile survival still requires validation.
- The reciprocal path is native firmware code. Slot-change handler `0x2f334`
  calls root vtable `+0x58` (`0x2f0d0`); that calls preset-component vtable
  `+0x24` (`0x30be0`) to read the selected `Stat` 0..3. Each recovered record
  fragment is passed through root `+0x4c` (`0x2f8ac`) and the firmware's bound
  application callback/router (`0x31674`/`0x3163c` to
  `0x20790`/`0x20754`). Universal Control is not part of this recall path.
- Firmware 1.28 embeds two eight-record factory banks in the same tagged record
  format and binds four `Stat` descriptors. `Slap Echo`, `Detuned Vocal`, and
  `Robot` each carry `voicefx.on=1`; the inactive Voice FX records carry 0 and
  four stereo/instrument records omit `voicefx` entirely. This is strong static
  evidence that activation intent is record-resident, not a missing standalone
  save/recall opcode.
- UC 4.7.2's inverse loader confirms the field mapping: its complete `+0xe6`
  access census shows the record parser finding `voicefx`, then `on`, accepting
  integer or real value 1, and storing the boolean used by the `VoiceFxOn`
  serializer. That byte is host record state; the serializer itself queues no
  enable command.
- The application router does not terminate at a generic parser. `0x20754`
  projects the installed singleton through `0x34cb8`/`0x3cc08`; secondary
  method `0x3cc40` forwards the record to the live device object at singleton
  `+0x138`. Its primary dispatcher `0x420bc` handles `Stat` and invokes
  structured-state method `0x531e0` through live-device vtable slot `+0x38`.
- The device component table binds numeric component 201 to the state interface
  at `device+0x11e4`. During `Stat` application, `0x531e0` calls that
  interface's method `+4`: adjustor `0x555b8` reaches block-201 state loader
  `0x5545c` on the base object at `device+0x11e0`.
- That loader clears `block+0x40` at `0x554ba`, writes halfword `0x0101` at
  `block+0x38` at `0x554bc` (so byte `+0x39=1`), and calls model selector
  `0x55388`, which writes `block+0x44=1` at `0x553a8` for model 0..5. These
  are exactly the three conditions checked by handler `0x50af8`. Native preset
  application therefore contains its own processing-gate assignment; there is
  no missing standalone host enable packet in this path.
- Constructor `0x591bc` proves the vtable ownership that older notes missed:
  primary vtable `0x10c6bc`, secondary state vtable `0x10c700`. Old sections
  that started at `0x10c6cc`, called `0x50af8` slot `+0x00`, or described
  `0x555b8` as the primary audio work slot are superseded. The actual primary
  work word is `0x10c6f0 -> 0x5f1f4`.
- `0x3c064` is vtable slot `+0x20`, an unrelated lifecycle/cache routine. Its
  `StLb` work attaches the `firmwareVersion` label to the string buffer at
  `device+0x120c`; it is not the `MemP` handler or preset component.

Latest durable result:
`runs/20260831T053346-0700-dual-private-reverb-host/REPORT.md`, with executable
source-bound v2 output and focused test log adjacent. The predecessor private
core identity run remains at `runs/20260831T040258-0700-doubler-private-reverb/`.
The Voice FX gate
seal remains at `runs/20260831T032608-0700-voicefx-gate-recall/`; the native
recall seal remains at `runs/20260831T024633-0700-stat-native-recall/`; the save
seal remains at `runs/20260831T004620-0700-json-stat-save/`.

## Lane boundary

CP34 is an isolated continuation for presets, effects, firmware behavior, and
native control evidence. It does not resume the older driver-transport task
tree, inherit its review queue, or use its terminology as the framing for this
work.

The immutable predecessor is:

`.superpowers/sdd/2026-08-28-preset-effect-persistence/`

That predecessor established dependable host JSON round trips and prepared the
native capture tooling. Do not edit or reseal it from CP34.

## Evidence baseline

Confirmed:

- The device exposes four front-panel slot indexes. In dual mode channel 1
  cycles 0/1 and channel 2 cycles 2/3, and those transitions are readable.
- Universal Control scene data contains four complete slot records and twelve
  user-library records. Factory records include Voice FX state.
- The direct driver can select a slot and can serialize Voice FX parameters.
- Reverb is a working positive control.
- The internal preset component and Voice FX processing object have been
  located in firmware-derived analysis.
- Universal Control's `StorePreset` branch updates the separate library through
  `SetP | Appl | 0 | MemP | PrsM`. Its active device-slot state machine uses
  the same sender with `Stat` 0..3 after first serializing the current channel.
- The driver now refuses `fx_on()` and `fx_off()` because their previous
  reverb-route writes could not activate or deactivate the Voice FX insert.
- `PROTOCOL.md` section 13s is a valid negative for an unidentified numeric
  slot recall followed by a direct block-201 re-arm. It did not verify that the
  selected slot named one of the active factory Voice FX records.
- Factory JSON record 4 is `Slap Echo`, with `voicefx.on=1`, a 150 ms delay,
  feedback 0.25, and mix 0.5.
- The native `Stat` application route reaches the block-201 state loader. It
  sets all three processing-gate conditions before applying the selected model
  state, so a separate Voice FX gate packet is not missing from preset recall.

Not yet proven:

- Physical nonvolatile commit, power-cycle survival, actual front-panel recall,
  and audible Voice FX on the unit.
- Static evidence does not claim that nested `voicefx.on` is copied directly
  into `block+0x44`; it proves the containing component-state load arms the
  processing gate and then delegates the selected model's nested state.

No existing capture contains the now-decoded slot update. A capture is therefore
a validation of physical commit/survival, not a prerequisite for discovering
the packet or the firmware's native recall representation.

The pinned 5.0.0 module is no longer a candidate feature baseline. On
2026-08-30 the user corrected the version premise after directing recovery from
the original Claude-session logs: the newer UC branch removed the Revelator
effects and stream-mixing controls needed by this task, so CP34 must use the
existing 4.x UC artifacts instead. Keep 5.0.0 only as a negative comparison.
This selects the host-software family. UC 4.7.2 now supplies the decoded slot
update; the Voice FX gate and device-resident survival still require proof.

The replacement Linux-native closure is now executable:

- `re/cp34_host_queue_inventory.py` statically analyzes the pinned PE module;
  it never loads or executes vendor code.
- `LINUX-OFFLINE-SHA256SUMS` pins the analyzer, contract, active CP34 records,
  and source vendor module for this continuation stage.
- The DLL has exactly six direct callers of its central queue at
  `0x1800546b0`: the local operation families are `FRst`, `VoFx`, `MemP`,
  `Pari`, `Para`, and the generic `SetP`/`GetP` wrapper.
- It has exactly three RIP-relative calls to the `WinUsb_WritePipe` IAT slot at
  `0x1800e53f0`: `0x1800780db`, `0x18007867d`, and `0x180084ac8`.
- The single queued `MemP` family is generic. It carries both `PrsM` library
  records and `Stat` device-slot records; a separate `Stat` queue caller is not
  expected.
- The generic base method at `0x180055570` is not present in the active device
  subobject vtable `0x18043a678`; its runtime slot `+0x10` is the known
  `SetP`/`GetP` builder at `0x180055410`.

The earlier six-caller census did not resolve the nested dynamic target and
therefore could not support a slot-save negative. The later firmware-native
trace resolves the processing gate inside component-state application; no
replacement packet should be guessed.

### 2026-08-30 official-source refresh

Read-only network research found official product evidence that narrows the
local static negative:

- The [Revelator io24 Owner's Manual](https://pae-web.presonusmusic.com/downloads/products/pdf/Revelator_io24_Owners_Manual_EN_08042022.pdf)
  documents two hardware-resident presets per channel, selection of any two of
  twelve available presets for the front-panel buttons, six user slots per
  channel, and import/export between Universal Control and the io24.
- The same manual documents the preset-manager store flow and identifies the
  Voice-tab power control as the user-visible Voice FX enable/disable seam.
- The current official [Revelator io24 download page](https://intl.presonus.com/products/revelator-io24)
  lists Universal Control 5.1.1.113315. The pinned local artifact analyzed by
  CP34 is from Universal Control 5.0.0.111903.

These sources prove intended device-resident preset assignment and a visible
Voice FX gate at the product/UI level. They do not reveal native transaction
bytes and do not prove behavior on firmware 1.28. The current 5.1.1 listing is
version-history evidence only and is not a CP34 artifact candidate.

The original Claude-session record supplies the relevant 4.x lineage:

- `4.1.0.93124` was named in the downgrade-era investigation; the session
  recorded the expected installer name and metadata but did not obtain it.
- `4.5.0.102825` was verified from the November 2024 milestone release notes
  and documented for the Revelator generation.
- `4.7.2.108537` surfaced as the last 4.x Windows candidate on the Revelator
  download path.

At that checkpoint those logs identified candidate versions, not trustworthy
local artifact paths, and the bounded inventories found only 5.x. A later
authorized artifact run recovered and extracted the exact 4.7.2 candidate. It
is now source-hash bound and compared below; the earlier absence was not a
capability result.

### 2026-08-30 Universal Control 4.7.2 static comparison

The candidate installer is 186,792,552 bytes with SHA-256
`1b5ddd6fd3ad4b93529caf8e5933bcd52b13194bdfa62652292b46ddcd980b95`.
Its extracted `Universal Control.exe` reports version `4.7.2.108537`; candidate
`dspusbdevice.dll` is 4,979,672 bytes with SHA-256
`de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.
The module contains the Revelator io24, Stream Mix A/B, Store/RestorePreset,
VoiceFxOn, and four preset-slot representations.

The first static comparison reproduced six central-queue callers and three
native-writer consumers but stopped one pointer adjustment too early. The
follow-up trace resolves the dynamic `Stat` path through the same `MemP` sender
used by `PrsM`, including snapshot, 500 ms write-through, slot mapping, and the
generic `SetP | Appl(0)` wrapper. The later firmware trace resolves the
component-state processing gate without adding another host sender.

Durable task record:
`runs/20260830T170210-0700-uc472-static/REPORT.md`. The candidate installer and
extraction remain only under `/tmp`; the report and JSON outputs are durable,
but re-running against source after cleanup requires the identical hash.

The remaining factory-recall question now has an offline-executable gate:

- `LINUX-LIVE-MATRIX.md` requires an already-assigned, device-screen-verified
  `Slap Echo`; it never assigns or stores a preset.
- `re/cp34_live_matrix.py` generates the fixed impulse stimulus, validates a
  target-specific restoration ledger, and analyzes two dry brackets, two
  active captures, and a reverb positive control without opening hardware.
- The deterministic stimulus SHA-256 is
  `318786a6af910736dbe8f96d152753884dac6fe360b8ad1e8a685b3077d68142`.
- The ordinary driver shadow has candidate reverb/FX-mix inverse values, but its
  2026-08-23 state is not current-attested and has no explicit assign/master
  rows. It is not yet restoration authority.

The earlier standalone `analyze-slot` delta was reviewed and bounded. The
following paragraph is historical classifier evidence, not a review of the
current-slot procedure or restoration verifier:

- A repeatable audible 150 ms dry/active delta is
  `SIGNATURE_PRESENT` / `REPEAT_150MS_SIGNATURE`, not a `Slap Echo` title or
  model identification.
- The report fixes model identity to `UNRESOLVED` and title verification, live
  readiness, and restoration verification to false.
- A repeatable late tail is `NON_SPECIFIC_LATE_TAIL` and remains inconclusive;
  its source and loaded model are not inferred.
- The focused hardware-free suite passes 37 tests.
- The combined CP34 hardware-free regression set passes 63 tests and 27
  subtests; both pinned DLL inventories reproduce six queue callers and three
  native-writer consumers, and every offline checksum entry verifies.
- This classifier reads already-acquired WAV files only. The later current-slot
  procedure and executable restoration contract are Fix3 offline-sealed and
  independently reviewed clean. Neither creates authority to acquire files or
  touch hardware.

L01 read-only discovery is now partially complete:

- The user authorized USB identity, interface-5 PRESTATE reads, and ALSA
  identity/mapping only on the single connected io24.
- The named target is `AB7C22200355`, USB `194f:0422`, sysfs `1-2`, bus 001
  device 003, `bcdDevice 1.28`.
- One bounded interface-5/alternate-1 claim produced four consistent 503-slot
  JaSt reads. Channel 1 was slot 0 enabled; channel 2 was slot 2 enabled;
  phantom was off on both inputs.
- ALSA exposed `R24` card 2 device 0 with six-channel S32_LE/24-bit 48 kHz
  capability; no playback/capture stream was opened.
- Durable report:
  `runs/20260829T010329-0700-l01-readonly/L01-REPORT.md`; snapshot SHA-256
  `4f114b8a4e215e2345b196543bfa7ce020b4de9ccba6a21b4365a9432c3182e4`.
- Operator-screen title/preset mode, the physical capture-channel map, and a
  current complete restoration baseline remain unresolved. Numeric slots are
  not title evidence.

## Corrections carried into CP34

- Slot selection is not preset-content storage.
- A successful reply, UI toast, or stored parameter blob is not audible-effect
  evidence.
- Voice FX is a channel processing path. Reverb-style return-bus behavior must
  not be assumed as proof of Voice FX operation.
- Do not send guessed tags or patch firmware to compensate for missing evidence.

## Authority and platform boundary

The user has directed this project to resolve both outcomes and has corrected
the platform assumption: Linux is the only host. Do not block the ordinary
continuation on Windows or macOS.

The recorded 2026-08-29 L01 authorization included only USB identity,
interface-5 PRESTATE reads, and ALSA identity/mapping on the connected io24. It
did not include audio playback/capture, front-panel actions, mapped writes,
preset/effect operations, L02-L07, firmware flashing, reset, DFU, installation,
driver staging, network use, access to `/home/ajuntanaga/.wine-io24`, or replay
of a newly decoded transaction. Wine remains prohibited. Stop at or below 10
percent battery.

On 2026-08-30 the user separately authorized network/online processes for CP34.
That permits network access when it is needed for this work. It does not grant
USB/device access, interface claim/detach, transfers, ALSA playback/capture,
front-panel actions, preset/effect operations, firmware actions, staging, or
access to `/home/ajuntanaga/.wine-io24`. Device connection is state, not live
authority. This checkpoint reconciliation required no network access.

The supported-host `CAPTURE-MANIFEST.md` was superseded without execution. The
active procedures are `LINUX-MANIFEST.md` and `LINUX-LIVE-MATRIX.md`.
`PRESTATE.md` now records the bounded L01 identity/state result and the
stale-shadow limitation. `LINUX-LIVE-MATRIX.md` also records the title-free
classifier as offline-only. No authority for L02-L07 or a slot survey is
recorded.

## Exact continuation

1. The current-slot survey implementation and six-row core-stage
   `CURRENT-SLOT-SURVEY-STAGE.sha256` are at Fix3. Final recorded broad
   verification was 104 tests plus 38 subtests, exit 0; its stage verifies 6/6
   and its then-current offline manifest verified 23/23. The later 4.7.2
   extension has a fresh 104-test/38-subtest result in 181.84 seconds, a 10/10
   source-bound run manifest, and an expanded 27/27 offline manifest. Both
   pinned 5.0 inventories and both candidate 4.7.2 inventories reproduce. Fix3
   binds derivatives to raw frozen-channel samples, derives
   JaSt summaries from canonical raw JSON, uses candidate-scoped interim seals,
   binds the actual run path to the plan, and enforces five-arrival/one-lag
   mapping and audible ordering. Its scoped independent re-review is clean.
   Passing tools, templates, tests, manifests, or review does not authorize
   hardware.

   The 4.7.2 scoped independent review also reproduced the source identities,
   candidate JSON outputs, pinned topology, representative disassembly paths,
   analyzer contracts, all three checksum gates, and a 104-test/38-subtest
   broad run in 310.87 seconds, exit 0. It found no Critical or Important
   issues; its sole Minor seam-bounding wording note is corrected in the run
   report. That review likewise grants no live authority.

   Revision 1 is rejected. Revision-2 Fix1 and Fix2 are historical and
   superseded by the clean Fix3 seal. The current review gate is complete, but
   no live authority follows from it.
2. Do not describe device-resident custom store/assignment as product-wide
   unsupported. Official documentation establishes the intended feature. The
   feature-bearing 4.7.2 candidate is now identified and statically compared;
   it preserves the same relevant Store/Restore, `MemP`, `Stat`, Voice FX, queue,
   and writer shapes as pinned 5.0 without exposing a distinct missing sender.
   This is source-bound negative evidence for the compared seams, not an
   observable outcome or permission to implement a guessed sender.
3. Keep the host JSON predecessor as the working Linux preset round trip, while
   keeping it explicitly separate from device-resident persistence.
4. L01 identifies target `AB7C22200355`, its current numeric slots, readable
   preset-enable state, and ALSA card. Obtain operator transcription of the
   currently visible title and preset mode without inferring either from the
   numeric slots. The physical channel A/B map and exact restoration values are
   still unknown. A no-write current-slot survey procedure and executable
   restoration contract now exist, are offline-sealed, and have a clean
   independent Fix3 review. They remain ineligible for execution without the
   separate exact authorization in step 6.
5. The current shadow is stale/unattested. A live run is ineligible unless the
   user can attest its validity since the last power cycle/editor change or
   separately authorizes a new known-baseline and restoration boundary.
6. The L01-only authority has been exercised. Do not execute L02-L07 or the
   current-slot survey on it. Although the Fix3 review is clean, any live run
   still requires a new, separately exact authorization. For
   the title-verified matrix, separate exact authorization must name serial
   `AB7C22200355` and permit the physical audio path, ALSA playback/capture,
   manual Preset-button actions, exact validated mapped writes, evidence
   directory, and restoration. The no-write current-slot survey likewise
   requires its own exact named-run authorization, including the source,
   stimulus hash, physical path and inverse, capture identity, bounded JaSt
   reads, two long manual toggles per attempted candidate, evidence directory,
   audible replay, battery floor, and stop conditions. Offline `VALID`,
   `MAPPED`, `SIGNATURE_PRESENT`, or `RESTORED` fixture results are not that
   authorization.
7. If an authorized factory recall makes Voice FX audible, preserve that result
   without mislabeling it as custom preset storage. If it does not, retain the
   positive control and record an honest negative.
8. Seal CP34 only if both original observable outcomes pass or the user accepts
   a capability-negative closure for an outcome the firmware/vendor pair does
   not expose.

Do not call either outcome resolved until the observable checks in step 8 pass.

## 2026-09-08 live effects continuation

The user authorized two serialized live stages on serial `AB7C22200355` with
battery above 10 percent and stereo link off. Stage 1 is complete: shared
block-202 Plate reverb at 35 percent Channel-1 send and 0 dB Main return was
audible to the user both with a native control connection held open and after
that connection closed while the io24 remained powered. Readable protected
state did not drift. This proves the configured shared reverb survives Host
disconnection while powered, but does not test a power cycle.

Stage 2 remains authorized: isolate the private path by disabling shared
reverb, overwrite Channel-1 Slot 2 / global slot 1 with the complete factory
`Reverb` record, separately select and enable it, obtain Host-open and
Host-closed listening evidence, then restore MAIN in Channel-1 Slot 1 / global
slot 0 and directly restore its exact strip state while preserving the user's
33 dB gain. Stop on Channel-2 drift, link change, or Voice FX ownership
mismatch. No power cycle, Wine, firmware, install, publication, or Obsidian
write is authorized.

Stage 2 was executed through the Host-open listen and then stopped: the
complete private-Reverb record was sent to global slot 1, selected, and enabled,
but the user reported Channel 1 slot 2 was dry. Host-closed listening was not
run because the effect was already inaudible. MAIN was restored to global slot
0 with its exact direct strip state and 33 dB gain; final readable Channel-2,
link, and Voice FX ownership state was unchanged, and the connection was
closed. User listening confirmation of MAIN is pending.

The user then answered `Yes, I believe so`, which is provisional listening
confirmation of the direct MAIN restoration only. It is not stored-slot recall
or power-cycle evidence. Offline inspection found the current durable Host
shadow contains both Channel-1 FX mix zero and preset enabled true. Default
preset replay quarantines the enable while retaining the zero-mix call, and an
explicit selector-inclusive replay currently orders enable before that mix.
Today's repeatable live coupling means either replay can finish with Channel 1
bypassed. No startup preset exists, so automatic startup replay is not
implicated. The float `Para/4` FX-mix and integer `Pari/4` preset-enable wire
routes remain source-distinct; their exact-zero coupling and the smallest safe
Host transaction are queued for the dedicated Claude peer before any fix.

Pinned-firmware disassembly subsequently proved they converge on one state.
The `JaSt` base serializer at `0x6004df78` reads internal float ids 3/4 and sets
bits 5/6 exactly when `input1FxMix`/`input2FxMix` equals zero. Integer wire 4
converts Boolean false/true to float 0/1 and invokes the same float dispatcher.
Therefore preset enable is a Boolean alias for the per-channel preset/effects
wet-dry value. The Host's independent preset-enable and reverb-send controls,
shadow keys, quarantine, and replay assumptions are incorrect. This directly
explains why a Channel-1 send-zero isolation disabled MAIN/compression and why
enable=true restored it at full mix. The test-first canonicalization/UI cleanup
proposal is in the dedicated Claude queue; no implementation or further live
action has occurred.

This finding reopens Full Parameter Verification Task 5. Its wheel/module/
entry-point evidence remains valid, but publication readiness does not: the
Host can currently persist and replay contradictory representations of one
audio control. The 750-row matrix and Task-5 checkpoint are stale until the
alias model, Host UI, regression suite, documentation, and same-52-file Claude
review are corrected and rerun.

An additional live defect is open: `reverb_off()` preserved readable state,
but `set_fx_mix(1, 0.0)` changed flags from 385 to 417, currently decoded as a
Channel-1 preset bypass; `set_preset_enabled(1, True)` returned it to 385. Do
not guess whether this is a setter mapping defect or a shared flag/assignment
semantic. Reconcile it with Claude and source/live evidence before changing the
Host API. The private-Reverb activation gate is likewise unresolved.

## Current sealed checkpoint

Fix3 supersedes Fix1 and Fix2. Final post-fix broad verification returned 104
passed and 38 subtests in 279.00s, exit 0. Stage 6/6 and offline manifest 23/23
verify; stage hash
`8b78a3fcf8abc06bdf702447325e8b1da3920a10f31e4dffe4bd2fff2c6acf69`.
Independent Fix3 re-review is clean. No live authority is granted.

The historical Fix1 current-slot gate was 39 passed and 9 subtests in 129.12s,
followed by a 102-pass/36-subtest broad gate and stage hash
`c4fc43129e998d2626670ef32ddd1a6f169c7a4613788899b1910b7db1109410`.
Its pending-review state and hashes are superseded by Fix3 and are not the
current continuation gate.

The 2026-08-30 resume reconciliation re-verified the six-row stage and 23-row
offline manifest before this status edit. BAT0 was 16 percent and charging by
passive sysfs. No USB, device, ALSA, Wine, or network action occurred.

The later 4.7.2 static continuation is recorded at
`runs/20260830T170210-0700-uc472-static/`. It is a separate offline evidence
stage and does not supersede the independently reviewed Fix3 current-slot seal.
Fresh broad verification returned 104 passed and 38 subtests in 181.84 seconds,
exit 0; its source-bound manifest verifies 10/10, the unchanged current-slot
stage verifies 6/6, and the expanded offline manifest verifies 27/27. Source
retention is temporary. Scoped independent review is clean after independently
reproducing the evidence and a 104-test/38-subtest broad run in 310.87 seconds,
exit 0; it found no Critical or Important issues. Final post-review controller
verification returned 104 passed and 38 subtests in 171.02 seconds, exit 0;
BAT0 was then 98 percent and charging via passive sysfs. No live authority
follows from this stage, and both CP34 observable outcomes remain unresolved.

## Exact next authorization gate

The authorized 4.7.2 artifact gate is complete through the compared static
seams. Do not continue its historical Wine branch: current project instructions
prohibit Wine during io24 work, and `RUNNING`/alive state was not Universal
Control synchronization. Do not clean up or move the retained `/tmp` installer
and extraction without a separate user choice.

Additional exact 4.1.x or 4.5.x source artifacts, if supplied, can receive the
same static-only comparison under a separately named artifact gate. They are
not inferred from the 4.7.2 result. Separately, before any live current-slot
survey, the user must provide one new authorization that names all of the
following without relying on the device merely being connected:

1. Target serial `AB7C22200355` and one run class: the no-write current-slot
   survey or the title-verified L01-L07 matrix.
2. The exact source and deterministic stimulus hash, physical audio path and
   inverse, ALSA playback/capture endpoints, and evidence directory.
3. Every permitted live action: bounded JaSt reads, specified manual Preset
   button actions, audible replay, and, only for the title-verified matrix, the
   exact validated mapped writes and restoration actions.
4. Operator transcription of the currently visible preset title and preset
   mode, or an explicit statement that the run is title-free and may conclude
   only `UNRESOLVED` model identity.
5. Either attestation that the restoration shadow is valid since the last power
   cycle/editor change or permission to acquire a new known baseline with an
   exact restoration boundary.
6. Stop conditions: abort at or below 10 percent battery, on target or capture
   mismatch, unexpected state, restoration failure, or unavailable positive
   control. No firmware, reset, DFU, installation, staging, guessed command,
   or access to `/home/ajuntanaga/.wine-io24` is included.

Until those fields are supplied together, the next executable state remains
offline-only despite network authorization and device presence.

## 2026-09-08 processing/effects-mix correction candidate

The dedicated Claude peer resumed successfully after its 10:00 AM reset on
UUID `a764bfc8-6fec-453f-9289-92ace5f16ce5`, with no permission error and the
same authorized 52-file disclosure boundary. It independently agreed that
wire-4 Boolean enable and float mix must be one canonical `set_fx_mix` state,
endorsed the conservative legacy migration and fail-closed Hot Key contract,
and agreed Task 5 must stay reopened during repair.

The candidate implementation passes 95/95 focused tests and 181/181 affected
Host/stage tests. Host state now stores one processing/effects scalar per
channel; legacy conflicts cannot replay a stale zero over explicit enable
intent; Hot Key retains exact fractional values and refuses unknown enabled
values; the GTK duplicate send/enable controls are replaced by one explicitly
write-only mix; registry reads require matching device identity. The matrix is
now 748 atomic rows because the two duplicate `preset_enabled` rows were not
real independent parameters. Final package/matrix/checkpoint verification and
same-UUID Claude review are pending. No live action occurred in this repair.

Final offline closure is clean. The same-UUID review found no implementation
defect. Release packaging passes 1/1 and the affected Host/stage suite passes
181/181. A fresh uninstalled wheel contains 15/15 modules and 7/7 console entry
points, imports all modules from its own archive in an empty directory, and
runs `python -m io24_scene`; wheel SHA-256 is
`1d15eb5e297f721d78837fa539ee07443bb2039d0e593e02f5fb6e286ea6f44c`.
Two regenerated 748-row matrices match the checked-in file at SHA-256
`2a08282d7017c4724c2240dbd5704d06319f2f961d7f5bb7ade16fb65e692300`.
Task 5 is complete for offline publication readiness only. The private Reverb
slot result remains dry/unresolved; no slot-body readback, power-cycle proof,
publication, installation, Host launch, USB/audio action, or Obsidian write was
performed by this repair.

## 2026-09-08 Host refinement closure

The user authorized an exact 53-file Anthropic snapshot, adding `io24_mbc.py`,
for dedicated peer review. On UUID
`15978222-d591-4549-9876-21c04f741e14`, Claude found two real multiband child-
process lifecycle races. Both were reproduced by failing regressions, fixed,
and closed in the next serialized turn. Separate same-UUID reviews of Host JSON
and GTK adoption, spectrum/EQ/feedback, and Mixer/Presets/claims found no
functional defect. The lone stale `Hot Key` guide phrase was corrected.

Host JSON now strictly validates and preserves the complete four-band
multiband chain while keeping it out of device-slot, preview, and reconnect
claims. Continuous controls do not emit per-step completion toasts. Spectrum,
EQ rack, Mixer, and Presets behavior implement the approved refinements. The
offline Host/stage suite passes 216/216 with `ResourceWarning` elevated to an
error. The final uninstalled 235718-byte wheel has SHA-256
`151f7c2adbffd57484a13494ded087e1a754609f67ec26e0e268c08a126e36ef`,
contains all 15 modules and seven entry points, imports from its own archive in
an empty directory, and runs `python -m io24_scene`. Two new 748-row matrices
and the checked-in artifact are identical at SHA-256
`b0c2b9ba42b879843d310024f22bc8736166311a2a97aa141b88524f36ca12a1`.

Task 5 is complete only for offline Host correctness and package readiness.
The interface was unplugged and no Host, device, USB, audio, Wine, install,
publication, Git, or Obsidian action occurred. Live visual acceptance, private
Reverb activation/audibility, and actual device persistence remain separate
future authorization gates.

The final same-UUID closure turn reviewed refreshed snapshot
`2026-09-08T15:07:43-07:00`, verified the documentation correction and all
disclosed closure claims against the earlier source slices, and reported no
substantive finding. Claude did not claim independent hash recomputation or a
local test rerun.
