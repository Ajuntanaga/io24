# UC 4.x VM media selection

Date: 2026-09-17

## Outcome

- Universal Control 5.0 is rejected for this Voice FX investigation.
- Both VM launchers now require the deliberately absent
  `.vm/io24-windows/media/io24-guest-tools-uc4x.iso` and no longer reference
  the existing `io24-guest-tools.iso` containing 5.0.
- No VM, network, Wine, USB, device, firmware, or hardware operation occurred.

## Local artifact findings

- The bounded search of the repository, Downloads, Documents, Desktop, trash,
  io24 cache, and recent Claude project records found no accessible 4.1 or 4.5
  installer.
- The recent Claude record says `4.1.0.93124` was named but not obtained, and
  `4.5.0.102825` was established from release notes rather than a trustworthy
  local artifact path.
- The exact locally available 4.x installer is
  `runs/20260906T001130-0700-uc472-official-reacquisition/PreSonus_Universal_Control_v4_7_2-108537.exe`:
  186,792,552 bytes, SHA-256
  `1b5ddd6fd3ad4b93529caf8e5933bcd52b13194bdfa62652292b46ddcd980b95`.
  It was not selected because 4.7.2 would be an unrequested substitution.
- `/home/ajuntanaga/Archive/Windows/Windows.old.zip` is the remaining plausible
  historical source, but it is a 67 GiB incomplete ZIP without an end-of-central-
  directory record. Bounded central-directory listing timed out. The archive was
  not brute-force scanned, consistent with the host-stability boundary against
  recursively searching all of Windows.old.

## Verification

- `bash -n` passes for `launch-install.sh` and `launch-guest.sh`.
- Invoking either inner launcher exits 2 before QEMU or device discovery with:
  `missing required VM file: .../media/io24-guest-tools-uc4x.iso`.

## Next

Use the exact local path to the intended 4.1/4.5 installer if supplied. If that
path is unavailable, the explicit alternatives are to approve the already
verified 4.7.2 artifact or separately authorize reacquisition of 4.5.
