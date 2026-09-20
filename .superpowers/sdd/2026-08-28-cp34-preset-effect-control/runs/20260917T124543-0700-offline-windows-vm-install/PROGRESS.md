# Offline Windows VM installation checkpoint

Date: 2026-09-17

## Done

- Installed the SHA-256-verified Windows 11 Enterprise LTSC 2024 Evaluation
  image into the isolated QEMU/KVM guest.
- Kept the guest offline with `-nic none`; the io24 was never passed through.
- Moved QEMU out of the inherited Codex 3 GiB / 4 GiB memory scope into the
  dedicated `io24-uc-vm.scope`.
- Added `launch-scoped.sh` as the repeatable entry point with a 14 GiB soft
  limit and 16 GiB hard limit.
- Reached the `io24 lab` Windows desktop, opened `IO24_TOOLS`, and selected the
  staged Fender Universal Control 5.0.0.110112 installer without executing it.
- Shut Windows down cleanly through ACPI after the installer action was denied
  pending separate exact authorization.

## Verified

- Running QEMU cgroup:
  `/user.slice/user-1000.slice/user@1000.service/app.slice/io24-uc-vm.scope`.
- Final live scope properties: `MemoryHigh=15032385536` and
  `MemoryMax=17179869184`.
- Peak charged memory during installation: `14094671872` bytes, below the
  final soft limit. Host memory PSI was zero at the final install stages.
- Shutdown unit result: `success`; QEMU stopped and the transient scope became
  inactive/dead.
- `qemu-img check` reported no errors. The qcow2 dirty and corrupt flags are
  both false; virtual size is 64 GiB and actual size at checkpoint is
  8269508608 bytes.
- Windows Explorer displayed the offline `IO24_TOOLS` disc and the staged
  `Fender_Universal_Control_v5_0_0_110112` application.

## Unverified

- Universal Control is not installed. The persistent installer launch needs a
  new exact authorization.
- No io24 USB passthrough, native Universal Control transaction, firmware
  prompt, or VoiceFX capture has occurred.
- VoiceFX audibility is unchanged by this VM checkpoint.

## Decisions

- Use `./.vm/io24-windows/launch-scoped.sh guest` for the next offline boot;
  do not invoke the inner QEMU launcher directly.
- Keep networking disabled and the io24 detached while installing Universal
  Control.
- After separately authorized installation, shut down and prepare a bounded
  host USB capture before any separately authorized `--with-io24` boot.
- Decline any firmware update prompt.

## Evidence

- `.vm/io24-windows/launch-scoped.sh`
- `.vm/io24-windows/README.md`
- `.vm/io24-windows/state/io24-win11.qcow2`
- `windows-desktop-tools-drive.png`

## Next

Obtain exact authorization to install the already staged, offline Fender
Universal Control v5.0.0.110112 package (SHA-256
`6e9a5953f1d0dd4eac839d67faed0923f626b63bb1a3968129295bc66677bf53`)
inside this guest. That authorization does not include io24 passthrough,
firmware changes, or network access.
