# Task 3 — exact UC 4.7.2 Standard high-shelf recovery

Recover the missing Standard high-shelf coefficient algorithm from retained exact Universal Control 4.7.2 evidence, make the recovery reproducible, and only then replace the current textbook-RBJ approximation.

## Exact retained authority

- DSP module: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260906T001130-0700-uc472-official-reacquisition/extracted/hwaccess/dspusbdevice.dll`
- Expected size: `4,979,672` bytes.
- Expected SHA-256: `de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.
- Shared UC coefficient designer begins at VA `0x180010d30`; its object layout and wire order `[b0, -a1, b1, -a2, b2]` are already documented in `io24_fx.py` around its coefficient helpers. The exact low-shelf branch/type 8 at VA `0x1800125de` is an established comparison point.
- High-band selector evidence is `eqtype4`, descriptor VA `0x1800ef2e8`, parameter id 19, enum `0..3`, UI step 2. Factory/scene evidence binds `eqbandop4=1` to high shelf but does not itself prove the designer selector value.

## Required analysis gate

- Add a bounded, read-only, hash-gated analyzer under `re/` and a focused test. It must refuse the wrong binary identity.
- Trace the exact `eqtype4`/high-band recompute path to the shared designer and prove the selector used for shelf mode. Do not assume selector 2 merely from the descriptor step.
- Disassemble only the relevant bounded call/branch regions. Record exact VAs, branch/selector evidence, constants, float precision/rounding behavior, operation order, normalization, and output field order.
- Produce a stable analysis artifact under a new task-local run directory with source identity, recovered selector/algorithm, and at least one exact five-float32 golden vector derived from a retained Standard factory high-shelf tuple (a known example has gain `6.030929`, Q `0.6`, frequency `3926.376953`).

## Integration gate

- Do not change `io24.biquad_highshelf` if any selector, branch, constant, sign, operation order, or float-rounding step remains inferred rather than source-bound. In that case report `BLOCKED` with the smallest next offline step.
- If fully proven, implement UC-bit-exact high shelf in the established coefficient format, with input validation consistent with other builders. Add exact-byte golden-vector tests and representative boundary/property tests.
- Ensure GTK response visualization uses the same production helper or exact semantics so displayed and transmitted response cannot diverge.
- Remove `exact_vendor_highshelf_bits_pending` only from rows actually closed by the evidence. Preserve all Passive/Vintage blockers.
- Update the deterministic 750-row matrix, plan/inventory wording, task-local analysis checkpoint, and the existing 7-entry campaign checkpoint only after tests are final.

## Verification and safety

- Run the new analyzer/test and focused Host/DSP/factory/Hot Key/P1 suites affected by the change, with bytecode disabled.
- Regenerate the matrix twice and prove byte identity; preserve exactly 750 rows.
- No USB/device/audio, Host launch, Wine or protected prefix access, firmware action, install, network, user-cache mutation, or Obsidian mutation.
- There is no Git repository. Record exact before/after hashes in the task report. You are not alone in the tree; preserve Tasks 1–2 and unrelated user/agent edits.

