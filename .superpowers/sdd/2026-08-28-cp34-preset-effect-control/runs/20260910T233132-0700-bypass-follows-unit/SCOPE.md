# Bypass follows the unit's press-and-hold — scope

Target: user-owned Revelator io24 serial `AB7C22200355`, firmware `0128`.

Objective: item 3 of the 2026-09-10 Codex handoff (`.claude-peer/OUTBOX.md`),
taken back by Claude after the user's "Resume" (23:28 PDT, usage window reset,
`main` fast-forwarded to `0f2dc41`, Codex not yet started). The Device page's
per-channel Bypass switch showed only what the Host sent; make it follow the
unit's own press-and-hold, which JaSt slot 42 bits 5/6 already report
(`s["preset_off"]`, io24gtk.py poll).

Constraints from the evidence: the bits latch during press-and-hold but a short
Preset press only blips them (poll comment), so a state must hold before it
counts; a poll taken before a Host write lands must never undo that write, so
only a device-side change may move a switch; the switch is adopted, never sent;
nothing is followed while the device is not alive.

Out of scope: the Presets-tab reorganization and every other handoff item
(left with Codex); any device, audio, USB, Host launch, Wine, install, network
or firmware action.

Lane: static source reading, code edits, hardware-free tests, deterministic
artifact regeneration, on worktree branch `worktree-io24-dsp-device-tab`.
