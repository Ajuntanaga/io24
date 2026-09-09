# CP34 UC 4.7.2 save/assign UI route

Timestamp: 2026-09-06T01:04:49-07:00
Status: authorized offline static continuation

## Objective

Use the already retained, hash-pinned Universal Control 4.7.2.108537 installer
to identify the UI/service modules involved in preset Save, Assign, and Recall;
trace their call or message route into the exact `dspusbdevice.dll`; and
determine whether a separate device-resident transaction or native-u32-two
producer exists beyond the already source-bound `MemP/Stat` record writer.

## Authorized

- Read-only parsing of the retained installer, decompressed payload, and exact
  extracted vendor modules.
- Offline extraction of relevant embedded modules into this run directory.
- Static strings, import/export, resource, disassembly, and cross-reference
  analysis using Linux tools.
- Test-first task-local analyzers, contracts, evidence, and checkpoint updates.

## Forbidden

- Loading or executing any vendor executable, DLL, installer, or service.
- Wine or access to `/home/ajuntanaga/.wine-io24`.
- USB/device access, interface claim/detach, transfer, ALSA/audio, front-panel,
  preset/effect, firmware-image, reset, DFU, flash, staging, or REAPER action.
- Network access or package installation.
- Emitting, modifying, or replaying firmware or a newly inferred device frame.

## Pinned inputs

- Installer SHA-256:
  `1b5ddd6fd3ad4b93529caf8e5933bcd52b13194bdfa62652292b46ddcd980b95`.
- Decompressed payload size/SHA-256: 260,786,914 bytes,
  `b346bcdf0e7216f06f5a7705a5f80bc102971b319e77868cedbbc9636a2ec5f2`.
- `hwaccess/dspusbdevice.dll` size/SHA-256: 4,979,672 bytes,
  `de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.
- Predecessor checkpoint:
  `runs/20260906T001130-0700-uc472-official-reacquisition/CHECKPOINT.sha256`.

## Claim boundary

Static call/message evidence may identify host behavior but cannot establish a
physical write, backend commit, stored-record equality, preset round trip,
runtime component selection, Voice FX activation, or audibility. Stop if
module extraction would require vendor-code execution or if a proposed live
frame lacks an exact source-bound path.
