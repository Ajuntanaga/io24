# CP34 custom firmware — runtime storage and placement recovery

Saved: 2026-09-01T00:45:35-07:00

## Objective

Continue the offline custom-firmware design after the source-bound model-0
private-reverb blend hook. Recover enough evidence to design newly owned
runtime state for `wet_ch1`, `wet_ch2`, `bypass_ch1`, and `bypass_ch2`, and
identify a defensible executable placement for a future parser/mix hook.

## Established predecessor facts

- The host extension is explicit-capability only; stock records stay legacy
  shaped and no stock acceptance of unknown fields is claimed.
- Model-0 processing selects a lane through model `+0x338`, loads shared mix
  from `+0x358` at raw `0x1e2be`, and calls the private core at raw `0x1e2cc`.
  The resolved core at raw `0x1c408` supplies the verified final dry/wet blend.
- The future scalar behavior is
  `effective_mix = bypass[lane] ? 0 : clamp(shared_mix * wet[lane], 0, 1)`.
- Existing per-lane-looking coefficient regions, nearby subobjects, and models
  0–5 are live. They are not extension storage or code caves.

## Allowed work

- static analysis of the pinned local raw application and vendor package;
- source-bound allocation/lifetime, parser, reset, relocation, reference, and
  executable-placement analysis;
- host-only import/preservation improvements and hardware-free tests;
- documentation and checkpoint evidence.

## Prohibited work

- producing, modifying, signing, staging, or uploading a firmware image;
- device enumeration, USB access, DFU, reset, audio, preset/effect writes,
  Wine access, network access, or access to `/home/ajuntanaga/.wine-io24`;
- claiming hardware persistence, audible effect operation, restore, or safety.

## Completion rule for this pass

This pass may close only with one of the following honest outcomes:

1. a source-bound storage and executable-placement design with explicit
   remaining binary-build gates; or
2. a source-bound finding that either prerequisite remains unresolved, with no
   guessed code cave or repurposed live state.

Either outcome leaves image emission and all hardware actions blocked.
