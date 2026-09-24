# Android controller implementation record

Version 0.3.4 is feature-complete for the offline and emulator milestone. The
remaining work is a separately controlled physical acceptance run, not more UI
scaffolding.

## Completed

- [x] Prove direct Android access to io24 interface 5 while another app records
      and plays USB audio.
- [x] Isolate the firmware's short `SetP` reply and serialize ACK drain before
      a fresh `JaSt` read.
- [x] Replace the fixed Input 2 prototype with immutable state, typed commands,
      a pure reducer, a serialized controller, and physical/simulated sessions.
- [x] Add exact scalar framing and generic allowlisted native block framing.
- [x] Port the established Linux native builders for mixer routing, all six
      Voice FX models, reverb, HPF, gate, Standard compressor, limiter, and
      Standard EQ.
- [x] Encode Voice FX selector replay, model materialization, channel 2 source
      selection, mutually exclusive On state with retained model settings, and
      UID wrap.
- [x] Treat the audio rate as unconfirmed on every connection; keep Delay off
      in hardware until the user confirms a safe current rate.
- [x] Enforce the above-48-kHz Delay replacement and old-rate settle sequence.
- [x] Build the five-screen mobile UI with system insets and ordinary fine
      scrolling.
- [x] Bind every Voice FX parameter and Wet/Dry value to its graph; present
      Vocoder Voiced as a read-only detector.
- [x] Add private semantic scenes, JSON import/export, batched load, and
      rate-aware effect placement without applying a saved rate or front-panel
      block selection.
- [x] Release USB away from the UI thread, discard queued writes after
      Disconnect, and report confirmed progress when a scene stops partway.
- [x] Keep front-panel blocks distinct from whole-setup phone scenes; add an
      exact Input 1/2 plus Block 1/2 native save flow with inactive-block,
      active-Delay-at-any-rate, and unsupported-model guards.
- [x] Add deterministic emulator states for verified control, failed readback,
      and semantic Delay at 88.2/96 kHz.
- [x] Exercise all five screens, fine Effects scrolling, reverb visibility,
      scene save/load across process restart, rate safety, and fail-closed UI at
      720x1600 and 320 dpi.
- [x] Pass host contracts, Java tests, lint, clean APK assembly, signature and
      permission inspection, and personal-string scanning.

## Physical acceptance still required

- [ ] Install the checksum-recorded 0.3.4 APK on the BLU 1660V.
- [ ] Reconfirm control plus Android audio coexistence.
- [ ] Verify the corrected Input 2 mute ACK/readback sequence.
- [ ] Exercise one safe representative from each native family at 48 kHz:
      mixer, Fat Channel, Voice FX on Input 1, Voice FX on Input 2, and shared
      reverb.
- [ ] Save a flat or otherwise harmless Fat Channel to the inactive
      front-panel block, recall it, and record the `WRITE_SENT_UNVERIFIED`
      boundary separately from audible behavior and power-cycle persistence.
- [ ] Confirm the 88.2/96 kHz Delay guard without selecting device model 5.
- [ ] Record objective readback or loopback evidence and update
      `LIVE_TEST_REPORT.md`.

No physical USB action is part of `./verify.sh`. A git commit or push also
remains a separate user action.
