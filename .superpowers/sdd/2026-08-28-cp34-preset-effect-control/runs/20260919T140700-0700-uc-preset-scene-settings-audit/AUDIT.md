# UC 4.7.2 preset, scene, and settings audit

Date: 2026-09-19

Scope: compare the current Linux Host working tree with retained Universal
Control 4.7.2 artifacts for preset saving, scenes, and settings. The VM was
opened offline without USB passthrough. No device, firmware, preset, or audio
operation occurred.

## Post-audit repair

The findings below describe the pre-repair tree inspected by this audit. The
same 2026-09-19 working session subsequently repaired every item for which the
retained UC/device evidence supplies a faithful mapping:

- the scene planner now validates and applies every supported top-level UC
  section, with 94–97 operations for each retained scene;
- exact alternate EQ, singleton VoiceFX, shared reverb, DSP amount, the complete
  routing matrix, source/output mutes, Host solo, bus masters, global settings,
  and one-shot mirror-main are included;
- the GTK Host exposes scene load, Channel Mute Sync, return-source mute, and
  output-bus mute;
- known device-block Load selects the block and directly replays its retained
  Fat Channel plus VoiceFX record, while unknown blocks remain selection-only;
- device store and load wording now preserves the
  `WRITE_SENT_UNVERIFIED`/Host-assisted VoiceFX boundary.

Mono-source pan, stereo width, exact `FXA`, `dawpostdsp`, output mono, writable
names, and a persistent mirror latch remain explicitly unsupported because no
proven io24 wire representation exists. They are reported rather than silently
substituted. The repair was hardware-free; no USB/device action was added to
this audit run.

Post-repair verification passed the 209-test focused suite. Full io24 discovery
ran 655 tests and exposed one static scene-copy assertion; after that copy-only
correction, its affected preset-page, no-embedded-description, and
deterministic-matrix checks passed 27/27. CLI dry runs validated the retained
scenes at 97/94/97 operations and 46 typed omissions each, with nothing sent.

## Result

The retained evidence is sufficient to define the io24 device data model, but
it did not preserve every UC screen. Today’s run preserves the UC application
menu and all five application Options tabs. The earlier connected-device run
preserves the io24 overview, device editor, expanded Fat Channel, preset menu,
and VoiceFX editor. A connected-device gear/settings page and the complete set
of save/restore dialogs are not preserved as screenshots.

The substantive implementation finding is:

- user channel presets and Host snapshots are broadly complete for their
  intended scopes;
- device-slot transport is not equivalent to a verified UC save/recall, and
  VoiceFX remains Host-assisted after slot selection;
- `io24_scene.py` is not a UC-complete scene importer. It is stale relative to
  backend support already present in the Host and ignores whole scene sections;
- device-relevant settings are mostly represented, but several UC fields remain
  partial or absent. UC application-shell preferences are a separate scope.

## Evidence retained

- Authoritative device vocabulary:
  `re/uc_component_model/dspusb_component_model.xml` and
  `re/uc_component_model/dsp_fx_params.xml`, extracted from UC 4.7.2's retained
  `studiolivepanel.dll`.
- Three complete UC scenes:
  `runs/20260914T031459-0700-native-slot-builder/backup/{B A S E,Main,Piano
  Accomany}.scene`.
- Exact UC binaries:
  `runs/20260906T010449-0700-uc472-save-assign-ui-route/extracted/` and the
  retained `dspusbdevice.dll` used by the alternate-EQ designer.
- Connected-device visuals:
  `runs/20260917T145627-0700-uc472-audio-suppressed-rerun/uc-launched-01.png`,
  `uc-device-page-01.png`, `uc-fat-channel-expanded-01.png`, and the VoiceFX
  screenshots in that directory.
- This directory contains the newly retained offline application settings
  captures and this audit.

## Preset-saving audit

### User channel presets

Status: pass for a UC-style channel preset, not a whole-device scene.

`~/.config/io24/user-presets.json` stores one selected channel's complete Fat
Channel state plus the selected singleton VoiceFX model/state. The record is
built from a complete factory base, replaces every Host-owned field, supports
Standard/Passive/Vintage EQ, validates VoiceFX, refuses a damaged store, and
writes through a temporary file plus rename. Mixer buses, global reverb, and
global device settings are intentionally outside this record.

### Host snapshots and last session

Status: pass with a non-atomic replay limitation.

The snapshot contains readable `Appl` values, the durable shadow of Host writes,
and Host-only features. Ordinary snapshots quarantine physical device slot and
preset-mode calls. Save is durable (`fsync`, replace, directory `fsync`). Host
features are validated before the first setter, but the subsequent device
setters are sequential and failures are reported rather than rolled back, so a
late failure can leave a partially applied snapshot.

### Device blocks

Status: transport implemented in the dirty working tree; device result remains
unverified and VoiceFX is not standalone.

The current working tree exposes **Save to device, block 1/2**, validates a
complete firmware-native v2 body, refuses to overwrite the selected block, and
records an identity-bound `WRITE_SENT_UNVERIFIED` receipt after transport. That
receipt is not body readback or durable-commit proof. The committed HEAD and
README still describe this action as disabled, so implementation and published
documentation currently disagree.

The controlling device result remains: Fat Channel state is audible without a
Host, while VoiceFX fields may be present in a saved record without becoming
audible on device-only recall. The GTK slot path explicitly pushes the locally
known global VoiceFX state after selecting a known slot. Slot selection also did
not re-apply the stored body during the retained live test. UI strings such as
“Saved” and “Recalled” therefore overstate what the Host has verified.

