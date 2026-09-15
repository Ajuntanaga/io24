# CP34 evidence ledger

Timestamp: 2026-09-06T14:54:07-07:00

## 2026-09-14 controlling selector-replay and live-null evidence

The authorized Ring-Mod run's direct-gate positive control changed the
Main/Input-1 ratio by `-19.277711 dB` against an `11.794912 dB` threshold.
Zero-output Ring Mod changed it by only `-0.098927 dB` against a `2.813849 dB`
threshold; off-state drift was `+0.054058 dB`. Raw report SHA-256:
`9157dd84bc6d3e9f91db6870a7eeb7de484f2b5565ccb6ee085b904dc519f001`.

That is a resolved negative for the transmitted selector -> wait -> state ->
wait -> state-replay sequence. Static follow-up pins block primary handler
`0x553d4`: `VoFx` reaches selector `0x55388`, while ordinary model-state tags
tail-call generic delegate handler `0x5079c` and never revisit the deferred
rebuild check. The required sequence is selector -> wait for bypass -> selector
replay -> model state. `Io24.send_fx` now emits that order.

The raw readable restoration guard differed only in flags bit 9 (`385 -> 897`).
Existing power-cycle evidence classifies it as session/stream state. Every other
readable field matched, both Host-known write-only intents were resent, and no
restoration call failed. No additional device write followed.

Executable analyzer schema `cp34-block201-delegate-lifecycle-v4` and the full
hardware-free suite pass 871 tests with one expected skip. The new Host sequence
is not live-proven. Evidence:
`runs/20260914T152132-0700-corrected-ringmod-live/`.

## 2026-09-14 superseded offline Ring-Mod discriminator design

Pinned firmware SHA-256
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`
source-binds model 3 to constructor `0x58920`, `botb` handler `0x58db0`, and
process `0x4ff6c`. Handler writes on/volume/mix to model offsets
`+0x14/+0x20/+0x2c`; process instructions `0x4ff92..0x4ff9e` derive
`dry=volume*(1-mix)` and `wet=2*volume*mix`, applied at
`0x50366..0x5036a`. The off wet-gain literal at `0x5034c` is zero and the dry
gain remains one.

The offline-ready profile `vol=0, mix=1` therefore has active gains dry 0 / wet
0 and off gains dry 1 / wet 0. This is a decisive scalar test independent of
carrier energy. `re/cp34_ringmod_discriminator_static.py` pins the firmware
slices and instructions; `re/io24_corrected_ringmod_probe.py` implements the
same-process gate control, Ring-Mod A/B/A, and exact restoration. Focused tests
pass 8/8; the full hardware-free suite ran 870 tests cleanly: 869 passed and
one skipped. The later authorized run executed this design, but its Host
sequencing was superseded by the selector-replay correction above.

## 2026-09-14 controlling model-5 execution extension

Pinned firmware SHA-256
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`
source-binds Delay constructor `0x56f34`, tagged handler `0x57240`, process
`0x4ebd4`, and the one-input/two-output in-place buffer descriptor. Tag `vech`
writes on/mix/feedback/time to `model+0x10..+0x1c`; the process reads those
same fields and receives clear descriptor flags.

The process recurrence derives +1.249387 dB expected stationary-white-noise
gain for the live call's fully-wet wire feedback 0.5. Since the retained live
threshold was 1.989850 dB, its scalar null is formally underpowered. Missing
model-5 state or lane binding is not the next hypothesis; use a temporal
signature or a model with a larger predicted scalar change.

Executable analyzer schema is `cp34-block201-delegate-lifecycle-v3`. Combined
focused verification passes 22/22; direct analyzer execution, bytecode compile,
and `git diff --check` pass. No device operation occurred in this extension.

## 2026-09-14 superseded first pacing-corrected live result

The authorized one-writer Delay/gate run completed on serial `AB7C22200355`,
firmware `0128`. The later primary-handler trace proves this state-replay
sequence did not trigger rebuild. Fully wet Delay moved the Main/Input-1 ratio
`-0.148022 dB` against a `1.989850 dB` threshold, with `-0.039869 dB`
off-state drift. It was not detected. The direct Channel-1 gate positive
control moved `-18.313364 dB` against a `12.014095 dB` threshold, with
`-0.049383 dB` drift, so the observation path was sensitive.

The gross gate control does not make this a decisive Delay null. Feedback 1.0
maps to coefficient 0.5, so uncorrelated stationary noise is expected to gain
only `1.249387 dB`, below the `1.989850 dB` threshold. The run is therefore
`INCONCLUSIVE_EXPECTED_LEVEL_SIGNATURE_BELOW_THRESHOLD`: it neither proves
Delay inert nor rejects Host pacing as the audibility mechanism. The next
static target is model-5 process state and actual input/output lane binding.

Readable state restored exactly; Host-known Transformer-off and Channel-1
`MAIN` gate intent were resent without error. Routes, slots, DSP Amount, and
`processingChannel` were untouched. Battery was 82 percent before and after.
Focused probe/sequencing verification passed 14/14 before the live action.
Report SHA-256:
`672083ccb336e08727abe0509dd6567f85511eee6dad177b465a8f0214f9652f`.
Evidence:
`runs/20260914T113431-0700-corrected-fx-rebuild-live/`.

## 2026-09-14 controlling block-201 audio-call-path correction

Pinned firmware proves constructor `0x591bc`'s null `block+0x14` store is only
intermediate. Its model-0 selector `0x55388` calls primary vtable `+0x34`,
`0x5f1f4`; helper `0x5f130` constructs the model at `block+0x60`, stores that
pointer at `block+0x14` (`0x5f170`), and clears `block+0x44` (`0x5f184`).
Handler `0x50af8` forwards incoming messages to delegate `vtable+0x10` before
testing `+0x44/+0x39/+0x40`.

The subsequent audio trace corrects the intermediate “rebuild-only” label.
Block process raw `0x1a580` uses `+0x44` as target bypass (`0=process`,
`1=bypass`), `+0x39` as latched bypass, and `+0x40` as its transition
countdown. Selector sets bypass before replacement; installer clears it after
replacement. Those three fields defer rebuilding until the old model is safely
bypassed; they are not an absent install gate.

The apparent `str ... [block+0x14]` at `0x5f24c` was a linear-disassembly false
positive. Work returns at `0x5f248`; `0x5f24c`/`0x5f250` are PC-relative
literals `0x49466163`/`0x4d525370` used by that function.

The historical “chain installer” at `0x3e608` is also corrected. It calls
`vtable+0x18` on the temporary three-object array, takes the maximum workspace
requirement, and sizes `device+0x11d0`; it retains no member pointers and does
not prove signal-path installation.

The real signal path is nevertheless source-bound. Audio root raw
`0x20546..0x2054e` passes a `stack+0x40` buffer descriptor to block 201 at
`device+0x11e0` and directly calls its process routine. The block invokes the
selected model's process virtual; model 0 reaches raw `0x1e1a8`. The root call
condition is sample rate at or below 96 kHz (`device+0x5e71`) with stereo-link
bit 12 clear, which matches the cold-boot run's declared 96 kHz/unlinked state.
The clean live null is not missing construction, scheduling, or buffer handoff.

The transition is source-bound in the same code. Setup computes a nominal 40 ms
bypass fade; at 96 kHz / 512 it is eight audio blocks, 42.667 ms. The first
pacing correction correctly extended the old 20 ms gap, but mistakenly treated
a model-state frame as the rebuild trigger. Primary handler `0x553d4` proves
ordinary state tags tail-call `0x5079c` and never reach selector `0x55388`.

`Io24.send_fx` now waits 60 ms and replays the selector itself before sending
state. The earlier live Delay and Ring-Mod results exercised the superseded
state-replay sequence; the selector-replay repair is locally verified and
audibility-unproved.

`re/cp34_block201_delegate_static.py` pins the complete paths and critical
slices at schema v4. The full hardware-free suite passes 871 tests with one
expected skip. Evidence:
`runs/20260914T105415-0700-block201-delegate-lifecycle/`. The complete
hardware-free suite immediately preceding the focused extension passed 845
with 1 expected skip and 265 subtests.

## 2026-09-14 controlling physical-storage completion result

The authorized active-slot discriminator subsequently completed and returned
`NO_NATIVE_ACTIVE_SLOT_GATE_EFFECT_DETECTED`. All three native gate bodies were
written while global slot 3 was active and each received a 2 -> 3 recall edge.
Effect delta was -0.068913 dB, off-to-off drift +0.112856 dB, and maximum MAD
0.349676 dB. The pinned Piano body was rewritten while active; readable state
restored exactly, battery stayed 99%, and the device remained `194f:0422` /
firmware `0x0128`. Body restoration is still write-sent rather than readable.
Report SHA-256:
`be5e19f27c703368a52ca3a0e460872fb3ae80b9baba1dff07040de22cc6d46d`.
This rejects inactive-slot timing and closes further `Stat` body variants.

`re/cp34_firmware_physical_storage_commit.py` extends the pinned firmware
ingress proof through device construction, the manager at `device+0x1108`, and
the concrete physical interface at `device+0x1384`. Device initializer
`0x20d3c` passes `device+8` to `0x3d4bc`; that binding is stored at singleton
field `+0x38` and reloaded by adapter `0x316dc/0x316b0` before device-vtable
query slot `+0x10`. Query `0x20808` then projects to the concrete interface.
Vtable `0x6012bc80` binds write slot `+0x4` to `0x4aa90`. The flag-one path
reads and compares existing bytes, runs changed data through program
transaction `0x526dc`, and completes ready poll `0x52a70` before success. No
additional commit/flush call follows on this route. Independent review caught
the formerly missing adapter-to-query join; the corrected analyzer pins it
with exact code-slice hashes, instructions, singleton literal, and direct
branch targets. Focused analyzer TDD passes 2/2.
The final combined ingress, recall, physical-backend, Standard-EQ probe, native
gate probe, and active-slot probe suite passes 18/18. Direct analyzer execution
on the pinned firmware, bytecode compilation, and `git diff --check` pass.

The live discriminator's sequence and restoration contracts pass 3/3. Its
earlier request was rejected before process launch because slot bodies cannot
be read back; that pre-authorization event remains recorded separately and
performed no mutation.

Evidence:
`runs/20260914T075215-0700-physical-storage-active-slot/`.

## 2026-09-06 controlling physical-channel correction and restoration

UC's VoiceFX ownership and the device's physical preset controls are separate
layers. Exact UC 4.7.2 code evaluates `processingChannel == 0` at initial apply
`0x180040729` and refresh `0x18004193f`, both calling ownership switch
`0x18003e6c0`. The owner activates/selects parameter 450 `fxmodel`; the
non-owner deactivates it and selects host sentinel `-1`. `voicefx.on` remains a
separate storable enable inside the selected model.

