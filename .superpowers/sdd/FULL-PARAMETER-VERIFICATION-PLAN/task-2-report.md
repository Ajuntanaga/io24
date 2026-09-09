# Task 2 report — source-bound Host Hot Key

Status: `DONE_WITH_CONCERNS`

## Outcome

Implemented the Linux Host Hot Key as a momentary, per-physical-channel Host
snapshot transition. It does not emit `Pari/151`, invent a Hot Key wire
command, create a device slot, or claim device readback/standalone persistence.

- `HostHotKeySession` captures a normalized full Host snapshot and projects
  only the selected channel's readable gain/phantom values, supported Fat
  Channel calls, channel-owned mixer routes, preset selector/enable state, and
  VoiceFX owner/model/state when that physical channel owns the singleton.
- `assign()` rejects incomplete, malformed, cross-channel/global,
  unknown-setter, and Passive/Vintage alternate-EQ state during preflight.
  Preflight exercises the real setter/builders with transport sinks discarded,
  before the first caller-device setter.
- `press()` captures the complete known normal Host state before replay and
  marks the channel active only after successful replay. `release()` replays
  that normal state. Repeated press/release events are no-write idempotent.
- Channel 1 and Channel 2 assignment, normal snapshots, and active state are
  independent.
- GTK now presents one `Capture Host snapshot` plus momentary `Hold Hot Key`
  control per physical channel in a separate `Host Hot Key snapshots` group.
  Its text explicitly says device readback and standalone persistence are
  unavailable. A synchronization guard makes programmatic adoption silent.

## TDD evidence

RED, before production edits:

```text
python3 -m unittest -v tests.test_io24_host_hotkey
Ran 6 tests: FAILED (failures=1, skipped=5)
AssertionError: source-bound HostHotKeySession is not implemented
```

Focused GREEN after implementation:

```text
python3 -m unittest -v tests.test_io24_host_hotkey
Ran 6 tests in 0.004s — OK
```

The focused tests cover per-channel projection, safe press/release ordering,
duplicate-event idempotence, preflight failure atomicity, failed-press session
state, VoiceFX ownership/order, other-channel isolation, and silent GTK event
adoption.

## Required regression verification

Command:

```text
python3 -m unittest -v \
  tests.test_io24_host_hotkey \
  tests.test_io24_host_parameter_repairs \
  tests.test_io24_host_state_repair \
  tests.test_io24_preset_persistence \
  tests.test_io24_voicefx_preset_apply \
  tests.test_io24_full_parameter_inventory
```

Result: `82 tests passed` in `0.366s`.

The suite emits one pre-existing `ResourceWarning` from
`io24_presets.py:200` for `json.load(open(p))`; it does not fail the suite and
was outside this task's minimal owned change.

## Matrix verification

`state.hotkey_ch1`, `state.hotkey_ch2`, and `state.hotkey_release` now use the
`host_mapping` profile and have no
`not_exposed_by_current_linux_host` blocker. The deterministic matrix remains
exactly 750 rows.

Fresh temporary generation and checked-in matrix were byte-identical:

```text
ce74f77850c3c218cca2fba7a541d1caea899a152db4623acd8b2f0868467afd  temporary
ce74f77850c3c218cca2fba7a541d1caea899a152db4623acd8b2f0868467afd  checked-in
```

## Exact before/after hashes

No Git repository is present, so no commit was attempted.

| File | Before SHA-256 | After SHA-256 |
| --- | --- | --- |
| `io24.py` | `539097c1f8e902804291f26677646a37e8b71d3329afb5f0dd5bbff34bcfaa82` | `ee9ff6f27394850ab8b8d70d6a83b99043070e93a5dfb9f2cf6d29df59c684ab` |
| `io24gtk.py` | `5f4632c3b5280146cb66dfcdb67dcaabd4d704eadbcd597ec5e2e2fd70ef3ce0` | `02a54e168f6dee58e2143a9bc069cd5b34da6d3bcaafc3619acb362198e924df` |
| `tests/test_io24_host_hotkey.py` | absent | `76c47d2b3bfa0953c5d1efde135d37a7cfa19e79eb658529fa30fca7cd5fd0ed` |
| `runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py` | `183237174cb994c99034d0e9287771b970088df91bac93290be7e8f1cd57333c` | `b28ff466609ca99b21f0f0341ba1f358aae8647da76350006459f855cb2d59b8` |
| `runs/20260906T165749-0700-host-live-routing-repair/PARAMETER-VERIFICATION-MATRIX.json` | `ef8a18fa92d37f54847d62db45af68054abfdf6f8c833739581964729e37a3e5` | `ce74f77850c3c218cca2fba7a541d1caea899a152db4623acd8b2f0868467afd` |

