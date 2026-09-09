# Task 4 report: fail-closed operator procedure and template

Status: complete; documentation and fixture scope only. No live acquisition,
device operation, USB/ALSA opener, Wine/prefix access, network action, install,
staging, firmware/reset/DFU, output playback, monitoring, slot selection,
mapped write, or guessed packet was run.

## RED/GREEN

RED: added
`SurveyTemplateContractTests.test_checked_in_template_is_rejected_as_unrecorded_and_unauthorized`
before the template existed. The real `validate-plan` subprocess returned exit
2 but the test failed at its `authorization_status` assertion because the absent
file produced only `plan_unreadable`.

GREEN: added the literal-shape checked-in template with
`authorization_status: "NOT_AUTHORIZED"` and all required physical-source
fields set to `"UNRECORDED"`. The contract then passed through the real
validator: exit 2, `INVALID`, with
`authorization_status_must_be_exactly_recorded` and
`unrecorded_value_prohibited` (case-insensitive assertion preserves the
required `UNRECORDED` sentinel contract).

## Exact test output

```text
...............................                                          [100%]
31 passed in 7.26s
```

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py
```

The 31 tests comprise 10 plan, 8 mapping, 12 restoration, and 1 template
rejection contract.

## Files and hashes

```text
1bb029a18181a85c602a84f42fbbf57602dbce321a5ae39727c14b9828a74ff3  re/cp34_current_slot_survey.py
2325bf438b18462455fc18a42e2b8869f8bb4b467ef23a5ac06709c2dcccecde  tests/test_cp34_current_slot_survey.py
8e5beb5b13da09cfa66b15908adf0189053c2861908822912e2d3ca860e52b28  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-DESIGN.md
72e8b2116271edad71afc77808abd1eab930a6398cee064de8117381e4e457cd  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md
3288d3be80f125e2a66f9be71e18fc213a5c6070fe1e99150d3e87cc80b72ac3  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-PLAN.template.json
7d24b3d3e6de5f0fc519768c9732cfdd08e49268cbb6024e4b43a299cc9f8e49  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-IMPLEMENTATION.md
```

## Stage manifest check

`sha256sum -c CURRENT-SLOT-SURVEY-STAGE.sha256` reported all six rows `OK`.
The stage manifest itself is:

```text
0dd9d317bc97ec843e4986b2f8e472442c5e99d642134d60e668c9981d309532  CURRENT-SLOT-SURVEY-STAGE.sha256
```

## Documentation self-review

Verified the required order: scope/prohibitions; no-authority statement; plan
gate; battery/source/phantom/level/physical preflight; exact
P0/M0/S1/T1/P1/S2/S3/T2/P2/S4 sequence; non-overlap of ALSA and interface-5;
offline map/analyze commands; restoration/final seal; positive/channel-2 rules;
outcome semantics; no-negative/title/model claims; and the exact future
authorization fields. The procedure documents JaSt summary-to-raw hash/path
bindings, deterministic `S1` through `S4` `mixN` derivatives, and the actual
`analyze-slot` result fields. All command examples are retained-file offline
validation, analysis, verification, or hashing only.

## Concerns

None. The procedure deliberately stops before live work; a valid populated plan
would still require a separately recorded exact authorization.

## Fix round 1

Status: complete; procedure/test/manifest changes only. No live acquisition,
device operation, USB/ALSA opener, Wine/prefix action, network action, install,
staging, firmware/reset/DFU, output playback, monitoring, slot selection,
mapped write, or guessed packet was run.

RED command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::SurveyTemplateContractTests::test_checked_in_template_is_rejected_as_unrecorded_and_unauthorized
F                                                                        [100%]
AssertionError: 3418 not less than 2913
1 failed in 0.08s
```

The focused assertion first proved that the P0/M0/S1/T1/P1/S2/S3/T2/P2/S4
sequence followed, instead of preceded, the explicit ALSA/interface-5
non-overlap rule. The same single existing test method also now requires the
explicit null-signal sentence and a NUL-safe, atomic no-clobber final seal.

GREEN command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::SurveyTemplateContractTests::test_checked_in_template_is_rejected_as_unrecorded_and_unauthorized
1 passed in 0.07s
```

Final suite:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py
31 passed in 7.27s
```

Changed files and refreshed manifest rows:

```text
e371c89d1fe9aa30114cee2085118aeb4bdd93fea05d6cf461ebe600e1b36aa2  tests/test_cp34_current_slot_survey.py
78983f3a33903d5cd896965f63b3a10913a455fecc028f94d873f63b2e9d4641  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md
```

`sha256sum -c CURRENT-SLOT-SURVEY-STAGE.sha256` reported all six rows `OK`.
The refreshed stage manifest hash is
`1cdf28109c9001419bf4b9f9f6019032fcf9475d6fdc408c24f6d11e05cd4d3b`.

Self-review: the complete discrete sequence now occurs before the explicit
ALSA/interface-5 no-overlap rule; the outcome text says, verbatim, "A null
signal is `INCONCLUSIVE`, never a negative." The final seal writes only a
temporary manifest, enumerates retained paths with `find -print0`, orders them
with `sort -z`, passes them through `xargs -0`, atomically publishes with `ln`,
and therefore fails if final `SHA256SUMS` already exists. It does not add live
authority or a live acquisition command.

## Fix round 2

Status: complete; procedure/test/manifest changes only. No live acquisition,
device operation, USB/ALSA opener, Wine/prefix action, network action, install,
staging, firmware/reset/DFU, output playback, monitoring, slot selection,
mapped write, or guessed packet was run.

RED command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::SurveyTemplateContractTests::test_checked_in_template_is_rejected_as_unrecorded_and_unauthorized
F                                                                        [100%]
AssertionError: 'set -o pipefail && find' not found in CURRENT-SLOT-SURVEY.md
1 failed in 0.09s
```

GREEN command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::SurveyTemplateContractTests::test_checked_in_template_is_rejected_as_unrecorded_and_unauthorized
1 passed in 0.06s
```

Final suite:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py
31 passed in 7.24s
```

Changed files and refreshed manifest rows:

```text
3119b35f1710470bc246897dce001098bfe75c86152754813e5e0913c724a55c  tests/test_cp34_current_slot_survey.py
295d6763f70a4bf095b0ad0fff1be16e85ac449aa9d6e7216a8cec8adcb87c43  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md
```

`sha256sum -c CURRENT-SLOT-SURVEY-STAGE.sha256` reported all six rows `OK`.
The refreshed stage manifest hash is
`25fbebbed34be6b11809f58e563a68844b675dfb3604805a51281b3d06c97f28`.

Self-review: `set -o pipefail` occurs before the NUL-safe
`find -print0 | LC_ALL=C sort -z | xargs -0r sha256sum --` pipeline within the
same `&&` chain. Thus a nonzero `find` or `sort` makes the pipeline nonzero and
prevents both the atomic `ln` publication and `sha256sum -c` verification. The
existing temporary cleanup, no-clobber behavior, and offline-only authority
boundary remain unchanged.
