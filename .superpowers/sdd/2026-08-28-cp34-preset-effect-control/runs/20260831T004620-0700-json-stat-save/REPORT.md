# UC 4.7.2 JSON-to-device-slot save-path correction

Timestamp: 2026-08-31T00:46:20-07:00

Status: offline static result and hardware-free implementation locally verified;
not independently reviewed; no live or device action authorized or performed

## Result

The scene JSON is the missing model. Universal Control does not save a pointer
or a preset title into a front-panel slot. It keeps four complete slot records,
copies the current channel/effect object into the active record, serializes that
object, and sends it as:

```text
SetP -> Appl(0) -> MemP -> Stat(global slot 0..3) -> serialized record
```

The global slot mapping is exact:

- slots 0 and 1: the two device-resident preset blocks for channel 1;
- slots 2 and 3: the two device-resident preset blocks for channel 2.

`presets.userpresets` is a separate host/library collection at indexes 16..27.
It uses the same outer envelope with nested `PrsM`, not `Stat`.

No sample-rate value or sample-rate branch participates in this path.

## UC 4.7.2 static path

- Scene writer `0x180037c70` serializes `presets.userpresets` and the separate
  four-record `presets.slots` collection. Scene loader `0x180038380` restores
  `slots["0"]` through `slots["3"]` into that collection.
- The four slot records live at the device-controller subobject offset `+0x2d8`
  with stride `0x38`; the collection owner is at `+0x2d0`.
- `0x18002e270` serializes the complete current channel component into the
  selected slot record. The inverse component application is `0x18002e690`.
- `0x1800420c0` validates the per-channel slot range and snapshots the current
  component. `0x1800421c0` selects the record, builds `{Stat,index}`, targets
  `{Appl,0}`, and invokes sender vtable slot `+0x10`.
- The periodic handler at `0x1800417a0` calls those two functions after 500 ms
  of settled changes in `filter`, `gate`, `comp`, `eq`, `limit`, `opt`,
  `voicefx`, or `voicefxopt`. Slot switching also writes through the current
  state before changing the active slot.
- Sender `0x180050f10` builds the `MemP` fragment envelope and queues it through
  `0x180053420`. Builder `0x1800541d0`, in mode 2 with its fifth argument zero,
  adds the exact outer `SetP`, `Appl`, and numeric block 0 header.

The earlier queue census saw the single generic `MemP` caller but treated the
dynamic `Stat` target as unresolved. That negative was wrong: `PrsM` and `Stat`
share the same sender, so a separate queue caller was never expected.

## JSON record encoding

The scene slot object and the nested wire record are two representations of the
same hierarchy. The binary archive uses:

- `{` and `}` for mappings;
- length-prefixed keys and strings;
- `i`, `I`, and `l` for signed 8-, 16-, and 32-bit integers;
- `d` followed by big-endian IEEE-754 binary32 for real values.

`io24_preset_record.py` now implements that conversion without hardware.
`io24.py` now implements the exact `MemP/Stat` frame builder and a direct
JSON-slot-to-frame composition. Neither function transmits anything.

As an independent byte check, the codec found 47 records beginning with
`{i\x0bpreset_name` inside the source-bound UC 4.7.2
`dspusbdevice.dll` and decoded/re-encoded all 47 byte-for-byte. One additional
substring occurrence was a surrounding structure with a duplicate `eqallon`
key, not a standalone preset record.

All twelve slot objects in the three recovered scene files encoded and decoded
successfully. Their binary record sizes were:

```text
B A S E.scene          668 670 687 716
Main.scene             673 780 583 580
Piano Accomany.scene   722 780 690 727
```

## Firmware boundary

Firmware 1.28 closes the incoming-record handoff. A previous trace indexed the
device-root vtable from its two-word header at `0x6d200`. The actual vtable
begins at `0x6d208`, so `MemP` slot `+0x80` is `0x2f210`; `0x3c064` is the
unrelated lifecycle/cache slot `+0x20`.

The corrected path is:

```text
SetP/Appl(0)/MemP
  -> root handler 0x2f210
  -> root+0x70
  -> preset component root+0x1240, vtable 0x674f8
  -> set-fragment entry +0x18 = 0x3099c
  -> record writer 0x3092c
  -> storage wrapper 0x2bfe4
  -> startup-bound backend write entry 0x316dc
```

Constructor chain `0x3c890 -> 0x30260 -> 0x2fca8` stores
`root+0x1240` at `root+0x70`; `0x3c8dc` constructs that object with vtable
`0x674f8`. Handler `0x2f210` loads it and invokes vtable `+0x18` with the
original `MemP` message. `0x3099c` accepts `Stat` 0..3 and `PrsM` 16..27, then
passes valid fragments to `0x3092c`. The latter writes a four-byte record length
and the serialized bytes through `0x2bfe4`.

Startup path `0x31ab0 -> 0x2d660 -> 0x300ac -> 0x306b4 -> 0x2c1c0` binds the
component wrapper to its firmware storage backend. Backend vtable `0x676ec`
maps write entry `+0x00` to `0x316dc`, which forwards the operation to the
underlying storage object with write flag 1.

The `0x3c064 -> 0x302b0` path instead connects `logoImage` and
`firmwareVersion` state labels. `device+0x120c` is the formatted
firmware-version string; it is not a preset component or delegate.

The source firmware image was 1,104,448 bytes with SHA-256
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.
`FIRMWARE-STATIC-ANCHORS.txt` pins the vtable words, object/call edges, and six
code-slice hashes used for this correction.
Static code now establishes the incoming record through the bound firmware
storage-write interface. Power-cycle/nonvolatile endurance and
editor-independent survival remain validation questions, not missing save
semantics.

## Verification

```text
python3 -m pytest -q \
  tests/test_io24_preset_persistence.py \
  tests/test_io24_capture_decode.py
```

Result: `23 passed, 21 subtests passed`, exit 0.

Python compilation succeeded for `io24.py`, `io24_scene.py`, and
`io24_preset_record.py`.

No Wine prefix was accessed. No vendor executable was started. No USB, audio,
device, preset/effect, firmware, installation, staging, or network action was
performed.

## Remaining proof

The slot-save transaction, JSON record, firmware dispatch, record assembly, and
storage-backend write handoff are decoded. A live packet is no longer needed to
discover them; it would only validate firmware acceptance, editor-independent
recall, and power-cycle survival. Audible Voice FX activation/restoration
remains the other CP34 outcome and must not be inferred from record contents
alone.
