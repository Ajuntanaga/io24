# CP34 two-lane Doubler private reverb and Linux host save

Timestamp: 2026-08-31T05:33:46-07:00
Status: offline source-bound and implementation PASS; no live device action;
physical acceptance pending; not independently reviewed

## Result

Doubler/Transformer's private reverb can be represented for both hardware
inputs at the same time. The firmware topology is one block-201/model-0 settings
instance over two input/output processing lanes. Both lanes therefore share one
`on/lows/width/mix` state; two independently parameterized Doubler instances do
not exist.

The paired device-resident representation is one complete `MemP/Stat` record
from each channel's slot pair:

```text
channel 1: global slot 0 or 1
channel 2: global slot 2 or 3
```

Both records contain an identical active object:

```json
"voicefx": {
  "__classid": "{66A10093-D461-4CAC-A80C-91F6A1BB37E5}",
  "on": 1,
  "lows": 0.06,
  "width": 0.405,
  "mix": 0.295
}
```

This is not shared reverb block 202 and carries no `vrvb`, `FXA`, `size`,
`predelay`, `hp_freq`, block-202 send, or sample-rate field.

## Firmware topology evidence

Pinned firmware SHA-256:
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.

The v2 analyzer pins these additional paths:

- audio-root code loads both physical-input mapping words at `device+0x5d74`
  and `device+0x5d78` (`0x3f8a4` and `0x3f8aa`), then uses stride `0xcec`
  to select two processing objects (`mla` at `0x3f8bc` and `0x3f8c8`);
- block-201 setup writes lane count 2 at `0x3dbf4`, stores 2 into both adjacent
  setup counts at `0x3dc10`, selects singleton `device+0x11e0`, and calls
  setup handler `0x553d4` at `0x3dc1c`;
- Doubler private-core configuration passes loop index `r4` as lane index `r3`
  at `0x5ae90`, calls indexed helper `0x56cc8` at `0x5aeac`, changes the index
  from 0 to 1 at `0x5aeb2`, and repeats;
- the model-0 handler is pinned with native literals `VFxO`, `Setu`, and `godv`;
  UC independently defines the storable model surface as only
  `on/lows/width/mix`.

`DOUBLER-REVERB-STATIC-V2.json` is schema
`cp34-doubler-private-reverb-v2` and records:

```text
block201 instances                         1
block201 setup inputs / outputs            2 / 2
private-core bound indexes                 0, 1
simultaneous hardware-input lanes          true
independent private-reverb parameter sets  false
```

## Host implementation

`io24_preset_record.py` now provides strict pure builders which:

- require a complete channel slot record, preventing a tiny `voicefx` mapping
  from erasing the rest of a device preset;
- remove only extractor metadata `_offset`;
- validate normalized finite `lows`, `width`, and `mix` values;
- enforce channel-1 slots 0/1 and channel-2 slots 2/3;
- install byte-equivalent Doubler state in both records without mutating either
  base record.

`io24.py` now provides:

- `build_paired_doubler_private_reverb_frames()` for hardware-free construction;
- `Io24.save_device_slot()` for one complete decoded `MemP/Stat` transaction;
- `Io24.save_paired_doubler_private_reverb()` for the two channel records;
- `saveprivatereverb <ch1block> <ch2block> [lows width mix]` in the CLI.

Both paired frame sets are completely built and validated before the first
write. The operation does not select or recall a slot, enable a preset channel,
write `processingChannel`, or touch block 202.

`io24gtk.py` now exposes Doubler/Transformer private reverb as preset state,
defaults to UC's recovered Reverb values, and has an explicit **Overwrite both
selected blocks** action. It uses the complete recovered Reverb channel-strip
record as the base for both selected blocks and stages no ineffective direct
model write while the sliders move. The button reports a sent transaction, not
nonvolatile survival.

`README.md`, `GUIDE.md`, `PROTOCOL.md`, `io24_scene.py`, and
`io24_presets.py` now distinguish this private two-lane core from block 202 and
remove the stale claims that native device-slot save is unreachable or that the
singleton necessarily means one audio input.

## Executable verification

Source-bound analyzer:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_doubler_reverb_static.py \
  /tmp/io24-fw-1.28.7DrxHf.bin \
  re/uc_factory_presets.json \
  re/uc_component_model/dsp_fx_params.xml
```

Result: exit 0; durable output is `DOUBLER-REVERB-STATIC-V2.json`.

Focused regression retained in `FOCUSED-TESTS.txt`:

```text
python3 -m unittest -v \
  tests.test_cp34_doubler_reverb_static \
  tests.test_cp34_dual_private_reverb_slots \
  tests.test_io24_preset_persistence \
  tests.test_cp34_preset_recall_static
```

Result: 39 tests passed in 0.192 seconds, exit 0.

Complete hardware-free regression:

```text
python3 -m unittest discover -s tests -v
```

Result: 127 tests passed in 144.275 seconds, exit 0. One pre-existing
`ResourceWarning` in `cp34_current_slot_survey.py` was non-fatal.

`python3 -m py_compile` also passed for every changed Python module.

## Boundary

This stage read pinned local artifacts and changed project source, tests, and
documentation only. It did not access USB or audio hardware, send either Stat
record to the unit, change a preset or effect, start Wine, access the protected
Wine prefix, use the network, install anything, stage firmware, reset the unit,
or enter DFU.

Static and hardware-free PASS does not prove physical nonvolatile commit,
front-panel recall, simultaneous audible output, power-cycle survival, or exact
restoration on the physical unit. Those remain a separately authorized live
acceptance run.