Neither this branch nor the firmware's exposed slot-value exchange renumbers
the physical preset API. The two prior live attempt-2 runners called
`set_preset_enabled(1, ...)` and `set_preset_slot(1, ...)`; readback shows they
changed physical Channel 1. Their `Stat(3)` transports remain evidence of a
sent record, but both listening results are invalid for Channel-2 recall or
audibility. The per-run classifications are
`INVALID_PHYSICAL_CHANNEL_CONTROL_MAPPING`.

The corrected runner uses physical channel 2 for every bypass, slot, and enable
call, while separately requiring/reasserting the `(1,0)` Input-2 VoiceFX
assignment. The normal Linux factory-preset path now exposes the same layered
order under explicit `with_fx=True`: assign the requested VoiceFX input, select
the model, then apply `voicefx.on` and its fields. Focused verification passes
28/28 across this route and both corrected runners. The final Reverb target is
factory-derived with `voicefx.mix` raised from 0.295 to 1.0 for the requested
maximum-wet discriminator. Record SHA-256 is
`191a5048c4995355932609e9d5ae225f37c50d8f112966f685a11b3f2a08e79c`;
its `Stat(3)` frame SHA-256 is
`d8ea35050b33484444e48c3d54cf1716bce35265a0b2b92f26939ea7bdf92c1f`.

The requested Channel-1 restoration completed on serial `AB7C22200355`,
firmware `0x0128`, at 20 percent battery. Its selector moved from 3 to 0 and it
remained bypassed; gains, link, Input-2 assignment, and Channel-2 state were
preserved. No record write occurred. Therefore neither Channel-1 preset body
was overwritten. Exact evidence is
`runs/20260906T100100-0700-channel2-voicefx-materialization/CHANNEL1-RESTORATION.json`.

The complete hardware-free suite was run as two disjoint commands: 254 passed,
one expected skip, and 44 subtests outside the slow survey; the survey then
passed 41 tests and 11 subtests. Total: 295 passed, one expected skip, and 55
subtests.

The separately authorized corrected sequence then executed once on serial
`AB7C22200355` at 45 percent battery and exited 0. Four pinned
model-before-state messages and one maximum-wet `MemP/Stat(3)` fragment were
sent. Exposed post-state retained Channel 1 at selector 0/bypassed, placed
Channel 2 at selector 3/enabled, retained gains 37/24 and the `(1,0)` Input-2
VoiceFX assignment, and retained stereo link off. Exact output is
`runs/20260906T100100-0700-channel2-voicefx-materialization/LIVE-ATTEMPT-3-CORRECTED-MAX-WET.json`.
The write had no readable reply. The user then unplugged and reconnected the
interface and reported no noticed change. With the deliberately 100-percent-
wet target, that is the terminal stock-firmware negative: the corrected path
did not meet the audible standalone acceptance condition. Exact human evidence
is
`runs/20260906T100100-0700-channel2-voicefx-materialization/STANDALONE-LISTENING-RESULT.md`.
The result does not isolate physical commit, persistence, parsing, model
activation, processing-gate restoration, or recall. The one-run authorization
is consumed, and the project proceeds to Linux-host cleanup and initial GitHub
packaging before any custom-firmware work.

## SUPERSEDED: pre-physical-mapping VoiceFX materialization stage

Run `runs/20260906T100100-0700-channel2-voicefx-materialization/` turns the
Hot Key/model-selection result below into a hardware-free, separately gated
Channel-2 discriminator.

The host now translates the six exact saved VoiceFX class IDs into the correct
model builder and UC field names. `Io24.apply_voicefx_snapshot()` emits the
block-201 `VoFx` model selector before the selected model state and does not
claim processing-gate activation or audibility. For the pinned factory Reverb
component, the sequence is four framed messages: model 0, two `Bqdf` filters,
then `godv`. Their individual SHA-256 values are sealed in `PLAN.json`.

At this earlier checkpoint, the successor stage inserted that four-message
transition before `MemP/Stat(3)`. Its live attempt was later authorized but was
invalidated because it recalled through physical Channel 1. The current runner
keeps all preset calls on Channel 2 and its exact dry result is `OFFLINE_READY`;
that corrected form has not been authorized or executed live.

Verification: final integrated focused run 38/38; complete hardware-free suite
293 tests, zero failures/errors, one expected historical-fixture skip, exit 0
in 185.344 seconds; AST parsing passes for all ten relevant implementation,
runner, and contract Python files. No USB/device, audio, Wine, network,
firmware, or GitHub operation had occurred at this historical checkpoint.

This is the last stock-firmware discriminator. Audible saved VoiceFX after a
fully disconnected, non-computer-powered Channel-2 recall is success. A
repeatable dry result under this exact corrected sequence is the terminal
stock-firmware negative. Custom firmware is deferred until after the initial
GitHub publication.

## 2026-09-06 Hot Key and VoiceFX model-selection route

Run `runs/20260906T090317-0700-hotkey-voicefx-state-route/` is the controlling
hash-pinned static result for the previously unexamined Hot Key path.

UC 4.7.2's component model assigns `processingChannel=149`,
`activePresetSlotIndex=150`, `presetHotKey=151`,
`presetHotKeyTitle=152`, and `voicefxopt/fxmodel=450`. The embedded UI binds a
single momentary transparent `presetHotKey` toggle to the same
`presets/preset` selection path used by the endless preset knob.

The exact parameter-151 dispatch reaches handler `0x1800412b0`. On selects the
complete-channel cached snapshot at `+0x180`; off resolves parameter 150 and
selects the active normal slot. Both enter generic deserializer `0x18002e690`
and the channel post-apply callback. Channel load `0x1800424b0` and save
`0x180042680` explicitly handle nested key `hotkey`; active capture at
`0x180042624` reaches serializer `0x18002e270`, the same serializer called by
`StorePreset` at `0x18003b5b3`.

`voicefx.__classid` deserializer `0x180049870` resolves six model class IDs.
Parameter-450 handler `0x1800491f0` calls factory `0x180049260`, which accepts
`-1` and `0..5`; model zero is Transformer/Doubler and `-1` is no model. Every
real model selection emits block 201, index 0, `VoFx`, size 16 before the
selected mutable child receives its state. `voicefx.on` is separately storable.
Consequently the algorithm used during save comes from UC's host component
tree, not DSP readback.

The source identities are:

- `dspusbdevice.dll`: 4,979,672 bytes, SHA-256
  `de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`;
- `studiolivepanel.dll`: 41,828,312 bytes, SHA-256
  `52e48cb1453b815abc4b55fd0232131e11115d1aceb2eb0ed899750db6c08dd8`;
- component model XML: 20,450 bytes, SHA-256
  `55388fd3fdcf6d5b466991db886d50a2d8c787afe50390cde554e46d74ff2bfc`;
- VoiceFX parameter XML: 13,925 bytes, SHA-256
  `3f5f99bd6efdfd54b65adf15c82d8b9da36116b25b11e3c88a4ad441b9decd89`.

The executable analyzer rejects mutated sources and its focused contract passes
2/2. Classification:
`UC472_HOTKEY_FULL_CHANNEL_OVERRIDE_AND_VOICEFX_SELECTION_ROUTE_SOURCE_BOUND`.
Boundary: runtime propagation, device-resident commit, standalone recall,
simultaneous block-201 routing, and audibility are not proved.

The user's intended Channel-2 closed-host observation was dry pops, with the
second block thinner than bypass or the first block and no identifiable effect.
It was later invalidated as a Channel-2 result because the runner had selected
physical Channel 1. No new device action occurred in this static stage. Custom
firmware, including a possible second independent block-201 model instance, is
deferred until after the initial GitHub publication.

## INVALIDATED: stage sent but physical Channel 1 was selected

The separately authorized retry exited 0 under a faulty assertion. Identity
matched and one complete 842-byte tagged Reverb record was sent only to
`MemP/Stat(3)`, but the runner called the preset APIs with channel 1. Readback
shows Channel 1 moved to slot 3 and became enabled; Channel 2 did not complete
the intended recall. No slot-0 record write occurred.

Only the fire-and-forget `Stat(3)` transport remains usable evidence. It proves
neither nonvolatile commit nor Channel-2 recall/audibility. Exact raw output:
`runs/20260906T064742-0700-channel2-reverb-assignment-correction/LIVE-ATTEMPT-2.json`.

## HISTORICAL: live safe-stop and processing-assignment slot exchange

The first authorized Channel-2 Reverb stage matched the pinned device, passed
the battery gate, and read back `Assign Voice FX = Ch2`. It failed closed at
the obsolete assumption that Channel 2 would remain at the same JaSt slot
index. The run reported `record_write_attempted=false`; no slot body was
written. Cleanup re-sent bypass on wire channel 2 without readback and closed;
after the processing swap that write cannot be claimed as physical Channel-2
bypass. Final exposed enable state is unavailable.

The exact firmware explains the state transition. The pinned 66-byte slice at
`0x2e77a` has SHA-256
`4fed3b4674f89b8a94498cf064f9e38fc8f5336da454bff5aeb399b9c4ae1093`.
Its register flow reads slot indexes 0 and 1, then invokes wire id `0x10`
(`Pari/16`) for target indexes 0 and 1 in exchanged order. Therefore a changed
`Pari/12` assignment swaps the two active slot indexes: physical Input 2's
slot-2/3 family follows it onto processing chain 1.

That historical correction was incomplete: it mistook processing-chain
ownership for physical preset-control addressing. The current runner accepts
the retained Input-2 assignment but calls every preset API with physical
channel 2. See the current run's `LIVE-ATTEMPT-1.json` and the later corrected
materialization run.

## 2026-09-06 controlling Channel-2 assignment correction

The previous top-level conclusion promoted four embedded firmware default
shapes into a legal slot-ownership rule. That conclusion is retracted.

Exact UC 4.7.2 `DEFAULT.SKIN` member `uceasy/settings.xml` contains the form
`EasySetingsItem.AssignVoiceFX`, label `Assign Voice FX`, and radio controls
`line/ch1/processingChannel` with `Ch1=0` and `Ch2=1`. The component model marks
`processingChannel` storable. Retained UC scene files independently contain a
`voicefx` member in every one of their four `presets.slots` entries.

The exact active-slot host writer emits a tagged mapping beginning with byte
`0x7b` through `MemP/Stat`. The four version-2 chunk records found in firmware
remain valid startup/default observations; their component presence or absence
does not constrain the fields a UC save may target to Channel 2.

The prior Channel-2 Slap Echo run left the processing map at its baseline
`0/1` values. It did not issue the UC `Ch2` assignment and therefore cannot
answer whether the saved effect is recalled on Channel 2. The new bounded
discriminator sets `line/ch1/processingChannel=1`, writes the exact complete
factory Reverb record only to global slot 3, recalls/enables it only through
Channel 2, and leaves the physical persistence/audibility result to the user's
disconnected cold-boot check.

