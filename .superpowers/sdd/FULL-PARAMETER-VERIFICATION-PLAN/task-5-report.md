# Task 5 report — offline Linux Host publication readiness

Date: 2026-09-08
Status: COMPLETE for offline Linux Host publication readiness; no publication
or new live/device action is authorized

## Outcome

The packaging result below and the repaired Host state model now form a clean
offline publication-readiness result. A later authorized live check and pinned-
firmware trace proved that `set_fx_mix(channel, 0)` is the same underlying state as
channel preset bypass: `JaSt` derives bits 5/6 directly from whether the two
`inputFxMix` floats equal zero, and integer preset-enable wire 4 forwards 0/1
through the same float dispatcher. The Host exposed these as independent
reverb-send and preset-enable controls and could save/replay contradictory
shadow entries. That defect changed Channel 1's compression during an isolation
step. That defect is now corrected in the Host model, migration, UI, matrix,
tests, and documentation and has a clean same-boundary Claude review.

The installable Python wheel now contains all local modules required by the
advertised Host entry points and adds the documented Universal Control scene
importer as `io24-scene`. The repaired wheel includes the previously omitted
`io24_mbc`, `io24_native_stat`, `io24_preset_record`, `io24_presets`, and
`io24_scene` modules.

README publication status now matches the task-local record:

- the corrected maximum-wet Channel-2 trial ran and produced no noticed
  power-cycle change, but later Host-state defects make it nonterminal rather
  than proof of a stock-firmware failure;
- those Host defects are repaired offline, while a clean Host-controlled live
  round trip remains separately authorization-gated;
- the Standard high shelf is source-bound to UC 4.7.2 selector 9; and
- Passive/Vintage direct-live replay remains fail-closed, including the
  disabled `--vintage-eq` approximation.

`GUIDE.md` already carried the corrected maximum-wet/nonterminal result, so it
required no edit. It does not describe Standard or alternate EQ; README is the
publication-facing document that satisfies that part of the brief.

## TDD and verification

The new wheel test first failed against the old metadata because these five
files were absent from the actual wheel:

```text
io24_mbc.py
io24_native_stat.py
io24_preset_record.py
io24_presets.py
io24_scene.py
```

After the minimal `pyproject.toml` repair, the same test passes. The first
serialized Task 5 peer review then identified a real regression-coverage gap:
the test asserted archive membership and entry-point metadata but did not
execute imports from the built wheel. A RED mutation added an unresolved import
to the staged `io24_scene.py` while leaving all expected filenames present; the
new isolated-import assertion failed on that exact missing dependency. After
removing only the mutation, the permanent regression imports all 15 shipped
modules from the wheel in an empty working directory, checks that every module
originates from the wheel, and runs `python -m io24_scene` without device
access. Its module-name derivation uses Python-3.8-compatible slicing rather
than `str.removesuffix`, preserving the declared minimum Python version. A
broader affected run still passes 114 tests across release packaging, Host
repairs, the full parameter inventory, exact Standard high shelf, Host state/
Hot Key, preset persistence, and VoiceFX preset application.

A fresh independently staged, dependency-free, no-build-isolation wheel build
in `/tmp` produced `io24-0.1.0-py3-none-any.whl`, 226781 bytes, SHA-256
`db9ee407673ba7696b6e86d77c3af8b7e8af248681f8b654911a6717f4f1c5ad`.
All 15 required modules and all seven declared console entry points were
present. Every module imported from the wheel in an empty working directory,
and `python -m io24_scene` printed its hardware-free usage text. No wheel was
installed. This wheel archive is a disposable verification output, not a
release artifact or deterministic checkpoint.

The parameter matrix regenerated twice to independent `/tmp` paths. Both
outputs and the checked-in 750-row artifact were byte-identical at SHA-256
`9b220c0c2b8224a1452c11cf9b79b336f5e369253503aa4387ffc968a8ba577e`.

## Before and after identities

| File | Before Task 5 | Candidate after |
|---|---|---|
| `pyproject.toml` | `a3024febca97a86446a2029b2685409ea90546927281df34965b3bd41c351635` | `6ad1c7061278fbb47a08973e7d180b37d6a3d3dc3d5b7ca18b3e27f807cfa766` |
| `README.md` | `f264634062353a85c1068991955395440de41e7e31809b7ddcf79a8752d972e0` | `8ead3b5eb28fe2222282d921928045b890c3cba2f59a8ed43e40941722a08aee` |
| `GUIDE.md` | `c9322d0a01d4a38a219195e44874a28bd24266c852d1ee1335d65cefca6fef7d` | unchanged |
| `tests/test_io24_release_package.py` | new | `bef5f7e14ea6fd4c30d221ff1f72ed179db8cd5ef0e16787ca851e5055e7b8d6` |
| `task-5-brief.md` | new | `fe9dde3e7af596152d37bfa3d2dbbfcb34e257059fdcb8df7295c8de788045d0` |

