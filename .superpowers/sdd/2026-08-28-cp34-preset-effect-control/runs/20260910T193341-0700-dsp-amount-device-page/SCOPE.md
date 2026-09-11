# DSP amount and Bypass on the Device page — scope

Target: user-owned Revelator io24 serial `AB7C22200355`, firmware `0128`.

Objective: the user asked, of the items the previous run left alone, that
"dsp amount and bypass dsp ... at the very least" be settings "in the
host/settings tab" (2026-09-10 ~18:53 PDT). Present them per channel on the
Device page as UC does — a DSP amount and a Bypass switch — and remove the
single processing-mix slider from the Effects page, so each setting has one
control.

Grounding: the firmware has one processing scalar per channel, wire id 4
(`input1FxMix` / `input2FxMix`; PROTOCOL.md 2026-09-08 controlling
correction): exact zero bypasses the whole channel chain, any positive value is
the amount. UC's schema declares `dspAmount` (min 0.00001, "min > 0") and a
`bypassDSP` toggle; neither has a recovered device binding
(re/UCNET_SHIM_SPEC.md 4f). The Host composes them onto wire 4 — zero while
bypassed, the amount otherwise — and says so; it does not claim UC's binding.
The `component.line_chN.{dspamount,bypassdsp}` matrix rows stay `PENDING`.

Out of scope, deliberately: following the unit's press-and-hold on the Bypass
switch (the JaSt bit is readable, but syncing it needs an edge-triggered
design to avoid fighting in-flight writes); `dawpostdsp` (host-bound to block
0, would move main volume; a bounded live measurement is only proposed);
linking the two channels' processing; and the pending Channel-1 slot-0 MAIN
rewrite (a separately authorized hardware action).

Lane: static source reading, code edits, hardware-free tests, deterministic
artifact regeneration, in worktree branch `worktree-io24-dsp-device-tab`. No
USB/device access, no audio, no Host launch, no Wine, no install, no network,
no firmware action, no device write of any kind.
