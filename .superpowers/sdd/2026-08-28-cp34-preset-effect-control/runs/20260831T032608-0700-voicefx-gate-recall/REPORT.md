# CP34 native Voice FX gate application

Timestamp: 2026-08-31T03:26:08-07:00
Status: offline source-bound PASS; not independently reviewed; no live authority

## Result

Firmware 1.28's native selected-`Stat` recall does not stop at the previously
identified application router. It forwards the recovered structured record to
the live firmware device object, whose `Stat` branch dispatches component 201
to the Voice FX block's structured-state loader.

That loader establishes all three conditions checked by the block-201
processing gate before it applies the selected model's nested state:

- `0x554ba`: `block+0x40 = 0`;
- `0x554bc`: stores little-endian halfword `0x0101` at `block+0x38`, so byte
  `block+0x39 = 1`;
- `0x554c2` calls model selector `0x55388`, whose valid-model path stores
  `block+0x44 = 1` at `0x553a8`.

Gate handler `0x50af8` requires `+0x44 != 0`, `+0x39 != 0`, and `+0x40 == 0`.
The native component-state application therefore supplies every processing
gate condition. Combined with the already-proved `voicefx.on` field inside the
same tagged record, this removes a missing standalone enable packet from the
preset save/recall model. The path contains no sample-rate-dependent branch.

This does not assert that the serialized `voicefx.on` value is copied directly
into field `+0x44`. The containing Voice FX component load arms the processing
gate and then delegates the selected model's nested state, where record-local
on/off intent is consumed.

## Corrected vtable ownership

Block constructor `0x591bc` installs:

- primary vtable at file offset `0x10c6bc` on the base object;
- secondary structured-state vtable at file offset `0x10c700` on base `+4`.

Earlier protocol notes started the primary table at `0x10c6cc`, sixteen bytes
late. Correctly indexed:

- file `0x10c6cc -> 0x50af8` is primary slot `+0x10`, the gated handler;
- file `0x10c6e4 -> 0x5545c` is primary slot `+0x28`, structured-state apply;
- file `0x10c6f0 -> 0x5f1f4` is the actual primary slot `+0x34`;
- file `0x10c704 -> 0x555b8` is secondary state method `+4`; the thunk adjusts
  `this` by `-4` and enters `0x5545c`.

This also corrects the older claim that `0x37e06` was the only setter of
`block+0x44`. `0x553a8` is a direct setter reached by both construction and
structured-record application.

## Native application route

The source-bound route from the predecessor recall checkpoint is now:

```text
selected Stat 0..3
  -> 0x2f334 -> 0x2f0d0 -> 0x30be0
  -> 0x2f8ac -> 0x31674/0x3163c -> 0x20790/0x20754
  -> 0x34cb8 -> singleton projection 0x3cc08
  -> singleton secondary forwarder 0x3cc40
  -> live device dispatcher 0x420bc, Stat branch 0x42200
  -> live-device vtable +0x38, 0x531e0
  -> component-id 201 table entry at device+0x11e4
  -> state-interface +4, 0x555b8 -> 0x5545c
  -> gate assignments -> selected model state apply
```

`RECALL-STATIC.json` uses schema `cp34-preset-recall-static-v2`. It pins the
firmware and UC source identities, all vtable words and exact code slices in
this route, the critical assignment bytes, all 16 firmware factory records,
the four `Stat` descriptor lengths, and UC 4.7.2's complete `voicefx.on` field
access census.

Pinned sources:

- firmware: 1,104,448 bytes, SHA-256
  `65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`;
- UC 4.7.2 `dspusbdevice.dll`: 4,979,672 bytes, SHA-256
  `de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.

## Executable verification

Source-bound analyzer:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_preset_recall_static.py \
  /tmp/io24-fw-1.28.7DrxHf.bin \
  /tmp/io24-uc472-extract.IHXUdb/hwaccess/dspusbdevice.dll
```

Result: exit 0. A second run reproduced `RECALL-STATIC.json` byte-for-byte.

Focused hardware-free regression:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_preset_recall_static.py \
  tests/test_cp34_host_queue_inventory.py \
  tests/test_io24_preset_persistence.py \
  tests/test_io24_capture_decode.py
```

Result: 31 passed and 21 subtests passed in 0.48 seconds, exit 0. Python
compilation succeeded for the analyzer and preset-record codec.

## Authority and claim boundary

This stage read only pinned local binaries and project sources. It did not
access USB/audio hardware, change a preset/effect, start Wine, access the
protected Wine prefix, use the network, install anything, stage firmware,
reset the unit, or replay a command.

Static PASS does not prove physical nonvolatile commit, power-cycle survival,
actual front-panel recall, audible Voice FX, or restoration on the physical
unit. It creates no live authority.
