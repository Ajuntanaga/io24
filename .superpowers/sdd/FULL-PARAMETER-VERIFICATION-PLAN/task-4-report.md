# Task 4 report — Claude P2 audit reconciliation

Date: 2026-09-08
Status: implementation and local verification GREEN; independent peer review
complete with no open Task 3 or Task 4 findings

## Outcome

The executable defects in Claude's 2026-09-07 read-only P2 audit are repaired
without touching hardware:

- restoration ledgers accept an explicit `clamp_probe` only for `set_send_db`,
  require the out-of-range requested value and exact clamped wire value, and
  still reject ordinary out-of-range mapped writes and unsafe inverses;
- the loopback analyzer records correlation and level for all six capture
  channels, treats physical Input 2 as the reference rather than routed
  leakage, requires the routed winner in USB 3/4, and fails on correlated
  leakage elsewhere;
- audio-rig validity is batch-scoped, with same-path positive controls at both
  batch boundaries; cold start is a future campaign precondition, not a 751st
  matrix row and not authority to act now;
- the plan and matrix carry bootloader trigger/recovery/`Upload Unsupported`,
  the 2026-08-11 block-201 prior negative, the MemP receiver ambiguity,
  selector-versus-recall language, and the firmware slot-index exchange;
- display-only preset mode now terminates as `PASS_FRONT_PANEL`, not
  `PASS_AUDIO`.

Claude's recommendation to search all six channels required one source-aware
adjustment: capture channel 2 is the Input-2 correlation reference, so it will
always correlate perfectly with itself. The analyzer records it but excludes
it from routed-winner and leakage classification. This preserves the intended
USB 3/4 exclusion proof.

## TDD evidence

The first focused run had 11 expected failures/errors across the missing
six-channel report, leakage/out-of-pair classifications, clamp-probe schema,
batch authority, clamp oracle, front-panel status, side-effect/selector notes,
prior evidence, and MemP blocker. After implementation, 77 focused tests pass.

The broader affected run passes 162 tests across:

- `tests.test_io24_loopback_foundation`
- `tests.test_cp34_live_matrix`
- `tests.test_io24_full_parameter_inventory`
- `tests.test_io24_host_parameter_repairs`
- `tests.test_io24_host_state_repair`
- `tests.test_io24_host_hotkey`
- `tests.test_io24_preset_persistence`
- `tests.test_io24_voicefx_preset_apply`
- `tests.test_uc472_standard_highshelf`

The matrix was generated twice to independent `/tmp` paths and compared with
the checked-in artifact. All three files were byte-identical at SHA-256
`9b220c0c2b8224a1452c11cf9b79b336f5e369253503aa4387ffc968a8ba577e`;
the row count remains exactly 750.

## Before identities

| File | SHA-256 before Task 4 |
|---|---|
| `FULL-PARAMETER-VERIFICATION-PLAN.md` | `9a2fd18dd3fd37f0a99fe56461a36f446d5c926b44b1a7cb5371bf6552714c66` |
| `build_parameter_matrix.py` | `f06d6679ac94d422e9ea4c7b72f857aad035665b44768f9a8e8cf120086fed22` |
| `PARAMETER-VERIFICATION-MATRIX.json` | `60a17f347832cc80dc9440832284c300c72b29708cd2b5d5fe6321db1cc93f16` |
| `re/io24_loopback_foundation.py` | `708a69c4f1011310ee1fdcb093a842d04402dd64e99b26b05336c81e3621a46d` |
| `re/cp34_live_matrix.py` | `aac2a39a49284cc42c01247fca53fbaf6b0af1a04dd3182b82aa7358c5db95c8` |
| `tests/test_io24_loopback_foundation.py` | not captured before edit; do not infer unchanged identity from the current/checkpoint hash |
| `tests/test_cp34_live_matrix.py` | `0f27703b9ba94b4af9807ca6bc1f9389f81deb31d12d8d14f435055d1d4b7b8f` |
| `tests/test_io24_full_parameter_inventory.py` | `1b50fa43acdd152e38f599769b805afe97a4752cf5bd2f265e242daa592e7017` |

## Boundary

No live P2 retry, USB/device access, playback/capture, Host launch, Wine access,
firmware/DFU/reset action, network access, installation, cache change, staging,
or Obsidian mutation occurred. The old failed P2 batch remains closed and its
raw evidence remains failure-labelled.

## Independent peer review

The serialized Claude peer reviewed two successive 32-file hash-pinned
snapshots created at `2026-09-08T01:39:37-07:00` and
`2026-09-08T01:48:51-07:00`. It independently re-derived Task 3 with no
finding and found no correctness defect in Task 4's clamp-probe schema,
Input-2 self-correlation exemption, exact bootloader re-enumeration/recovery
text, or per-batch positive-control mechanics. It reported no remaining open
Task 3 or Task 4 item.

The peer also noticed that this report presented the current/checkpoint hash of
`tests/test_io24_loopback_foundation.py` as its pre-Task-4 identity. No genuine
pre-edit hash was captured for that file. The table now records that limitation
instead of claiming an unchanged RED-to-GREEN test identity. This is a report
provenance correction; it does not change source, tests, or the local GREEN
result.
