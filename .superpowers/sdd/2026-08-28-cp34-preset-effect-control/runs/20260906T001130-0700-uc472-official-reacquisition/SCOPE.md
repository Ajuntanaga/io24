# CP34 official UC 4.7.2 reacquisition

Timestamp: 2026-09-06T00:11:30-07:00
Status: authorized acquisition and offline static analysis

## Objective

Reacquire the exact PreSonus Universal Control 4.7.2.108537 Windows installer
from the official product-download URL, verify it against the previously pinned
identity, extract the exact `hwaccess/dspusbdevice.dll` without installing or
executing vendor code, and trace the byte-level structured-state serializer
needed by CP34.

## Authorized

- One download from the official PreSonus/FMIC asset URL.
- Local hashing and immutable retention of the downloaded installer in this run.
- Offline archive extraction into this run directory.
- Read-only PE inspection, disassembly, and task-local analyzer/test work.
- Task-local evidence and checkpoint updates.

## Forbidden

- Installation or execution of the installer or any extracted vendor binary.
- Wine or access to `/home/ajuntanaga/.wine-io24`.
- USB/device access, interface claim/detach, transfer, ALSA/audio, front-panel,
  preset/effect, firmware-image, reset, DFU, flash, or REAPER action.
- Network access beyond the exact authorized official installer acquisition.

## Pinned expectations

- Official URL:
  `https://www.fmicassets.com/Damroot/Original/10121/PreSonus_Universal_Control_v4_7_2-108537.exe`
- Installer length: `186792552` bytes.
- Installer SHA-256:
  `1b5ddd6fd3ad4b93529caf8e5933bcd52b13194bdfa62652292b46ddcd980b95`.
- Expected `dspusbdevice.dll` length: `4979672` bytes.
- Expected `dspusbdevice.dll` SHA-256:
  `de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.

## Stop conditions

Stop if the installer size or SHA-256 differs, extraction would require vendor
code execution, or the exact DLL identity is absent. Static evidence must not
be reported as physical device behavior or authority for live work.
