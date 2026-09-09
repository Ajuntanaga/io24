# Task 3 report — exact UC 4.7.2 Standard high shelf

Status: `DONE_WITH_CONCERNS`

## Outcome

Recovered and implemented the exact Universal Control 4.7.2 Standard
high-shelf route from the retained, hash-gated `dspusbdevice.dll`.

- Standard `eqtype4` UI enum `2` maps through `[3, 8, 9, 6]` to designer
  selector `9`; the selector was not inferred from descriptor step `2`.
- The Standard component uses the binary64 designer at `0x18000f8b0`, not the
  float designer at `0x180010d30` named in the task brief.
- The exact selector-9 high-shelf branches are `0x18001039d` for full
  recompute and `0x1800175cd` for the Standard incremental clone.
- `io24.biquad_highshelf()` now follows the source instruction order, narrows
  its three parameter inputs to binary32, performs the designer operations in
  binary64, and independently narrows the five output fields to binary32 in
  wire order `[b0, -a1, b1, -a2, b2]`.
- GTK high-shelf visualization calls that same production helper and only
  reorders/sign-corrects its wire fields into graph convention. Displayed and
  transmitted high-shelf coefficients therefore share one implementation.
- The exact retained Bright Vocal vector is
  `ac5ce03f98b18e3ff79b16c08c69b6be1c88573f`.
- Only the eight Standard EQ `shape` rows lost
  `exact_vendor_highshelf_bits_pending`. All 34 Passive/Vintage rows remain
  fail-closed, and both Passive `bfreq` rows retain the unresolved vendor
  `20kHz` blocker.

No production edit was made until the selector, branches, constants, signs,
operation order, normalization, precision transitions, and output order were
all source-bound and the analyzer tests were GREEN.

## Exact retained authority and identity gate

| Input | Size | SHA-256 |
| --- | ---: | --- |
| `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260906T001130-0700-uc472-official-reacquisition/extracted/hwaccess/dspusbdevice.dll` | 4,979,672 | `de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28` |
| `re/uc_factory_presets.json` | 47,158 | `89b0572dd760b77831d012e2db0568b4f4eeb158985a4ca86126be28e934c73d` |

`re/uc472_standard_highshelf.py` checks both size and SHA-256 before PE
parsing or disassembly. Its wrong-identity test flips the final DLL byte and
requires `AnalysisError: DSP SHA-256 differs` before analysis.

The analyzer treats the PE as bytes; it never loads or executes vendor code.
It disassembles 18 named, independently SHA-pinned regions totaling 2,275
bytes and 484 instructions. Tables and constants are read only at exact VAs.
The stable artifact records every region start, exclusive end, size,
instruction count, and SHA-256:

`.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260907T192625-0700-uc472-standard-highshelf/ANALYSIS.json`

Artifact status:
`UC472_STANDARD_HIGHSHELF_SOURCE_BOUND`.

## Required brief reconciliation

Two locations supplied in the brief do not describe the exact retained DLL's
Standard path and were not trusted:

1. The Standard descriptor constructor at `0x180048aa3` registers 25 records
   beginning at `0x1800ed690`, with stride `0x68`. Record 19 is therefore
   `0x1800ede48` and decodes as kind `2`, id `19`, name `eqtype4`, range
   `0..3`, default `0`, UI step `2`. The brief's `0x1800ef2e8` does not begin
   with the exact `(kind=2,id=19)` identity and is marked stale for this DLL.
2. The brief's shared float designer `0x180010d30` is not called by the
   Standard route. The Standard setter at `0x1800167e0` widens the three
   binary32 band values and calls the binary64 full designer at
   `0x18000f8b0` when the mapped type changes.

These corrections are assertions in the analyzer and saved artifact, not
post-hoc narrative substitutions.

## Exact selector and recompute route

