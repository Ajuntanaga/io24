# CP34 evidence ledger

Timestamp: 2026-08-28T20:44:16-07:00

## Observed or independently represented

- `PROTOCOL.md` documents the device preset address ranges: four device slots
  and twelve user-library entries.
- `re/uc_component_model/dspusb_component_model.xml` represents the slot list,
  preset caches, and Voice FX selector/component.
- `re/uc_factory_presets.json` contains factory preset records with Voice FX
  content.
- `io24.py` implements preset mode, enable, and slot selection, plus Voice FX
  parameter serialization.
- The sealed predecessor proves host JSON persistence and strict capture
  normalization.

## Negative evidence

- Existing passive captures contain no Universal Control preset or Voice FX
  operation.
- Direct slot-index writes do not store preset content.
- Static component models contain values and ranges but not the missing native
  transaction.
- Existing block-201 writes store parameter intent without established audible
  processing.

## Evidence still required

- Native baseline and Voice FX activation/parameter captures.
- Native user-preset store and slot-assignment captures.
- Editor-independent hardware recall showing device-resident survival.
- Audible A/B evidence with a positive control.
- Full restoration and deletion of the test preset.

This ledger records evidence quality, not completion. Update it only with paths,
hashes, instruction addresses, capture rows, or executable results.

## Current offline verification

Verified 2026-08-28 after the CP34 corrections:

- `python3 -m pytest -q tests/test_io24_preset_persistence.py
  tests/test_normalize_io24_capture.py tests/test_io24_capture_decode.py`:
  23 passed, 27 subtests passed.
- Python compilation succeeded for the driver, GTK and web frontends, capture
  helpers, decoder, and their regression tests.
- The active route and CP34 directory contain none of the retired workstream's
  labels.
- `tests/fx_gate_probe.py` performs no device action when executed; it exits 2
  and directs the operator to `CAPTURE-MANIFEST.md` C00-C07.

No live device, preset, effect, native capture, Wine, installation, firmware,
reset, staging, or network action occurred in this offline verification.

## Reproduced vendor-image evidence

Reproduced 2026-08-28T20:53:55-07:00 without starting the vendor application or
accessing a device:

- Source module:
  `/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll`
  - size: 4,984,704 bytes
  - SHA-256:
    `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`
- Two independent extractions produced identical read-only firmware images:
  - `/tmp/io24-cp34-fw-a.GfGSjJ/io24-firmware-1.28.bin`
  - `/tmp/io24-cp34-fw-b.O5BUqw/io24-firmware-1.28.bin`
  - size: 1,104,448 bytes each
  - SHA-256:
    `65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`
  - exact source slice: file offsets `0x216030..0x323a70`
- The raw image has a Cortex-M vector table for load base `0x60020000`:
  initial SP `0x20000600`, reset vector `0x60020335`, reset offset `0x334`.
- The block-201 gate at firmware offset `0x50af8` tests object bytes `+0x44`,
  `+0x39`, and `+0x40` before its virtual dispatch.
- The internal builder at firmware offset `0x37da0` requires `+0x45 != 0` and
  `+0x46 == 0` before setting `+0x44 = 1` at `0x37e06`. Its reproduced callers
  are `0x37ea4`, `0x37f5a`, and `0x38004`.
- The preset component dispatcher at firmware offsets `0x3099c` and `0x30b70`
  accepts one index range `0..3` and another `0x10..0x1b`.

The instructions establish the internal state transition and preset ranges.
They do not establish a host-callable activation or store command.

## Reproduced host-module preset dispatcher

The same source DLL contains one request handler at
`0x18003b650..0x18003c54a`:

- It reads an exact `id` field and dispatches `RestorePreset` at
  `0x18003b6c8` and `StorePreset` at `0x18003bb2c`.
- Both paths optionally read `presetTarget`. The target extractor at
  `0x18003cce0` parses a signed decimal identity before the first `.`,
  optionally after one `/` prefix segment. Static code does not prove the
  canonical prefix, valid identifiers, or transport carrying the request.
