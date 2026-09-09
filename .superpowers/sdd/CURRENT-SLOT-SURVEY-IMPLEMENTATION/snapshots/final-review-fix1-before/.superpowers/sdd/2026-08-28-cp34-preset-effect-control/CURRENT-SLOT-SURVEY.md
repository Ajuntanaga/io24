# CP34 current-slot survey operator procedure

## Scope and hard stop

This is a future, current-slot-only, positive-only survey for serial
`AB7C22200355`. It may examine `ch1-slot1` (channel 1, numeric slot 0), then
`ch2-slot1` (channel 2, numeric slot 2) only after a restored inconclusive
channel-1 result. It never establishes a preset title or effect-model identity.

Do not select a slot, short-press a Preset button, map a write, send a guessed
packet, use device-output playback or io24 monitoring, access Wine or
`/home/ajuntanaga/.wine-io24`, access the network, install or stage anything,
detach USB, or perform firmware, reset, or DFU work. Do not overwrite an
existing run directory or evidence file.

This file is not authority for a live run. Offline validation and analysis
commands below consume already-retained files only; they do not grant device,
USB, ALSA, capture, playback, front-panel, or interface-5 authority. Stop
before any live work until a future request records the exact authorization
fields in the final section.

## Plan gate before any live work

Copy the checked-in template to a new, never-before-used run directory and
populate it only under an exact future authorization. The checked-in template
is deliberately invalid: `authorization_status` is `NOT_AUTHORIZED` and every
physical-source field is `UNRECORDED`. It must remain invalid in source control.

The populated plan must retain serial `AB7C22200355`, the fixed candidate order,
two long `manual_preset_toggle` actions per candidate, `stop_on_first_positive`
as `true`, battery floor `10`, six-channel `S32_LE`/48 kHz audio, effect
candidates `[3, 4]`, discrete `P0`, `P1`, and `P2` reads, and the complete
prohibition list. Validate the retained plan before any live step:

```text
python3 re/cp34_current_slot_survey.py validate-plan RUN/PLAN.json
```

Continue only when its JSON status is `VALID` and its exit status is zero. Any
other result, including `UNRECORDED`, is a stop. A valid plan does not grant
live authority.

## Preconditions for an authorized future run

At or below 10% battery, stop. Record the external line-level source identity,
its isolated power source, exact local stimulus path and SHA-256, full cable and
adapter chain, external-source volume mark, target physical input, initial
connection, and predeclared inverse physical restoration. Use a separate source,
never an io24 output. Confirm phantom power is off. Do not adjust io24 gain,
level, routing, monitor, or any mapped value.

The declared raw-input peak must be from -36 through -12 dBFS, and every
captured channel must remain at or below -3 dBFS. If battery, identity, source,
phantom, physical connection, capture shape, or level preflight fails, record
`UNAVAILABLE` and stop before a Preset toggle. Only an exact later authorization
may permit adjustment of the external source; it never permits an io24 setting
change.

## Per-candidate sequence

For the attempted candidate, preserve each raw JaSt snapshot and bind its
summary to it by `raw_snapshot_path` and `raw_snapshot_sha256`. Summaries are
not substitutes for their immutable raw JaSt evidence. Write monotonic action
log entries in this exact order:

1. `P0`: bounded JaSt read; record the raw binding, selected numeric slot,
   enable flag, processing channels, phantom flags, input gains, headphone,
   main, and monitor blend. A slot mismatch is `UNAVAILABLE`; do not select it.
2. `M0`: capture the unchanged six-channel mapping WAV, close and hash it, then
   offline-map it. Freeze exactly one Mix A channel before any toggle.
3. `S1`: capture the initial-state raw WAV, close and hash it.
4. `T1`: after all streams close, make exactly one authorized long front-panel
   Preset press to enter the opposite enable/bypass state.
5. `P1`: bounded JaSt read and raw binding. The selected numeric slot must be
   unchanged and enable must be the logical inverse of `P0`; otherwise enter
   restoration handling immediately.
6. `S2`, then `S3`: capture and hash two opposite-state raw WAVs.
7. `T2`: after all streams close, make exactly one authorized restoring long
   front-panel Preset press.
8. `P2`: bounded JaSt read and raw binding. Selected slot, enable state,
   processing map, phantom, gains, headphone, main, and monitor blend must
   equal `P0`.
9. `S4`: capture and hash the restored-initial-state raw WAV.

ALSA capture streams and interface-5 claims never overlap. Close every ALSA
stream before a bounded interface-5 JaSt read, then release the claim before
the next capture. There is no continuous interface-5 claim.

Create post-close mono derivatives with the frozen map result only. Their names
are deterministic: `S1.mixN.mono.wav`, `S2.mixN.mono.wav`,
`S3.mixN.mono.wav`, and `S4.mixN.mono.wav`, where `N` is the frozen Mix A
channel (3 or 4). Raw WAVs remain unchanged. If `P0.enabled` is true, `S1` and
`S4` are active and `S2`/`S3` are dry; if false, their roles reverse. Filenames
never determine roles.

## Offline retained-file analysis

After a mapping raw WAV is closed and hashed, analyze the already-retained file:

```text
python3 re/cp34_current_slot_survey.py map-channel RUN/ch1-slot1/MAP.raw.wav --input-channel 1
```

The result has schema `cp34-current-slot-map-v1`, reports `raw_sha256`, input
metrics, scores for channels `3` and `4`, `frozen_mix_channel`, and reasons.
`MAPPED` freezes the higher score; an equal six-decimal score freezes channel 3.
`UNAVAILABLE` means no toggle and no replacement scan of channels 1, 2, 5, or 6.