## Boundaries and concerns

- Hardware/runtime audibility, device readback, and standalone persistence
  remain unverified by design; this task was hardware-free.
- No GTK Host launch, USB/device/audio access, Wine access, firmware action,
  network access, Obsidian operation, or user-cache access occurred.
- The existing `ResourceWarning` noted above is the only test-output concern.

## Review fix round 1/5 — 2026-09-07

Status: `FIXED_GREEN`

The three Important findings and one Minor finding were addressed without
changing the GTK file or reverting the concurrent Task-1 repair:

1. `press()` now records the captured normal snapshot before target replay.
   If any target setter fails, it immediately replays the fully preflighted
   normal plan. The original exception remains the raised exception and gains
   `hotkey_rollback="RESTORED"` plus an exception note. If rollback itself
   fails, the original exception records `hotkey_rollback="FAILED: ..."`, and
   the session deliberately remains active with its normal snapshot retained
   so `release()` can retry restoration.
2. Capture now takes a fresh readable parameter observation and overlays the
   selected channel's gain, phantom, slot index, preset-enable flag, and exact
   processing ownership before projection. Stale shadow selector calls cannot
   win. When readable ownership differs from cached ownership, cached
   write-only `set_fx` state is discarded rather than reassigned to the newly
   observed owner.
3. A held snapshot that changes VoiceFX ownership now captures the prior owner
   in the normal replay plan. Both owner-2 normal -> owner-1 held -> owner-2
   release and the inverse are covered.
4. The three 750-row matrix entries now trace directly to
   `HostHotKeySession.assign`, `.capture`, `.press`, and `.release` as
   applicable; row count remains 750.

### Round-1 RED

```text
python3 -m unittest -v tests.test_io24_host_hotkey
Ran 9 tests in 0.016s
FAILED (failures=4, errors=1)
```

The expected failures showed: no `hotkey_rollback` status, stale slot `1`
instead of readable slot `0`, only the held owner call in both ownership
directions, and empty matrix API lists.

### Round-1 GREEN

```text
python3 -m unittest -v tests.test_io24_host_hotkey
Ran 9 tests in 0.017s
OK
```

Required focused suite:

```text
python3 -m unittest -v \
  tests.test_io24_host_hotkey \
  tests.test_io24_host_parameter_repairs \
  tests.test_io24_host_state_repair \
  tests.test_io24_preset_persistence \
  tests.test_io24_voicefx_preset_apply \
  tests.test_io24_full_parameter_inventory
Ran 94 tests in 0.498s
OK
```

`python3 -m py_compile` also passed for `io24.py`, the focused test, and the
matrix builder. A fresh temporary matrix was byte-identical to the generated
matrix at SHA-256
`2118a8ddb9956d1dec8708735552cb59a153445a3304148b4a46d830dc931293`.

### Round-1 exact hashes

| File | Before round 1 | After round 1 |
| --- | --- | --- |
| `io24.py` | `ee9ff6f27394850ab8b8d70d6a83b99043070e93a5dfb9f2cf6d29df59c684ab` | `f07b79c1774d43e76d0de579a3252491246481d8af8bb8e6f8fcd9c74960e89f` |
| `io24gtk.py` | `1f815f5725a7b6f0bc1f85bcef26d55c40d5909730b4d047a152f6677add1985` | `1f815f5725a7b6f0bc1f85bcef26d55c40d5909730b4d047a152f6677add1985` |
| `tests/test_io24_host_hotkey.py` | `76c47d2b3bfa0953c5d1efde135d37a7cfa19e79eb658529fa30fca7cd5fd0ed` | `3802cf366aa56dbf150510780cfdc4e3852454a62f1cea6f91df450c761187f4` |
| `runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py` | `0c48d84d6fc8a71dec1b372b87897083015cc4056b4243b045614b3c9f35ede5` | `9f4be96178cc235158ba0f23fc73aedfc76094d3a739c5f4b57823947456c92b` |
| `runs/20260906T165749-0700-host-live-routing-repair/PARAMETER-VERIFICATION-MATRIX.json` | `1b7bf5a09e7a88092795d1e5995061835be0f05f9e619bb659a5ebfdec7859ae` | `2118a8ddb9956d1dec8708735552cb59a153445a3304148b4a46d830dc931293` |

No Git repository is present, so no commit was attempted. No device, USB,
audio, Wine, network, Host launch, firmware, Obsidian, or user-cache action
occurred.

