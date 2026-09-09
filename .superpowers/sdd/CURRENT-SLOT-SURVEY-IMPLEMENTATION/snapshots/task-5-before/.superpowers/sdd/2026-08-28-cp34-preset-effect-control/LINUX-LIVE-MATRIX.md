# CP34 Linux factory Voice FX live matrix

Status: L01 read-only discovery partially executed on `AB7C22200355`;
L02-L07 not authorized or executed

## Question this matrix can answer

Does a front-panel recall of an already-assigned, name-verified factory preset
whose serialized record has `voicefx.on = 1` make that Voice FX audibly present?

This is narrower than the historical probe in `PROTOCOL.md` section 13s. That
probe changed to an unidentified numeric slot and then re-sent the direct
block-201 payload. It produced a valid negative for "arbitrary slot recall opens
the direct block-201 gate", but it did not prove that the recalled slot was one
of the factory records with active Voice FX.

The preferred target is `Slap Echo`. In the pinned
`re/uc_factory_presets.json` (SHA-256
`89b0572dd760b77831d012e2db0568b4f4eeb158985a4ca86126be28e934c73d`),
record 4 has:

- `preset_name = "Slap Echo"`;
- `voicefx.on = 1`;
- class ID `{98A527BA-2D6E-4B35-BB26-251EC081A067}`;
- `time = 0.15`, `feedback = 0.25`, and `mix = 0.5`.

Records 5 and 6 are active `Detuned Vocal` and `Robot` alternatives, but they
are not interchangeable with this matrix. If `Slap Echo` is not already
accessible from a front-panel slot, stop. Do not assign a slot, guess a title,
or substitute a different effect without first extending the observable and
acceptance criteria offline.

This matrix cannot prove custom device-resident preset storage or assignment.

## Authority boundary

This file is a design, not live authority. A future authorization must name the
target device/serial and explicitly permit every live class below that will be
used:

- ALSA playback/capture on the io24;
- the declared safe physical audio connection and test stimulus;
- manual short and long presses of the declared channel's Preset button;
- one claim of USB interface 5, alternate setting 1, for bounded state reads;
- only the source-bound mapped writes listed in the approved run record;
- local creation and hashing of the run evidence directory; and
- restoration of every changed value to the recorded PRESTATE.

The matrix never permits Wine or access to `/home/ajuntanaga/.wine-io24`, USB
detach, configuration changes, unknown writes, slot assignment, user-preset
storage, firmware access, reset, power cycle, DFU, installation, staging outside
the declared run directory, or network access. Stop at or below 10 percent
battery.

### Recorded L01 authority and result

On 2026-08-29 the user authorized USB identity, interface-5 PRESTATE reads, and
ALSA identity/mapping on the single connected io24. That bounded L01 discovery
identified serial `AB7C22200355` and produced
`runs/20260829T010329-0700-l01-readonly/L01-REPORT.md`. It did not authorize or
perform audio playback/capture, front-panel actions, mapped writes, preset or
effect operations, or L02-L07.

L01 remains partial because the operator-screen title, declared preset mode,
physical capture-channel A/B map, and current complete restoration baseline are
not recorded. Numeric slots 0 and 2 do not establish a `Slap Echo` assignment.

## Hard preconditions

Do not begin the active sequence unless all of these are true:

1. The exact device identity, firmware version, host audio card identity, sample
   rate, channel map, physical connection, and monitor level are recorded in
   `PRESTATE.md`.
2. Phantom power is off on the test input, the source is line-level and
   current-limited, and the monitor path begins muted or at a safe level.
3. The device screen identifies the selected slot as `Slap Echo`. A numeric slot
   index, LED, inferred default, or filename is not title evidence.
4. The initial selected slot and preset enabled/bypassed state are recorded for
   both channels. The declared `presetMode` is recorded as operator knowledge,
   because the device does not report it.