## Independent peer review

The dedicated serialized peer UUID `4aa42435-e87a-4ba1-befe-5571013b4cc1`
completed the first Task 5 turn successfully with zero permission denials. It
reviewed the snapshot created `2026-09-08T03:21:51-07:00`, bound to 40 sorted
`EVIDENCE.sha256` entries. It found no module-list discrepancy, stale
publication claim, or accidental authority expansion. Its one substantive
finding was the missing executable wheel-import regression described above.
The peer explicitly classified the already performed manual import check as
valid candidate evidence but recommended locking it into the suite; this report
does not treat the peer as an approval authority.

The same dedicated UUID then reviewed the correction from a refreshed snapshot
created `2026-09-08T03:31:35-07:00`, again with 40 sorted manifest entries and
zero permission denials. It read the executable import and module-invocation
mechanics directly, closed its finding, verified the GUIDE/README wording
correction, and reported no remaining correctness defect, stale claim, or
authority expansion. Codex reconciled that response against the executed RED /
GREEN evidence, the 114-test affected run, the independent wheel audit, the
two deterministic matrix regenerations, and the five-entry checkpoint before
closing the task.

A final same-boundary turn reviewed the Python 3.8 compatibility correction
from the 40-entry snapshot created `2026-09-08T03:41:50-07:00`. It completed on
the same UUID with zero permission denials, confirmed the slice is equivalent
for the fixed `*.py` module-name set, and found no new correctness, claim, or
coverage issue. All Claude text is retained verbatim in `.claude-peer/OUTBOX.md`.

## Boundaries and release concerns

- No USB/device/audio, Host or GUI launch, Wine/protected-prefix access,
  firmware/DFU/reset, network publication, dependency installation, user-cache
  mutation, Git initialization, staging, or Obsidian mutation occurred.
- The wheel deliberately does not redistribute `re/uc_factory_presets.json`.
  `io24_presets` still imports, and the GTK Host already presents its existing
  missing-data explanation rather than hiding device-slot/Hot Key controls.
- The ignored `io24.egg-info/` directory contains stale generated metadata. It
  is not an authority record and must not be used as the publication manifest.
- No Git repository exists, so no commit or tracked-file publication inventory
  was created.

## 2026-09-08 post-closure reconciliation

Later Host correctness work changed `README.md` to document the separation
between the fixed 80 Hz preamp HPF and the write-only Fat Channel HPF, and to
document the default quarantine of device-slot selectors from ordinary Host
snapshots. That made the original README entry in Task 5's five-file checkpoint
stale without invalidating the wheel implementation.

The release-package regression and the expanded affected Host suite now pass
121/121. The matrix was regenerated twice again; both outputs and the checked-
in 750-row artifact are byte-identical at SHA-256
`4fae0d3d338a00a9ce1892a20109a43381530131d28914f174cbeed851beedac`.
The five-entry checkpoint was refreshed to the current README identity and
verified. This is still offline publication readiness only; it is not evidence
of physical-screen behavior, preset-body readback, audibility, or publication.

## 2026-09-08 closure invalidated by functional effects-state evidence

The later live effects lifecycle did not merely add an untested feature. It
exposed a source-proved contradiction in an advertised Host control and its
persistence model. The prior wheel contents, entry points, isolated imports,
and `python -m io24_scene` checks remain valid historical evidence, but they do
not make a functionally incorrect Host ready for publication. The 750-row
matrix and five-entry Task 5 checkpoint are stale pending correction and final
reverification. No publication is authorized or performed.

## Processing-mix correction candidate

The dedicated 52-file Claude peer independently endorsed canonicalizing the
Boolean enable API onto the exact scalar, preserving explicit legacy bypass
intent, refusing unknown exact Hot Key values, and removing the duplicate GTK
controls. The candidate now passes 95 focused tests and 181 affected Host/stage
tests. The corrected matrix contains 748 atomic rows, not 750: the two former
per-channel `preset_enabled` rows duplicated the two `inputFxMix` parameters
and their APIs now index those canonical rows. Task 5 remains reopened until
the final wheel audit, double matrix regeneration, checkpoints, and same-UUID
Claude re-review are clean.

## Final correction closure

The candidate passed its final gates. The release-package regression is 1/1;
the expanded affected Host/stage suite is 181/181 with `ResourceWarning`
elevated to error. A fresh no-dependency, no-build-isolation wheel was built to
`/tmp` without installation: 231903 bytes, SHA-256
`1d15eb5e297f721d78837fa539ee07443bb2039d0e593e02f5fb6e286ea6f44c`.
It contains all 15 declared modules and seven console entry points; all modules
imported from the wheel in an empty working directory and `python -m io24_scene`
returned its hardware-free usage text.