## Review fix round 2/5 — 2026-09-07

Status: `FIXED_GREEN`

The remaining VoiceFX coherence issue is fixed:

- An ownership-changing press now treats the prior owner selector and that
  owner's complete cached `set_fx` model/state as one normal-state unit.
  Successful release and failed-press rollback both replay the prior owner
  before its exact model/state.
- If the readable prior owner has no complete cached `set_fx` state, or the
  cached owner disagrees with readable ownership, normal capture raises
  `HostActionError` before the first held-state setter or ownership write.
  No write-only model is inferred.
- Distinct held/normal values prove the behavior: held owner model uses
  `time_s=0.11`; both normal release and rollback restore the prior owner's
  `time_s=0.77`. Both ownership directions are covered for successful release.

### Round-2 RED

```text
python3 -m unittest -v tests.test_io24_host_hotkey
Ran 10 tests in 0.015s
FAILED (failures=5)
```

The failures showed rollback and both release directions retained only
`time_s=0.11`, while missing and owner-incoherent prior FX state did not fail
closed.

### Round-2 GREEN

```text
python3 -m unittest -v tests.test_io24_host_hotkey
Ran 10 tests in 0.011s
OK
```

Required focused suite:

```text
python3 -m unittest -v \
  tests.test_io24_host_hotkey \
  tests.test_io24_host_parameter_repairs \
  tests.test_io24_host_state_repair \
  tests.test_io24_preset_persistence \
  tests.test_io24_voicefx_preset_apply \
  tests.test_io24_full_parameter_inventory
Ran 97 tests in 0.384s
OK
```

`python3 -m py_compile` passed for `io24.py`, the Hot Key test, and the matrix
builder. The first combined verification invocation used the checkpoint
subdirectory as its working directory, so repository-relative compile/test
paths failed; rerunning unchanged from the project root produced the GREEN
result above. The checkpoint manifest itself passed `sha256sum -c`.

The regenerated 750-row matrix and a fresh temporary build were byte-identical
at SHA-256
`cfd23cddccfba35cc0e0e8ea79b29aa70442e3aa1f21ac63f11ee7fd62771278`.

### Round-2 exact hashes

| File | Before round 2 | After round 2 |
| --- | --- | --- |
| `io24.py` | `f07b79c1774d43e76d0de579a3252491246481d8af8bb8e6f8fcd9c74960e89f` | `e3afa4304d07c8ec9cec00544d60600ee835c66804e4170cdc59d3ec77bd931c` |
| `io24gtk.py` | `1f815f5725a7b6f0bc1f85bcef26d55c40d5909730b4d047a152f6677add1985` | `1f815f5725a7b6f0bc1f85bcef26d55c40d5909730b4d047a152f6677add1985` |
| `tests/test_io24_host_hotkey.py` | `3802cf366aa56dbf150510780cfdc4e3852454a62f1cea6f91df450c761187f4` | `b0f1d4e3332879d83fceb0a40e69a227116b5ba471e43706e8f3da75467ced8c` |
| `runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py` | `9f4be96178cc235158ba0f23fc73aedfc76094d3a739c5f4b57823947456c92b` | `9f4be96178cc235158ba0f23fc73aedfc76094d3a739c5f4b57823947456c92b` |
| `runs/20260906T165749-0700-host-live-routing-repair/PARAMETER-INVENTORY.json` | `4ace9a7375c3f91b94d02d8bd8b1244f373170035f6907716a944ea09c7a3af6` | `4ace9a7375c3f91b94d02d8bd8b1244f373170035f6907716a944ea09c7a3af6` |
| `runs/20260906T165749-0700-host-live-routing-repair/PARAMETER-VERIFICATION-MATRIX.json` | `73d84f4f0df6dc03110275786943a20f17c2aa6ca4aade63539d9d745e6fc713` | `cfd23cddccfba35cc0e0e8ea79b29aa70442e3aa1f21ac63f11ee7fd62771278` |
| `runs/20260906T165749-0700-host-live-routing-repair/CHECKPOINT.sha256` | `7a3999c40212b73c78fa30c9bffd16cb5557a9e5e179dfe18ad14895a6a40926` | `fd1d04859a351895fc8caf747338f97e794e539b49d5ed857a1977165b7da3dc` |

No Git repository is present, so no commit was attempted. No device, USB,
audio, Wine, network, Host launch, firmware, Obsidian, or user-cache action
occurred. Concurrent Task-1 GTK, inventory, builder, matrix, and checkpoint
content was preserved; only the matrix/checkpoint hashes required by this
round's `io24.py` and focused-test changes were refreshed.