The exact encoded Reverb record is 842 bytes, SHA-256
`c85119953bef5fd41f83f4b60e207519e9d57c6bf174f9d8a8e7ce6a88ed65c4`;
its one-fragment `MemP/Stat(3)` frame SHA-256 is
`e9154a66a7691ae8e415b891eab299310a3899df9b6cb2658ebb94d99ccf4306`.
Focused verification passes 61 tests and 12 subtests; the complete
hardware-free suite passes 272 tests and 47 subtests with one expected skip.
That statement describes the pre-live checkpoint; the later bounded safe-stop
and its correction are recorded above.
See `runs/20260906T064742-0700-channel2-reverb-assignment-correction/`.

The two sections below are retained as superseded chronology, not current
constraints.

## 2026-09-06 user-prohibited Channel-1 target

The user rejected slot 0 and requested an actual second-channel slot. No live
write had occurred. The slot-0 plan is cancelled, and the staging runner now
blocks live use of both Channel-1 owning slots before device open under the
current requirement.

The source-bound native layout supplies no model-0 substitution in Channel-2
slots 2/3: both contain `opt ` only, with no numeric component 201. Shared
block-202 reverb is likewise not part of any native slot record. Thus a stock
Channel-2 slot cannot store the requested private reverb. Focused verification
including the new user-prohibition gate passes 21/21. See
`runs/20260906T050813-0700-standalone-native-model0-preflight/CHANNEL2-CONSTRAINT.md`.

## 2026-09-06 standalone model-0 acceptance preflight

Run `runs/20260906T050813-0700-standalone-native-model0-preflight/` converts the
native slot/layout result below into one bounded physical question. The pass
condition is human-audible model-0 private reverb after a cold transition from
computer USB to non-computer USB power, with recall/control performed on the
unit. No transport or connected-host observation substitutes for that result.

The exact first candidate targets native slot 0 and physical Input 1. It is
1092 bytes with SHA-256
`da1b3e00463ed6e51139119611ef18ba8b8286d4db41f7d6dac7290e2f041c57`.
It retains the pinned firmware slot-0 Fat Channel byte-for-byte and changes only
component 201 to enabled parent-version-6 model 0 with the mapped
`on/lows/width/lows-mirror/mix` words. The exact firmware-default restoration is
SHA-256
`1cf1d764c48be395c1e5af43d6c37cc0ced2aa27ba4408d2c112b9cf251f4df7`.
Unknown current slot contents remain unreadable and cannot be backed up.

The new staging runner validates record, slot, hash, battery, identity,
firmware, link, selector family, command order, and exposed post-state. It also
normalizes the driver's zero-based processing-channel readback to physical
Input 1/2 operator language. It deliberately reports storage, standalone
recall, and audibility as unproved. Focused tests pass 20/20; exact dry run is
`OFFLINE_READY`; compilation passes. The final complete hardware-free suite
passes 261 tests with one expected skip, no failures, and exit 0 in 160.291
seconds.

No live action occurred. The exact slot-0 overwrite and interface/read/write
scope remain separately gated in `LIVE-PLAN.md`.

## 2026-09-06 native Stat layout, slot family, and model-0 bridge

Run `runs/20260906T044958-0700-native-stat-slot-family/` resolves the format
and ownership attribution that the preceding host/UI trace left open.

Exact source identities:

- UC 4.7.2 `dspusbdevice.dll`: 4,979,672 bytes, SHA-256
  `de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`;
- embedded package: SHA-256
  `790f668608448b7c9f244c360ad72e3c51f71b4e8a3d828eab0e08cd03b35de1`;
- firmware 1.28 application: 1,104,448 bytes, SHA-256
  `65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.

Startup copy entry raw `0x310` copies package address `0x60149c40` to RAM
`0x202b0e00`, length `0xa4d`. Its initialized pointer table binds the first
four entries to raw records `0x69230`, `0x69670`, `0x69ab0`, and `0x69eb4`.
The descriptor-length table at raw `0x691e0` is exactly
`[0x440, 0x440, 0x404, 0x404]`; the records are contiguous and end at
`0x6a2b8`. The next sixteen pointers bind tagged factory/library archives, with
`Broadcast` first at `0x6a2b8` and prefix `7b690b70`.

Every native record begins with little-endian u32 version `2`, then a
length-delimited chunk directory. Their nested channel strip contains `filt`
120 bytes, `gate` 128, `comp` 228, `eq  ` 432, and `lim ` 28. Slots 0/1 also
contain numeric component key 201 and slots 2/3 do not. This matches the
source-bound storage-dispatch families and directly retracts the prior
paired-channel JSON write assumption. It does not restrict Voice FX to physical
Input 1: the host processing-channel selector can route the singleton to either
input, traditionally one at a time.

The component-201 parent version is `6`. Both native owning defaults select
model 5; their 16 state bytes are exactly
`000000000000003fcdcccc3d5c8f423e`, matching mapped Delay state. Model-0
serializer `0x53680` emits a u32 byte count `0x14` and copies exactly `0x14`
bytes from `model+0x340`. The already source-bound `godv` path names those
words `on/lows/width/lows-mirror/mix`. The new encoder reproduces the exact
same five words as the existing direct model-0 builder while retaining every
non-Voice-FX byte from its native base.

`io24_native_stat.py`, `re/cp34_native_stat_layout.py`, and their hardware-free
contracts make the distinction executable. `save_device_slot()` now rejects a
tagged archive and enforces slot-family ownership before `_exec`; the former
paired JSON and factory Slap Echo actions refuse before any read, write, or
selector change.

Controlling result:
`FIRMWARE128_NATIVE_STAT_SLOT_FAMILY_AND_MODEL0_LEAF_SOURCE_BOUND`.

No physical record was read or written. Receipt, backend commit, persistence,
front-panel recall, power-cycle survival, activation, and audibility remain
unobserved and require separate live authority. The distinct model-0 private
reverb core has two bound lane indexes, establishing capacity but not stock
simultaneous activation; that routing/gate is now the specific live question.

The host/UI sections below remain evidence for the tagged library workflow.
Their claims of a missing native-prefix transformation and a paired JSON slot
representation are superseded.

## 2026-09-06 exact UC 4.7.2 Save/Assign UI route

The latest offline run is
`runs/20260906T010449-0700-uc472-save-assign-ui-route/`. It pins the exact UC
4.7.2 panel, service, main executable, UCNet, and DSP modules. The predecessor
checkpoint verified 14/14 entries before these shared files changed.

The panel RCDATA resource `DEFAULT.SKIN`, RVA `0x1320348`, file offset
`0x1305f48`, is a 21,371,451-byte `PACKAGEF` container with 275 members. Its
`uceasy/uceasy.xml` member has compressed offset/size `0x14579b5`/5,918 and
raw size/SHA-256 39,057/
`a710cf06425a48ff1bb0e9ae72ad74d15613b939e675d134b27f4441074d5dfa`.
The parsed XML contains `presetSlot` radio values 1..4, labels the remote model
`Device Presets`, binds `storeNamedRemotePreset` to `Store`, and places
`sendToMixer` between the local and remote preset lists.

Panel registration and dispatch establish:

- `sendToMixer`, ID `0x452`, event `0x1800f9178` -> `0x1800fe080` ->
  `0x180113ba0`; the generic transfer validates `MixerPreset`, captures
  through owner `+0x298`, creates `ZStr` items, and inserts them into the
  remote list model;
- `storeNamedRemotePreset`, ID `0x45f`, event `0x1800f94a3` ->
  `0x180103ba0`; calls at `0x180103e77`/`0x180103e82` resolve to the exact
  UCNet network and file-transfer manager imports;
- Jackson vtable `0x1803b25a8 + 0x220` -> `0x18006ef10`, which constructs
  `StorePreset` with `presets`, `presetFile`, and `presetTarget`, then
  dispatches through object `+0x298`, vtable `+0x80`.

The exact DSP receiver `0x18003aef0` recognizes the matching `StorePreset`.
Its branch calls serializer `0x18002e270` at `0x18003b5b3`, updates the
selected record, and calls helper `0x180037250` at `0x18003b5dc`. That helper
constructs `PrsM` plus `Appl` and reaches the existing `MemP` fragmenter
`0x180050f10`. This source-binds the high-level Store endpoint to the existing
user-library sender, while runtime UCNet delivery between the statically
matched endpoints remains unobserved.

The UI's `Device Presets` library is the `PrsM` 16..27 route. It is distinct
from `presetSlot` 1..4, whose existing settled-state DSP path maintains
`Stat` 0..3. No separate Assign frame or native-u32-two producer was located
in this exact route. The exact `Stat` writer still begins its physical record
at byte `0x7b` with no inserted prefix.

The result is
`UC472_SAVE_ASSIGN_UI_ROUTE_SOURCE_BOUND_TO_EXISTING_DEVICE_LIBRARY_AND_SLOT_STATE_PATHS`.
The exact boundary is
`STATIC_UI_AND_HOST_MESSAGE_ROUTE_RESOLVED_RUNTIME_UCNET_DELIVERY_FORMAT_TRANSFORMATION_PHYSICAL_COMMIT_RECALL_AND_AUDIBILITY_UNOBSERVED`.
Therefore a Linux-native reimplementation is plausible, but no simple
DLL/syscall or one-packet Wine workaround is source-bound. The remaining safe
offline direction is the high-level state-machine behavior and unresolved
format seam, not a guessed frame.

TDD recorded 2/2 intended failures before implementation and focused GREEN
2/2 afterward. Related reconciliation passed 12/12; the complete
hardware-free suite passed 240 tests with one expected skip in 199.013
seconds, exit 0. No Wine prefix, vendor code, USB/device, audio, front-panel,
preset/effect, firmware-image, install, network, or REAPER action was used.

## 2026-09-06 exact UC 4.7.2 save serializer

The officially reacquired Universal Control 4.7.2.108537 installer is exactly
186,792,552 bytes with SHA-256
`1b5ddd6fd3ad4b93529caf8e5933bcd52b13194bdfa62652292b46ddcd980b95`.
Its Nullsoft payload was decompressed as data without execution. The retained
4,979,672-byte `hwaccess/dspusbdevice.dll` has SHA-256
`de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`,
exactly matching the historical UC 4.7.2 pin.

The same `r14d` slot is passed through snapshot
`0x180041c1c -> 0x1800420c0` and send
`0x180041c33 -> 0x1800421c0`. Snapshot resolves the selected record and calls
serializer `0x18002e270`, which returns success immediately afterward.

The serializer resets the selected record cursor through record vtable slot
`+0x8 -> 0x180063020`, clears length `+0x30`, installs writer vtables
`0x18043aa08/0x18043aa50`, and stores the record at writer `+0x18`. Null-name
archive opener `0x1800688b0` takes its zero-length branch and presents exactly
one byte `0x7b` through secondary writer slot `+0x8` at `0x180068a1e`.

That slot resolves to adapter `0x1800649a0`, which obtains writer `+0x18` and
tailcalls record append `0x180063060`. Append calls the PE import `memcpy` with
destination `record.data(+0x10) + record.cursor(+0x2c)`, the one-byte source,
and size one. Cursor and length advance from zero to one; no prefix or headroom
is inserted. Same-slot sender fragmenter `0x180050f10` subsequently reads the
record's data `+0x10` and length `+0x30`.

The exact result is
`UC472_SAVE_SERIALIZER_SOURCE_BOUND_RECORD_BYTE_ZERO_0X7B_NO_NATIVE_U32_TWO_PREFIX`.
The sealed firmware ingress/storage and recall analyses show record byte zero
reaches `0x531e0` unchanged. Its required native little-endian u32 `2` begins
with `0x02`, so the exact UC 4.7.2 save record beginning `0x7b` is ineligible
for that gate as serialized.

The boundary is
`UC472_SERIALIZER_RESOLVED_DEVICE_COMMIT_RUNTIME_COMPONENT_SELECTION_AND_AUDIBILITY_REMAIN_UNOBSERVED`.
This does not prove a device write, backend commit, physical stored bytes,
preset round trip, runtime component selection, Voice FX activation, or
audibility.

TDD recorded the intended two-test RED for the absent analyzer. Focused GREEN
passed 2/2, related UC 4.7.2/UC5 and firmware reconciliation passed 8/8,
direct execution and compilation passed, and the complete hardware-free suite
passed 238 tests with one expected skip in 189.613 seconds, exit 0. The
pre-existing unclosed-WAV `ResourceWarning` at
`re/cp34_current_slot_survey.py:260` did not affect the successful exit.
Independent review remains open. No vendor binary was loaded; no device, USB,
audio, Wine, install, firmware-image, preset/effect, or REAPER action occurred.
Network use was limited to the one authorized official installer acquisition.
Evidence is in
`runs/20260906T001130-0700-uc472-official-reacquisition/`.

## 2026-09-05 final derived zero-selector receiver correction

The exact stored-record recall selector is `{0,0}` and returns device global
`0x20216660`. Lazy initializer `0x3d4f0` passes that global to derived
constructor `0x5e014` at direct call `0x3d52a`. The derived constructor first
calls base constructor `0x5d990` at `0x5e018`. That base temporarily installs
primary vtable `0x6008d3a8`, whose raw `+0x38` slot does target the four-byte
success/no-op at `0x3ccb4`.

The derived constructor then overwrites the base tables. It loads exact header
pointer `0x6012cb38` from literal raw `0x5e08c`, adds eight at `0x5e02a` to
form final primary vtable `0x6012cb40`, and stores it to `[global+0]` at
`0x5e036`. The final table has raw slot zero `0x10cb40 -> 0x420bc` and raw slot
`+0x38` `0x10cb78 -> 0x531e0`. The header pointer occurs exactly once. The
formed final pointer occurs zero times literally, which is expected and is not
evidence that the table is unbound.

Function `0x41580` restores base vtables, but initializer `0x3d4f0` loads it as
a callback only after derived construction and registers it through
`0x3d536 -> 0x5fc04`. It is teardown, not the state left by construction.
Confusing these transient base-construction and teardown writes with final
derived state caused the provisional no-op result.

Dispatcher `0x420bc` captures the selected global in `r5`; both virtual calls
at `0x42266` and `0x42280` load final slot `+0x38` and reach `0x531e0`. The
source-bound controlling results are:

- `ZERO_SELECTOR_STAT_ROUTE_SOURCE_BOUND_FINAL_DERIVED_SLOT_0X38_0X531E0`;
- `STAT_STREAM_CURSOR_ZERO_SOURCE_BOUND_FIRST_WORD_FROM_ACCUMULATION_BUFFER`;
- `STORED_STAT_RECALL_SOURCE_BOUND_BYTE_PRESERVING_NO_PREFIX_INSERTION`;
- `FIRMWARE_STAT_INGRESS_RECALL_SOURCE_BOUND_LOGICAL_BYTE_ZERO_UNCHANGED_NO_PREFIX_INSERTION`.

The outer host `{Appl,0}` envelope is not passed literally as the selector query
on this stored-recall route; the actual selector query is `{0,0}`. The initial
premise of the current run was narrowed accordingly. Physical backend commit,
the exact UC 4.7.2 serializer, device-resident round trip, runtime component
selection, Voice FX activation, and audibility remain unobserved.

The previous run
`runs/20260905T212623-0700-zero-selector-recall-vtable-correction/` remains
unchanged, but its no-op route conclusion is explicitly retracted. Its
checkpoint has ten expected stale shared-file rows after this correction and
seven verifying immutable/task-local predecessor rows; it is not a restore
source for current shared files. The superseding evidence is in
`runs/20260905T231733-0700-appl-zero-selector-receiver/`.

Fresh verification passed 53/53 affected contracts, including the 47/47
firmware-static module. Python compilation passed. The complete hardware-free
suite passed 235 tests, one expected skip, and 47 subtests in 158.89 seconds,
exit 0. The recurring `Failed to create stream fd` diagnostic did not affect
the successful exit. Independent review remains open. No device, USB, audio,
Wine, network, firmware-image, preset/effect, or REAPER action occurred.

The exact boundary is
`0X531E0_RUNTIME_COMPLETION_SELECTED_COMPONENT_AND_PHYSICAL_OUTCOMES_REMAIN_UNRESOLVED`.

## 2026-09-05 firmware ingress/storage framing

Pinned firmware 1.28 now has an exact logical-byte path from accepted incoming
`MemP/Stat` through record writer, storage wrapper, paired reader, and the
sealed recall-to-parser route. The 1,104,448-byte application SHA-256 is
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`;
it was recovered from the installed package in memory only.