- The `StorePreset` path serializes the resolved component into a local preset
  record, updates `[this+0x158] + index*0x120`, and invokes helpers at
  `0x18002e9e0`, `0x18003c720`, `0x1800379b0`, `0x18003b070`, and
  `0x18003c550`.
- The notification literal used by this exact path is `RenamedPreset` at
  `0x180436db8`. `StoredPreset` is a separate string at `0x180436d88`.
- None of those six complete function ranges directly calls any of the DLL's
  three native pipe-writer sites (`0x1800780db`, `0x18007867d`, or
  `0x180084ac8`).
- The call at `0x180037a17` is now resolved. It dispatches through the owner
  subobject at `this+0x118`, whose constructor installs vtable
  `0x18043a5b0`; slot `+0x10` is function `0x180052270`.
- `0x180052270` constructs a `MemP` envelope of length `0x7ec`, includes the
  `PrsM`/index descriptor and the selected preset record, then hands it to
  `0x1800546b0`. That function creates and schedules a native operation node
  through a runtime transport queue.
- The queue's device-subobject vtable is `0x18043a678`; slot `+0x10` resolves to
  `0x180055410`. In its initialized mode 2, with the Store path's fifth argument
  zero, that function constructs exactly `SetP | Appl | index 0 | MemP` and
  copies the full `0x7ec` memory-preset blob after the 12-byte command/block
  header.
- The resulting `0x7f8`-byte command is queued. The queue consumer and final
  edge to a vendor pipe writer remain unresolved, and no transfer has been
  observed.

This establishes that the vendor host constructs and queues the packet. It does
not establish device-resident saving; the firmware reconciliation below proves
that the reachable io24 handler does not consume the nested record.

The `MemP` blob built at `0x180052270` has these observed fields relative to
its start:

- `+0x00`: u32 `MemP`
- `+0x04`: u32 constant `0x7ec`
- `+0x08`: u32 `PrsM`
- `+0x0c`: u32 preset index
- `+0x10`: u16 zero
- `+0x12`: u32 fragment offset
- `+0x16`: u8 continuation flag
- `+0x17`: u16 fragment length, at most `0x7ce`
- `+0x19`: u32 serialized-record length
- `+0x1d`: serialized-record fragment bytes

The Store path uses `PrsM`; a distinct host path for the four device-slot
`Stat` records has not yet been located.

## Firmware reconciliation of the Store envelope

The exact host-built packet is now traced through the io24 1.28 firmware:

- The `Appl` SetP dispatcher at firmware offset `0x2d9b8` recognizes `MemP`
  and dispatches through vtable slot `+0x80`.
- For numeric block index 0, resolver `0x3ce98` selects the device root. Its
  vtable `0x6d200` maps slot `+0x80` to firmware offset `0x3c064`.
- `0x3c064` republishes six live input-state views through `StVw` and marks
  their cache state. It has no observed read of the nested `PrsM` tag, user
  index, fragment metadata, or serialized record bytes.
- The ordinary application-object vtables `0x672fc` and `0x673c0` map the same
  slot to `0x2da30`, an immediate return.

Therefore `SetP | Appl | 0 | MemP | PrsM` is accepted and can trigger cache
work, but it does not reach the preset component and does not store the record.
The earlier description of this packet as a credible device-save path is
superseded by this handler trace.

The real preset component remains at `dev+0x120c`, vtable `0x674f8`, with
dispatchers `0x3099c`/`0x30b70`: `PrsM` accepts indexes 16..27 and `Stat`
accepts 0..3. No decoded numeric block route reaches that component yet.

## Host `Stat` inventory

- Host offsets `0x180033eae`, `0x180033eda`, `0x180033f0c`, and
  `0x180033f3e` build `Stat` descriptors for indexes 0, 1, 2, and 3.
- They invoke vtable slot `+0x18`, not the `+0x10` path that serializes
  `PrsM` updates. The same sequence then enumerates the `PrsM` library.
- A separate builder at `0x1800429b1` accepts a caller-supplied `Stat` index,
  but its dynamic target cannot be established as the update serializer.
- No host `SetP | Appl | Stat` assignment transaction is statically proven.