Two final matrix regenerations and the checked-in 748-row artifact are byte-
identical at SHA-256
`2a08282d7017c4724c2240dbd5704d06319f2f961d7f5bb7ade16fb65e692300`.
The dedicated Claude UUID `a764bfc8-6fec-453f-9289-92ace5f16ce5` reviewed the
refreshed 52-file implementation snapshot created
`2026-09-08T10:26:01-07:00`, found no defect, endorsed the 748-row correction,
and stated Task 5 could proceed to final offline verification. Claude's result
is peer evidence, not approval authority.

Task 5 closes only the offline Host publication-readiness gate. The private
device-slot Reverb trial remained audibly dry, device-body recall and power-
cycle persistence remain unproved, and no publication, Host launch, USB/audio
operation, install, Git initialization, or Obsidian write occurred here.

The final serialized closure turn on the same dedicated UUID used snapshot
`2026-09-08T10:38:40-07:00`. Claude matched all five Task 5 checkpoint entries
and the checked-in matrix hash to that snapshot, found no scope overclaim or
substantive defect, and concluded the offline closure stands. It correctly
did not claim to have rerun Codex's local tests or the out-of-boundary 16-entry
effects checkpoint.

## Host refinement closure

User-reported defects reopened the gate again for a 53-file review including
`io24_mbc.py`. The Host now persists the complete four-band multiband state in
strictly validated Host-only JSON without putting it in device slots, temporary
previews, or reconnect replay. Process launch/stop paths clean private configs,
replace stale configured graphs, and fail visibly off. Continuous HPF movement
no longer floods completion notifications; the spectrum uses 4096-point FFTs,
1024-sample hops, 256 display bins, and elapsed-time release; EQ drag sends one
coherent trailing-guaranteed band state. Mixer no longer horizontally scrolls,
and Presets plainly separates device slots, Host-only A/B previews, and
searchable factory sounds.

Claude's serialized review on dedicated UUID
`15978222-d591-4549-9876-21c04f741e14` found two multiband lifecycle races.
Both received RED regressions and corrections; Claude's next turn closed both.
The subsequent JSON/GTK, spectrum/EQ/feedback, and layout/claims slices found no
functional defect. Claude's one remaining documentation finding, a retired
`Hot Key` phrase in `GUIDE.md`, was corrected before final verification.

The final offline suite passes 216/216 with `ResourceWarning` elevated to an
error. A fresh, uninstalled wheel is 235718 bytes at SHA-256
`151f7c2adbffd57484a13494ded087e1a754609f67ec26e0e268c08a126e36ef`;
it contains 15/15 modules and 7/7 entry points, imports every module from the
wheel in an empty directory, and executes `python -m io24_scene`. Two fresh
regenerations match the checked-in 748-row matrix at SHA-256
`b0c2b9ba42b879843d310024f22bc8736166311a2a97aa141b88524f36ca12a1`.

Task 5 is complete for offline Host correctness and packaging. This does not
claim a live visual acceptance run, device-slot multiband persistence, private
Reverb activation, audibility, or power-cycle persistence. No Host, device,
USB, audio, Wine, installation, publication, Git, or Obsidian action occurred.

The final same-UUID closure turn used the refreshed 53-entry snapshot created
`2026-09-08T15:07:43-07:00`, verified the guide correction and closure claims
against all four earlier slices, and reported no substantive finding. Claude
confirmed checkpoint shape and narrative consistency but correctly did not
claim to recompute hashes or rerun Codex's tests.

## Mixer, pan, and notification refinement closure

The next user-directed refinement removes routine bottom-toast updates across
the Host. Continuous EQ, dynamics, Voice FX, reverb, pan, rate, delay, routing,
and preset-selector changes now use the control itself or an inline subtitle;
toasts remain for connection transitions, constraints/failures, and discrete
file, factory-load, preview-capture, mirror, or device-slot completion. Factory
preset completion is emitted only after its worker transaction returns.

The Mixer now identifies displayed device slots as `S1`/`S2` plus a blue active
dot: displayed S1 breathes on a 3.2-second period, displayed S2 on a 1.6-second
period, bypass is an empty ring, and GTK reduced-motion makes the active dot
steady. The fixed preamp switch is labelled `HPF`. Bus headings are consolidated
into one footer and their meters are narrower. The cached-control reapply banner,
handlers, and state machine are removed from the GTK Host; the connection banner
and connect/disconnect notices remain.

