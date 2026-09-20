# Universal Control 4.7.2 live VoiceFX capture attempt

Date: 2026-09-17

## Done

- Forwarded the one exact Revelator io24, serial `AB7C22200355`, to the
  offline Windows guest and recorded QEMU's libusb traffic with the retained
  `usbtap` interposer.
- Logged into the guest, verified Windows' composite-device enumeration,
  checked the control-interface driver and the PreSonus Hardware Access
  Service, and launched Universal Control 4.7.2 twice.
- Stopped the live session immediately when Windows automatically opened an
  audio-output stream. No VoiceFX control, preset operation, firmware action,
  reset, DFU action, network access, Wine use, or power cycle occurred.
- Rebooted the guest without the io24 and exported bounded Windows service,
  PnP, SetupAPI, and network diagnostics to a temporary NTFS image. The
  diagnostic guest was then shut down cleanly.

## Verified

- Preflight battery was 99 percent; the only forwarded USB identity was
  `194f:0422`, serial `AB7C22200355`, firmware revision `0128`.
- Windows enumerated `Revelator IO 24`, `Revelator IO 24 MIDI`,
  `Revelator IO 24 CTRL`, and `Revelator IO 24 DFU`. Device Manager reported
  the CTRL function as working and bound to Microsoft's WinUSB driver
  `10.0.26100.1150`.
- Enumeration returned Microsoft's OS 1.0 descriptors: interfaces 5 and 6 are
  `WINUSB`; interface 5 carries `DeviceInterfaceGUID`
  `{69EE78BD-5751-4BB4-B00C-ECE34E011DF8}` and interface 6 carries
  `{833A3A1A-7703-481F-841D-499764520869}`.
- SetupAPI recorded successful installation/start of the PreSonus
  `PaeDSPUSB`/`PaeDSPUSBks` functions during this first live attachment.
- `PreSonus Hardware Access Service` was running, automatic, and listening on
  UDP 47809. `Universal Control.exe` independently listened on the same port.
  This worked with no present virtual network adapter, so `-nic none` is not
  the enumeration blocker.
- Universal Control still displayed `No Devices available`. The trace contains
  zero bulk lines on control endpoint 1, so the Hardware Access Service never
  opened the io24 UCNET/control channel in this attempt.
- Windows automatically issued 34,544 trace lines on audio OUT endpoint 3,
  beginning before any VoiceFX action. The VM was stopped on detection.
- Postflight restored the io24 to Linux; the Windows qcow2 passed
  `qemu-img check` with zero errors. The later no-device diagnostic VM also
  passed the same check after shutdown.
- `bash -n` passes for the guest launchers, `vnc-control.py` compiles, and the
  three `usbtap` contracts pass.

## Unverified

- Universal Control did not reach the device page, so no UC VoiceFX rack,
  independent component On transaction, model selection, or parameter delta
  was captured.
- No new evidence yet changes the established listening verdict: Host block
  201 remains inaudible while reverb/block 202 works.
- The Linux Host's missing live activation transaction therefore remains to be
  derived; this attempt proves the VM USB and Windows driver layers, not that
  VoiceFX is fixed.

## Decisions

- Do not add a virtual NIC. UCNET's required local discovery path is already
  active without one.
- The first attachment installed the PreSonus device drivers during the live
  session; the Hardware Access Service was running when inspected afterward.
  A second attachment with those drivers already staged, followed if necessary
  by one Hardware Access Service restart, is the smallest discriminator for
  the failed hand-off.
- A repeat must prevent Windows Audio from opening the composite audio
  endpoints before USB attachment. The bounded method is to boot without USB,
  temporarily stop Windows Audio in the guest, hot-plug the exact serial,
  watch for any endpoint-3 traffic and detach immediately if it appears, then
  restore the service after the capture.
- Temporarily stopping/restarting Windows services is a new system-state gate;
  do not perform that rerun without exact authorization.

## Evidence

- `uc-qemu-usbtap.txt`: raw enumeration/audio trace, 780,243,680 bytes,
  SHA-256 `705ab30c4a7a756a3563fbfedd15145534416511abfe67baa35dab3e0ccd3a73`.
- `uc-qemu-control-filtered.txt`: endpoint-0/endpoint-1 view, 2,347,344 bytes,
  SHA-256 `d5dddcb715948af97348b4dd97f16e2ba7fed11d93730dde3d78714b94c0c285`.
- `diag-export.ntfs`: guest diagnostic export image, SHA-256
  `64c432aa896cac705be77b1bff80baaef7fbd547833bc5e56fe5244802ed05ca`.
- `ctrl-properties-02.png`, `ctrl-driver-01.png`,
  `ctrl-interface-guids.png`, `services-presonus.png`, `uc-open-02.png`, and
  `uc-reopen-01.png` record the live Windows/UC state.
- `diag-ucnet-processes.png`, `diag-netadapter-2.png`, and
  `diag-export-files.png` record the isolated follow-up diagnosis.

## Next

After explicit authorization to temporarily stop/start Windows Audio and, if
needed, restart only the PreSonus Hardware Access Service inside the isolated
guest: boot with no device, stop audio, hot-plug the exact io24, verify UC
enumeration, and capture the smallest VoiceFX component On -> one parameter ->
Off sequence with continuous endpoint-3 abort monitoring and full restoration.
