# Effects lifecycle and Host cleanup

Started: 2026-09-08T07:00:00-07:00

## User outcome

Make the io24 effects workflow function coherently with the Linux Host and
without the Host, covering the shared reverb, the distinct Voice FX/private
reverb, and removal of redundant or misleading Host controls.

## Functional domains

- **Shared reverb (block 202):** one device engine, fed through each channel's
  broader processing/effects mix, and one FX return source routed independently
  to Main, Mix A, and Mix B. The input scalar is not an isolated reverb send:
  exact zero bypasses that channel's Fat Channel and effects. An engine-on write
  alone is not an audible-path result.
- **Voice FX/private reverb (block 201, model 0):** one stock Voice FX owner and
  model state. Direct owner/model writes do not establish the unresolved native
  activation gate. A complete device-slot record plus selection/enable/recall
  is the current source-bound standalone candidate.
- **Host absent while powered:** onboard DSP may continue after the Host closes;
  this is distinct from nonvolatile survival.
- **Power-cycle standalone:** requires a separately observed device-resident
  save/recall result and must not be inferred from USB transport completion.

## Current authorization

Authorized now: offline source, UI, documentation, test, and peer-review work.
The user expanded the approved Anthropic disclosure from 40 to exactly 53
files; the thirteen additions, including `io24_mbc.py`, are recorded in
`.claude-peer/INBOX.md` and the factory-preset archive remains excluded.

Not authorized by this run: USB/device access, audio capture or playback, Host
launch, device-slot overwrite/select/enable, effect write, power cycle, Wine,
firmware, installation, publication, or Obsidian write. Any live stage must
name the channel, slot, effects, protected state, restoration behavior, and
human listening/observation steps before asking for authorization.

## First offline correction

The production Effects page now names the two domains explicitly: `Shared
reverb` and `Voice FX insert`. The shared engine switch states that sends and a
return are also required. The Voice FX switch is labelled as the model-state
field it actually sends and states that standalone activation requires the
device-slot workflow. The stale structural-lane explanation and two dead
Channel-2 experiment helpers are removed from production source.

This is presentation and containment work. It is not evidence that either
effect is audible or device-resident.

## Peer status

The decision model and review questions were appended to Claude's durable
`INBOX.md` before implementation. Successful serialized turns on dedicated
UUID `a764bfc8-6fec-453f-9289-92ace5f16ce5` found the repeated Voice FX owner
assignment and missing registry device identity, then independently reviewed
the processing-mix unification after the 10:00 AM reset. The final candidate
review found no defect and endorsed the 748-row atomic correction. The earlier
zero-token 429 remains recorded as unavailable, not review.

## Offline store gate

The Host refuses an overwrite when it does not possess a complete known base,
when live slot state is unavailable, or when the destination is currently
selected. The local registry says `Host-written; device readback unavailable`
and is bound to exact device identity. Slot selection, irreversible body
overwrite, recall/enable, and direct live apply remain separate explicit
actions.

## Complete-record registry implementation

The offline backend now has a local `DeviceSlotRegistry` and
`Io24.save_known_device_slot`. They validate an existing registry and a
complete slot record before transport, perform only the record write, and then
persist `HOST_WRITTEN_DEVICE_READBACK_UNAVAILABLE` provenance. Zero replies are
retained honestly as `WRITE_SENT_UNVERIFIED`; the API never selects, enables,
recalls, or directly applies the slot. The public API was added to the existing
slot-write matrix row instead of bypassing the inventory gate.

The GTK Factory presets group exposes this backend through a confirmed
inactive-slot body write. This completes the offline product path, not its live
acceptance. Host-running, Host-closed-while-powered, and power-cycle listening
remain separate future gates.
