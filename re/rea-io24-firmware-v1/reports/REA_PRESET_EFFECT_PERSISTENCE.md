# io24 preset and effect persistence

Date: 2026-10-14

## Scope and safety

This report follows the firmware-native `MemP/Stat` path from ingress through
stored-record loading and Voice FX application. All binary work used REA 6.4.0
with its Ghidra 12.1.4 provider. The connected io24 was not opened. No USB
request, preset operation, reset, DFU transition, firmware execution, or device
write occurred.

The analyzed image is `analysis/io24-package-arm-reset.elf`, SHA-256
`9603830a27f480011a29924d4cfef552185024a9b1f9b7dc39e82a6462320e14`, a
byte-preserving envelope around the immutable vendor package whose SHA-256 is
`790f668608448b7c9f244c360ad72e3c51f71b4e8a3d828eab0e08cd03b35de1`.

## Result

The firmware has a genuine device-side record path for the four channel preset
slots. A native `Stat` record can contain the Fat Channel and a compatible
Voice FX model. On load, the firmware restores the selected Voice FX model,
enables its two state bytes, validates the model-specific record, and dispatches
that record to the selected processor's state loader.

That result does **not** put every effect in a channel preset. Shared device
reverb is block 202 and remains separate from Voice FX block 201. It is absent
from the decoded channel `Stat` record. Transformer, by contrast, owns a private
instance of the reverb core, so Transformer state can persist as part of the
Voice FX model without persisting the independent shared reverb rack.

The exact physical nonvolatile medium is not yet established. The decoded path
reaches a bounded, checksum-aware storage abstraction; the concrete flash or
EEPROM backend below its virtual interface is unresolved in the current image
profile. Physical survival across a cold power cycle was not tested in this
static pass.

## Record write path

`FUN_6005099c` is the preset ingress handler. It accepts `PrsM` indexes 16..27
and `Stat` indexes 0..3, checks the selected storage partition's capacity, and
passes accepted fragments to `FUN_6005092c`. Evidence:
`ev_fabbfd12c0101efe899b1a9382daf6bd847c5bdd004799a972d04557782c484d`.

`FUN_6005092c` writes the record framing on the first fragment, walks existing
chunks when needed, and forwards the fragment payload to the lower storage
primitive. Evidence:
`ev_f7d080ef807480d4ea02cc8d3032a4a68dcb46b2f68c33930ffc36ffb0b72772`.

`FUN_6004bfe4` is the bounded storage-interface write. It validates the target
range and writes record metadata/checksum, length, and payload as three parts,
returning explicit errors on failure. Evidence:
`ev_04f208516094a60ce77adc8fad240e4ef0300e3ca216e3d22561e2cbcb21d6e5`.

The storage binding in `FUN_6005c850` configures regions of `0xc1c`, `0x5dc`,
`0x41a`, and `0x5dc` bytes and a `0x40` field used by the preset component.
Evidence: `ev_c8b3d4019cc258265e9e680dbe7d745bbdab84d0ebf56ae31fa2134dfc9ea31e`.

## Record read and apply path

`FUN_60050be0` is the `Stat` slot reader. It rejects indexes above 3, requests
the stored record, and has an embedded fallback route for an empty or missing
record. Evidence:
`ev_3336ee4fde93ba9f817ea42fed76c97a73a3b1091ad63fe33ace89124910a5ad`.

`FUN_60050a90` walks the framed chunks, validates record sizes and checksum
state, limits an individual fragment to `0x7ce` bytes, and succeeds only when
the accumulated length exactly equals the declared record length. Evidence:
`ev_ba4d79ee6589ab54359036d62ab85b55bf6d8334cf9a4ad71c2fe296d030f83c`.

`FUN_6007545c` is the load side that materially establishes effect persistence.
It validates the parent component, clears the block's prior state, writes
`0x0101` to the two enable bytes, selects the saved Voice FX model through
`FUN_60075388`, validates the nested model identifier and length, and invokes
that model's state loader. Evidence:
`ev_94c9949a4beb471bf9acdb5151ff85d2e3e1f9a7da44c517dfccd42281f1a9fa`.

The slot-change handler `FUN_6004f334` reads both selected slot indexes and
compares them with cached values. It invokes the stored-record recall method
only when the corresponding status/bypass bit permits it; otherwise it records
a pending change. Evidence:
`ev_2d9cd1e285e4b9c203838e14dfb29528423b7a2cada31c64f1654cc9f76ba7ca`.

This conditional branch reconciles two facts: a firmware recall path exists,
but changing the selected front-panel block alone did not reapply the body in
the previously observed live state. Cold boot remains the decisive physical
persistence test.

## Effect and reverb boundary

The channel record's effect child is Voice FX block 201. Its parent stores the
selected model and a nested model-specific body. The decoded Android and Linux
record builders currently materialize Transformer because that native body is
known and bounded; they reject unsupported active models rather than silently
dropping state.

Shared reverb block 202 has its own eleven-word `vrvb` state and independent
wire handler, documented in `REA_REVERB_EFFECTS_FAT_CHANNEL.md`. No block-202
child or `vrvb` state appears in the channel `Stat` format. Therefore:

- Fat Channel plus compatible Voice FX can use the firmware-native channel
  preset path.
- Transformer's private reverb-like network persists with Transformer state.
- Shared device reverb must be retained by a host/phone scene unless a future
  firmware format adds a separate persistent global-effects container.

## Remaining material REA work

1. Resolve the concrete nonvolatile backend below the virtual storage object,
   including medium, erase/write granularity, atomicity, wear behavior, and
   recovery after an interrupted write.
2. Trace the boot-time selection and the status bits that gate
   `FUN_6004f334`, so selection-time and power-on recall behavior are fully
   distinguished.
3. Search the global-settings loaders for an independent persistent container
   for shared block-202 reverb. Its absence from channel `Stat` is established;
   absence from every global store is not yet claimed.
4. Before any firmware extension, recover a safe executable/data placement,
   parser version migration, default initialization, package checksum/update
   rules, and boot-failure recovery path.
5. Lift only the remaining DSP inner loops needed for a named algorithm change;
   a blind sweep of all 1,311 procedures would not resolve these persistence
   questions.

The application package does not contain the device-side DFU bootloader/ROM.
REA cannot decompile bytes that have not been acquired; obtaining them would be
a separate, explicitly authorized hardware-acquisition task.

## Audit verdict

One post-analysis audit compared the ingress constraints, framed writer,
checksum-aware reader, conditional recall handler, and Voice FX state loader.
Their ranges, identifiers, sizes, and calls form one consistent storage-to-DSP
chain. No decoded path places shared reverb block 202 inside the channel
`Stat` record. The result is sufficient to correct the host/app persistence
contract, while the physical medium and cold-boot survival remain unproved.
