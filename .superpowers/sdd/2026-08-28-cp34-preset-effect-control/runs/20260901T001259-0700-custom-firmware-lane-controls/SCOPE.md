# CP34 custom per-lane private-reverb firmware fork

Saved: 2026-09-01T00:12:59-07:00

## Objective

Extend the block-201/model-0 private-reverb path with independently persisted
wet gains and wet bypasses for the two existing physical input lanes.  The
extension must survive the existing device-slot `Stat` recall path when the
custom firmware is eventually installed.

## Public persisted contract

```json
{
  "voicefx": {
    "on": 1,
    "lows": 0.06,
    "width": 0.405,
    "mix": 0.295,
    "wet_ch1": 1.0,
    "wet_ch2": 1.0,
    "bypass_ch1": false,
    "bypass_ch2": false
  }
}
```

`wet_ch1` and `wet_ch2` are finite floats clamped to `0.0..1.0`.  Missing
fields mean `1.0`; missing bypasses mean `false`.  `on` still controls the
whole stock Voice FX model and `mix` remains the model's existing shared
algorithm parameter.  These fields do not modify block 202, its send, or its
shared reverb state.

Only an explicitly selected custom-firmware host capability serializes the four
extension fields; normal saves retain the exact legacy `voicefx` record because
stock acceptance of unknown keys is not established. Each selected
channel-1/channel-2 custom `Stat` pair receives an identical complete copy of
the four extension fields. Recalling either successful record restores both
lane controls. The two transfers are sequential rather than atomic and must
report completed and failed slots if the second write fails. This avoids
misrepresenting conflicts between two records that enter one firmware singleton.

## Offline implementation boundary

Allowed in this stage:

- inspect and hash pinned local firmware and Universal Control artifacts;
- correct package extraction, metadata inspection, and CRC verification;
- implement host-side record/schema support and regression tests;
- document an exact static patch design and its preconditions.

Not allowed in this stage:

- emitting or staging a modified firmware binary;
- DFU, reset, firmware update, USB claims/transfers, preset/effect writes,
  audio I/O, front-panel action, Wine, or access to `/home/ajuntanaga/.wine-io24`;
- declaring persistence, audibility, power-cycle survival, or recoverability
  verified on hardware.

## Firmware design constraints

1. Retain the stock `godv` handler for its five existing model fields.
2. Parse the four extension fields during structured `Stat` application, with
   old-record defaults before model state reaches the two-lane DSP path.
3. At the source-bound model-0 private-core call, use the selected lane and
   replace the core mix scalar with `bypass ? 0 : clamp(shared_mix * wet, 0, 1)`;
   the unchanged core supplies its verified final dry/wet blend. Do not
   repurpose the live per-lane `0.5` coefficient arrays.
4. Preserve the complete original vendor image and validate its metadata/CRC
   before any future updater work.
5. Do not call an image flashable until a static patch has a safe executable
   home, an explicit restore story, and separately authorized hardware tests.

## First-pass outcome

- Host schema, CLI, and GTK controls are capability-gated; stock serialization
  remains legacy-shaped and paired failures are explicit.
- Offline package extraction/inspection now rejects truncation and requires the
  exact known UC 4.7.2 io24 recovery package for extraction.
- Reset relocation, the model-0 lane selector, mix load, private-core call,
  and final dry/wet blend are source-bound in
  `re/cp34_lane_control_firmware_static.py`.
- Image emission remains blocked: no safe owned extension storage, parser
  lifecycle implementation, or executable placement is proven. No firmware
  binary, staging, USB/Wine access, or live hardware action occurred.