5. Every write-only value that the run would change has an exact restoration
   value and provenance. For mixer sends and reverb this requires a current,
   complete driver mirror whose file hash is recorded and whose validity since
   the last power cycle or external editor use is explicitly confirmed.
6. If the write-only baseline is incomplete or stale, the run stops before any
   mapped write. Do not manufacture a baseline by assuming defaults.
7. The playback stimulus and capture analyzer have passed hardware-free fixture
   checks. The stimulus contains at least five isolated, level-limited impulses
   spaced far enough apart to expose a 150 ms repeat without overlap.
8. The exact inverse of every allowed mutation is present in the restoration
   ledger before its forward action can run.

## Evidence rows

Each row produces a timestamped command/action log, the unmodified multichannel
WAV, a mono analysis derivative, an analysis result, and SHA-256 hashes. Use
48 kHz throughout; refuse a rate or channel-count substitution.

| Row | Single change | Required observation |
| --- | --- | --- |
| L00 | No device action: pin tool versions, scripts, factory JSON, and empty run layout | Reproducible offline baseline |
| L01 | Bounded PRESTATE reads and operator screen transcription only | Device identity, slot/title, enabled state, audio map, and complete restoration ledger |
| L02 | With `Slap Echo` bypassed, play/capture the fixed impulse train once | First dry bracket, no clipping, stable direct arrival, and no repeat at 150 ms above the declared floor |
| L03 | Keep the preset bypassed; enable the known-good reverb with the exact approved parameters, capture once, then restore it immediately | Reverb changes the same captured path by at least 3 dB or the run is inconclusive and stops |
| L04 | Restore reverb off/baseline; enable only the already-selected `Slap Echo` preset with the front-panel long press | No slot assignment, model write, or direct block-201 write |
| L05 | Play/capture the identical impulse train twice with `Slap Echo` active | Audible repeats plus a repeat-energy peak at 150 ms within the declared tolerance in both captures |
| L06 | Bypass only the same preset and capture the identical train once again | Second dry bracket returns and the 150 ms peak disappears |
| L07 | Restore the original selected slot, enabled state, reverb, routes, gains, monitor level, and physical connection | Readable state matches PRESTATE; every write-only restoration replay and limitation is recorded |

L03 may change only the reverb and route values whose exact PRESTATE values and
inverse calls are already in the restoration ledger. If that prerequisite is
not satisfied, L03 cannot run and the entire matrix remains inconclusive; a
software-only echo is useful for analyzer QA but is not a substitute for the
required device-DSP positive control.

## Hardware-free gate tool

`re/cp34_live_matrix.py` never imports the io24 driver and never opens USB or an
audio device. Three subcommands are executable gates for this design. A fourth,
`analyze-slot`, is a separately scoped offline capture classifier and is not a
live gate.

Generate the fixed four-second, 48 kHz, mono S32_LE stimulus at a new path:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_live_matrix.py \
  generate-stimulus <new-run-path>/slap-impulses.wav
```

The deterministic output SHA-256 is
`318786a6af910736dbe8f96d152753884dac6fe360b8ad1e8a685b3077d68142`.
The generator refuses to overwrite an existing file.

Validate the target-specific restoration ledger before L01:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_live_matrix.py \
  validate-ledger <run-path>/restoration-ledger.json
```

The ledger schema is `cp34-restoration-ledger-v1`. It requires a run ID, device
serial, exact `Slap Echo` title, one pinned/current-attested driver-shadow hash,
unique actions, one inverse per action, one fixed reverb positive control, and
one `front-panel-enable` action. Mapped methods and argument keys are allowlisted;
direct Voice FX and preset-slot methods are prohibited. A write-only inverse
must cite the exact pinned shadow as `shadow:<sha256>`.

Analyze two dry brackets, two active captures, and one reverb control after
creating mono derivatives without changing the raw multichannel WAVs:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_live_matrix.py analyze \
  --target-title 'Slap Echo' --audible-attested \
  --dry <dry-1.wav> --dry <dry-2.wav> \
  --active <active-1.wav> --active <active-2.wav> \
  --reverb <reverb.wav>
