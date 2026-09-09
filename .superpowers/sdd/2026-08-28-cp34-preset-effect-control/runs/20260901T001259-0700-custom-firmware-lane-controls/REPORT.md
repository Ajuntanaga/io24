# CP34 custom per-lane private-reverb fork — first-pass report

Completed: 2026-09-01T00:41:48-07:00

## Outcome

The Linux host and publishable documentation now support the proposed
per-lane private-reverb schema safely, and the firmware's real per-lane blend
control point is source-bound. No custom firmware image exists yet.

The exact outstanding firmware work is newly owned storage and lifecycle code
for four parsed values, followed by a reviewed executable placement. Image
emission remains blocked until those conditions, recovery proof, and a separate
hardware authorization are present.

## Delivered host behavior

- `voicefx.wet_ch1`, `wet_ch2`, `bypass_ch1`, and `bypass_ch2` have finite/
  boolean validation, defaults for old records, and codec coverage.
- Default serialization remains exactly the stock class id plus
  `on/lows/width/mix`. Custom keys are emitted only when the caller explicitly
  supplies `custom_firmware_lane_controls=True`.
- CLI use requires `saveprivatereverb --custom-firmware ...`; GTK has an
  explicit **Enable custom-firmware lane extension** switch, off by default.
- Paired `Stat` writes are correctly modeled as sequential. The result reports
  `completed_slots`, `failed_slot`, completed reports, and an error on a
  second-write failure. Neither UI nor CLI calls this atomic.
- The library supports separate complete channel bases. The current CLI/GTK
  convenience path still uses the factory Reverb template for both bases and
  explicitly warns that it overwrites full Fat Channel state; no trustworthy
  device read/merge source has been established.

## Firmware evidence

- The reset copy table relocates raw `0x0fd8..0x405d0` to ITCM
  `0x000002c0..0x0001f8b8`; low veneer targets must map back to their copied
  source offsets rather than coincident low raw offsets.
- Model-0 processing is raw `0x1e1a8` (ITCM vtable entry `0x1d491`). It selects
  the active lane through model `+0x338`, loads shared mix from model `+0x358`
  at raw `0x1e2be`, and calls the private core at raw `0x1e2cc`.
- The resolved private core is raw `0x1c408` and has the verified final dry/wet
  output blend. The patch contract is therefore
  `effective_mix = bypass[lane] ? 0 : clamp(shared_mix * wet[lane], 0, 1)` at
  the existing scalar-load/call boundary.
- The two tempting model coefficient regions at `+0x6a4..+0x6c3` are live,
  reinitialized graph state. Nearby subobjects/config fields are also occupied,
  and models 0–5 remain factory-dispatchable. None is safe extension storage or
  code space.

## Package/recovery guard

`io24_firmware.py` is offline-only. It verifies package metadata/CRC and only
accepts the pinned UC 4.7.2 io24 recovery package for extraction: target
`0x194f0407`, image id `1`, vector table, full `0x12a694` length, and the
complete-package SHA-256 recorded in `SHA256SUMS`. The historical
`0x10da40` raw extraction is rejected. The tool has no live defaults, status,
detach, staging, or firmware-write path.

## Verification and scope

```
python3 -m unittest discover -s tests
Ran 148 tests in 156.203s
OK
```

The suite emits one pre-existing `ResourceWarning` for a temporary WAV reader
in `re/cp34_current_slot_survey.py`; it is unrelated and was not changed.

No USB/device action, USB enumeration, transfer, preset write, audio action,
Wine access, network access, firmware image emission, staging, DFU, reset, or
flash occurred in this fork.

## Next bounded task

Recover a new owned model-0 extension-state allocation and its constructor,
reset, structured-`Stat` parser, and lifetime behavior; then identify a safe
reviewed executable placement. Only after that offline proof is complete may a
separately authorized image-build/recovery plan be considered.
