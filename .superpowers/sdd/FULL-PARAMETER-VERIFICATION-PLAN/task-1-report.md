# Task 1 fix round 1 report — reconciled P1 Host repairs

Status: `DONE_WITH_CONCERNS`

No Git repository is present, so no commit was attempted.

## Outcome

All eight findings in `task-1-brief.md` were addressed in an offline,
hardware-free candidate:

1. `io24_scene.plan(..., vintage=True)` can no longer generate a
   `set_eq_band` call for Vintage EQ. Passive and Vintage alternate-model EQ
   remain record-preserved and fail-closed for direct-live replay until exact
   coefficient builders exist. The legacy flag is accepted only to report that
   it is disabled.
2. A successful explicit cached-state reapply captures the normalized Host
   shadow and adopts its remembered headphones source into the GTK selector
   while `_phones_source_mute` is held. The signal callback emits no write.
3. Factory compressor application preflights the complete selected Standard,
   Tube, or FET object before the first device-facing call. Required fields,
   finiteness, documented ranges, booleans, and the FET ratio index are checked,
   then the real selected `io24_dsp.cpxt_*` builder must serialize a 64-byte
   blob. A malformed compressor therefore cannot leak an earlier order,
   high-pass, gate, or other write.
4. `ucnet_shim.State` no longer invents `global/phonesSrc=Main`. The route is
   absent until an explicit UCNET write or a valid `set_phones_source` Host
   shadow identifies the requested write-only state.
5. The P1 plan and parameter inventory now describe the implemented headphones
   route and Host Hot Key, and state the fail-closed alternate-EQ policy.
6. The deterministic matrix now binds `io24d.py`, `io24_scene.py`, and
   `ucnet_shim.py` in `source_sha256`.
7. GTK factory-preset dynamics adoption now resolves the compressor through
   `io24_presets.compressor_model()`, the same class-ID-first resolver used by
   dispatch.
8. `io24_presets.load()` uses a context-managed read; its behavior and cache
   semantics are unchanged.

The pre-existing Host Hot Key implementation and its six tests remained
byte-identical.

## TDD evidence

### RED

The new regression contracts were written before production changes.

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest -v tests.test_io24_host_parameter_repairs
```

Exact summary:

```text
Ran 18 tests in 0.016s

FAILED (failures=12, errors=1)
```

The failures directly exposed the open-file `ResourceWarning`, stale inventory,
three absent matrix source hashes, malformed compressor acceptance/partial-write
risk, executable Vintage approximation, stale GTK selector after reapply, and
fabricated UCNET Main state. The builder-preflight test initially errored because
`io24_presets` did not yet import the selected builder module, also confirming
the missing preflight path.

The first field-conflict fixture accidentally agreed with the old heuristic. It
was corrected before implementation to a Standard class ID carrying a misleading
FET field, then run alone.

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_io24_host_parameter_repairs.FactoryPresetDispatchTests.test_gtk_compressor_adoption_uses_the_dispatch_model_resolver
```

Exact failure:

```text
AssertionError: 2 != 0
Ran 1 test in 0.003s

FAILED (failures=1)
```

### GREEN

Behavioral loop after the implementation changes:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest -v tests.test_io24_host_parameter_repairs.PhonesSourceTests tests.test_io24_host_parameter_repairs.FactoryPresetDispatchTests
```

```text
Ran 15 tests in 0.006s

OK
```

Complete repair module after inventory and matrix regeneration:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest -v tests.test_io24_host_parameter_repairs
```

```text
Ran 18 tests in 0.019s

OK
```

No `ResourceWarning` was emitted in either GREEN run. The existing UCNET routing
test prints its dry fake-route diagnostic after the test summary:

```text
global/phonesSrc = 1.0000 -> Pari id=11 index=0 value=2
```

## Focused regression

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest -v tests.test_io24_full_parameter_inventory tests.test_io24_host_hotkey tests.test_io24_host_state_repair tests.test_io24_preset_persistence tests.test_io24_voicefx_preset_apply tests.test_io24_host_delay_action tests.test_cp34_host_queue_inventory tests.test_cp34_preset_recall_static tests.test_cp34_uc472_hotkey_voicefx_route
```

Exact summary:

```text
Ran 85 tests in 1.134s