| Evidence | Exact VA/value | Source-bound conclusion |
| --- | --- | --- |
| Standard component constructor | `0x180048aa3` | Calls object constructor `0x180015970`; Standard vtable is `0x180434320`. |
| Descriptor registration | `0x180048bb3` | Table `0x1800ed690`, 25 records, stride `0x68`; actual `eqtype4` record `0x1800ede48`. |
| Parameter setter | `0x180015c80` | id 19 partitions as high band `(19-1)//6 = 3`, field case `(19-1)%6 = 0`. |
| `eqtype` case | `0x180015d84` | Adds exact binary32 `0.5`, applies `cvttss2si`, then calls virtual slot `+0xc0`. |
| Mapper and table | `0x180015c60`, `0x1800e81e0` | Exact u32 table `[3, 8, 9, 6]`; UI enum `2` becomes selector `9`. |
| Standard band caller | `0x1800160c0` | Loads gain/Q/frequency with `movss` and calls setter `0x1800167e0` at `0x1800160db`. |
| Full designer call | call `0x1800168ef` -> `0x18000f8b0` | Standard type change uses binary64 full recompute. |
| Full dispatch | `0x18000f922`, common trig `0x18000ff44` | Outer and inner exact tables map selector `9` to `0x18001039d`. |
| Full high-shelf branch/tail | `0x18001039d`, `0x18001033b` | Exact high-shelf arithmetic and shared coefficient tail. |
| Incremental dispatch/branch | `0x180017036`, `0x1800175cd` | Matching Standard selector-9 clone; golden bytes agree with full recompute. |
| Sample-rate scaling | `0x18000f7d0` | Stores `pi/sample_rate`; recompute forms `w=(f+f)*(pi/sample_rate)`. |
| Paired trig | `0x1800d15c0` | Binary64 low lane is sine and high lane is cosine. |
| Power call | thunk `0x1800d3556`, IAT `0x1800e4508` | `api-ms-win-crt-math-l1-1-0.dll!pow`, binary64. |
| Output call/conversion | call `0x18001610f` -> `0x180013270`; conversion begins `0x180014396` | Five independent `cvtpd2ps` conversions yield adjacent output floats. |

The full and incremental outer maps both send selector `9` into trig class 7;
their inner maps send that selector into high-shelf class 4. This makes the
selector and branch identity independent of the factory label.

## Constants, precision, signs, and field order

Exact binary64 constants used by the branch:

| Name | VA | Bits | Value |
| --- | --- | --- | ---: |
| gain exponent | `0x1804807a8` | `0x3f9999999999999a` | `0.025` |
| one half | `0x1804807f0` | `0x3fe0000000000000` | `0.5` |
| one | `0x1804807f8` | `0x3ff0000000000000` | `1.0` |
| pi | `0x180480810` | `0x400921fb54442d18` | `3.141592653589793` |
| power base | `0x180480828` | `0x4024000000000000` | `10.0` |
| minus two | `0x180480a68` | `0xc000000000000000` | `-2.0` |
| sign mask lane 0 | `0x180480d60` | `0x8000000000000000` | `-0.0` |

The Standard caller supplies frequency, gain, and Q as binary32. The setter
widens each exactly with `cvtss2sd`/`cvtps2pd`. There is no intermediate
binary32 narrowing in the branch. The five object doubles at offsets `+0x78`,
`+0x80`, `+0x88`, `+0x90`, and `+0x98` represent
`[b0, -a1, b1, -a2, b2]`; conversions at `0x1800143a3`, `0x1800143a7`,
`0x1800143b8`, `0x1800143d6`, and `0x1800143da` narrow them independently to
binary32 in that order.

The recovered operation order is:

```text
f = round_f32(frequency); g = round_f32(gain); q = round_f32(Q)
pi_over_fs = pi / fs
w = (f + f) * pi_over_fs
sine = sin(w); cosine = cos(w)
A = pow(10.0, g * 0.025)
Am1 = A - 1.0
beta_base = sqrt(A) * (1.0 / q)
Ap1 = A + 1.0
Am1c = Am1 * cosine
denominator_base = Ap1 - Am1c
Ap1c = Ap1 * cosine
numerator_base = Ap1 + Am1c
beta = beta_base * sine
normalization = 1.0 / (denominator_base + beta)
-a1 = ((Am1 - Ap1c) * -2.0) * normalization
A_normalized = A * normalization
b1 = ((Am1 + Ap1c) * -2.0) * A_normalized
-a2 = -((denominator_base - beta) * normalization)
b2 = (numerator_base - beta) * A_normalized
b0 = (numerator_base + beta) * A_normalized
return round_f32_each([b0, -a1, b1, -a2, b2])
```

The placement of `normalization`, `A_normalized`, the two `-2.0`
multiplications, and the separate `-a2` sign operation are preserved exactly;
algebraically equivalent reassociation was not used.

## Retained factory golden vector

The retained factory extraction has exactly one matching record:

| Field | Value |
| --- | --- |
| preset | `Bright Vocal` |
| retained record offset | `154728487` |
| Standard EQ class | `{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}` |
| factory flags | `eqbandop4=1`, `eqbandon4=1` |
| gain | `6.030929` -> binary32 `0x40c0fd5f` |
| Q | `0.6` -> binary32 `0x3f19999a` |
| frequency | `3926.376953` -> binary32 `0x45756608` |
| sample rate | `48000.0` Hz |

Output in established wire order:

```text
[1.7528281211853027,
 1.1147947311401367,
-2.353269338607788,
-0.3562740087509155,
 0.8419206142425537]
```

Binary32 words:

```text
[0x3fe05cac, 0x3f8eb198, 0xc0169bf7, 0xbeb6698c, 0x3f57881c]
```

Exact little-endian bytes:

```text
ac5ce03f98b18e3ff79b16c08c69b6be1c88573f
```

The prior textbook helper produced
`ac5ce03f98b18e3ff79b16c08b69b6be1b88573f`; the final two words were each
one ULP below the retained UC result. The analyzer's independent full and
incremental source-order transcriptions produce identical corrected bytes.

## TDD evidence

### Analyzer RED

The identity/selector/golden tests were written before the analyzer existed:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_uc472_standard_highshelf
```

Observed result: three analyzer tests failed. Each stopped on the intended
missing-capability assertion:

```text
AssertionError: UC 4.7.2 Standard high-shelf analyzer is missing
```

### Analyzer GREEN

After adding the bounded analyzer and stable artifact, the same three tests
passed. The final combined focused module result is shown below.

The exact analyzer command was:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/uc472_standard_highshelf.py \
  '.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260906T001130-0700-uc472-official-reacquisition/extracted/hwaccess/dspusbdevice.dll' \
  re/uc_factory_presets.json \
  --output '.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260907T192625-0700-uc472-standard-highshelf/ANALYSIS.json'
```

Result: exit `0`, no stdout/stderr.

### Production/GTK RED

Five integration test methods were added before changing production. Their 15
failures showed all intended gaps:

- the old helper returned
  `ac5ce03f98b18e3ff79b16c08b69b6be1b88573f` rather than the exact golden;
- boundary results were not independently narrowed to binary32;
- non-finite/out-of-descriptor inputs were accepted, and zero sample rate
  raised `ZeroDivisionError` rather than `ValueError`;
- GTK's response helper did not call the production high-shelf helper.

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_uc472_standard_highshelf.StandardHighShelfIntegrationTests
```

Observed RED result: five methods ran with 15 failed assertions/subtests.

### Matrix/documentation RED

The final two ledger tests were added before updating generator, inventory, or
plan. Both failed because all eight Standard shape rows still carried
`exact_vendor_highshelf_bits_pending` and the inventory still listed the
Standard builder as unresolved.

Observed RED result: two tests ran, `FAILED (failures=2)`.

### Final focused GREEN

```text
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest -v \
  tests.test_uc472_standard_highshelf
