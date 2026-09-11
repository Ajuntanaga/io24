# Host solo, auto gain and alternate-model EQ view — scope

Target: user-owned Revelator io24 serial `AB7C22200355`, firmware `0128`.

Objective: act on the Host gaps Codex's 2026-09-09 parameter audit left open
after `db39742` closed limiter release, sample-rate propagation and reverb
Host-state persistence. The user chose all three buildable items together:

1. a Host-side mixer solo (UC `solo` has no device binding);
2. a Host-side automatic preamp gain (UC `autogain`/`autogainmode` have no
   firmware descriptor; re/UCNET_SHIM_SPEC.md 4c);
3. a read-only view of recalled Passive/Vintage EQ bodies, with a save that
   carries such an EQ through verbatim instead of overwriting it.

Out of scope, deliberately: `dawpostdsp` (host-bound to block 0, would move
main volume), `dspAmount`/`bypassDSP` (shadow-only, no device binding),
vocoder `avoiced` (no readback path), scene-import skips, and the pending
Channel-1 slot-0 MAIN rewrite (a separately authorized hardware action).

Lane: static source reading, code edits, hardware-free tests, deterministic
artifact regeneration. No USB/device access, no audio, no Host launch, no Wine,
no install, no network, no firmware action, no device write of any kind.