Channel 1 and Channel 2 pan controls are independent and remain operable when
stereo link is off. Their complete Host-only state is strictly validated and
round-trips in Host JSON. Enabling `Host input pan` creates a distinct PipeWire
capture-to-playback filter chain with explicit two-channel inputs/outputs and
equal-power gains; it does not reuse the app-playback multiband sink. The route
defaults off, never changes the device Monitoring Blend automatically, and
warns inline about direct-path doubling and round-trip latency. Identical starts
are idempotent. This is offline implementation evidence only: no live routing,
latency, control feel, or audible pan acceptance was performed.

The dedicated 53-file Claude UUID
`15978222-d591-4549-9876-21c04f741e14` reviewed the implementation. Codex
accepted and corrected its findings about the still-live hidden reapply feature
and redundant pan-chain relaunch. Codex disagreed with its breathing-speed
finding because the peer had read zero-based slot indexes as display numbers;
the directional regression proved the mapping, and the next same-UUID turn
explicitly withdrew that finding. Snapshot `2026-09-08T16:26:40-07:00` then
confirmed all three reconciliations, found no remaining defect, and returned
with zero permission denials. Peer feedback is not approval authority.

Fresh offline gates pass: release packaging 1/1 and the affected Host suite
172/172 with `ResourceWarning` elevated to error. A separately staged,
uninstalled wheel is 236508 bytes at SHA-256
`58719a27dd9b2505ff0baad081042fca2a24da5007fee29399e630d85365a77f`;
it contains all 15 runtime modules and seven console entry points, imports every
module from the wheel in an empty directory, and executes `python -m io24_scene`.
Two independent 748-row matrix regenerations and the checked-in artifact match
at SHA-256
`84e0b3fbe7e9aa6ee736a8f52db6da50732013e5a482e33fcc0c01443d967f28`.
The five-entry Task 5 checkpoint was refreshed and verified.

Task 5 remains complete for offline Host correctness and packaging. No Host,
USB/device/audio, Wine, install, publication, Git, or Obsidian operation was
performed. Live Host visual acceptance, independent-pan routing/latency/sound,
private Reverb activation/audibility, and device persistence remain separate
gates.

The terminal same-UUID handoff review used the refreshed 53-entry snapshot
created `2026-09-08T16:42:06-07:00`, returned with zero permission denials,
verified that the older recovery text no longer advertises the removed GTK
reapply UI or old HPF label, and found no new substantive defect. It did not
claim a local test rerun or any live action.

## 2026-09-09 Mix bus source correction — offline pre-peer closure

The superseding GTK design removes the per-input pan controls and the opt-in
physical-capture monitor. Main remains centered and disabled because no complete
Main pair is exposed by USB capture. While the Host runs, Mix A and Mix B are
modeled as two independently owned, passive, non-remixing PipeWire sources:
`io24 Host Mix A` selects USB capture 3-4 and `io24 Host Mix B` selects 5-6.
Neither source has a playback target or routes anywhere by default. Each source
becomes adjustable only after its exact public node is visible; start, timeout,
update, and failure state are isolated per bus.

`host_features.pan` is now strict version 2 data containing only `mixa` and
`mixb` balances. Center leaves both stereo legs at unity; movement attenuates
only the opposite leg and never crosses channels. A valid legacy version 1
per-input state migrates to neutral bus balance with the discrete load notice
`legacy input pan was not applied; Mix A/B balances centered`; malformed legacy
data still fails before device setters.

The focused source/persistence gate passes 123 tests plus 46 subtests. The
complete affected Host suite passes 183 tests plus 81 subtests with
`ResourceWarning` elevated to error, and the release-package contract passes
1/1 without installation, retaining isolated imports and the hardware-free
`python -m io24_scene` execution. Two independent 748-row matrix regenerations
match the checked-in artifact byte-for-byte at SHA-256
`e3b4b378dd3cd0701415e4af9499dad29c60b6299f9c65d80aa8a7a1f8cae037`.
The row set was unchanged; regeneration updated only current source-provenance
hashes, including two source changes that predated this correction.

The authorized architecture review used the exact 53-file snapshot created
`2026-09-09T10:33:34-07:00`. Claude found the design sound and required both
`stream.dont-remix` flags plus a separate owner per bus; both requirements are
implemented and covered offline. This is not the separately gated final
implementation review. Live PipeWire source publication, channel selection,
visual layout/control feel, balance behavior, and audible routing remain
unproved. No Host, USB/device/audio, Wine, install, publication, firmware, or
Obsidian action occurred.

The separately authorized final review refreshed the same exact 53-path
boundary at `2026-09-09T11:14:02-07:00`. The serialized result used dedicated
UUID `15978222-d591-4549-9876-21c04f741e14`, returned success with nonzero token
use and zero permission denials, and its 53-entry manifest verifies. Claude
checked the requested source, lifecycle, migration, GTK, documentation, and
regression areas, found no substantive defect, agreed the implementation is
sound, and explicitly stopped without another review turn. Claude did not
claim live function or rerun Codex's local tests.
