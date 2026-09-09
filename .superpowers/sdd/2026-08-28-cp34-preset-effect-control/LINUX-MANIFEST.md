# CP34 Linux-only continuation

Status: CP34 stock-firmware investigation complete with a terminal negative;
Linux-host cleanup and initial GitHub packaging are next

Linux is the project host. The current continuation does not use Wine, the
protected io24 prefix, audio capture, firmware, network access, installation,
or a vendor process. Historical live attempts are retained separately and do
not authorize another device operation.

## Pinned source

- Module:
  `/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll`
- Size: 4,984,704 bytes
- SHA-256:
  `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`
- Queue function: `0x1800546b0`
- `WinUsb_WritePipe` IAT slot: `0x1800e53f0`

Refuse conclusions if the module hash differs.

## L00AA: controlling Channel-2 assignment correction

The exact UC UI exposes `Assign Voice FX` as
`line/ch1/processingChannel`, with `Ch1=0` and `Ch2=1`. Retained UC scenes put a
`voicefx` member in all four slot records. The later inference that four
embedded version-2 defaults impose component-201 ownership on slots 0/1 is
retracted: those are startup/default shapes, while UC's exact active-slot writer
emits the complete tagged record beginning with `0x7b`.

Exact UC code now supplies the missing distinction: a channel object owns the
singleton VoiceFX model when `processingChannel == 0`, but assignment does not
renumber `set_preset_enabled(1|2)` or `set_preset_slot(1|2, ...)`. Two earlier
runners used physical channel 1 after assigning VoiceFX to Input 2; their
readback invalidates them as Channel-2 recall tests. Channel 1 was subsequently
returned to selector 0 while bypassed without a record-body write.

The current Linux-only acceptance runner is
`re/cp34_channel2_voicefx_materialization_stage.py`. It requires/reasserts the
Input-2 VoiceFX assignment, keeps every preset operation on physical Channel 2,
selects model 0 before its state, and writes only global slot 3. Its target is
derived from UC Reverb but raises private `mix` from 0.295 to 1.0. Record
SHA-256 is
`191a5048c4995355932609e9d5ae225f37c50d8f112966f685a11b3f2a08e79c`;
the `Stat(3)` frame SHA-256 is
`d8ea35050b33484444e48c3d54cf1716bce35265a0b2b92f26939ea7bdf92c1f`.
Its default invocation performs no hardware access. See
`runs/20260906T100100-0700-channel2-voicefx-materialization/`.

The separately authorized live invocation executed once on serial
`AB7C22200355` at 45 percent battery. It sent the four model-before-state
messages and one maximum-wet `Stat(3)` fragment, then exposed Channel 1 still
at selector 0/bypassed and Channel 2 at selector 3/enabled, with Input-2
VoiceFX assignment and link-off retained. The exact output is
`LIVE-ATTEMPT-3-CORRECTED-MAX-WET.json` in that run. The transport had no
readable write reply. The user subsequently unplugged and reconnected the
interface and reported no noticed change. The maximum-wet effect was not
audibly present after the power cycle, which closes the stock-firmware
investigation with a terminal negative. See `STANDALONE-LISTENING-RESULT.md` in
that run. This does not identify the failed internal commit, persistence,
parsing, activation, gate, or recall boundary. No further live authority
follows; cleanup and initial GitHub packaging precede custom-firmware work.

## L00A: controlling 4.7.2 correction

The later JSON/slot trace supersedes the L03 and L03A statements below that no
`Stat` update sender exists. The six-caller inventory was correct, but its
negative interpretation was not: `PrsM` and `Stat` are nested variants carried
by the same generic `MemP` caller.

Current source-bound result:

- slots 0/1 are channel 1 and slots 2/3 are channel 2;
- UC snapshots the complete current channel into the active slot;
- after 500 ms of settled processing/effect edits it sends
  `SetP | Appl | 0 | MemP | Stat(slot) | serialized-record`;
- scene JSON and the binary record are two encodings of the same object;
- the corrected root `MemP` handler `0x2f210` directly invokes the preset
  component at `device+0x1240`; its record writer reaches the startup-bound
  firmware storage backend;
- native component-state application reaches block 201 and establishes all
  three internal processing-gate conditions;
- power-cycle/nonvolatile survival and audible Voice FX remain live validation
  questions, not missing save-format, routing, or gate-packet questions.

See
`runs/20260831T004620-0700-json-stat-save/REPORT.md` and run the hardware-free
focused verification:

```text
python3 -m pytest -q \
  tests/test_io24_preset_persistence.py \
  tests/test_io24_capture_decode.py
```

Expected current result: 23 passed, 21 subtests passed. No live authority is
created by this correction.

## L00: analyzer contract

```text
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_cp34_host_queue_inventory.py -v
```

Expected: three tests pass. They cover instruction-boundary scanning,
resynchronization across mixed code/data, and RIP-relative IAT resolution.

## L00B: native Stat recall, record activation intent, and processing gate

The source-bound recall analyzer is static and hardware-free:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_preset_recall_static.py \
  /tmp/io24-fw-1.28.7DrxHf.bin \
  /tmp/io24-uc472-extract.IHXUdb/hwaccess/dspusbdevice.dll
```

It refuses any source identity other than firmware 1.28 SHA-256
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`
and UC 4.7.2 module SHA-256
`de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.
It asserts the selected-Stat reader/application callback vtables and code
slices, follows the live firmware dispatcher into component 201's corrected
state-interface vtable, pins the three processing-gate assignments,
byte-round-trips all 16 embedded firmware presets against their two size
tables, verifies all four Stat descriptors, and reproduces UC's complete
`+0xe6` field-access census and `voicefx.on == 1` parser.

The hardware-free contracts are:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_preset_recall_static.py
```

Latest durable output and report:
`runs/20260831T032608-0700-voicefx-gate-recall/`. The predecessor recall seal is
`runs/20260831T024633-0700-stat-native-recall/`. This proves the static native
record/application and processing-gate model. It does not prove physical
commit, power-cycle survival, front-panel behavior, or audible output and
grants no live authority.

## L00C: Doubler private reverb and JSON save contract

The hardware-free analyzer distinguishes shared block 202 from the reverb core
embedded in Voice FX model 0:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_doubler_reverb_static.py \
  /tmp/io24-fw-1.28.7DrxHf.bin \
  re/uc_factory_presets.json \
  re/uc_component_model/dsp_fx_params.xml
```

It refuses any firmware, JSON, or component-model identity other than the
pinned hashes. It verifies exact firmware vtable words, code-slice hashes, and
Thumb call targets showing that block 202 and Doubler construct/configure the
same reverb-core implementation at separate object addresses. It then checks
all 41 factory JSON records recursively and verifies the separate UC parameter
models.

Hardware-free contracts:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_doubler_reverb_static.py
```

Expected: eight tests pass. Predecessor durable output:
`runs/20260831T040258-0700-doubler-private-reverb/`. The result proves that a
Doubler slot record saves class id + `on/lows/width/mix`, not block-202 or
reverb-send state. Runtime sample rate, including 96 kHz, is not a preset field.
It grants no device-write authority and does not prove physical commit,
audibility, front-panel recall, survival, or restoration.

## L00D: paired two-channel private-reverb host save

The controlling v2 analyzer and implementation seal is:

`runs/20260831T053346-0700-dual-private-reverb-host/`

The additional pinned firmware seams prove:

- two physical-input mapping selectors at `device+0x5d74` and `+0x5d78` with
  per-channel processing stride `0xcec`;
- block-201 setup counts 2 inputs and 2 outputs on singleton
  `device+0x11e0`;
- Doubler private-core bindings for indexed lanes 0 and 1;
- one shared `on/lows/width/mix` parameter surface, not two independent model
  instances.

The Linux implementation builds two complete scene-shaped records before the
first write, enforces one slot from each channel pair, installs identical
Doubler state, and emits only `MemP/Stat`. Core API, CLI, and GTK host are
updated. The GTK button is explicit about overwriting both selected blocks and
does not recall them.

Reproduce the retained focus:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_cp34_doubler_reverb_static \
  tests.test_cp34_dual_private_reverb_slots \
  tests.test_io24_preset_persistence \
  tests.test_cp34_preset_recall_static
```

Expected: 39 tests pass. Current complete hardware-free result:

```text
python3 -m unittest discover -s tests -v
```

Result: 127 passed in 144.275 seconds, exit 0. The run manifest must verify:

```text
cd .superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260831T053346-0700-dual-private-reverb-host
sha256sum -c SHA256SUMS
```

This stage grants no USB/preset/audio authority and does not establish physical
commit, recall, audibility, power-cycle survival, or restoration.

## L01: central queue callers

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_host_queue_inventory.py \
  '/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll' \
  --target 0x1800546b0 --context-before 384
```

Expected direct call sites:

