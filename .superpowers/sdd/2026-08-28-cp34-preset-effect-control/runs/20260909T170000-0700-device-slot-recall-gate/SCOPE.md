# Device-slot recall and the Voice FX gate — scope

Target: user-owned Revelator io24 serial `AB7C22200355`, firmware `0128`.

Objective: give the Host the missing device-slot recall path, and make the
Effects page state whether block 201's gate is open, so Voice FX stops being
tuned behind a handler that discards every write.

Lane: static source reading, code edits, hardware-free tests, deterministic
artifact regeneration. No USB/device access, no audio, no Host launch, no Wine,
no install, no network, no firmware action, no device write of any kind. Every
live action remains a separate explicit authorization.
