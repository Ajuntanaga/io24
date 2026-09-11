# Presets tab, A/B removal, and resuming the last session — scope

Target: user-owned Revelator io24 serial `AB7C22200355`, firmware `0128`.

Objective: the user's answers of 2026-09-11 to the Presets proposal:

1. Presets as two drop-downs, **User Presets** and **Factory Presets**, instead
   of separate sections for device slots, Host presets, factory sounds and A/B
   previews.
2. "Persist all settings so that [the Host] always leaves off where it did last
   time it was open/used."
3. A preset loads into the selected channel, or both when linked.
4. Remove the A/B preview; the user called it unnecessary and unplayable while
   holding an instrument.

Decisions taken in building it, reported to the user:

- Resume re-sends the write-only settings the driver last sent on every
  connection. This reverses the earlier deliberate rule that a reconnect never
  re-sends the cache; the user asked for it. Setters the unit reports itself
  (mute, headphone mute, stereo link) are skipped so a hardware change made
  while the Host was closed stands; device preset selectors stay quarantined.
- When the last session had Voice FX on, the owning channel's selected block is
  recalled first (the Stat load that opens the Voice FX gate), then its saved
  DSP amount is re-sent because a recall on a bypassed channel enables it.
- Host-only features (multiband, reverb character/movement) come back once per
  launch from `~/.config/io24/last-session.json`, not on a USB reconnect.
- User presets live on the computer in `~/.config/io24/user-presets.json`, the
  factory file's format; "Put on the unit's button" writes one to a block and
  loads it after one confirmation. Saving over a name and deleting also confirm.
- Auto gain and solo remain session-only, as in Universal Control.

Out of scope: UC's own `presetHotKey` quick-loader (never implemented; the user
was asked what it did); Doubler private-reverb shaping, a device-resident
multiband, and any firmware change (the user's stated goals, recorded in
memory, needing a separate plan and explicit authorization); the pending MAIN
slot-0 rewrite.

Lane: static source reading, code edits, hardware-free tests, deterministic
artifact regeneration, on worktree branch `worktree-io24-dsp-device-tab`. No
USB/device access, no audio, no Host launch, no Wine, no install, no network,
no firmware action, no device write of any kind.
