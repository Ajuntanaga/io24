# Preset saving and effect correctness — scope

Target: user-owned Revelator io24 serial `AB7C22200355`, firmware `0128`.

Objective: make saving a preset produce something the user can name, find and
hear, and make the effects correct at the clock the device is actually running.
Also correct the record about what `MAIN` contains.

Lane: static source reading, code edits, hardware-free tests, deterministic
artifact regeneration. No USB/device access, no audio, no Host launch, no Wine,
no install, no network, no firmware action, no device write of any kind.