The recovered `Stat` sequence is therefore enumeration/read-like evidence,
not a device-slot assignment path.

## Closed preset-component ingress map

- The preset component is constructed at `dev+0x120c`; its sole vtable load is
  at firmware offset `0x306bc`.
- Both decoded top-level command paths ultimately resolve blocks through
  `0x3ce98`. Its numeric accept set is closed: root block 0, mixer-family block
  100, Voice FX block 201, reverb block 202, and the block-203 family. Its
  chain resolver accepts only `opt `, `filt`, `gate`, `comp`, `eq  `, and
  `lim `.
- None resolves or forwards to `dev+0x120c`. The component happens to sit
  0x2c bytes inside the parent block-201 allocation, but proximity is not an
  ingress edge.
- Retained firmware xrefs to the component offset remain inside the preset
  module. No host resolver, button routine, or nonvolatile-storage call chain
  to its `PrsM`/`Stat` methods is proven.

Static analysis has therefore exhausted the decoded external command surface
without finding a device-preset writer. A supported-host C04/C05 capture is the
decisive check for a different transport or for host-only product behavior.

## Voice FX host state-machine trace

- Host function `0x180049980` handles `fxmodel` id 450. Its factory builds a
  16-byte `VoFx` payload for block 201 and queues it through `0x1800546b0`.
  This proves model selection/commit, not audible activation.
- The `VoiceFxOn` serializer reads a per-channel scene byte at `+0xe6`. Scene
  parsing sets that byte from the saved `voicefx.on` child; the serializer does
  not send an enable command.
- `bypassDSP`, `processingChannel`, reverb level `FXA`, and the mixer
  `fxreturn/ch1` are separate host-model controls. No static path proves the
  ordering or combination that opens the audible insert.

The remaining Voice FX evidence gap is therefore one single-variable native
capture: model selection and wet/dry change with an audible A/B on the
supported host.

The firmware-side gate closure is more specific:

- Block 201 processes audio only when byte `+0x44` is nonzero, byte `+0x39` is
  nonzero, and the word at `+0x40` is zero.
- The only known set of `+0x44` occurs at `0x37e06`, after `+0x45 != 0` and
  `+0x46 == 0`. The upward builder call graph terminates in internal heap/list
  construction with no known external message ingress.
- `processingChannel` has a decoded direct route, but no instruction edge to
  those five gate fields. `bypassDSP` has no device wire id in the host route
  table, and slot selection did not establish a gate transition.

No safe command sequence can therefore be derived by equating a visible host
parameter with an internal flag.

## Local Universal Control capability evidence

- The io24 component model has separate surfaces for a host `ChannelPresets`
  library/cache and four readonly-titled device slots with a mutable selected
  index.
- Generic host strings include `StorePreset`, `RestorePreset`,
  `GetPresetFileDescriptions`, `StoredPreset`, and `RecalledPreset`.
- io24-specific strings include input preset selection, per-input slot index,
  and preset mode. No local io24 artifact names an assignment from a user
  library item to a front-panel slot.
- Richer Copy/Reorder/Preset Library strings occur in reusable multi-product UI
  components and are not proof of io24 capability.

This supports host-library storage plus independent device-slot selection, but
does not by itself prove the absence of a hidden native assignment action. C04
and C05 are retained specifically to distinguish those possibilities.

The alternate host-path search also found integer and float component-value
writers at `0x180054250` and `0x1800542d0`, with repeated callers in the normal
component mutation loop. There is no static edge from `StorePreset`,
`RestorePreset`, or the preset dispatcher to either writer. Generic
`targetSlot`, drag/drop, Copy, and Reorder vocabulary occurs in other product
panels, but no corresponding action or bridge appears in `dspusbdevice.dll`.
Consequently, “restore a host preset by replaying individual component writes”
remains a capture hypothesis rather than an io24 assignment mechanism.

## Hardware-free control regressions

- `tests/test_io24_preset_persistence.py` proves `fx_on()` refuses an unknown
  activation sequence without writing reverb routes.
- The same suite proves `fx_off()` refuses an unknown deactivation sequence
  without writing reverb routes.
