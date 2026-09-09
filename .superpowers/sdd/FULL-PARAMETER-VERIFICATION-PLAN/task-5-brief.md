# Task 5 — offline Linux Host publication readiness

Prepare the repaired Host for a future initial source publication without
publishing, installing, initializing Git, or touching hardware.

## Required behavior

1. A wheel built from `pyproject.toml` must contain every local runtime module
   needed by the advertised Host entry points.
2. The supported Universal Control scene importer must have an installed
   console entry point. Its module and the GTK Host's optional factory-preset
   browser module must ship in the wheel; recovered PreSonus preset data remains
   source-tree evidence and is not silently added to the wheel.
3. README and GUIDE status must match the current task-local evidence: the
   corrected maximum-wet Channel-2 run occurred but was invalidated as a
   terminal firmware verdict by later Host-state defects; a clean Host round
   trip remains separately live-gated.
4. Documentation must describe the exact source-bound Standard high-shelf and
   keep Passive/Vintage direct-live replay fail-closed. It must not advertise
   the removed `--vintage-eq` approximation as executable.
5. Preserve the initial-release boundary: no custom-firmware implementation or
   device operation is made publishable by this task.

## Verification

- First observe a failing wheel-content test against the current metadata.
- Build the wheel offline with no dependency resolution or build isolation.
- Inspect the actual wheel contents and console-entry metadata.
- Run the affected Host/preset/documentation tests and the broader
  hardware-free Python suite appropriate to the changed surface.
- Regenerate the 750-row matrix twice and retain byte identity.
- Record exact before/after hashes and invoke the serialized Claude peer at the
  task boundary.

## Boundary

No USB/device/audio, Host or GUI launch, Wine/protected-prefix access,
firmware/DFU/reset, network publication, installation, user-cache mutation,
Git initialization, staging, or Obsidian mutation is authorized. The wheel is
built only in a disposable `/tmp` directory.
