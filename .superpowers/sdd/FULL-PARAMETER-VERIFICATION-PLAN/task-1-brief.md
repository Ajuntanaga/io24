# Task 1 fix round 1 — reconcile recovered P1 Host repairs

Address every finding from the independent review of the 2026-09-06 P1 repair. Preserve the now-present source-bound Host Hot Key implementation and its tests.

## Required fixes

1. Remove or make non-executable the `io24_scene.py` Vintage-to-Standard approximation. `plan(..., vintage=True)` must never return direct-live `set_eq_band` calls for Vintage/Passive state; exact alternate EQ remains blocked and fail-closed.
2. After explicit cached-state reapplication, adopt the remembered `phonesSrc` into the GTK selector under its mute guard. The visible selector and requested write-only Host state must agree, and programmatic adoption must not emit a write.
3. Make factory preset application atomic for malformed compressor inputs. Before the first device-facing call, validate finiteness, ranges, enum/index values, and real selected model builder serialization. A malformed Standard/Tube/FET compressor must produce zero device calls, including no earlier order/filter/gate write.
4. Stop UCNET from publishing a fabricated default `global/phonesSrc=Main`. Before an explicit Host write or identified Host shadow, the write-only route must be absent or explicitly unknown, never asserted as device state.
5. Reconcile the run artifacts: update the P1 plan wording and inventory to reflect implemented `phonesSrc` and fail-closed alternate EQ; update the checkpoint only after all required files/tests/matrix are final.
6. Bind `io24d.py`, `io24_scene.py`, and `ucnet_shim.py` in the deterministic matrix `source_sha256` inventory.
7. Use `io24_presets.compressor_model()` for GTK compressor display/adoption so UI and actual dispatch cannot diverge.
8. Fix the existing `ResourceWarning` in `io24_presets.load()` by using a context-managed read without changing behavior.

## Verification

- Extend `tests/test_io24_host_parameter_repairs.py` with direct regression contracts for every behavioral finding above, including all three compressor models and zero-call failure atomicity.
- Run the focused P1/Hot Key/preset/Host suites. Run with warnings elevated where practical so the file-handle regression is meaningful.
- Regenerate the 750-row matrix and verify deterministic byte identity.
- Recompute `CHECKPOINT.sha256` only after all listed artifacts have reached their final reviewed candidate state. Do not claim a seal or live verification.

## Safety and ownership

No USB/device/audio, GTK launch, Wine, firmware, network, install, cache mutation, or Obsidian mutation. Work only in the current project tree. There is no Git repository; record before/after hashes in the report. You are not alone in the codebase: preserve the Hot Key changes and all unrelated user/agent edits.