OK
```

Together, the final focused evidence is 103 passing tests: 18 repair contracts
plus 85 Host/Hot Key/preset/static regression tests, with resource warnings
elevated to errors.

## Deterministic matrix and checkpoint evidence

The 750-row matrix was generated twice to separate temporary paths, compared,
and then regenerated into the saved artifact.

Commands:

```text
PYTHONDONTWRITEBYTECODE=1 python3 runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py --output /tmp/io24-task1-matrix-a.json
PYTHONDONTWRITEBYTECODE=1 python3 runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py --output /tmp/io24-task1-matrix-b.json
cmp /tmp/io24-task1-matrix-a.json /tmp/io24-task1-matrix-b.json
sha256sum /tmp/io24-task1-matrix-a.json /tmp/io24-task1-matrix-b.json
PYTHONDONTWRITEBYTECODE=1 python3 runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py --output runs/20260906T165749-0700-host-live-routing-repair/PARAMETER-VERIFICATION-MATRIX.json
```

Exact output/return evidence:

```text
first generation: exit 0, no stdout/stderr
second generation: exit 0, no stdout/stderr
cmp: exit 0, no stdout/stderr
1b7bf5a09e7a88092795d1e5995061835be0f05f9e619bb659a5ebfdec7859ae  /tmp/io24-task1-matrix-a.json
1b7bf5a09e7a88092795d1e5995061835be0f05f9e619bb659a5ebfdec7859ae  /tmp/io24-task1-matrix-b.json
saved generation: exit 0, no stdout/stderr
```

The saved matrix reports `coverage.total_rows = 750`. Its source inventory
matches all three required dispatch sources:

```text
io24d.py       0d351c37b2fa3450446a9dcd6c0922b88d76e209b74df03a1bd55d1337c1ced5  match=True
io24_scene.py  8c5be86b1b44b80d84ff9e7346232bee05c20a408ca4cc4e52810adc173187e6  match=True
ucnet_shim.py  84d0c5a7f54ce41b478a923d2bf729a2f2c4ef22d50431c3564e602c8c863892  match=True
```

After all code, tests, plan, inventory, and matrix files were final, the
candidate checkpoint was updated and validated from its run directory:

```text
sha256sum -c CHECKPOINT.sha256
```

```text
FULL-PARAMETER-VERIFICATION-PLAN.md: OK
PARAMETER-INVENTORY.json: OK
PARAMETER-VERIFICATION-MATRIX.json: OK
build_parameter_matrix.py: OK
../../tests/test_io24_full_parameter_inventory.py: OK
../../tests/test_io24_host_parameter_repairs.py: OK
../../tests/test_io24_host_hotkey.py: OK
```

The execution wrapper also printed three `Failed to create stream fd: Operation
not permitted` diagnostics before the seven successful rows. A separate
read-only Python SHA-256 walk verified the same seven rows cleanly; there was no
manifest mismatch.

## Exact before/after hashes

Hashes were captured before the first edit and after final test/matrix work.

| File | Before SHA-256 | After SHA-256 |
| --- | --- | --- |
| `io24gtk.py` | `02a54e168f6dee58e2143a9bc069cd5b34da6d3bcaafc3619acb362198e924df` | `1f815f5725a7b6f0bc1f85bcef26d55c40d5909730b4d047a152f6677add1985` |
| `io24_scene.py` | `94b2e76c54655636eadf9e77f3d25b275306d84600d92e4e28f01d6648cb12f4` | `8c5be86b1b44b80d84ff9e7346232bee05c20a408ca4cc4e52810adc173187e6` |
| `io24_presets.py` | `6f000bd38b39243f48b5f38a5678f7576ca8ebfb09a3c3303913f0c272423359` | `e95e786b500218b4f0c623544260e35d3e4789309e39b1ba1ef6887dc286685f` |
| `ucnet_shim.py` | `c3ad843610bdfffc8d9e947221fcc60389eebaf5f5aba513a44b546a7194e1d8` | `84d0c5a7f54ce41b478a923d2bf729a2f2c4ef22d50431c3564e602c8c863892` |
| `tests/test_io24_host_parameter_repairs.py` | `0c78eb81839aa8e5665c40cf2f7831398a82dfba2aa2fe16a65a81b15f421910` | `cd54d74497611d091290c4f80eff6f5dfb965851a5166ee1a5feefaf88722bad` |
| `FULL-PARAMETER-VERIFICATION-PLAN.md` | `4d144cb160f8b311de941530ce8defea15928b21b440e5d9b9168f93677766eb` | `be8c51df20134010b7a89064d60bdfc8cacc7bbbb6722c9c9bac48c5e3e57295` |
| `PARAMETER-INVENTORY.json` | `5421f6791e421f77b4f8e482fe31f145372a553afe71dfa37c538889d91af2c7` | `f1f137f2181e412ea2607343fd697f9cbe505d0d97bdcf6d56645f52fd3272c9` |
| `PARAMETER-VERIFICATION-MATRIX.json` | `ce74f77850c3c218cca2fba7a541d1caea899a152db4623acd8b2f0868467afd` | `1b7bf5a09e7a88092795d1e5995061835be0f05f9e619bb659a5ebfdec7859ae` |
| `build_parameter_matrix.py` | `b28ff466609ca99b21f0f0341ba1f358aae8647da76350006459f855cb2d59b8` | `0c48d84d6fc8a71dec1b372b87897083015cc4056b4243b045614b3c9f35ede5` |
| `CHECKPOINT.sha256` | `f1c89e5381fb22c22acd2228f98ec26d7e155ded251afec9fdc49bdc75c50af9` | `a31e5fd5a9e7142fa58b40aa332c8c76e460e15602927af08c114befefa754f1` |

Preserved/unchanged files relevant to the concurrent Host Hot Key work:

| File | Before and after SHA-256 |
| --- | --- |
| `io24.py` | `ee9ff6f27394850ab8b8d70d6a83b99043070e93a5dfb9f2cf6d29df59c684ab` |
| `io24d.py` | `0d351c37b2fa3450446a9dcd6c0922b88d76e209b74df03a1bd55d1337c1ced5` |
| `tests/test_io24_host_hotkey.py` | `76c47d2b3bfa0953c5d1efde135d37a7cfa19e79eb658529fa30fca7cd5fd0ed` |
| `tests/test_io24_full_parameter_inventory.py` | `78f31e3ab618283e8f3b12e72aa9692f19d2eba11c4a2aecd58c6205f69cfc54` |

This report was newly created and is intentionally not self-hashed inside its
own contents.

## Boundaries and concerns

- This is an internally consistent candidate, not an independent review seal.
- All 750 matrix rows remain pending; no live device, readback, audio, or
  audibility result is claimed.
- Exact Passive/Vintage EQ builders, the exact Standard high-shelf builder, and
  generic `line/ch3` io24 applicability remain unresolved as recorded in the
  plan and inventory.
- No USB/device/audio access, GTK Host launch, Wine access, firmware operation,
  network access, installation, cache mutation, or Obsidian operation occurred.

## Round 2/5 — key-filter domain and positive Host capability inventory

Status: `DONE_WITH_CONCERNS`

No Git repository is present, so no commit was attempted.

### Outcome

- Factory compressor preflight now accepts only the model's documented
  key-filter off sentinel or `40..16000 Hz`: Standard and FET use `20 Hz`, Tube
  uses `0 Hz`. A value such as `1 Hz` fails before order, filter, gate, or any
  other device-facing call for all three models.
- `PARAMETER-INVENTORY.json` now has a positive
  `supported_host_capabilities` section. It explicitly records the write-only
  `global/phonesSrc` route and its five Host entrypoints, plus Channel-1 Hot Key
  snapshot override, Channel-2 Hot Key snapshot override, and release-to-normal
  behavior.
- The concurrent Hot Key repair had advanced before round 2 began. Its current
  `io24.py`, Hot Key test, matrix-builder, and matrix hashes were captured as
  the round-2 baseline; none was overwritten. The matrix was regenerated from
  that current builder only after the round-2 code/tests/inventory were final.

### Round-2 RED

After correcting a test fixture so an unrelated Vintage EQ record could not
mask the compressor result, the clean RED command was:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest -v tests.test_io24_host_parameter_repairs.FactoryPresetDispatchTests.test_below_minimum_compressor_keyfilters_fail_before_every_device_call tests.test_io24_host_parameter_repairs.ArtifactAndResourceTests.test_inventory_records_implemented_host_routes_and_fail_closed_eq tests.test_io24_full_parameter_inventory.FullParameterInventoryTests.test_supported_host_capabilities_are_positively_inventoried
```