```

```text
Ran 10 tests in 0.051s
OK
```

These tests cover exact retained identity, wrong-DLL rejection, descriptor and
selector route, full/incremental agreement, literal five-float golden bytes,
public `set_eq_band()` Bqdf delivery, both descriptor-corner byte vectors,
finite/stable outputs, invalid direct inputs, GTK helper reuse, inventory/plan
wording, row count, and precise blocker retention.

## Required affected regression verification

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest -v \
  tests.test_uc472_standard_highshelf \
  tests.test_io24_host_parameter_repairs \
  tests.test_io24_full_parameter_inventory \
  tests.test_io24_host_hotkey \
  tests.test_io24_host_state_repair \
  tests.test_io24_preset_persistence \
  tests.test_io24_voicefx_preset_apply \
  tests.test_io24_host_delay_action \
  tests.test_io24_factory_slap_action \
  tests.test_cp34_host_queue_inventory \
  tests.test_cp34_preset_recall_static \
  tests.test_cp34_uc472_hotkey_voicefx_route
```

```text
Ran 121 tests in 0.812s
OK
```

The trailing dry diagnostic remained the expected existing line:

```text
global/phonesSrc = 1.0000 -> Pari id=11 index=0 value=2
```

`-W error::ResourceWarning` remained GREEN; no ResourceWarning was emitted.

Additional hardware-free DSP/factory builder checks:

```text
PYTHONDONTWRITEBYTECODE=1 python3 io24_dsp.py
```

Result: exit `0`, `ALL CHECKS PASSED`.

```text
PYTHONDONTWRITEBYTECODE=1 python3 io24_fx.py
```

Result: exit `0`, `OK -- all six models`.

## Deterministic matrix and blocker scope

Two fresh builds were made with:

```text
PYTHONDONTWRITEBYTECODE=1 python3 \
  runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py \
  --output /tmp/io24-task3-matrix-a.json

PYTHONDONTWRITEBYTECODE=1 python3 \
  runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py \
  --output /tmp/io24-task3-matrix-b.json

cmp /tmp/io24-task3-matrix-a.json /tmp/io24-task3-matrix-b.json
```

Both builds and `cmp` exited `0`. Both temporary files and the saved matrix
have SHA-256:

```text
60a17f347832cc80dc9440832284c300c72b29708cd2b5d5fe6321db1cc93f16
```

Exact matrix audit:

```text
rows                                      750
Standard EQ shape rows                      8
Standard shape rows with old blocker        0
Passive/Vintage alternate rows             34
alternate builder blocker retained          34
Passive bfreq rows                           2
vendor 20kHz blocker retained                2
```

All 750 campaign rows remain `PENDING`; closing this static implementation
blocker does not claim a live verification result.

## Checkpoints

The new task-local analysis checkpoint has exactly seven entries and SHA-256
`843535f42f52b721532df2b98f88ec38548f5c29d6dca83d17abc76967eed549`.
From the project root:

```text
sha256sum -c \
  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260907T192625-0700-uc472-standard-highshelf/CHECKPOINT.sha256
```

Result: `7/7 OK`.

The existing campaign checkpoint remains exactly seven entries and now has
SHA-256
`eb0d625abd05e260b9bf1035feaee1655e12aaa85ce682c179268d3ed25cf449`.
From its run directory:

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

## Exact before/after hashes

