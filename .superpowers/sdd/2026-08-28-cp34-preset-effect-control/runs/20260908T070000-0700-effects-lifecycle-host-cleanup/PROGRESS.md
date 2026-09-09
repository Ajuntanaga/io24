# Progress

## Completed offline

- Separated the production labels for block-202 shared reverb and block-201
  Voice FX/private reverb.
- Changed the switches and status text so model/engine writes are not presented
  as proof of an audible or standalone effect.
- Removed the obsolete structural-lane explanation, stale `fx_save_both`
  branch, and two dead Channel-2 experiment GTK methods.
- Added a source-level regression which was RED before the edit and GREEN
  afterward.
- Appended the decision and result to Claude's durable inbox before and after
  implementation. The attempted peer turn timed out with zero tokens and is
  recorded as unavailable.
- Added a crash-safe local complete-record registry keyed by global slot. It
  stores the owning physical channel, complete body, canonical hash, source,
  timestamp, transport counts, and the exact provenance
  `HOST_WRITTEN_DEVICE_READBACK_UNAVAILABLE`.
- Added `save_known_device_slot`, which validates the registry and record before
  transport, records only after the slot-write call returns, and cannot select,
  enable, recall, or directly apply a slot.
- Added the new public API to the existing device-slot matrix row after the
  generator correctly rejected the un-inventoried method.
- Accepted Claude's finding that ordinary Voice FX edits re-sent the
  permutation-sensitive owner assignment. The worker now sends that assignment
  once per connected device/target and re-sends only for a real target or
  device change. The UI discloses the exposed-slot exchange behavior.
- Bumped the registry to schema v2 and bound every entry to the connected
  serial, VID/PID, and firmware `bcdDevice`; missing identity fails before
  transport.
- Added the production GTK complete-record workflow. Any complete factory
  record can be written to the other slot in its selected physical channel
  after an explicit overwrite confirmation. The action performs only the body
  write and local registry commit.

## Verification

- Expanded Host/effects/stage suite: 176 passed with `ResourceWarning` elevated
  to error.
- Matrix: 750 rows.
- Checked-in matrix and two independent regenerations are byte-identical.
- Matrix SHA-256:
  `de1ff7fd14b1555e081c0beccd23490bd0c3a518a39d7759be5ee068cedc1ec7`.

## Still open

- Host-running live shared-reverb path verification: engine, selected input
  send, selected return, and listening evidence.
- Host-closed while-powered verification for shared reverb.
- Voice FX/private-reverb device-slot save, select/enable/recall, Host-closed
  listening, and later power-cycle persistence verification.
- Claude review of the corrections and GTK store workflow. The first successful
  fresh-UUID 52-file turn found and explained the two defects above. Its
  immediate follow-up returned an explicit 429 and is unavailable until the
  stated 10:00 AM Pacific reset.

No live action occurred in this run.

## Live Stage 1: shared reverb

Live Stage 1 subsequently completed against serial `AB7C22200355` at 96
percent battery with stereo link off. Shared block-202 Plate reverb was sent
with a 35 percent Channel-1 send and 0 dB Main return. The readable protected
state remained unchanged, including Channel 2 and Channel-1 Voice FX ownership.
The user reported the Plate reverb audible both while the native control
connection was held open and after that connection was closed with the io24
still powered. This is positive audible evidence for while-powered standalone
shared reverb; it is not power-cycle persistence evidence.

## Live Stage 2: private Reverb and restoration

Fresh preflight passed at 95 percent. A one-call diagnostic found that
`reverb_off()` preserved the exact readable baseline, while
`set_fx_mix(1, 0.0)` alone changed flags 385 to 417, currently decoded as
Channel-1 preset disabled. Re-enabling Channel 1 restored the baseline. This is
an open Host control-mapping defect; no API correction is justified until the
flag semantics and Para/Pari 4 interaction are reconciled with source, live
evidence, and Claude.

With shared block 202 off, the complete unmodified 842-byte factory `Reverb`
record was sent to global slot 1, recorded as `WRITE_SENT_UNVERIFIED`, then
selected and enabled on physical Channel 1. The user reported `Channel 1,
slot2: dry` while the native control connection was open. Thus complete record
write plus selector/enable did not activate an audible private effect. The
redundant Host-closed listen was not run.

MAIN was then restored by selecting global slot 0, enabling it, and directly
applying its pinned comp-first Standard compressor, four-band Standard EQ,
limiter, digital HPF bypass, and separate preamp HPF-off state. Final readback
was Channel 1 slot 0 enabled at 33 dB; Channel 2 remained slot 2 enabled at
24.287769317626953 dB; link remained off and Voice FX ownership remained on
Channel 1. The connection was closed. Shared reverb remains off. User listening
confirmation of MAIN restoration is pending.

The user subsequently answered `Yes, I believe so`, providing provisional
listening confirmation that the direct MAIN restoration sounds restored. This
does not establish device-slot-byte recall or power-cycle persistence.

Offline inspection then found a concrete Host persistence hazard. The durable
shadow currently contains both Channel-1 `set_fx_mix(..., 0.0)` and
`set_preset_enabled(..., true)`. Ordinary preset replay quarantines the enable
but retains the zero mix; selector-inclusive replay orders enable before the
default-phase mix. Either can reproduce today's zero-mix/preset-bypass outcome.
No startup preset exists, so there is no automatic startup replay implicated.
The wire mapping remains source-confirmed and distinct; root-cause semantics
and the correct Host transaction are queued for Claude before implementation.