| Call site | Local operation evidence |
| --- | --- |
| `0x180035abe` | `FRst`, `Appl` |
| `0x180049f2f` | `VoFx` |
| `0x18005238e` | `MemP` |
| `0x1800542a9` | `Pari` |
| `0x18005432a` | `Para` |
| `0x1800555ae` | generic `SetP`/`GetP` builder context |

The ASCII immediates are bounded context evidence, not automatic semantic
labels. The disassembly around each call establishes the payload family.

## L02: native writer consumers

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_host_queue_inventory.py \
  '/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll' \
  --target 0x1800e53f0 --call-kind rip-indirect --context-before 384
```

Expected `WinUsb_WritePipe` calls:

- `0x1800780db`
- `0x18007867d`
- `0x180084ac8`

These are buffer consumers. They do not construct an additional preset or
Voice FX command family.

## L03: firmware reconciliation

- `FRst` restores live defaults.
- `VoFx` carries model parameters but does not open the processing gate.
- The callable root vtable begins at `0x6d208`; its `MemP` slot `+0x80` is
  `0x2f210`, not lifecycle/cache routine `0x3c064` at slot `+0x20`.
- `0x2f210` forwards `MemP` through `device+0x70` to the preset component at
  `device+0x1240`; `0x3099c` accepts `Stat` 0..3 and `PrsM` 16..27.
- `0x3092c` writes record length and fragments through the startup-bound
  storage wrapper. Backend entry `0x316dc` forwards to the underlying firmware
  storage object with write flag 1.
- UC 4.7.2 constructs the device-slot save as
  `SetP | Appl | 0 | MemP | Stat(slot) | serialized-record`; the same generic
  sender carries `PrsM` library records.
- The native `Stat` component-state loader establishes all three block-201 gate
  conditions before applying selected-model state; no separate host-side gate
  operation is missing from that preset path.

Therefore this exact vendor module and firmware do expose the source-bound
device-slot save sender, firmware storage handoff, reciprocal native recall,
and internal processing-gate assignment. Live acceptance, recall,
power-cycle survival, and audible output remain validation questions.

## L03A: Universal Control 4.7.2 comparison

The feature-bearing 4.7.2 candidate is recorded under:

`runs/20260830T170210-0700-uc472-static/`

Pinned candidate facts:

- `Universal Control.exe` version: `4.7.2.108537`.
- `dspusbdevice.dll` SHA-256:
  `de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.
- Queue target: `0x180053420`; six direct callers.
- `WinUsb_WritePipe` IAT slot: `0x1800e43f0`; three consumers.

The exact analyzer outputs are `QUEUE-INVENTORY.json` and
`WRITER-INVENTORY.json`. `REPORT.md` reconciles the candidate Store/Restore,
`MemP | PrsM`, four `Stat` records, dynamic `Stat`, Voice FX model, and
`VoiceFxOn` serializer paths against the pinned 5.0 module. The candidate
preserves those control shapes. The dynamic `Stat` path is now identified as
the native slot save carried by the existing generic `MemP` sender; no separate
queue caller or explicit Voice FX gate sender is expected. Firmware-native
component-state application performs the gate assignment.

Verify the source-bound run while its `/tmp` artifacts remain:

```text
sha256sum -c \
  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260830T170210-0700-uc472-static/SHA256SUMS
```

The task-local outputs remain durable, but the candidate source itself is only
temporarily retained under `/tmp`. This comparison does not establish GUI
rendering, synchronization, device behavior, or either CP34 outcome.

Fresh extension verification: the complete hardware-free suite returned 104
passed and 38 subtests in 181.84 seconds, exit 0; the source-bound run manifest
verifies 10/10; the current-slot stage verifies 6/6; and the expanded offline
manifest verifies 27/27. Scoped independent review then reproduced the source
identities, both candidate JSON outputs, pinned topology, representative
disassembly paths, analyzer contracts, all three checksum gates, and a complete
104-test/38-subtest broad run in 310.87 seconds, exit 0. It found no Critical or
Important issues. The 4.7.2 stage is independently reviewed clean and grants no
live authority.