| File | Before Task 3 SHA-256 | After Task 3 SHA-256 |
| --- | --- | --- |
| `io24.py` | `e3afa4304d07c8ec9cec00544d60600ee835c66804e4170cdc59d3ec77bd931c` | `ec2b4fc3d2a20656af700560c0d4aa2c26b175fbf20039baf66eee592dcc5dd6` |
| `io24gtk.py` | `1f815f5725a7b6f0bc1f85bcef26d55c40d5909730b4d047a152f6677add1985` | `f30f33ac673cf0863a3ea332a4fafc71c7899c4c403f2b0e1b963b155b003ea7` |
| `re/uc472_standard_highshelf.py` | absent | `3b7b8a82117433e07c7fc5a9f4b753de820934159b6ba000279f935b27b79923` |
| `tests/test_uc472_standard_highshelf.py` | absent | `f9286257d336c53b2918d7322a947a9ab69817649b7adbe2f1324dcfe8305f0f` |
| task run `SCOPE.md` | absent | `e61680d1d0bacbc11d502dc577e9621642eb8a5871a1c974754f48e04d382424` |
| task run `ANALYSIS.json` | absent | `1272b104009b931c61cc7798bb90fa3918e9a2aa3a8e836ee4402d2701070012` |
| task run `PROGRESS.md` | absent | `108031a1d381bb15782e43406e1c0509a4c3c2c38ab727fdf7d8bf1d63df0ebe` |
| task run `CHECKPOINT.sha256` | absent | `843535f42f52b721532df2b98f88ec38548f5c29d6dca83d17abc76967eed549` |
| `runs/20260906T165749-0700-host-live-routing-repair/build_parameter_matrix.py` | `9f4be96178cc235158ba0f23fc73aedfc76094d3a739c5f4b57823947456c92b` | `f06d6679ac94d422e9ea4c7b72f857aad035665b44768f9a8e8cf120086fed22` |
| `runs/20260906T165749-0700-host-live-routing-repair/PARAMETER-INVENTORY.json` | `4ace9a7375c3f91b94d02d8bd8b1244f373170035f6907716a944ea09c7a3af6` | `d608461881d536bf3dc76a32b26d938828555ffe06e1eb8b3208a7b4d3e68e45` |
| `runs/20260906T165749-0700-host-live-routing-repair/PARAMETER-VERIFICATION-MATRIX.json` | `cfd23cddccfba35cc0e0e8ea79b29aa70442e3aa1f21ac63f11ee7fd62771278` | `60a17f347832cc80dc9440832284c300c72b29708cd2b5d5fe6321db1cc93f16` |
| `runs/20260906T165749-0700-host-live-routing-repair/FULL-PARAMETER-VERIFICATION-PLAN.md` | `be8c51df20134010b7a89064d60bdfc8cacc7bbbb6722c9c9bac48c5e3e57295` | `9a2fd18dd3fd37f0a99fe56461a36f446d5c926b44b1a7cb5371bf6552714c66` |
| `runs/20260906T165749-0700-host-live-routing-repair/CHECKPOINT.sha256` | `fd1d04859a351895fc8caf747338f97e794e539b49d5ed857a1977165b7da3dc` | `eb0d625abd05e260b9bf1035feaee1655e12aaa85ce682c179268d3ed25cf449` |
| `.superpowers/sdd/FULL-PARAMETER-VERIFICATION-PLAN/progress.md` | unavailable; only prefix `23d13...` survived context compaction | `f05137942215e9bf2918ce01c1e0a3ca069f0996e80b23761fdaf31f2fab42ae` |

The full pre-Task-3 progress-ledger digest was searched for in task-local
reports/logs, Claude outputs, and temporary prompt artifacts but was not
recoverable. It is explicitly unavailable rather than inferred. Every current
and final digest above is exact. This newly created report intentionally does
not self-hash.

## No-commit note, boundaries, and concerns

`git rev-parse --is-inside-work-tree` exits `128` with `fatal: not a git
repository`; no commit was possible or attempted.

- This is static retained-source and hardware-free host-byte evidence. It does
  not establish device acceptance, audible response, device-resident storage,
  recall, or standalone persistence.
- The task brief's descriptor VA and float-designer starting point were stale
  for the exact retained DLL. The analyzer records the mismatch and gates the
  actual Standard path; no fact was carried forward from those stale locations.
- Passive and Vintage EQ algorithms remain unimplemented and fail-closed. The
  Passive `20kHz` vendor literal remains unresolved.
- No device/USB/audio access, Host launch, Wine or protected-prefix access,
  firmware action, network access, installation, user-cache access, or
  Obsidian operation occurred.
- Tasks 1 and 2 and unrelated workspace edits were preserved.