Pinned-firmware disassembly then proved the root cause. The `JaSt` base
serializer reads internal float ids 3/4 (`input1FxMix`/`input2FxMix`) and sets
flags bits 5/6 exactly when each value equals zero. Integer wire 4 converts its
Boolean to float 0/1 and dispatches through the same float-parameter handler.
Thus `presetEnable` is a Boolean alias of the per-channel FX/preset wet-dry
control, not independent state. The current Host's separate reverb-send and
preset-enable model is wrong; shadows can retain contradictory calls and
zeroing the supposed reverb send bypasses compression/Fat Channel. A test-first
canonicalization and UI cleanup proposal is queued for Claude; no code or live
state was changed by this offline finding.

## Processing-mix correction candidate

The post-reset dedicated Claude turn completed successfully on UUID
`a764bfc8-6fec-453f-9289-92ace5f16ce5` against a verified 52-entry snapshot.
Claude independently endorsed scalar canonicalization, conservative legacy
migration, exact-value Hot Key capture, the merged UI, and reopening Task 5.

The implementation is now test-first GREEN in 95 focused tests and 181 affected
Host/stage tests. `set_preset_enabled` delegates to `set_fx_mix(0.0/1.0)` and is
no longer independently shadowed or quarantined. Legacy conflicts preserve an
explicit bypass intent and label inferred-full migration. Hot Key capture keeps
an exact positive mix, records readable bypass as exact zero, and refuses an
enabled channel whose exact scalar is unknown. GTK exposes one disabled-until-
established processing/effects mix per channel and no duplicate enable switch.
Registry reads now require matching current-device identity.

The atomic matrix is intentionally 748 rows: the two false per-channel
`preset_enabled` parameter rows were removed and their APIs are indexed on the
two real `processing_mix` rows. Documentation now distinguishes that scalar
from the global block-202 algorithm wet mix and FX returns. Final matrix double
regeneration, wheel verification, checkpoints, and Claude re-review remain
pending. No USB, audio, Host launch, slot write, or other live action occurred.

## Final offline verification

The same dedicated Claude UUID reviewed the refreshed 52-file candidate and
found no correctness defect. Release packaging passes 1/1 and the affected
Host/stage suite passes 181/181. A fresh wheel was built without installation;
it contains 15/15 modules and 7/7 entry points, imports each module from the
archive in an empty directory, and executes `python -m io24_scene`. Wheel SHA-
256 is `1d15eb5e297f721d78837fa539ee07443bb2039d0e593e02f5fb6e286ea6f44c`.
Two final 748-row matrices match the checked-in artifact byte-for-byte at SHA-
256 `2a08282d7017c4724c2240dbd5704d06319f2f961d7f5bb7ade16fb65e692300`.
Task 5 is complete for offline publication readiness. Private Reverb activation
and device-slot recall remain unresolved; no new live or publication action
was taken.

## Host refinement closure

The authorized peer boundary is now exactly 53 files, including
`io24_mbc.py`. Dedicated Claude UUID
`15978222-d591-4549-9876-21c04f741e14` found two multiband lifecycle races;
both were reproduced RED, fixed, and closed by its next serialized review.
Later JSON/GTK, spectrum/EQ/feedback, and layout/claims slices found no
functional defect. Its only remaining documentation finding, the stale
`Hot Key` guide phrase, is corrected.

Final offline evidence is 216/216 tests with `ResourceWarning` elevated to an
error; a fresh uninstalled wheel at SHA-256
`151f7c2adbffd57484a13494ded087e1a754609f67ec26e0e268c08a126e36ef`
contains 15/15 modules and 7/7 entry points and passes isolated imports plus
`python -m io24_scene`; two fresh 748-row matrices and the checked-in artifact
match SHA-256
`b0c2b9ba42b879843d310024f22bc8736166311a2a97aa141b88524f36ca12a1`.

Task 5 is complete offline. No Host launch or device/audio action occurred;
live visual acceptance, private Reverb activation/audibility, and device
persistence remain unresolved and separately authorized.

The final same-UUID turn reviewed the refreshed 53-entry snapshot created
`2026-09-08T15:07:43-07:00`, verified the guide correction and closure claims
against the four earlier slices, and reported no substantive finding. It did
not claim independent hash recomputation or a local test rerun.

## Mixer, pan, and notification refinement closure

Routine per-control bottom toasts are removed across Host tabs; the GTK cached-
reapply feature is fully removed while connection feedback remains. Mixer slot
state now uses `S1`/`S2` plus slow/fast reduced-motion-aware blue breathing and
an empty bypass ring; bus labeling/meters are consolidated; the fixed preamp
label is `HPF`; and Channel 1/2 pan independently through a separate opt-in
PipeWire capture-to-playback chain whose state persists only in Host snapshots.

Claude UUID `15978222-d591-4549-9876-21c04f741e14` confirmed the two accepted
corrections and explicitly withdrew its zero-based-slot speed finding. Fresh
offline gates are package 1/1, affected Host suite 172/172, a 236508-byte
uninstalled wheel at SHA-256
`58719a27dd9b2505ff0baad081042fca2a24da5007fee29399e630d85365a77f`
with complete modules/entry points/isolated imports/`python -m io24_scene`, and
two matching 748-row matrices at SHA-256
`84e0b3fbe7e9aa6ee736a8f52db6da50732013e5a482e33fcc0c01443d967f28`.
The five-entry Task 5 checkpoint verifies. This closes offline Task 5 only;
live pan routing, latency, audible behavior, and visual acceptance remain
unverified, and no Host or device/audio action occurred.

The terminal same-UUID handoff-text turn used refreshed snapshot
`2026-09-08T16:42:06-07:00`, had zero permission denials, confirmed that older
recovery paragraphs no longer expose the removed GTK reapply UI or old HPF
label, and found no new defect. Claude did not claim a local test rerun or live
inspection.