The root retains its preset component at `root+0x70 = root+0x1240`. Root
handler `0x2f210` preserves the incoming message and dispatches via component
vtable `0x600874f8` slot `+0x18` to handler `0x3099c`. Its `Stat` path calls
record writer `0x3092c` at `0x30a06`.

For fragment offset zero, writer `0x3092c` first passes the four-byte total
record length at message `+0x19` to wrapper `0x2bfe4`. It then passes payload
source `message+0x1d` and the exact u16 fragment length at message `+0x17` to
the same wrapper. No prefix pointer, size increase, or source transformation
occurs.

Wrapper vtable `0x60086994` resolves write to `0x2bfe4`, read to `0x2c0a8`,
and overhead to eight bytes. The write-side backend-address layout is:

```text
storage_address + 0: CRC32
storage_address + 4: payload length
storage_address + 8: payload bytes
```

Reader `0x2c0a8` consumes CRC32 and length into its own stack, reads exactly
the stored length from `+8` into the caller destination, recomputes CRC32 over
that destination, and returns the payload length only on success. It never
exposes the wrapper header.

Constructor and startup binding resolve backend vtable `0x600876ec`. Slot 0
forwards the same address/source/length through `0x316dc/0x316b0`, adding only
a separate write flag one. Slot `+4` forwards the same read arguments through
`0x3170c/0x316e4`. Slot `+0xc` reaches `0x3198c/0x3196c`, whose bytewise call
to `0x3665c` is CRC32.

Stored-record reader `0x30a90` reads the separate total length into message
`+0x19`, advances by its four logical bytes plus eight wrapper bytes, and reads
serialized payload into message `+0x1d`. The result is
`FIRMWARE_STAT_INGRESS_RECALL_SOURCE_BOUND_LOGICAL_BYTE_ZERO_UNCHANGED_NO_PREFIX_INSERTION`.

The sealed recall stage then presents
`little_endian_u32(incoming_payload[0:4])` at `0x531e0`. Conditional prefix
`7b690b70` remains native word `0x700b697b`, not required word `0x00000002`.
The storage header cannot satisfy that gate because it is not parser-visible.

The boundary is
`PHYSICAL_BACKEND_COMMIT_AND_UC472_SERIALIZER_REMAIN_UNOBSERVED`. This closes
the explicit firmware ingress/storage-transform uncertainty but does not prove
the backend physically committed bytes, the unit contains them, or the missing
UC 4.7.2 serializer emits current UC5's format. Persistence, component
selection, Voice FX activation, and audibility remain unobserved.

The intended two-test RED failed on the absent analyzer. Focused GREEN passed
2/2, related ingress/recall/UC5/persistence contracts passed 32 tests and 6
subtests, Python compilation passed, and the complete hardware-free suite
passed 233 tests with one expected skip in 160.306 seconds, exit 0. Its only
diagnostic was the pre-existing unclosed-WAV `ResourceWarning` at
`re/cp34_current_slot_survey.py:260`. Independent review remains open. Passive
sysfs reported BAT0 at 99 percent and not charging. No device, USB, audio,
Wine, network, firmware-image, preset/effect, or REAPER action occurred.
Evidence is in
`runs/20260905T210639-0700-firmware-ingress-storage-framing/`.

## 2026-09-05 UC5 record-writer sink

The exact installed UC5 serializer's logical first byte is now source-bound to
physical byte zero of the selected record. The 4,984,704-byte module SHA-256
is
`567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`;
it was read as data and never loaded or executed.

Serializer `0x18002e9e0` captures the output record in `r14`. Record vtable
slot `+0x8` resolves to reset `0x1800643b0`, which places zero at cursor
`+0x2c`; instruction `0x18002ebbd` separately clears length `+0x30`. The
stack writer uses primary vtable `0x18043bbd8`, secondary vtable
`0x18043bc20`, and binds `writer+0x18 = r14`.

Archive call `0x180069dae` supplies source byte `0x7b`, size one, through
secondary writer slot `+0x8`. Vtable evidence resolves that slot to adapter
`0x180065d30`. From the secondary receiver it follows `+0x10` to original
`writer+0x18`, obtains the selected record, and tailcalls record vtable slot
`+0x18`, exact append target `0x1800643f0`.

Append reads cursor zero and copies exactly one byte through the PE import
`memcpy` to `record.data(+0x10) + record.cursor(+0x2c)`. It then advances
cursor and length to one. There is no prefix offset or additional write. The
result is
`UC5_RECORD_WRITER_SOURCE_BOUND_PHYSICAL_BYTE_ZERO_0X7B_NO_PREFIX_INSERTION`.

Snapshot returns immediately after serialization. The caller passes the same
slot to send with no record mutation, and fragmenter `0x180052270` reads data
`+0x10` and length `+0x30`. This closes the UC5 logical-writer versus physical-
record uncertainty.

The boundary is
`UC5_ONLY_UC472_AND_FIRMWARE_INGRESS_STORAGE_TRANSFORM_UNRESOLVED`.
UC5 does not establish missing UC 4.7.2 behavior. Firmware ingress from
incoming `MemP/Stat` to stored bytes is not yet bound closely enough to exclude
a storage transformation. The connected unit's stored bytes, persistence,
recall, component selection, Voice FX activation, and audibility remain
unobserved.