## Scene audit

All three retained scenes contain these top-level sections:

`global`, `line`, `return`, `fxreturn`, `aux`, `main`, `fx`, `presets`

Current dry-plan result:

| Scene | Planned calls | Reported skips |
| --- | ---: | ---: |
| B A S E.scene | 36 | 18 |
| Main.scene | 32 | 19 |
| Piano Accomany.scene | 36 | 18 |

`io24_scene.py` processes only `global` and `line`, then reports preset names.
It entirely ignores `return`, `fxreturn`, `aux`, `main`, and `fx`, including the
scene's shared reverb and mixer/output state.

The planner also skips fields whose setters now exist: Passive/Vintage EQ,
VoiceFX, pair pan, solo, DSP amount, preset mode, mirror-main behavior, and
shared reverb. Its “no driver support yet” and “exact coefficient builder is not
recovered” messages are stale. The README simultaneously claims alternate EQ is
applied and later says the simplified form is skipped; the implementation skips
every alternate EQ.

Fields still genuinely absent or incomplete are `dawpostdsp`, stereo width,
channel/user names, output mono, exact per-input `FXA` reverb-send mapping,
per-output mute semantics, and persisted `auxMuteMode`. There is no GTK scene
import/export UI. Apply is sequential, catches individual failures, and has no
prevalidated all-or-nothing plan or rollback.

## Settings audit

### Device-relevant settings already covered

- PipeWire rate/quantum equivalents for UC sample rate/block size; io24 clock
  source is fixed Internal rather than a missing selector.
- Main and phones levels, monitor blend, phones source and mute.
- Input gain, phantom, mute, link, sends/assigns, bus masters, Host solo, and
  mirror-main as an explicit copy action.
- Processing assignment, DSP amount/bypass, output delay/bus.
- Fat Channel, all three EQ models, shared reverb, and all six VoiceFX models.
- Preset button mode, slot selection, and native body construction, with the
  verification limits above.

### Partial or missing device-relevant settings

- `auxMuteMode`: inferred backend setter only; no UI, snapshot persistence, or
  scene mapping.
- `aux1_mirror_main` / `aux2_mirror_main`: one-shot Host copy rather than UC's
  storable state, and skipped by scene import.
- `pan`: supported as Host capture-pair balance, not a proven mono-source device
  pan; `stereopan` width is absent.
- `dawpostdsp`, exact `FXA`, output `mono`, user/channel/mix names, and full
  output mute semantics are absent.
- Automatic gain is a Host feature, not a replay of UC's device parameter.
- Main mute is readable but has no proven writable parameter.

### UC application-shell settings

The VM recapture shows: Always On Top, Run at Startup, language, Options, Open
Settings Folder, update/network/streaming/OBS actions; and Options tabs for
General, Appearance, Network MIDI, WDM Setup, and AVB. General contains language,
computer nickname, and the Windows PreSonus power-plan toggle. These are UC
application, Windows, or network preferences rather than io24 DSP/mixer state.
They should be documented as intentionally out of Linux Host device-control
scope, not counted as missing protocol support. WDM device configuration was
unavailable because this audit deliberately used no USB passthrough.

## Verification

- Focused hardware-free suite: 230 tests passed.
- `git diff --check`: clean.
- No USB/device operation in this audit.
- VM retained its existing 14 GiB `MemoryHigh` / 16 GiB `MemoryMax`; no increase
  was needed. Host ended with about 21 GiB available and zero memory PSI.
- Guest received clean ACPI `system_powerdown`; `qemu-img check` reported no
  errors.

## Repair order at audit time

1. Replace the stale scene planner with a schema-driven, prevalidated mapping
   that covers every supported top-level section and emits typed reasons only
   for genuinely unsupported fields.
2. Add UI/persistence/scene support for `auxMuteMode`, stereo width, names,
   output mono/mute, `dawpostdsp`, and exact `FXA` as each mapping is proven.
3. Reconcile device-save/selection wording and docs with the verified boundary:
   native transport receipt, standalone Fat Channel, Host-assisted VoiceFX.

## Capture hashes

```text
ae34738eea7450746c14b5cab03902534951aa848261e92da6da52f2520b118b  io24-uc-audit-menu.png
96505a9a8c55b43acd3c5ada8e2adc6ce46d8ac1094a059abcc628e7fa25c7cb  io24-uc-audit-options-appearance.png
b2b8c6009dbe3692f0f162ec79ae324aa8d3b0e7feeaa3d4dbf91376c8c6ccd5  io24-uc-audit-options-avb.png
2929b166085e532bd15b1a22fdf6d7c7cba0cad7199844c6d426d9d791f2bfb6  io24-uc-audit-options-network-midi.png
f71d600b0b7445e33e313283506dbc0c15d4ad9bccd6e5014dc752c611499edc  io24-uc-audit-options-wdm.png
31af241edf045edeb2de550730a2d8d1540935a3597a4ec4fb6983b830447384  io24-uc-audit-options.png
f0ecbad43c10e91d3cf7eb94015597e94691c995f27e2eaaede0dcb2399047d4  io24-uc-audit-settings-open.png
a86219c1da080e3f828b89d3f8011748ec159c2d1d5dbece17cf91e1b7617a15  io24-uc-audit-settings-submenu.png
5bd5842f31de0139b377c3b330a10b49dda5229d9c27dddb92fefac11d443f45  io24-uc-audit-uc-home.png
```