Exact summary:

```text
Ran 3 tests in 0.006s

FAILED (failures=3, errors=2)
```

All three subtests (`Standard`, `Tube`, and `FET`) failed because `1 Hz` did
not raise `ValueError`. Both inventory tests errored with:

```text
KeyError: 'supported_host_capabilities'
```

### Round-2 GREEN

The same three-test command after the minimal changes produced:

```text
Ran 3 tests in 0.003s

OK
```

Required touched-artifact and focused Host/Hot Key regression command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest -v tests.test_io24_host_parameter_repairs tests.test_io24_full_parameter_inventory tests.test_io24_host_hotkey tests.test_io24_host_state_repair tests.test_io24_preset_persistence tests.test_io24_voicefx_preset_apply
```

Exact summary:

```text
Ran 96 tests in 0.524s

OK
```

No warning was suppressed; `ResourceWarning` remained elevated to an error.

### Round-2 deterministic matrix and checkpoint

Commands:

```text
PYTHONDONTWRITEBYTECODE=1 python3 runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py --output /tmp/io24-task1-round2-matrix-a.json
PYTHONDONTWRITEBYTECODE=1 python3 runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py --output /tmp/io24-task1-round2-matrix-b.json
cmp /tmp/io24-task1-round2-matrix-a.json /tmp/io24-task1-round2-matrix-b.json
sha256sum /tmp/io24-task1-round2-matrix-a.json /tmp/io24-task1-round2-matrix-b.json
PYTHONDONTWRITEBYTECODE=1 python3 runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py --output runs/20260906T165749-0700-host-live-routing-repair/PARAMETER-VERIFICATION-MATRIX.json
```

Exact output/return evidence:

```text
first generation: exit 0, no stdout/stderr
second generation: exit 0, no stdout/stderr
cmp: exit 0, no stdout/stderr
73d84f4f0df6dc03110275786943a20f17c2aa6ca4aade63539d9d745e6fc713  /tmp/io24-task1-round2-matrix-a.json
73d84f4f0df6dc03110275786943a20f17c2aa6ca4aade63539d9d745e6fc713  /tmp/io24-task1-round2-matrix-b.json
saved generation: exit 0, no stdout/stderr
```

The final checkpoint validation command was:

```text
sha256sum -c CHECKPOINT.sha256
```

```text
FULL-PARAMETER-VERIFICATION-PLAN.md: OK
PARAMETER-INVENTORY.json: OK
PARAMETER-VERIFICATION-MATRIX.json: OK
build_parameter_matrix.py: OK
../../tests/test_io24_full_parameter_inventory.py: OK
../../tests/test_io24_host_parameter_repairs.py: OK
../../tests/test_io24_host_hotkey.py: OK
```

As in round 1, the execution wrapper printed three `Failed to create stream
fd: Operation not permitted` diagnostics before the seven successful hash rows;
there was no manifest mismatch.

### Round-2 exact before/after hashes

| File | Round-2 before SHA-256 | Round-2 after SHA-256 |
| --- | --- | --- |
| `io24_presets.py` | `e95e786b500218b4f0c623544260e35d3e4789309e39b1ba1ef6887dc286685f` | `2f430b50320447c0842d5681774213ce61df1aa686cbf88814f6d60c518e8922` |
| `tests/test_io24_host_parameter_repairs.py` | `cd54d74497611d091290c4f80eff6f5dfb965851a5166ee1a5feefaf88722bad` | `8c7d8ff29f7b356dd97054347f3ba9fd2c393fcd83404db68b58ed599071a021` |
| `tests/test_io24_full_parameter_inventory.py` | `78f31e3ab618283e8f3b12e72aa9692f19d2eba11c4a2aecd58c6205f69cfc54` | `1b50fa43acdd152e38f599769b805afe97a4752cf5bd2f265e242daa592e7017` |
| `PARAMETER-INVENTORY.json` | `f1f137f2181e412ea2607343fd697f9cbe505d0d97bdcf6d56645f52fd3272c9` | `4ace9a7375c3f91b94d02d8bd8b1244f373170035f6907716a944ea09c7a3af6` |
| `PARAMETER-VERIFICATION-MATRIX.json` | `2118a8ddb9956d1dec8708735552cb59a153445a3304148b4a46d830dc931293` | `73d84f4f0df6dc03110275786943a20f17c2aa6ca4aade63539d9d745e6fc713` |
| `CHECKPOINT.sha256` | `a31e5fd5a9e7142fa58b40aa332c8c76e460e15602927af08c114befefa754f1` | `7a3999c40212b73c78fa30c9bffd16cb5557a9e5e179dfe18ad14895a6a40926` |

Concurrent files preserved unchanged during round 2:

| File | Round-2 before and after SHA-256 |
| --- | --- |
| `io24.py` | `f07b79c1774d43e76d0de579a3252491246481d8af8bb8e6f8fcd9c74960e89f` |
| `tests/test_io24_host_hotkey.py` | `3802cf366aa56dbf150510780cfdc4e3852454a62f1cea6f91df450c761187f4` |
| `build_parameter_matrix.py` | `9f4be96178cc235158ba0f23fc73aedfc76094d3a739c5f4b57823947456c92b` |

Round 2 remains an offline reviewed candidate, not a seal or live verification.
All 750 matrix rows remain pending; no USB/device/audio access, GTK Host launch,
Wine access, network access, firmware action, installation, cache mutation, or
Obsidian operation occurred.
