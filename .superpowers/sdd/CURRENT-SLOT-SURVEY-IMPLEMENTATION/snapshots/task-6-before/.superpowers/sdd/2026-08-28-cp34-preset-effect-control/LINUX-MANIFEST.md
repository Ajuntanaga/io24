# CP34 Linux-only continuation

Status: active; offline host-operation closure and scoped slot classifier
reproduced; L01 read-only discovery partial

Linux is the project host. This procedure does not use Wine, the protected
io24 prefix, USB, audio hardware, firmware, network access, installation, or a
vendor process.

## Pinned source

- Module:
  `/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll`
- Size: 4,984,704 bytes
- SHA-256:
  `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`
- Queue function: `0x1800546b0`
- `WinUsb_WritePipe` IAT slot: `0x1800e53f0`

Refuse conclusions if the module hash differs.

## L00: analyzer contract

```text
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_cp34_host_queue_inventory.py -v
```

Expected: three tests pass. They cover instruction-boundary scanning,
resynchronization across mixed code/data, and RIP-relative IAT resolution.

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
- `MemP | PrsM` reaches the root cache-republication handler and does not
  consume or persist the nested preset record.
- `Pari` and `Para` update live parameters; the closed resolver does not route
  them to the internal preset component.
- No queue caller constructs `Stat`, slot assignment, a save-point operation,
  or an explicit Voice-FX-on command.

Therefore this exact vendor module and firmware expose no source-bound sender
for custom device-resident store/assignment and no explicit host-side Voice FX
gate operation. Do not manufacture one from printable tags.

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

Expected and reproduced: 94 passed and 31 subtests passed. The 31 current-slot
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

The final fix wave has not received a clean review. The next gate is a scoped
independent offline re-review. Only after that review is clean
may a new separately exact authorization be requested for a named live run.
No live action occurred while producing or integrating this stage.
