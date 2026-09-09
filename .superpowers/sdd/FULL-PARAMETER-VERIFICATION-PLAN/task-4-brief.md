# Task 4 — reconcile Claude P2 hazard and metric audit

Implement only the hardware-free corrections supported by the independent
2026-09-07 Claude audit. No live retry is part of this task.

## Required behavior

1. Record the bootloader trigger, cold-power recovery, powered-hub caveat, and
   `Upload Unsupported` boundary in both human and machine-readable plans.
2. Make mixer clamp probes explicit and restoration-ledger-valid while keeping
   ordinary out-of-range mapped writes invalid. `None`/`-145.0` remains off;
   numeric `-144.0` remains a signal-passing floor.
3. Correlate the P2 capture across all six channels. Treat physical Input 2 as
   the reference rather than routed leakage; require the routed winner to be in
   USB 3/4 and reject correlated leakage elsewhere.
4. Make deterministic audio-rig validity batch-scoped and record cold start as
   a future live precondition without adding a 751st parameter row or granting
   live authority.
5. Preserve the block-201 prior negative, MemP receiver ambiguity, selector vs
   recall boundary, and firmware slot-index exchange on their matrix rows.
6. Replace the display-only preset-mode `PASS_AUDIO` label with
   `PASS_FRONT_PANEL`.

## Verification

Use RED/GREEN focused tests for the loopback analyzer, restoration ledger, and
deterministic 750-row matrix. Regenerate the matrix twice and prove byte
identity. Update the seven-entry campaign checkpoint and add a task-local
checkpoint/report only after all changed files are final.

## Safety

No USB/device/audio, Host launch, Wine or protected-prefix access, firmware,
DFU, reset, network, install, cache, staging, or Obsidian mutation. The exact
live preconditions documented here remain unexecuted and separately gated.
