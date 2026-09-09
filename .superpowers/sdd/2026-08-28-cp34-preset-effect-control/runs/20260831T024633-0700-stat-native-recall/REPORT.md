# CP34 native Stat recall and Voice FX record evidence

Timestamp: 2026-08-31T02:46:33-07:00
Status: offline source-bound PASS; not independently reviewed; no live authority

## Result

Firmware 1.28 contains a complete reciprocal path for the already-decoded
`MemP/Stat` save model. A selected global `Stat` index is read from the preset
component and the recovered tagged record is handed to the firmware's native
application callback/router. Universal Control is not in this recall path.

The firmware also embeds two banks of eight factory presets in the same tagged
record format used by scene JSON and `MemP/Stat`. All 16 records decode and
re-encode byte-for-byte. Three records—`Slap Echo`, `Detuned Vocal`, and
`Robot`—set `voicefx.on=1`. Inactive Voice FX records set 0; four records omit
the Voice FX object. This establishes that Voice FX activation intent is part
of the saved/recall record. A separate host enable opcode is not needed to
represent that state.

This does not prove physical nonvolatile commit, power-cycle survival, actual
front-panel recall, audible processing, or the final internal assignment from
decoded `voicefx.on` to the firmware DSP gate bits.

## Firmware recall path

The pinned firmware image is 1,104,448 bytes, SHA-256
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`,
with load base `0x60020000`.

- Root vtable `+0x6c` is slot-change handler `0x2f334`. It compares each
  channel's selected slot against the cached selection and invokes root vtable
  `+0x58` when the selected slot changes.
- Root `+0x58` is `0x2f0d0`. It stores the selected index and calls
  preset-component vtable `+0x24`.
- Preset-component `+0x24` is `0x30be0`. It accepts `Stat` indexes 0..3 and
  reads the matching stored record in fragments.
- Each recovered fragment is passed to root `+0x4c`, `0x2f8ac`.
- The root callback bound during startup reaches manager interface
  `0x31674`/`0x3163c`, then application-router interface
  `0x20790`/`0x20754`.

`RECALL-STATIC.json` pins the corresponding vtable words and eight exact code
slices. This proves a firmware-native stored-record application route at the
code level, not the current physical contents of any unit.

## Firmware record model

Constructor `0x3c890` binds two factory banks and four `Stat` descriptors:

- bank-0 size table `0x691f0` exactly matches record lengths
  822, 814, 854, 697, 659, 850, 645, and 846 bytes;
- bank-1 size table `0x69210` exactly matches record lengths
  822, 814, 854, 697, 712, 731, 720, and 537 bytes;
- `Stat` descriptor table `0x691e0` contains `0x440`, `0x440`, `0x404`, and
  `0x404`.

The descriptor values are reported as configured lengths only. This stage does
not reinterpret them as a user-facing maximum record size.

## Universal Control inverse loader

The pinned UC 4.7.2 module is 4,979,672 bytes, SHA-256
`de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.

Its complete `.text` census contains exactly six accesses to per-channel byte
`+0xe6`: four writes and two reads. Parser `0x18003bfc0` clears the byte, finds
parent `voicefx`, finds child `on`, accepts an integer or real value, compares
it with 1, and stores the boolean at `0x18003c20d`. Serializer read
`0x18003bb38` conditionally includes `VoiceFxOn`; it does not queue a device
operation. Thus `+0xe6` is host record state and confirms the inverse mapping
from saved `voicefx.on`.

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

Result: 30 passed and 21 subtests passed in 0.48 seconds, exit 0. Python
compilation also succeeded for the analyzer and codec.

## Authority and activity boundary

This stage read only the two pinned local binary files and project sources. It
did not access USB/audio hardware, change a preset/effect, start Wine, access
the protected Wine prefix, use the network, install anything, stage firmware,
reset the unit, or replay a command. The output creates no such authority.