The intended two-test RED failed on the absent analyzer. Focused GREEN passed
2/2, related writer/serializer/recall contracts passed 6/6, direct analyzer
execution and Python compilation passed, and the complete hardware-free suite
passed 231 tests with one expected skip in 160.888 seconds, exit 0. Its only
diagnostic was the pre-existing unclosed-WAV `ResourceWarning` at
`re/cp34_current_slot_survey.py:260`. Independent review remains open. Passive
sysfs reported BAT0 at 99 percent and not charging. No device, USB, audio,
Wine, network, firmware-image, preset/effect, or REAPER action occurred.
Evidence is in
`runs/20260905T204944-0700-uc5-record-writer-sink/`.

## 2026-09-05 firmware stored-record recall framing

Pinned firmware 1.28 now has an exact byte/framing route from selected `Stat`
record reader `0x30be0` to the first native-u32 read at structured-state method
`0x531e0`. The 1,104,448-byte application SHA-256 is
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`;
it was recovered from the installed package in memory only.

Storage reader `0x30a90` puts record length at message `+0x19` and reads stored
payload bytes directly to message `+0x1d`. The zero-length descriptor fallback
`0x30c2a -> 0x30708` also copies source bytes directly to `+0x1d`. Recall
driver `0x2f0d0` passes the complete message with two zero metadata words to
callback `0x2f8ac`, which constructs
`SetP | 0 | 0 | nested Stat message` without changing the nested payload.

Manager and application routing reach singleton forwarder `0x3cc40`. The
previously omitted dynamic seam is now bound through lazy singleton cell
`0x20216664`, vtable `0x6008d3f0`, adjustor `0x41b6c`, and packet router
`0x419a0`. Its zero/zero selector route `0x3cf20/0x3ce98` returns the primary
live device. The `SetP` branch retains `r1 = packet+0xc` and invokes live
dispatcher `0x420bc` through final primary vtable `0x6012cb40` slot 0.

The exact route correcting the older shorthand is:

```text
0x3cc40
  -> 0x41b6c/0x419a0
  -> 0x3cf20/0x3ce98
  -> 0x420bc