For an enabled `P0`, analyze the retained derivatives exactly as follows (replace
`N` with the already-frozen channel; this is an offline file-analysis command).
Run it with the run directory as the working directory so the report preserves
the verifier's exact run-relative path labels:

```text
survey_root=$(pwd) && (cd RUN && python3 "$survey_root/re/cp34_live_matrix.py" analyze-slot --candidate ch1-slot1 --audible-attested --dry ch1-slot1/S2.mixN.mono.wav --dry ch1-slot1/S3.mixN.mono.wav --active ch1-slot1/S1.mixN.mono.wav --active ch1-slot1/S4.mixN.mono.wav)
```

For a bypassed `P0`, pass `S1` and `S4` as the two `--dry` values and `S2` and
`S3` as the two `--active` values. The actual `analyze-slot` result has schema
`cp34-slot-survey-audio-v1`, `candidate`, `model_identity: "UNRESOLVED"`,
`title_verified: false`, `live_ready: false`, `restoration_verified: false`,
`expected_delay_s`, dry/active metrics, and reasons. Only a result with
`status: "SIGNATURE_PRESENT"` and `classification:
"REPEAT_150MS_SIGNATURE"` remains a positive candidate for restoration
verification; do not make title or model claims from it.

## Restoration and sealing

Restore the predeclared physical connection and record its operator attestation.
Seal `EVIDENCE-SHA256SUMS` over every verifier input before invoking the
retained-file verifier:

```text
python3 re/cp34_current_slot_survey.py verify-restoration RUN --candidate ch1-slot1
```

Only `RESTORED` is a passing verifier status. Its `SIGNATURE_PRESENT` outcome
requires the restored state, exact evidence, and post-restoration audible
attestation; it supports only a restored repeatable audible 150 ms effect
signature on the controlled path. JaSt cannot prove every internal DSP byte.

The verifier does not trust `MAP.json` or `AB.json` as assertions. It
recomputes the canonical map from the snapshotted `MAP.raw.wav` bytes and the
plan's physical input, then compares the complete map result. It also invokes
the single `analyze-slot` algorithm on the four already-snapshotted derivative
byte buffers with their exact run-relative labels and compares the complete A/B
result. It creates no temporary WAV, rereads no live path, and imports no
driver. `MAP.raw.wav` and `S1.raw.wav` through `S4.raw.wav` must all be present
and exact six-channel S32_LE/48 kHz files independently of manifest exactness.

After saving the verifier JSON as `RESTORATION.json` and writing `REPORT.md`,
make the final retained-file seal and verify it:

```text
(cd RUN && tmpdir=$(mktemp -d .sha256sums.XXXXXX) && trap 'rm -rf "$tmpdir"' EXIT && set -o pipefail && find . -type f ! -name SHA256SUMS ! -path "./$tmpdir/SHA256SUMS" -print0 | LC_ALL=C sort -z | xargs -0r sha256sum -- > "$tmpdir/SHA256SUMS" && ln "$tmpdir/SHA256SUMS" SHA256SUMS && sha256sum -c SHA256SUMS)
```

The atomic `ln` fails if `SHA256SUMS` already exists; do not replace or remove
that file. The temporary manifest is excluded from its own NUL-safe enumeration.
`set -o pipefail` makes a failed `find` or `sort` fail the `&&` chain, so neither
`ln` nor verification can publish or accept a partial manifest.
This final SHA-256 command is an offline seal of retained files, not authority
for further operation.

## Outcome and candidate rules

`SIGNATURE_PRESENT` is positive only after `RESTORED`; stop after that first
positive. A null signal is `INCONCLUSIVE`, never a negative. `INCONCLUSIVE`
means no distinctive signature, non-specific late tail, or failed audible
attestation after successful restoration. Only a restored `INCONCLUSIVE` result for `ch1-slot1` makes
`ch2-slot1` eligible. `UNAVAILABLE` is a pre-mutation identity, battery, level,
map, or capture failure and does not permit channel 2. `RESTORATION_FAILED` is
an unresolved post-mutation state or physical restoration mismatch and does not
permit channel 2. If state after `T1` cannot be established from `P1` or
unambiguous front-panel observation, do not blind-toggle; record
`RESTORATION_FAILED` and stop for direction.

Before channel 2 can become eligible, the verifier requires the complete saved
channel-1 restoration result, including empty reasons, exact scope, frozen
channel, JaSt limitation, and scoped input hashes. It then independently
re-evaluates channel 1's plan, JaSt/raw snapshots, map, action log, five raw
captures, four derivatives, A/B result, audible attestation, and physical
restoration from the same immutable run snapshot. The saved result must exactly
equal that recomputation; neither a newly manifested result assertion nor its
hash is proof by itself.

No outcome proves a negative, a preset title, a model identity, custom
device-resident storage, or complete internal-DSP restoration. The procedure
never claims a title or model.

## Required future exact authorization

A future request must explicitly name: device serial; new run ID and evidence
directory; external-source device and power; exact local stimulus path and
SHA-256; cable/adapter chain; external-source volume; physical input,
connection, and inverse restoration; battery floor; phantom-off and no-io24-
setting preflight; six-channel ALSA capture identity and format; each bounded
interface-5 JaSt read and release; exactly two manual long presses per attempted
candidate; evidence creation and hashing; post-restoration external playback
for audible attestation; and the permitted candidate order/stop condition. It
must separately state that all prohibitions above remain in force. Without every
one of those fields, stop before live work.