- `_build_captured_memp_frames()` encodes the recovered `0x7f8`-byte vendor
  envelope as a private fixture. Its docstring explicitly states that the
  packet is not a device-save operation and no live sender is exposed.

## Reproduced Voice FX metadata correction

`VoiceFxOn` at `0x180436b60` is copied into an outbound list at
`0x18003c2cc` only when a per-channel record byte at `+0xe6` is set. That site
is a conditional metadata serializer, not an action handler or a proven gate
write. The setter for `+0xe6` and its relationship to the firmware gate remain
unresolved.

## Linux-only host queue and writer closure

Reproduced 2026-08-28T22:52:27-07:00 without loading or executing vendor code,
starting Wine, accessing the protected prefix, or opening a device:

- Source module SHA-256 remained
  `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`.
- `re/cp34_host_queue_inventory.py` SHA-256:
  `8675c57273ea856909b673d58f780035b375c13af281de4a707486855833cf19`.
- `tests/test_cp34_host_queue_inventory.py` SHA-256:
  `a7e13d48310ae64b51c550d987460bb0ef6b85005ea98c45c90d2ba244f20faa`.
- The analyzer has three behavioral contracts: exact instruction-boundary
  calls, mixed-code/data resynchronization, and RIP-relative IAT resolution.
- Exact direct callers of queue function `0x1800546b0` are:
  `0x180035abe`, `0x180049f2f`, `0x18005238e`, `0x1800542a9`,
  `0x18005432a`, and `0x1800555ae`.
- Their bounded operation evidence is `FRst`/`Appl`, `VoFx`, `MemP`, `Pari`,
  `Para`, and the generic `SetP`/`GetP` wrapper. No caller constructs `Stat`,
  slot assignment, a save-point operation, or an explicit Voice-FX-on command.
- Exact calls to the `WinUsb_WritePipe` IAT slot `0x1800e53f0` are
  `0x1800780db`, `0x18007867d`, and `0x180084ac8`. All three consume queued
  buffers; none constructs a second io24 command family.
- The generic base queue method `0x180055570` is at base vtable
  `0x18043a5e8 + 0x50`. It is absent from the active device subobject vtable
  `0x18043a678`, whose `+0x10` slot is the known mode-2 `SetP`/`GetP` builder
  `0x180055410`.
- Across the extracted Universal Control tree, `WinUsb_WritePipe` imports occur
  in product-specific hardware-access modules. The io24 uses
  `dspusbdevice.dll`; no separate io24 module was found.

Combined with the firmware handler map above, the current vendor module and
firmware contain no distinct host operation for custom device-resident preset
store/assignment and no explicit host operation that opens the Voice FX gate.
This is a source-bound capability-negative, not evidence for guessing a packet.

Current Linux verification:

- `python3 -m pytest -p no:cacheprovider -q
  tests/test_cp34_host_queue_inventory.py
  tests/test_io24_preset_persistence.py
  tests/test_normalize_io24_capture.py tests/test_io24_capture_decode.py`:
  26 passed, 27 subtests passed.
- Python compilation succeeded for the new analyzer and its contract suite.
- Both pinned inventory commands in `LINUX-MANIFEST.md` exited 0 and reproduced
  the six queue callers and three writer call sites above.

## Linux factory-recall matrix gates

Added offline on 2026-08-29 without opening USB/audio hardware or importing the
io24 driver:

- `LINUX-LIVE-MATRIX.md` narrows the remaining live question to an
  already-assigned, device-screen-verified `Slap Echo` factory record.
- This is not a replay of the historical section 13s result. That probe changed
  to an unidentified numeric slot and then re-sent the direct block-201 payload;
  it did not establish that the recalled slot named an active factory record.
- Factory source `re/uc_factory_presets.json` SHA-256
  `89b0572dd760b77831d012e2db0568b4f4eeb158985a4ca86126be28e934c73d`
  records `Slap Echo` at record 4 with `voicefx.on=1`, time 0.15,
  feedback 0.25, and mix 0.5.
