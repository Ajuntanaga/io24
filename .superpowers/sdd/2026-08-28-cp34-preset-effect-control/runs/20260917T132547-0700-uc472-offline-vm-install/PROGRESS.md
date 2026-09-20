# Universal Control 4.7.2 offline VM installation

Date: 2026-09-17

## Done

- Built `media/io24-guest-tools-uc472.iso` from the retained official
  Universal Control 4.7.2.108537 installer plus bounded install and verification
  scripts.
- Hash-pinned both VM launchers to that ISO so the rejected 5.0 media cannot be
  substituted under the selected filename.
- Booted the Windows guest with `-nic none` and without `--with-io24`.
- Installed Universal Control, launched it successfully, performed a direct
  installed-file version readback, and shut the guest down cleanly.

## Verified

- Source installer: 186,792,552 bytes, SHA-256
  `1b5ddd6fd3ad4b93529caf8e5933bcd52b13194bdfa62652292b46ddcd980b95`.
- Selected ISO SHA-256:
  `876a9f2cb6ab9933505894247b06acfeef52eee1cfe3c605850093e769eff506`.
- Extracting the installer and both scripts back from the ISO reproduced their
  source hashes exactly.
- Universal Control opened normally and displayed `No Devices available`.
- Installed executable:
  `C:\Program Files\PreSonus\Universal Control\Universal Control.exe`.
- Installed product version: `4.7.2.108537`.
- Verifier result: `APP_FOUND=1`, `VERSION_MATCH=1`, `VERIFY_EXIT=0`.
- Final `qemu-img check --output=json` reported `check-errors: 0`.
- The monitor socket and PID file disappeared after ACPI shutdown.

## Unverified

- No io24 was attached, so Universal Control's Revelator io24 rack UI and live
  Voice FX activation transaction have not yet been captured in this VM.
- This installation does not itself prove audible Voice FX.

## Decisions

- Universal Control 5.0 remains a rejected comparison artifact and is not
  referenced by either launcher.
- The guest remains offline. Device passthrough remains a separate explicit
  authorization gate.
- The first install batch used a protected `C:\` log target and received
  `Access is denied`; the installer completed successfully. The scripts and
  ISO were corrected to use the desktop before the final version readback.

## Evidence

- `UC472-VERIFY.png` shows the installed path, exact product version, successful
  match, and zero verifier exit code.
- `.vm/io24-windows/README.md`
- `.vm/io24-windows/shared/install-uc472.cmd`
- `.vm/io24-windows/shared/verify-uc472.cmd`
- `.vm/io24-windows/launch-guest.sh`
- `.vm/io24-windows/launch-install.sh`

## Next

With separate exact USB/device authorization, boot using
`./launch-scoped.sh guest --with-io24`, confirm Universal Control renders the
Revelator io24 Voice FX rack, and capture the smallest live enable/disable
transaction without firmware update or preset-save operations.
