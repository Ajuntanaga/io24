# UC 4.7.2 hardware-module extraction

Timestamp: 2026-09-06T00:18:42-07:00
Status: exact offline extraction; vendor code not executed

The pinned installer is a Nullsoft self-extracting PE. `NullsoftInst` occurs at
file offset `90120` (`0x16008`), and its zlib stream begins at offset `90140`
(`0x1601c`). Python's standard zlib reader decompressed that stream as data;
the installer and decompressed payload were never loaded as executable code.

The temporary decompressed stream was 260,786,914 bytes with SHA-256
`b346bcdf0e7216f06f5a7705a5f80bc102971b319e77868cedbbc9636a2ec5f2`.
A bounded scan of valid embedded PE headers located the exact expected
4,979,672-byte module at payload offset `146818467` (`0x8c045a3`). Its first
bytes are an `MZ` header and its PE-header offset is `0x120`.

The retained extraction is `extracted/hwaccess/dspusbdevice.dll`, a PE32+
x86-64 DLL with seven sections. Its SHA-256 is
`de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`,
exactly matching the historical pin.

The decompressed stream remains temporary under `/tmp` and is not a recovery
dependency. The installer and exact extracted DLL are retained in this run.
No Wine, install, USB/device, audio, firmware-image, or live action occurred.