- `re/cp34_live_matrix.py` is hardware-free. It generates a deterministic
  low-level impulse stimulus, validates a target-specific inverse ledger, and
  analyzes two dry/two active/reverb-control WAV derivatives.
- The generated stimulus SHA-256 is
  `318786a6af910736dbe8f96d152753884dac6fe360b8ad1e8a685b3077d68142`.
- The analyzer requires fixed 48 kHz mono PCM, matching impulse count/cadence,
  non-clipping captures, a late-energy reverb positive control, a repeatable
  150 ms active peak at least 6 dB above every dry bracket, source hashes, and
  explicit audible attestation.
- The ledger validator refuses unknown action kinds, missing/partial inverses,
  duplicate IDs, mismatched control identities, stale or unpinned write-only
  baselines, extra method arguments, direct `set_fx`/preset methods, wrong bus,
  clamped values, and altered reverb-control parameters.

These gates make a future Linux run reproducible; they are not live evidence.
The target title, device identity, current write-only baseline, audio mapping,
and restoration still require separately authorized PRESTATE collection.

Offline shadow audit:

- `/home/ajuntanaga/.cache/io24/shadow.json` existed at 4,841 bytes with mtime
  2026-08-23T00:58:28.962800758-07:00 and SHA-256
  `36f6ef20c89d2dbb7625689d002bafd9bcde18576398f8dfde9a0e9208a0fc98`.
- It contains all seven Mix A `set_send_db` rows, channel 1/2 `set_fx_mix`
  values 0.0, and reverb false/0.1/0.0/200.0/0.02 at 48 kHz.
- It has no explicit Mix A assign or bus-master rows, and no evidence proves it
  remained current through later power cycles or editor/device changes.

The shadow is useful candidate inverse provenance but is currently ineligible.
No live action may treat it as current without explicit attestation or a newly
authorized known-baseline boundary.

## L01 read-only live discovery

Executed 2026-08-29 under the user's exact L01-only authorization. The durable
report is
`runs/20260829T010329-0700-l01-readonly/L01-REPORT.md`.

- Linux identified one `194f:0422`, serial `AB7C22200355`, at sysfs `1-2`, bus
  001 device 003, high speed, configuration 1, with `bcdDevice 1.28`.
- Interface 5 was unbound before the read. One bounded claim of alternate 1
  reported protocol 1 and maximum command/response sizes 2048/2048.
- Four JaSt reads each contained 503 slots. Their relevant PRESTATE fields were
  identical: channel 1 slot 0 enabled, channel 2 slot 2 enabled, chains mapped
  to physical inputs 1/2, and phantom off on both inputs.
- Snapshot SHA-256:
  `4f114b8a4e215e2345b196543bfa7ce020b4de9ccba6a21b4365a9432c3182e4`.
- ALSA exposed `R24` card 2 device 0 for both playback and capture, stopped,
  with six-channel S32_LE/24-bit streams supporting 48 kHz. The kernel's
  logical map is `FL FR FC LFE RL RR`; no stream was opened to prove the
  physical channel map.
- Battery stayed safe at 76-77% and charging.

No preset title was inferred from the numeric slots. No audio stream, setting
write, front-panel action, preset/effect operation, Wine/prefix access, detach,
firmware action, reset, installation, network action, or restoration action
occurred. L02-L07 remain ineligible pending operator title transcription,
physical-map proof, and a current complete restoration baseline.

## Scoped title-free classifier review

Reviewed and reproduced offline on 2026-08-29 without importing the io24
driver, opening USB/audio hardware, accessing Wine, or using the network:

- `re/cp34_live_matrix.py` SHA-256:
  `6d3f309aa63a90b6c4f68ab5ee7c0511fb86dbca0c7f133ecd2d91f40cc17659`.
- `tests/test_cp34_live_matrix.py` SHA-256:
  `165028a3cee10900cd320bdacdfd1621f767f940f1c6148ec1263a11f77e2980`.
- The focused hardware-free suite passed: 37 tests in 9.90 seconds.
- The combined CP34 hardware-free regression set passed: 63 tests and 27
  subtests in 22.15 seconds.
- The pinned host inventory reproduced six direct queue callers and three
  RIP-relative native-writer consumers from DLL SHA-256
  `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`.