```

Dispatcher `0x42200` copies `Stat+0x1d` into the accumulation buffer unchanged.
The non-owning reader remains at cursor zero and `0x42266 -> 0x531e0` consumes
the stored record's first four bytes. The result is
`STORED_STAT_RECALL_SOURCE_BOUND_BYTE_PRESERVING_NO_PREFIX_INSERTION`.

The consumed word is exactly
`little_endian_u32(stored_record[0:4])`; recall does not supply native u32 `2`.
Conditionally, stored bytes `7b690b70` reach the gate as `0x700b697b` and fail
its required value `2`.

The boundary is
`PHYSICAL_STORED_BYTES_AND_UC472_SERIALIZER_REMAIN_UNOBSERVED`. The unit's
actual stored bytes were not read. Physical commit, recall success, Voice FX
activation, audibility, and UC 4.7.2 output remain unresolved. The UC5 archive
opener's logical `0x7b` writer input is not yet source-bound through writer
slot `+0x8` to record-buffer byte zero; that is the next safe static question.

The intended two-test RED failed on the absent analyzer. Focused GREEN passed
2/2, the new framing plus prior recall/UC5/cursor contracts passed 55/55 in
19.66 seconds, and Python compilation passed. Complete hardware-free
reproduction passed 229 tests with one expected skip in 156.897 seconds, exit
0; its only diagnostic was the pre-existing unclosed-WAV `ResourceWarning` at
`re/cp34_current_slot_survey.py:260`. Independent review remains open. Passive
sysfs reported BAT0 at 100 percent and full. No USB/device, audio, Wine,
network, firmware-image, preset/effect, or REAPER action occurred. Evidence is
in
`runs/20260905T202119-0700-firmware-stored-record-recall-framing/`.

## 2026-09-05 UC 5.0 structured-state serializer comparison

The installed UC5 `dspusbdevice.dll`, size 4,984,704 and SHA-256
`567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`,
now has an exact hardware-free serializer comparison. This source is not the
missing 4,979,672-byte UC 4.7.2 module.

One caller uses the same `r14d` slot for snapshot
`0x18004239c -> 0x180042840` and send
`0x1800423b3 -> 0x180042940`. Snapshot resolves the selected record at
`0x180042888 -> 0x1800427e0`, passes it as serializer output `rcx`, and calls
`0x180042893 -> 0x18002e9e0`. The serializer captures the output in `r14`,
resets the record, clears `[r14+0x30]`, binds it as writer output, and calls
archive opener `0x180069c40` with a null/empty name.

The opener's zero-length branch `0x180069c76 -> 0x180069d96` presents one
logical byte `0x7b` (`{`) to writer slot `+0x8`. Dynamic sender
`0x180042940` selects
`[controller+0x2d8] + slot*0x38`, passes the record in `r9`, and dispatches
`{Appl,0}/{Stat,slot}` through the `controller+0x308` vtable. Constructor and
vtable evidence resolve slot `+0x10` to `0x180052270`; that fragmenter reads
record length `+0x30` and data pointer `+0x10`, copies the first fragment via a
PE import resolved as `memcpy`, and queues it at `0x1800546b0`.

The result is
`UC5_SAVE_SERIALIZER_SOURCE_BOUND_TAGGED_MAP_OPENER_NOT_NATIVE_U32_TWO`.
This pins the archive opener's first logical writer input. It does not yet pin
the writer implementation's physical record-buffer byte zero.

The sealed controlling boundary was
`UC5_ONLY_UC472_AND_FIRMWARE_RECALL_TO_LIVE_STAT_BRIDGE_UNRESOLVED`. The later
firmware-framing evidence resolves the recall bridge but exposes the narrower
UC5 writer-sink question. This still does not establish UC 4.7.2 behavior or
justify adding a prefix. Physical persistence, writer-sink framing, component
selection, Voice FX activation, audibility, and custom-firmware readiness
remain unresolved.

The two-test intended RED failed on the absent analyzer. Focused GREEN passed
2/2, related serializer/queue tests passed 5/5, Python compilation passed, and
the complete hardware-free suite passed 226 tests with one expected skip and
47 subtests in 155.19 seconds, exit 0. Independent review remains open. No
vendor binary was loaded or executed and no USB/device, ALSA, Wine, network,
firmware-image, preset/effect, or REAPER action occurred. Evidence is in
`runs/20260905T200005-0700-uc5-structured-state-serializer-comparison/`.

## 2026-09-05 UC 4.7.2 host-source retention audit

The exact host artifacts required for the next byte-level serializer trace are
not currently available in the bounded accessible local roots. The historical
UC 4.7.2 manifest reports its installer, executable, `cclgui.dll`, and
4,979,672-byte `dspusbdevice.dll` `/tmp` rows missing; its six analyzer, tests,
inventories, report, and installed UC 5.0 comparison rows remain intact. Bounded
exact-name/exact-size searches found no accessible copy and did not access any
Wine prefix or recursively inspect `Windows.old`.

The result is
`UC472_HOST_SERIALIZER_SOURCE_UNAVAILABLE_IN_BOUNDED_LOCAL_ROOTS`. It limits
the next exact analysis; it does not change the older source-bound conclusions
that were preserved in the independently reviewed report. That report and its
JSON inventories retain topology but not the exact byte-level serializer slice
needed to resolve the newly identified leading-word question.

The installed UC 5.0 comparison DLL is 4,984,704 bytes with SHA-256
`567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`;
it is not the missing UC 4.7.2 module whose SHA-256 is
`de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.
Reacquisition requires separate explicit network authorization. Until the
exact source is restored and validated, the leading representation remains
unresolved and no framing change or device replay is justified. Artifacts are
in `runs/20260905T183725-0700-uc472-host-source-retention-audit/`.

## 2026-09-05 structured-state input cursor provenance

The live `Stat` branch now has a source-bound byte path into structured-state
method `0x531e0`. At `0x42200..0x4221e`, the dispatcher reads a fragment offset
from input-object `+0x12`, advances its source to `+0x1d`, and copies caller
bytes into the capped device accumulation buffer at `device+0x18+offset`.
After completion byte `+0x16` becomes zero, constructor `0x2ccf4` makes a
non-owning reader over `device+0x18`, stores its limit at reader `+0x20`, and
initializes cursor `+0x1c` to zero. The direct call at `0x42244` retains cursor
zero before the stream is passed at `0x42266`.

At `0x531e0`, the first four-byte request forwards through the stack reader's
vtable slot raw `0x669f4` to `0x2cbb4`. That reader loads the data pointer at
stream `+0x8`, adds cursor `+0x1c`, copies the requested bytes, and advances the
cursor. The result is
`STAT_STREAM_CURSOR_ZERO_SOURCE_BOUND_FIRST_WORD_FROM_ACCUMULATION_BUFFER`.
The actual word remains caller-supplied for arbitrary traffic.

For an object whose live `Stat` fragment has offset zero at `+0x12`, completion
zero at `+0x16`, length 850 at `+0x19`, and raw archive data `7b690b70` at
`+0x1d`, the cursor trace proves that native word `0x700b697b` reaches the gate
directly, where integer `2` is required. The existing Linux `MemP/Stat` builder
does produce those nested field values, but this stage does not prove that the
stored save frame reaches the later live dispatcher unchanged. The valid host-
or recall-generated leading representation, physical storage, factory-recall
framing, and sufficiency of a four-byte prefix all remain unresolved.

After one initial missing-key test error was corrected to an assertion failure,
the intended RED was observed. Focused GREEN passed 1/1 in 16.871 seconds, the
firmware-static module passed 46/46 in 18.210 seconds, the existing framing
module passed 24/24 in 0.182 seconds, and the complete hardware-free suite
passed 225 tests with one expected skip in 159.328 seconds, exit 0. No firmware
image, USB/device, ALSA, preset/effect, Wine, network, reset, DFU, install, or
REAPER action occurred. Artifacts are in
`runs/20260905T181808-0700-structured-state-input-cursor-provenance/`;
independent review remains open.

## 2026-09-05 structured-state record-prefix gate

Pinned instructions now bind the pre-selection gate in structured-state method
`0x531e0`. The method constructs a stack wrapper at `sp+0x60`, installs
specialized vtable `0x66b54`, and stores the incoming record stream at wrapper
offset `+0x8`. The vtable's first slot targets `0x2cd20`, which forwards to the
underlying stream's `+0x8` method. Reader `0x2ce10` requests exactly four bytes.
The wrapper was constructed with its byte-reverse flag zero, so the reader's
`rev` branch is skipped.

At `0x5320e` the method loads the resulting native word. `0x53212` requires
integer `2`, and only the equal branch at `0x53216` reaches `0x53222` and the
later component-selection gates. The retained factory Slap Echo archive at raw
`0x6b1c8` begins `7b690b70`. The existing pure `MemP/Stat` encoder independently
produces the same prefix. Without reversal those bytes are native word
`0x700b697b`, not `2`.

The result is
`STRUCTURED_STATE_PREFIX_GATE_SOURCE_BOUND_RAW_FACTORY_ARCHIVE_NOT_DIRECTLY_ELIGIBLE`.
This establishes that the raw archive cannot be supplied unchanged from byte
zero to this entry and pass. It does not establish that the raw record was not
stored, that stored bytes differ, or that recall rejects the record. No edge in
the bounded slice proves whether framing is stripped, a cursor is advanced, a
type word is prepended, or another transformation occurs before this method.
Physical commit, stored-record equality, selected component index, Voice FX
activation, and audible processing remain unresolved.

The intended focused contract passed 1/1 in 16.853 seconds after its observed
missing-report-key RED. The firmware-static module passed 45/45 in 18.537
seconds. The complete hardware-free suite passed 224 tests with one expected
historical-artifact skip in 233.126 seconds, exit 0; its only diagnostic was the
pre-existing unclosed-WAV `ResourceWarning` at
`re/cp34_current_slot_survey.py:260`. No firmware image, USB/device access,
ALSA, preset/effect action, Wine, network, reset, DFU, install, or REAPER action
occurred. Artifacts are in
`runs/20260905T172026-0700-structured-state-record-prefix-gate/`; independent
review remains open.

Resume reconciliation repaired the interrupted zero-byte checkpoint manifest.
Fresh reproduction passed the focused contract 1/1 in 16.609 seconds, the
firmware-static module 45/45 in 18.427 seconds, and the complete hardware-free
suite 224 tests with one expected skip in 158.624 seconds, exit 0. The rebuilt
six-row manifest then verified 6/6.

## 2026-09-04 linked gate-transition audible-path result

The operator authorized one bounded low-level gate-transition trial and asked
the assistant to perform the listening. Offline-first implementation added a
byte-pinned factory-gate action, a default-dry execute-gated runner, and a
strict six-channel analyzer. The focused eligibility set passed 26 tests; the
scope and four gate blobs were sealed before live access; battery was 53
percent at execution; and serial-pinned preflight returned flags `0x1a1`, link
off, Channel 1 disabled on slot 0, and Channel 2 enabled on slot 3.

The single execution completed Channel 2 `3 -> 2`, stereo link on, Channel 2
`2 -> 3`, exact factory gate on, gate off, exact gate-on restoration sent, and
stereo link off. It made no playback, gain, routing, output, or preset-content
change. The action's final readable Channel-1 guard matched baseline. A
separate postflight returned the exact starting slot/link flags and two
identical 2040-byte `JaSt` replies with SHA-256
`408195df650fbe897953f0cf7983e9ee6f20b791e252d9dfaaca3ff2d3dd448f`.
Because the gate is not readable, restoration is claimed only as the exact
factory write sent.

The 14.0-second six-channel S32_LE/48 kHz capture exited 0, is 16,128,044
bytes, and has SHA-256
`9f2307056e44b909668deb4226ec2b191d1e23ade12d641996fc9669e4beafda`.
Every monitor channel changed by approximately 48.142 dB between the gate-on
and gate-off windows, establishing that the captured buses observe the gate.
In the gate-off window each fitted Input 2 with direct coefficient
approximately `0.70794561` and model correlation approximately `0.99999542`.
The 150 ms/direct ratio was only approximately `0.00001426`, far below the
predeclared `0.05` signature threshold.

The controlling result is `NO_REPEAT_DOWNSTREAM_GATE_OFF`. This supersedes the
earlier `UNPROVED_NO_ABOVE_GATE_STIMULUS` ambiguity: the linked recalled path
did not produce the factory 150 ms repeat in a capture path positively shown
to be downstream of the gate. It remains distinct from proof of physical
record storage, stored-record equality, or the missing record-driven
activation condition.

The final focused regression passed 18/18. The complete hardware-free suite
passed 223 tests with one expected historical-artifact skip in 176.921 seconds,
exit 0. Its only diagnostic was the pre-existing unclosed-WAV
`ResourceWarning` in `re/cp34_current_slot_survey.py:260`. No further live
action followed postflight. Artifacts are in
`runs/20260904T025429-0700-gate-transition-probe/`.

After all live steps were complete, an unrelated REAPER process started at
03:16:54 -0700 and acquired `/dev/snd/pcmC1D0c` and
`/dev/snd/pcmC1D0p`. The CP34 run neither created nor touched that process.
This later ownership does not affect the completed capture, but it is a hard
state-reconciliation requirement before any future audio access.

## 2026-09-04 linked positive-slot live trial

The operator explicitly accepted the linked-recall risk and asked the assistant
to perform the listening.  The test-covered action required serial
`AB7C22200355`'s exact readable baseline: link off, Channel 1 disabled on slot
0, and Channel 2 enabled on slot 3.  It then confirmed Channel 2 `3 -> 2`
unlinked, link on, Channel 2 `2 -> 3` linked, and link off in a `finally` path.
The live action completed at 94 percent battery.  Its final Channel-1 readable
gain, processing-channel, slot, and enable guard matched baseline.  A separate
no-write postflight passed at 93 percent with flags `0x1a1`, Channel 1 slot 0
disabled, Channel 2 slot 3 enabled, and two identical 2040-byte replies.

The simultaneous 14-second six-channel S32_LE/48 kHz capture exited 0 and has
SHA-256
`e587d9a7cbf78312eabcb4b2b4ee5e2f806d88335d3c812dd4d7372b1120aa14`.
In the clean linked-slot-3 window, capture channels 3-6 each matched Input 2 at
correlation `0.99999668` with direct coefficient `0.70797731`.  A joint fit
against current, 150 ms delayed, and 300 ms delayed Input 2 assigned only
`0.00000642` to the 150 ms term; the captured noise contains no repeat.

That is not an audible-effect negative.  The retained physical source was an
open cable and Input 2 measured -97.15 dBFS RMS / -83.66 dBFS peak.  The exact
factory Slap Echo record has its gate enabled at -47.5 dBFS, leaving even the
strongest captured sample 36.16 dB below threshold.  The controlling result is
therefore `UNPROVED_NO_ABOVE_GATE_STIMULUS`: linked routing was exercised and
restored, but no listening-level input reached the gate.  This result neither
proves nor disproves Voice FX selection, audible effect, or physical `Stat`
storage.

TDD first produced three expected failures because the bounded action was
absent.  Its focused contracts then passed 3/3; the linked and existing host
actions passed 7/7; the final complete hardware-free suite passed 208 tests
with one expected historical-artifact skip in 196.907 seconds.  No playback,
gain, gate, routing, output, preset-record, firmware, reset, DFU, install, Wine,
or network action occurred.  Artifacts are in
`runs/20260904T022636-0700-linked-channel2-slot3-audio/`.

## 2026-09-04 controlling channel-pair dispatch correction

The 2026-08-31 Voice FX gate section below proves a possible indexed component
route, but it overclaimed that route for every selected `Stat`. The current
pinned-firmware contracts now bind the missing caller conditions:

- dispatcher `0x420bc` loads flags at `device+0x5e58`, projects flags bit 12
  into N at `0x4224e`, and branches to `0x424d6` when that stereo-link bit is
  clear;
- the unlinked path collapses valid slots with `slot >> 1`, so slots 0/1 enter
  `0x531e0` with `r1=0` and slots 2/3 enter with `r1=1`;
- the nonzero `r1` path branches at `0x53224` to alternate table slot 2 at
  `device+0x5e88`, distinct from Voice FX slot 1 at `device+0x5e80`;
- the base initializer constructs channel-strip owners at `device+0x43a0` and
  `device+0x508c`; the second owner's `+4` state interface is the slot-2 object
  at `device+0x5090`;
- that interface resolves through vtable word `0x10cb1c` and adjustor
  `0x52aec` to state apply `0x52978`, whose table contains only `filt`, `gate`,
  `comp`, `eq  `, and `lim `. Voice FX/component 201 is not a member;
- with link bit 12 set, a positive slot instead reaches the paired calls at
  `0x42266` (`r1=0`, `r3=1`, normal indexed selector) and `0x42280` (`r1=1`,
  `r3=0`, second channel strip). The first table contains Voice FX at slot 1,
  but its selected index remains data-dependent and unresolved.

The bounded live read during this continuation returned flags `0x1a1` (link
bit clear), Channel 1 slot 0 disabled, and Channel 2 slot 3 enabled. Its two
2040-byte `JaSt` replies were identical with SHA-256
`086ca18f0f9dd095d25a046d5d2ceddf0d22e693a554a9c4b38081088702576e`.
This places the preceding custom Delay and factory Slap Echo dry observations
on the unlinked Channel-2/second-strip route. It explains why those recalls did
not make Voice FX audible, but it neither proves nor disproves physical storage
of the complete `Stat` record because full record readback remains unavailable.

TDD added the raw flag/link fields to the dedicated no-write preflight and
added source-bound unlinked, slot-2 identity, and linked-positive dual-dispatch
contracts. The preflight module passes 4/4 and the firmware-static module passes
44/44. The earlier broad-suite attempt hit its 420-second wrapper timeout while
all tests observed to that point were green and remains incomplete. The final
longer hardware-free run passed 205 tests with one expected historical-artifact
skip in 482.698 seconds, exit 0; its sole diagnostic was the pre-existing
unclosed-WAV `ResourceWarning` in `re/cp34_current_slot_survey.py:260`. Current
artifacts are under
`runs/20260904T015915-0700-unlinked-channel2-stat-routing/`.

This section supersedes the blanket claim below that native `Stat` recall
always reaches block 201. It does not erase the source-bound Voice FX loader or
gate path; it makes that path conditional on caller routing and record-driven
component selection. A linked live trial crosses the retained Channel-1-
untouched boundary and requires separate exact authorization.

## 2026-08-31 controlling two-lane and paired-host-save correction

Pinned firmware resolves the singleton-versus-lane distinction that the older
manual/resolver inference missed:

- `0x3f8a4` and `0x3f8aa` load physical-input mapping words at
  `device+0x5d74` and `device+0x5d78`; `0x3f8ae` loads stride `0xcec`, and
  `mla` instructions at `0x3f8bc`/`0x3f8c8` select two processing objects;
- block-201 setup sets `r2=2` at `0x3dbf4`, stores `r2,r2` into adjacent setup
  counts at `0x3dc10`, selects singleton `device+0x11e0`, and calls `0x553d4`
  at `0x3dc1c`;
- Doubler private-core configuration passes its loop index as lane index at
  `0x5ae90`, calls indexed helper `0x56cc8` at `0x5aeac`, changes the index
  from 0 to 1 at `0x5aeb2`, and repeats.

The result is one shared model-0 `on/lows/width/mix` settings instance driving
two hardware-input processing lanes. The same private-reverb state can be
simultaneous on both inputs; independently parameterized per-channel Doubler
instances cannot coexist.

The Linux host implements the corresponding paired record operation:

- `io24_preset_record.py` requires two complete channel records, validates
  finite normalized parameters, enforces slots 0/1 for channel 1 and 2/3 for
  channel 2, strips extractor-only `_offset`, and installs identical Doubler
  mappings without mutating either base;
- `io24.py` builds and validates both complete frame sets before the first
  write, exposes general `save_device_slot()` plus paired
  `save_paired_doubler_private_reverb()`, and provides CLI command
  `saveprivatereverb`;
- `io24gtk.py` exposes the recovered Reverb defaults and explicit paired block
  overwrite. Parameter motion is record staging only; save does not write
  block 202, either reverb send, `processingChannel`, preset selection, or
  recall;
- tests decode both generated Stat records and prove byte-equivalent `voicefx`
  state, correct slot ownership, complete-record validation, no base mutation,
  no unrelated transaction, and no direct GTK routing shortcut.

Executable result:
`runs/20260831T053346-0700-dual-private-reverb-host/`. Its analyzer output uses
schema `cp34-doubler-private-reverb-v2`; retained focused verification is 39
tests passed, and the complete hardware-free suite passed 127 tests in 144.275
seconds. This is source-bound and implementation evidence only. No hardware
transaction occurred, and physical commit, actual recall, audibility, survival,
and restoration remain unproved.

## 2026-08-31 controlling Doubler private-reverb correction

The preset named `Reverb` is a Voice FX Doubler record, not shared reverb
block 202:

- pinned `re/uc_factory_presets.json` contains 41 records; its sole `Reverb`
  title is index 30 and carries class
  `{66A10093-D461-4CAC-A80C-91F6A1BB37E5}` with exactly `on=1`, `lows=0.06`,
  `width=0.405`, and `mix=0.295`;
- a recursive key census across all 41 records finds none of `reverb`, `vrvb`,
  `FXA`, `size`, `predelay`, or `hp_freq`;
- pinned `dsp_fx_params.xml` maps that class to the `VoiceOfGod` param list
  (`on/lows/width/mix`) and declares `VocalReverb` separately as
  `on/size/mix/hp_freq/predelay`.
- after removing only the extractor annotation `_offset`, the exact record-30
  object passed the JSON codec and `MemP/Stat(0)` frame builder; decoded f32
  values re-encoded byte-for-byte.

Pinned firmware 1.28 independently resolves the implementation:

- device construction creates block 201 at `device+0x11e0` and block 202 at
  `device+0x3a70`;
- model factory `0x5f254` creates model 0 at block-201+`0x10` through
  constructor `0x5e270`;
- block 202 at `0x5b274` and Doubler at `0x5e37c` both call reverb-core
  constructor `0x5af14`, but with different member addresses (`+0x10` versus
  `+0x384`);
- block 202 at `0x5ade6` and Doubler at `0x5ae0e` both call core configurator
  `0x5a6a8` on those distinct members;
- model-0 runtime method `0x5bfe0` calls its private configuration path
  `0x5adfc` at `0x5c06c`.

Therefore Doubler shares reverb **code**, not the block-202 state object or its
send/return route. Its native preset save consists of class id plus
`on/lows/width/mix`. Sample rate—including 96 kHz—is runtime configuration and
does not belong in the JSON/`Stat` record.

Predecessor source-bound evidence:
`runs/20260831T040258-0700-doubler-private-reverb/DOUBLER-REVERB-STATIC.json`,
schema `cp34-doubler-private-reverb-v1`. Static PASS does not prove physical
commit, audible output, front-panel recall, power-cycle survival, or
restoration, and creates no live authority.

## 2026-08-31 controlling Voice FX gate correction

The firmware-native `Stat` route now reaches a concrete internal assignment,
not a generic parser boundary:

- Application callback `0x20754` uses router lookup `0x34cb8`; singleton
  projection `0x3cc08` returns the secondary interface whose method `0x3cc40`
  forwards the record to the live firmware device object at singleton `+0x138`.
- The live object's vtable begins at file `0x10cb40`; method `0x420bc` accepts
  `Stat`, and its completed-record branch invokes vtable slot `+0x38`, file
  `0x10cb78 -> 0x531e0`.
- Constructor `0x5e014` binds component id 201 to `device+0x11e4` in the table
  consumed by `0x531e0`. The latter selects the matching component and calls
  state-interface method `+4`.
- Block constructor `0x591bc` installs primary vtable `0x10c6bc` and secondary
  state vtable `0x10c700` at base-object offsets 0 and 4. State-interface word
  `0x10c704 -> 0x555b8` adjusts `this` by `-4` and enters state loader
  `0x5545c` on the block base at `device+0x11e0`.
- On a valid component record, `0x554ba` clears `block+0x40`; `0x554bc` stores
  little-endian halfword `0x0101` at `block+0x38`, making byte `+0x39=1`; and
  `0x554c2` calls `0x55388`, whose valid-model path writes `block+0x44=1` at
  `0x553a8`.
- Handler `0x50af8` requires `+0x44 != 0`, `+0x39 != 0`, and `+0x40 == 0`.
  The structured-state load establishes all three before delegating the
  selected model's nested state.

This corrects older vtable indexing that began at `0x10c6cc`, sixteen bytes
inside the primary table. `0x50af8` is primary slot `+0x10`, not `+0x00`; the
primary work word at `+0x34` is `0x10c6f0 -> 0x5f1f4`. `0x54ed8` and
`0x555b8` are secondary state-interface adjustors, not the primary work slot.
It also corrects the claim that `0x37e06` was the only setter of `+0x44`:
`0x553a8` is a direct setter in both construction and record application.

Together with the record codec, embedded active factory records, and UC's
inverse `voicefx.on` parser, this removes a missing standalone enable packet
from the native preset model. It does not claim `voicefx.on` itself is copied
directly into `+0x44`, and it does not prove physical commit, power-cycle
survival, actual front-panel recall, or audible output.

Durable source-bound detail:
`runs/20260831T032608-0700-voicefx-gate-recall/REPORT.md`; adjacent
`RECALL-STATIC.json` uses schema `cp34-preset-recall-static-v2` and pins the
full callback/dispatcher/component path, corrected vtable words, assignment
bytes, both source identities, and the predecessor record evidence.

## 2026-08-31 controlling save/recall correction

The scene JSON resolved the save model and the missed dynamic target in UC
4.7.2. The following evidence supersedes older sections below that describe
`Stat` as enumeration-only, say its update target was not located, claim the
firmware root has no preset-component relationship, or call static analysis
exhausted:

- `presets.slots[0..3]` are four complete records, with 0/1 assigned to channel
  1 and 2/3 assigned to channel 2. `presets.userpresets[16..27]` is a separate
  library.
- Host `0x1800420c0` snapshots the current channel through serializer
  `0x18002e270`; `0x1800421c0` selects the slot record and constructs
  `{Stat,index}` for owner sender `0x180050f10`.
- `0x180050f10` emits the same `MemP` fragment layout as the known `PrsM` path,
  and `0x1800541d0` wraps it as `SetP | Appl | 0 | MemP` before queue
  `0x180053420`.
- Periodic handler `0x1800417a0` snapshots and sends the active slot 500 ms after
  eligible processing/effect edits settle. Slot changes also write through the
  current state before switching.
- `io24_preset_record.py` reproduces the tagged binary archive represented by
  the scene JSON. Forty-seven standalone preset records in the source-bound
  4.7.2 module round-trip byte-for-byte through the codec.
- The device-root vtable begins at `0x6d208`, not its two-word header at
  `0x6d200`. Its `MemP` slot `+0x80` is `0x2f210`; `0x3c064` is the unrelated
  lifecycle/cache slot `+0x20`.
- Constructor path `0x3c890 -> 0x30260 -> 0x2fca8` stores the preset component
  at `device+0x1240` into `device+0x70`. Root handler `0x2f210` then invokes the
  component's vtable `+0x18`, `0x3099c`, with the incoming `MemP` record.
- `0x3099c` accepts `Stat` 0..3 and `PrsM` 16..27 and forwards valid fragments
  to `0x3092c`. That writer stores the record length and bytes through the
  startup-bound backend path `0x31ab0 -> 0x2d660 -> 0x300ac -> 0x306b4 ->
  0x2c1c0`; backend write entry `0x316dc` forwards to the firmware storage
  object with write flag 1.
- `0x3c064`/`0x302b0` instead connect the `logoImage` and `firmwareVersion`
  state labels; `device+0x120c` is the formatted firmware-version string, not a
  preset component or delegate.
- Slot-change handler `0x2f334` compares each channel's selected slot with its
  cached value and calls root vtable `+0x58`, `0x2f0d0`, for a changed slot.
  `0x2f0d0` calls preset-component vtable `+0x24`, `0x30be0`, which reads the
  matching `Stat` 0..3 record.
- Every recovered fragment is immediately handed to root vtable `+0x4c`,
  `0x2f8ac`. Its startup-bound callback reaches manager bridge
  `0x31674`/`0x3163c`, then application-router interface
  `0x20790`/`0x20754`. This is a firmware-native record-application route; UC
  is not required to drive recall after the record exists.
- Constructor `0x3c890` binds two eight-record factory banks using size tables
  at `0x691f0` and `0x69210`, and binds four `Stat` descriptors from
  `0x691e0`. All 16 embedded records decode and re-encode byte-for-byte through
  `io24_preset_record.py`.
- The embedded `Slap Echo`, `Detuned Vocal`, and `Robot` records set
  `voicefx.on=1`. Inactive Voice FX records set 0; four records omit the object.
  The firmware therefore represents Voice FX activation intent inside the same
  native preset record rather than requiring a separate save/recall opcode.
- In UC 4.7.2, record parser `0x18003bfc0` clears byte `+0xe6`, finds parent
  `voicefx`, finds child `on`, converts an integer or real value, compares it
  with 1, and writes the result at `0x18003c20d`. The complete `.text` census
  contains only four writes and two reads of `+0xe6`; serializer read
  `0x18003bb38` conditionally emits `VoiceFxOn` and does not queue an action.

This proves the host save representation, trigger, serializer, nested command,
outer wrapper, firmware dispatch, record assembly, storage-backend handoff,
firmware-native Stat read/application route, and record-resident Voice FX
activation intent. The controlling section above additionally proves that the
component-state application opens all three internal processing-gate
conditions. Neither result proves physical nonvolatile commit, power-cycle
survival, actual device recall, or audible output.

Durable detail:
`runs/20260831T024633-0700-stat-native-recall/REPORT.md`; adjacent
`RECALL-STATIC.json` pins both source identities, the recall vtable words and
code slices, all 16 embedded records, all three active `voicefx.on=1` records,
and UC's complete `+0xe6` access census. The predecessor save detail remains in
`runs/20260831T004620-0700-json-stat-save/`.

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
- Static XML component models contain values and ranges but do not encode the
  save transaction; the transaction instead comes from the 4.7.2 executable
  path and firmware dispatch traced above.
- Existing block-201 writes store parameter intent without established audible
  processing.

## Evidence still required

- Physical validation that a decoded `MemP/Stat` transaction commits on the
  unit and survives the declared power/recall boundary.
- Audible A/B validation if the CP34 audible-outcome claim is to be closed.
- Full restoration and deletion of any later live test preset.

A native capture is no longer a discovery prerequisite for either the save
packet or the recall representation. A one-to-one mapping from nested
`voicefx.on` to a model-local runtime byte is not claimed, but the containing
record's native application path now demonstrably establishes the processing
gate. It is not evidence that another host enable packet exists.

This ledger records evidence quality, not completion. Update it only with paths,
hashes, instruction addresses, capture rows, or executable results.

## Current offline verification

Latest focused verification on 2026-08-31:

- `python3 -m unittest discover -s tests -v`: 127 tests passed in 144.275
  seconds, exit 0.
- The retained paired-host focus in
  `runs/20260831T053346-0700-dual-private-reverb-host/FOCUSED-TESTS.txt` is
  39/39; its source-bound v2 analyzer exited 0 and records two physical-input
  processing mappings, block-201 setup 2-in/2-out, and private-core indexes
  0/1.
- Python compilation succeeded for all changed Python modules; CLI help exposes
  `saveprivatereverb` as a paired save that does not recall and does not use
  block 202.
- `python3 -m pytest -p no:cacheprovider -q
  tests/test_cp34_doubler_reverb_static.py
  tests/test_cp34_preset_recall_static.py
  tests/test_cp34_host_queue_inventory.py
  tests/test_io24_preset_persistence.py tests/test_io24_capture_decode.py`:
  38 passed, 21 subtests passed.
- The source-bound Doubler/reverb analyzer exited 0; a second run reproduced
  `DOUBLER-REVERB-STATIC.json` byte-for-byte. `python3 io24_fx.py` returned
  `OK -- all six models`.
- `python3 -m pytest -p no:cacheprovider -q
  tests/test_cp34_preset_recall_static.py
  tests/test_cp34_host_queue_inventory.py
  tests/test_io24_preset_persistence.py tests/test_io24_capture_decode.py`:
  31 passed, 21 subtests passed.
- The source-bound recall/gate analyzer exited 0 and a second run reproduced
  `RECALL-STATIC.json` byte-for-byte. Python compilation succeeded for the
  analyzer and preset-record codec.
- `python3 -m pytest -q tests/test_io24_preset_persistence.py
  tests/test_io24_capture_decode.py`: 23 passed, 21 subtests passed.
- Python compilation succeeded for `io24.py`, `io24_scene.py`, and
  `io24_preset_record.py`.
- All twelve recovered scene slot objects encoded/decoded locally and produced
  valid `Stat` envelopes; record sizes were 580..780 bytes.

Earlier 2026-08-28 verification:

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

The named StorePreset path uses `PrsM` for the twelve-record user library. The
active device-slot path uses the same sender with `Stat` 0..3; its dynamic
target and save trigger are now resolved below.

## Firmware reconciliation of the Store envelope

The conclusions in this historical subsection were corrected on 2026-08-31.
The root vtable was previously indexed from its two-word header. The corrected
vtable begins at `0x6d208`, so slot `+0x80` is `0x2f210`; the `0x3c064` entry is
slot `+0x20`. The controlling result is the correction at the top of this
ledger and the durable JSON/`Stat` report.

The exact host-built packet is now traced through the io24 1.28 firmware:

- The `Appl` SetP dispatcher at firmware offset `0x2d9b8` recognizes `MemP`
  and dispatches through vtable slot `+0x80`.
- For numeric block index 0, resolver `0x3ce98` selects the device root. The
  corrected root vtable `0x6d208` maps slot `+0x80` to firmware offset
  `0x2f210`.
- `0x2f210` delegates the original record to the preset component at
  `device+0x1240` through `device+0x70`, then updates the matching `Stat` slot
  flag after the final fragment.
- The ordinary application-object vtables `0x672fc` and `0x673c0` map the same
  slot to `0x2da30`, an immediate return.

Therefore `SetP | Appl | 0 | MemP | Stat/PrsM` reaches the real preset
component at `device+0x1240`, vtable `0x674f8`. Dispatcher `0x3099c` accepts
`PrsM` indexes 16..27 and `Stat` indexes 0..3; writer `0x3092c` sends the
record length and fragments to its bound storage backend. The previous negative
and the `device+0x120c` component address are superseded.

## Host `Stat` save path

- `0x1800420c0` validates the channel-local slot selection and snapshots the
  complete current component through serializer `0x18002e270`.
- `0x1800421c0` selects the corresponding global record, builds
  `{Stat,index}`, targets `{Appl,0}`, and invokes sender vtable slot `+0x10`.
- Shared sender `0x180050f10` builds the `MemP` fragments; `0x1800541d0`
  supplies the outer `SetP | Appl | 0` command and `0x180053420` queues it.
- Periodic handler `0x1800417a0` performs the snapshot and send after 500 ms
  of settled processing/effect changes. A slot switch first writes through the
  current slot and then changes the selection.
- The four earlier `Stat` descriptor builders remain enumeration evidence, but
  they are not the save path and do not negate this dynamic sender.

## Corrected preset-component ingress and storage map

- The root object is selected by numeric block 0. Its callable vtable begins at
  `0x6d208`; `MemP` slot `+0x80` maps to root handler `0x2f210`.
- Constructor chain `0x3c890 -> 0x30260 -> 0x2fca8` stores
  `device+0x1240` at `device+0x70`; `0x3c8dc -> 0x306bc` constructs that
  object with preset vtable `0x674f8`.
- `0x2f210` loads `device+0x70` and calls the component's vtable `+0x18`,
  `0x3099c`, with the original `MemP` message. No separately addressable
  preset block id is required.
- `0x3099c` accepts `Stat` 0..3 and `PrsM` 16..27. Writer `0x3092c` emits the
  record length and fragments through wrapper `0x2bfe4`.
- Startup path `0x31ab0 -> 0x2d660 -> 0x300ac -> 0x306b4 -> 0x2c1c0`
  binds the wrapper to the storage backend; entry `0x316dc` forwards writes to
  the underlying storage object with flag 1.

Static analysis therefore reaches the firmware storage-write interface. A live
capture is no longer needed to discover the packet; separately authorized live
work is only needed to validate acceptance, recall, and power-cycle survival.

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

The remaining product-level Voice FX evidence gap is physical/audible
validation. Static evidence already establishes that active native factory
records carry `voicefx.on=1` and that firmware recall applies the stored record;
it does not yet identify the final internal assignment to the DSP gate fields.

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

In UC 4.7.2, `VoiceFxOn` at `0x1804359a0` is conditionally serialized after
read `0x18003bb38` observes per-channel byte `+0xe6`. The setter is now
resolved: parser `0x18003bfc0` clears the byte, locates `voicefx.on`, accepts
integer or real 1, and writes the boolean at `0x18003c20d`. This is an inverse
record-loader/metadata path, not a queued enable action. Its relationship to
the firmware's final internal DSP gate assignment remains untraced.

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
This is a source-bound negative for that module/firmware pair, not a
product-wide negative or evidence for guessing a packet.

Current Linux verification:

- `python3 -m pytest -p no:cacheprovider -q
  tests/test_cp34_host_queue_inventory.py
  tests/test_io24_preset_persistence.py
  tests/test_normalize_io24_capture.py tests/test_io24_capture_decode.py`:
  26 passed, 27 subtests passed.
- Python compilation succeeded for the new analyzer and its contract suite.
- Both pinned inventory commands in `LINUX-MANIFEST.md` exited 0 and reproduced
  the six queue callers and three writer call sites above.

## Universal Control 4.7.2 static comparison

Recorded offline on 2026-08-30 without executing vendor code, starting Wine,
accessing the protected prefix, opening hardware, or using the network:

- Candidate installer SHA-256 is
  `1b5ddd6fd3ad4b93529caf8e5933bcd52b13194bdfa62652292b46ddcd980b95`;
  its extracted `Universal Control.exe` version resource is `4.7.2.108537`.
- Candidate `dspusbdevice.dll` is 4,979,672 bytes with SHA-256
  `de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.
  Its feature vocabulary includes the Revelator io24, both Stream Mix buses,
  Store/RestorePreset, VoiceFxOn, and all four active preset slots.
- The version-local central queue is `0x180053420`; exactly six direct callers
  occur at `0x18003535d`, `0x1800497c1`, `0x180051065`, `0x180052e10`,
  `0x180052fca`, and `0x18005308b`. The named writer slot is
  `0x1800e43f0`; exactly three consumers occur at `0x18007700b`,
  `0x1800775ad`, and `0x180083a98`.
- The Store/Restore dispatcher, generic `MemP` sender, four `Stat` enumeration
  paths, dynamic `Stat` builder, Voice FX model sender, and `VoiceFxOn` scene
  serializer all have direct version-local counterparts to the pinned 5.0
  paths. The `MemP` sender builds the same `0x7ec` fragment envelope, and the
  VoiceFxOn serializer still does not queue an enable operation.
- The 2026-08-30 comparison did not resolve the existing generic sender's
  dynamic `Stat` target. The 2026-08-31 JSON-guided trace did: it is the active
  slot save-point transaction. The remaining negative applies only to an
  explicit Voice FX gate operation.

Durable record:
`runs/20260830T170210-0700-uc472-static/REPORT.md`, with exact queue and writer
JSON plus a source-bound `SHA256SUMS`. The installer and extracted source remain
under `/tmp`, so source retention is temporary even after the task-local record
is sealed. No newly identified packet is eligible for replay.

Fresh post-record verification returned 104 passed and 38 subtests in 181.84
seconds, exit 0. The source-bound run manifest verifies 10/10, the unchanged
current-slot stage verifies 6/6, and the expanded offline manifest verifies
27/27.

Scoped independent review is clean. It independently reproduced all five
artifact identities, both candidate analyzer outputs byte-for-byte, the pinned
5.0 six-caller/three-writer topology, representative disassembly for the named
paths, all three analyzer contracts, and a complete 104-test/38-subtest broad
run in 310.87 seconds, exit 0. The 10/10 source-bound, 27/27 offline, and 6/6
current-slot checksum gates also passed. No Critical or Important issue was
found; the sole Minor wording note was corrected by making the result explicitly
seam-bounded. This review grants no live authority, and neither observable CP34
outcome is resolved.

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

Fix1 and fix2 evidence are historical/superseded. Final fix3 broad verification
returned 104 passed and 38 subtests in 279.00s, exit 0. Stage 6/6 and offline
manifest 23/23 verify; the stage hash is
`8b78a3fcf8abc06bdf702447325e8b1da3920a10f31e4dffe4bd2fff2c6acf69`.
The offline-manifest file hash is recorded outside its pinned inputs in the
task-local implementation report. BAT0 was 11 percent, discharging, via
passive sysfs. Independent fix3 re-review is clean.

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