## L04: scoped slot-capture classifier

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_live_matrix.py
```

Expected: 37 tests pass. The `analyze-slot` contracts require two dry and two
active captures with matching impulse count/cadence, an audible attestation,
and a repeatable 150 ms delta. A positive classification is
`REPEAT_150MS_SIGNATURE`, not a preset title or model identity. A repeatable
late tail is source-neutral and inconclusive.

The classifier reads existing local WAV files only and reports
`live_ready=false` and `restoration_verified=false`. It is not a capture
procedure, restoration ledger, live authorization, device-source proof, or
negative-result gate.

## Next safe action

The separate design now exists at `LINUX-LIVE-MATRIX.md`. It distinguishes the
historical unidentified-slot recall negative from a front-panel recall of a
name-verified active `Slap Echo` factory record. The matrix aborts unless that
exact title is already accessible and every changed write-only value has a
current inverse.

The hardware-free impulse generator, WAV analyzer, and restoration-ledger
validator named by the matrix are implemented and contract-tested. The ordinary
driver shadow was audited offline: it has the needed reverb/FX-mix rows, but its
2026-08-23 state is not current-attested and its assign/master baseline is not
explicit. It is therefore not yet restoration authority.

The title-free `analyze-slot` classifier is also contract-tested, but it does
not remove those live preconditions. The no-write current-slot survey now has
its own offline procedure and executable restoration contract; they require an
independent offline review before a separate exact authorization can be
requested.

L01 now names target `AB7C22200355` and records its readable slots and ALSA
identity. It remains partial: the device-screen title, preset mode, physical
capture map, and current complete restoration ledger are unresolved. Do not
execute L02-L07 without those preconditions and separate exact live-device
authorization. A factory recall can test audible Voice FX; it cannot prove
custom device-resident storage.

## L05: current-slot survey offline stage

The positive-only no-write survey is now implemented and hash-pinned without
running it. Its six core-stage files are listed in
`CURRENT-SLOT-SURVEY-STAGE.sha256`; verify that manifest before review:

```text
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
```

The complete hardware-free regression command is:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_host_queue_inventory.py \
  tests/test_cp34_live_matrix.py \
  tests/test_cp34_current_slot_survey.py \
  tests/test_io24_preset_persistence.py \
  tests/test_normalize_io24_capture.py \
  tests/test_io24_capture_decode.py
```

Historical revision-1 result, now superseded: 94 passed and 31 subtests passed.
The 31 then-current current-slot
contracts cover exact plan rejection, frozen six-channel Mix A mapping,
restoration and evidence-manifest verification, and the intentionally invalid
checked-in template. The extra four subtests cover S1-S4 raw/derivative
sample-stream mismatches. The broader 23-row offline manifest separately pins
the unchanged live-matrix analyzer seam and tests used by restoration.

`validate-plan` returns `VALID` only for exact authorization and source
provenance. `map-channel` freezes channel 3 or 4 before any effect result.
`verify-restoration` consumes the existing `cp34-slot-survey-audio-v1` schema,
derives JaSt summaries from canonical raw JSON, compares every derivative with
the decoded frozen channel of its raw capture, and fail-closes on any missing
evidence input. It recomputes both complete map and A/B reports, requires every
map arrival at one lag, binds the normalized run path to `plan.evidence_dir`,
uses no-clobber candidate-scoped interim seals, and recomputes channel 1 before
accepting its exact saved result as the channel-2 predecessor. A passing offline result is not
a preset title or model claim, is never a negative result, and is not live
authority. Channel 2 requires a sealed channel-1 result of exactly `RESTORED`
plus `INCONCLUSIVE`.

Revision-1 plan/restoration schemas are rejected and superseded by v2. Fix3 is
offline-sealed and its scoped independent review is clean. That review did not
authorize a live action. The later 4.7.2 static stage's scoped independent
review is also clean and likewise grants no live authority.

Fix1 and fix2 evidence are historical. Final fix3 broad verification returned
104 passed and 38 subtests in 279.00s, exit 0. Stage 6/6 and offline manifest
23/23 verify at stage hash
`8b78a3fcf8abc06bdf702447325e8b1da3920a10f31e4dffe4bd2fff2c6acf69`.
BAT0 was 11 percent, discharging, via passive sysfs. Independent fix3 re-review
is clean. No live authority is granted.

Historical 94/31/hash statements are superseded by fix1 current-slot evidence:
39 passed, 9 subtests in 129.12s, exit 0. Broad verification was pending at
that intermediate checkpoint and is superseded below.

Fix1 broad gate is authoritative: 102 passed, 36 subtests in 157.09s, exit 0.
The prior 94/31 result is historical/superseded. Stage 6/6 and offline manifest
23/23 verify; the stage-manifest hash is
`c4fc43129e998d2626670ef32ddd1a6f169c7a4613788899b1910b7db1109410`.
The offline-manifest file hash is recorded outside its pinned input set in the
task-local implementation report.
Passive sysfs reported BAT0 at 40 percent, discharging; no live action occurred.