- The title-free classifier accepts only the four declared channel/slot
  candidates and two dry/two active captures with matching stimulus cadence.
- A repeatable audible 150 ms delta is reported as
  `SIGNATURE_PRESENT` / `REPEAT_150MS_SIGNATURE`. The report explicitly leaves
  model identity unresolved and sets title verification, live readiness, and
  restoration verification false.
- A repeatable late tail is `NON_SPECIFIC_LATE_TAIL` and remains inconclusive;
  neither its source nor loaded model is inferred.

This closes the earlier overclaim in the unsealed classifier. It does not turn
the classifier into a live capture procedure or restoration contract. No
title-free live slot survey is authorized or executable from the current CP34
records.

## Current-slot survey offline integration

Integrated 2026-08-29 after Tasks 1-4 passed their independent reviews. The
hashes and `94 passed, 27 subtests passed` count in this original block are
superseded by the final-fix-wave block below and retained only as history. The
then-current six-row task-local stage was
`CURRENT-SLOT-SURVEY-STAGE.sha256`; its current SHA-256 is recorded by
`LINUX-OFFLINE-SHA256SUMS`. The tracked artifact hashes are:

```text
ad694447f07b2999d67c12c614f14e726fc3dc4623efd5040a0bd73cc8768d08  re/cp34_current_slot_survey.py
2c315c79a68e477807d4ae34e33a50dc93b60b5374186310998256f2b60499a4  tests/test_cp34_current_slot_survey.py
8e5beb5b13da09cfa66b15908adf0189053c2861908822912e2d3ca860e52b28  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-DESIGN.md
5bb402f6b0e98f83f2ab082d738d7fd9a071356c07ae64cf0119ea7886f116f8  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md
3288d3be80f125e2a66f9be71e18fc213a5c6070fe1e99150d3e87cc80b72ac3  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-PLAN.template.json
7d24b3d3e6de5f0fc519768c9732cfdd08e49268cbb6024e4b43a299cc9f8e49  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-IMPLEMENTATION.md
```

The full hardware-free command covering the host inventory, live-matrix,
current-slot survey, retained host persistence, capture normalization, and
capture decoder returned `94 passed, 27 subtests passed`. The two pinned host
inventories reproduced six direct callers of `0x1800546b0`, three RIP-relative
consumers of `0x1800e53f0`, and DLL SHA-256
`567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`.

The implemented offline contracts are:

- plan validation schema
  `cp34-current-slot-survey-plan-validation-v1`, with `VALID`/exit 0 only for
  an exact populated plan; the checked-in template remains intentionally
  `NOT_AUTHORIZED` with `UNRECORDED` source fields and is rejected;
- mapping schema `cp34-current-slot-map-v1`, with `MAPPED`/exit 0 only for an
  exact six-channel 48 kHz S32_LE input, five pinned-cadence impulses, safe
  levels, and a score of at least 0.80 on predeclared Mix A channel 3 or 4;
  the chosen channel is frozen before effect results are visible;
- analyzer schema `cp34-slot-survey-audio-v1`, retaining `candidate`,
  `model_identity: "UNRESOLVED"`, `title_verified: false`, `live_ready: false`,
  `restoration_verified: false`, exact dry/active metric rows, and their local
  derivative paths and SHA-256 values; and
- restoration schema `cp34-current-slot-restoration-v1`, with `RESTORED`/exit
  0 only after exact plan, event, P0/P1/P2, map, A/B, audible, physical, and
  manifest checks. It returns the snapshotted `input_hashes` and preserves the
  literal limitation `JaSt cannot prove every internal DSP byte.`

Each `P0.json`, `P1.json`, and `P2.json` JaSt summary must use schema
`cp34-current-slot-jast-summary-v1` and bind its untouched raw JaSt input by
safe relative `raw_snapshot_path` plus exact `raw_snapshot_sha256`. The
retained `MAP.raw.wav` binds to `MAP.json.raw_sha256`. `AB.json` binds exactly
two dry and two active `S1.mixN.mono.wav` through `S4.mixN.mono.wav`
derivatives by safe relative `path` and `sha256`, where `N` is the already
frozen Mix A channel. Roles derive from `P0.enabled`, never filenames.
`EVIDENCE-SHA256SUMS` must exactly cover every pre-verification input; the
final no-clobber `SHA256SUMS` covers every retained file except itself.