```

Use `--audible-attested` only after the operator actually hears the repeat in
both active rows. The analyzer refuses wrong formats/rates, clipping, changed
impulse counts or cadence, dry contamination, a level-only fake reverb control,
missing audible attestation, or a non-repeatable 150 ms active delta. It hashes
every input in its JSON report.

### Title-free offline capture classifier

`analyze-slot` can classify already-acquired dry/active WAV derivatives when a
device-screen title and a current reverb baseline are unavailable:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_live_matrix.py analyze-slot \
  --candidate <ch1-slot1|ch1-slot2|ch2-slot1|ch2-slot2> \
  --audible-attested \
  --dry <dry-1.wav> --dry <dry-2.wav> \
  --active <active-1.wav> --active <active-2.wav>
```

A repeatable 150 ms delta produces status `SIGNATURE_PRESENT` and classification
`REPEAT_150MS_SIGNATURE`. That is signal-domain evidence only. The report fixes
`model_identity` to `UNRESOLVED`, `title_verified` to false, `live_ready` to
false, and `restoration_verified` to false. It does not identify `Slap Echo`,
prove that the source was the io24, prove the selected slot, or satisfy either
CP34 outcome by itself.

A repeatable broadband late tail is `NON_SPECIFIC_LATE_TAIL` and remains
`INCONCLUSIVE`; its source and loaded model are unresolved. Absence of the
150 ms signature is also inconclusive because this classifier has no same-run
device-DSP positive control.

This command analyzes files only. It does not authorize acquiring them. Before
any title-free live survey, a separate offline procedure must name the physical
path, candidate-selection and enable/bypass sequence, initial and final readable
state, evidence directory, abort behavior, and executable restoration check.
That procedure then requires separate exact live-device authorization. The
current L01 authority and the L02-L07 matrix above do not supply it.

## Acceptance rules

Voice FX passes only when all of the following hold:

- L03 proves the same device audio path can expose a working DSP effect through
  a late-energy ratio at least 3 dB above the worst dry bracket;
- both L05 captures contain a plainly audible repeat and a repeat-energy peak at
  150 ms within the predeclared tolerance;
- both bracketing L02/L06 captures lack that peak above the same threshold;
- the device screen continued to identify the active target as `Slap Echo`;
- no direct block-201/model write occurred; and
- L07 restoration completes without an unresolved mismatch.

A repeat-energy delta of at least 6 dB between each active capture and the worst
dry reference is the starting signal criterion. It must be fixed before the run
by hardware-free fixtures; do not tune it after seeing device data.

The result is an honest negative only if the `Slap Echo` title is verified, the
reverb positive control passes, both active captures lack the expected audible
and signal-domain repeat, both dry brackets are stable, and restoration passes.
Otherwise label the row `UNAVAILABLE`, `INCONCLUSIVE`, or
`RESTORATION-FAILED`, never negative.

## Failure and restoration behavior

- Any clip, dropout, sample-rate change, channel-map ambiguity, missing inverse,
  USB/audio error, target-title change, or battery floor aborts forward work.
- Restoration runs in reverse mutation order. Failure to restore one item stops
  further experimentation and is recorded; do not power-cycle or reset as an
  improvised recovery.
- Write-only values can be proven replayed but not read back. State that
  limitation explicitly rather than claiming device confirmation.
- Preserve raw evidence even for unavailable, inconclusive, negative, or failed
  runs. Never overwrite an earlier row.

## Exact next gate

The hardware-free generator, impulse/WAV analyzer, and restoration-ledger
validator are implemented and contract-tested. Populate the still-unrecorded
target-specific PRESTATE fields and validate the real restoration ledger next.
Live authority can then be requested only for that named device and the exact
L01-L07 actions. If the title-verified path remains unavailable, design and
review the separate no-write slot-survey procedure before requesting its own
authority. Do not treat `PASS` or `SIGNATURE_PRESENT` from an offline fixture as
device evidence.
