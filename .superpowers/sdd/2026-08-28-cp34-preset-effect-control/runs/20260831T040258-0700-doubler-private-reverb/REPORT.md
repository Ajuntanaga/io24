# CP34 Doubler private-reverb and preset representation

Timestamp: 2026-08-31T04:02:58-07:00
Status: offline source-bound PASS; not independently reviewed; no live authority

## Result

Transformer/Doubler does contain reverb internally. It does not enable shared
reverb block 202 and does not use block 202's send/return state. Firmware model
0 constructs a private instance of the same reverb-core implementation used by
block 202.

The preset representation is therefore the high-level Voice FX JSON object:

```json
"voicefx": {
  "__classid": "{66A10093-D461-4CAC-A80C-91F6A1BB37E5}",
  "on": 1,
  "lows": 0.06,
  "width": 0.405,
  "mix": 0.295
}
```

No shared-reverb object, reverb send, or sample-rate-dependent coefficient set
belongs in this device-slot record.

## JSON and component-model evidence

Pinned `re/uc_factory_presets.json` has 41 records. Its only record titled
`Reverb` is index 30 and contains the Voice FX object above. A recursive key
census across every record finds none of:

```text
reverb  vrvb  FXA  size  predelay  hp_freq
```

Pinned `re/uc_component_model/dsp_fx_params.xml` independently maps class
`{66A10093-D461-4CAC-A80C-91F6A1BB37E5}` to `VoiceOfGodComponent`, whose
storable parameter list is `on/lows/width/mix`. It declares shared
`VocalReverb` separately as `on/size/mix/hp_freq/predelay`.

The exact record-30 object, excluding the extractor-only `_offset` annotation,
also passed the pure JSON-to-tagged-record codec and `MemP/Stat(0)` envelope
builder. Its decoded single-precision values re-encoded byte-for-byte.

Source identities:

- factory JSON SHA-256
  `89b0572dd760b77831d012e2db0568b4f4eeb158985a4ca86126be28e934c73d`;
- concatenated FX parameter resource SHA-256
  `3f5f99bd6efdfd54b65adf15c82d8b9da36116b25b11e3c88a4ad441b9decd89`.

## Firmware implementation evidence

Pinned firmware 1.28 SHA-256:
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.

The source-bound construction and configuration paths are:

```text
device constructor 0x5d9a8
  -> 0x591bc constructs block 201 at device+0x11e0
  -> 0x5b258 constructs block 202 at device+0x3a70

model factory 0x5f254, model 0
  -> 0x5e270 constructs Doubler at block201+0x10

block 202 constructor
  this+0x10 -> call 0x5af14 at 0x5b274

Doubler constructor
  model+0x384 -> call 0x5af14 at 0x5e37c

block 202 configuration
  this+0x10 -> call 0x5a6a8 at 0x5ade6

Doubler configuration
  model+0x384 -> call 0x5a6a8 at 0x5ae0e
```

Thus the two cores occupy distinct state:

- Doubler-private core: `device+0x1574`;
- shared block-202 core: `device+0x3a80`.

They share constructor `0x5af14` and configurator `0x5a6a8`, not an instance or
signal route. Model-0 runtime method `0x5bfe0` reaches the private configuration
path at call site `0x5c06c`.

## 96 kHz implication

The JSON/`Stat` record has no sample-rate field. Sample rate enters the model's
runtime configuration path; the firmware configures the private core for the
device's current rate. Consequently 96 kHz uses the same saved class and
`on/lows/width/mix` fields. The 48 kHz defaults in direct live-blob helper code
do not define the native preset format.

## Executable verification

Analyzer:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_doubler_reverb_static.py \
  /tmp/io24-fw-1.28.7DrxHf.bin \
  re/uc_factory_presets.json \
  re/uc_component_model/dsp_fx_params.xml
```

Result: exit 0. A second run reproduced `DOUBLER-REVERB-STATIC.json`
byte-for-byte. Output schema: `cp34-doubler-private-reverb-v1`.

Focused hardware-free regression:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_doubler_reverb_static.py \
  tests/test_cp34_preset_recall_static.py \
  tests/test_cp34_host_queue_inventory.py \
  tests/test_io24_preset_persistence.py \
  tests/test_io24_capture_decode.py
```

Result: 38 passed and 21 subtests passed in 0.51 seconds, exit 0.
`PYTHONDONTWRITEBYTECODE=1 python3 io24_fx.py` also returned
`OK -- all six models`.

## Save implication and boundary

The existing pure JSON-to-tagged-record codec and `MemP/Stat` frame builder
already carry every field this effect needs. A correct device-resident save of
the Doubler/Reverb preset must not add block-202 `vrvb`, channel `FXA`, a shared
reverb-send write, or synthesized 96 kHz coefficients.

This run read pinned local files only. It did not access USB/audio hardware,
change a preset/effect, start Wine, access the protected Wine prefix, use the
network, install anything, stage firmware, reset the unit, or replay a command.

Static PASS does not prove physical nonvolatile commit, front-panel recall,
audible Voice FX, power-cycle survival, or restoration on the physical unit.
It creates no live authority.