This is positive-only evidence. `SIGNATURE_PRESENT` becomes meaningful only
with `RESTORED` and supports only a restored, repeatable audible 150 ms effect
signature on the controlled path. A null signal or non-specific late tail is
`INCONCLUSIVE`, never a negative. Neither a signature nor restoration proves a
preset title, effect model, custom device-resident storage, device source, or
every internal DSP byte. Channel 2 is eligible only after channel 1 is exactly
`RESTORED` plus `INCONCLUSIVE`; `UNAVAILABLE` and `RESTORATION_FAILED` stop.

No live acquisition, USB/device access, ALSA stream, Wine/prefix access,
front-panel action, preset/effect operation, mapped write, firmware/reset/DFU,
installation, external staging, network action, or audio monitoring occurred
during this integration.

### Fix round 1 canonical replay evidence

The first independent integration review rejected four assertions that were
structural but not canonical. The offline verifier now closes each one:

- `analyze_map_bytes` consumes the already-snapshotted `MAP.raw.wav` bytes.
  Restoration recomputes the complete `cp34-current-slot-map-v1` result using
  the plan's physical input and requires exact type-preserving equality with
  `MAP.json`, including raw hash, metrics, scores, status, reasons, and frozen
  winner.
- `re/cp34_live_matrix.py` exposes `analyze_slot_bytes`, which accepts exactly
  two dry and two active `(run-relative label, immutable bytes)` inputs. The
  ordinary path CLI reads each file once and delegates to that same algorithm.
  Restoration invokes the byte seam directly with the four snapshotted
  derivatives and requires complete equality with `AB.json`; it creates no
  temporary file and does not reread a live path.
- `MAP.raw.wav` and `S1.raw.wav` through `S4.raw.wav` are now individually
  required and validated as exact six-channel S32_LE/48 kHz captures. The plan,
  three JaSt summaries and raw bindings, action log, map, four deterministic
  derivatives, A/B, audible attestation, physical restoration, and exact input
  manifest remain independent mandatory inputs.
- A channel-2 check recomputes the complete channel-1 restoration result from
  the same immutable run snapshot. The saved predecessor must exactly match
  that result, including empty reasons, slot/channel/frozen scope, literal JaSt
  limitation, and scoped input hashes. A newly manifested result JSON or hash
  cannot substitute for valid underlying channel-1 evidence.

The immutable analyzer seam is pinned here as
`re/cp34_live_matrix.py` SHA-256
`aac2a39a49284cc42c01247fca53fbaf6b0af1a04dd3182b82aa7358c5db95c8`
and `tests/test_cp34_live_matrix.py` SHA-256
`0f27703b9ba94b4af9807ca6bc1f9389f81deb31d12d8d14f435055d1d4b7b8f`.
No live action occurred. Independent re-review remains required.

### Historical revision-1 final fix wave — superseded

```text
bf7484eb9257075259b77177d8f0ff00a1d281a97f0927bff0a3db6f897c753b  re/cp34_current_slot_survey.py
93df2c3f108575e14c404814f6cc4cf29f5209bc8279e6a4e6eadcaa5116e590  tests/test_cp34_current_slot_survey.py
8e5beb5b13da09cfa66b15908adf0189053c2861908822912e2d3ca860e52b28  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-DESIGN.md
c96d0e8adec4274feb7c21ec06a2c994b45a32318f823e19b17fc3f91db04e01  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md
3288d3be80f125e2a66f9be71e18fc213a5c6070fe1e99150d3e87cc80b72ac3  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-PLAN.template.json
7d24b3d3e6de5f0fc519768c9732cfdd08e49268cbb6024e4b43a299cc9f8e49  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-IMPLEMENTATION.md
```

The complete hardware-free regression returned `94 passed, 31 subtests passed
in 103.54s`. The four added subtests independently corrupt the frozen-channel
sample stream in S1, S2, S3, and S4 and require rejection.

The verifier compares every supplied mono derivative with the decoded frozen
channel of its corresponding immutable raw capture; M0 remains bound by the
canonical map recomputation. Each JaSt raw snapshot is canonical UTF-8 JSON
under `cp34-current-slot-jast-raw-v1`, and every supported summary field is
recomputed from those bytes. Exact recursive plan field sets and the normalized
non-symlink run path are enforced.

Candidate evidence is sealed without clobber at candidate-scoped
`EVIDENCE-SHA256SUMS` paths; the root final seal is delayed until the terminal
candidate. Channel 2 binds the channel-1 interim manifest/result while the
verifier independently rechecks all underlying channel-1 evidence. Mapping
requires all five expected arrivals at one consistent lag and the 96-sample
cadence tolerance. Post-restoration no/failed audible confirmation yields
restored `INCONCLUSIVE`, never `RESTORATION_FAILED`.

The broader 23-row offline manifest, not the six-row core-stage manifest, also
pins unchanged analyzer dependency `re/cp34_live_matrix.py` at
`aac2a39a49284cc42c01247fca53fbaf6b0af1a04dd3182b82aa7358c5db95c8`
and its tests at
`0f27703b9ba94b4af9807ca6bc1f9389f81deb31d12d8d14f435055d1d4b7b8f`.
No live action occurred. The final fix wave is ready only for scoped independent
re-review; it is not reviewed, final-approved, or live-authorized.

### Revision-2 correction — pending independent review

Revision 1 is rejected/superseded. Revision 2 accepts only
`cp34-current-slot-survey-plan-v2` with
`cp34-current-slot-evidence-v2`, emits validation/restoration v2 results, and
rejects non-finite or float-overflow JaSt numbers deterministically before raw
canonical serialization. Its procedure seals each candidate with `pipefail`
before its first pipeline and requires physical restoration followed by separate
non-io24 replay of all four derivatives before audible attestation and A/B.
No live action occurred; this correction remains pending independent review.

Fix1 authoritative current-slot evidence supersedes historical 94/31 claims:
39 passed, 9 subtests passed in 129.12s, exit 0. It covers v2 physical/audible
contracts, AB provenance, numeric bounds, root-artifact rejection, and seals.
Broad-suite and manifest verification were pending at that intermediate
checkpoint; the completed evidence below supersedes it.

Controller broad verification is authoritative: 102 passed, 36 subtests in
157.09s, exit 0. Historical 94/31 claims are superseded; no live action occurred.

Current revision-2 fix1 core hashes are:

```text
e48b34a31fc7c6d85756ff1fe0c2e006ed54085b2185caf54cc0df5c434b65b6  re/cp34_current_slot_survey.py
d84bd72abc8b0f2521cc1a2c541532a6a42aa57a92eabdeb1780636ae8dbd03f  tests/test_cp34_current_slot_survey.py
816e2a3a27ac1ecb15eea554d40fcca5d67354afd8b3fe7876708bb06bb9130f  CURRENT-SLOT-SURVEY-DESIGN.md
18a0c68f66e16a8d393aeeda8d035a2798f9e5621006924fead84db838c8f14b  CURRENT-SLOT-SURVEY.md
83db1ffc91f7fc3b5ec3cd6c689bd7ccdefa208e12c3722775b5d794f7338c14  CURRENT-SLOT-SURVEY-PLAN.template.json
d8c671881a8007e65af9f959de66aa9288b2a27b8c7d834ccba6fbb8e771bc0b  CURRENT-SLOT-SURVEY-IMPLEMENTATION.md
```

The six-row stage manifest verifies at
`c4fc43129e998d2626670ef32ddd1a6f169c7a4613788899b1910b7db1109410`;
the 23-row offline manifest verifies completely, and its post-record file hash
is retained in the task-local implementation report rather than in a file that
the manifest itself pins.
Passive sysfs reported BAT0 at 40 percent, discharging. These are offline seal
facts only; independent fix1 re-review remains pending and no live action is
authorized.
