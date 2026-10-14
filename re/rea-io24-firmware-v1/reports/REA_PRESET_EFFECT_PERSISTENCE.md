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

Block 202 nevertheless has its own complete structured-state pair. Its writer
exports the eleven-word (`0x2c`-byte) body at block offset `0x370`; its loader
requires exactly `0x2c` bytes, restores that body, and reapplies the reverb DSP
state. This is a real firmware save/load capability, but it is not the channel
`Stat` path. The decoded root-settings writer does not traverse block 202, and
the DSP/audio reconfiguration path explicitly sends block 202 its default
`Setu` state. No decoded call chain binds the structured pair to a
device-resident global container at shutdown or cold boot. The controlling
contract is therefore host/phone save and replay across reconfiguration.

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

The preset-region initialization in `FUN_6005c850` configures regions of
`0xc1c`, `0x5dc`, `0x41a`, and `0x5dc` bytes and a `0x40` field used by the
preset component. It does not itself identify the lower physical medium.
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
child or `vrvb` state appears in the channel `Stat` format.

### Shared-reverb structured state

The block-202 vtable contains three mutually consistent paths:

- `FUN_60076e70` accepts a `vrvb` message, copies eleven words into
  `block+0x370`, and calls `FUN_60076da8` to apply them. Evidence:
  `ev_5983f7680b42d4a14dfce13424c5b5421dbb91e7e04fcf1bcf7ccbcc580968ce`.
- The writer at `0x6006faa0` constructs the structured-state wrapper, emits a
  `0x2c` length through `FUN_6004cdcc`, and asks the supplied stream to write
  `0x2c` bytes from `block+0x370`. The helper writes the length as a four-byte
  word and honors the wrapper's byte-order flag. Evidence:
  `ev_3a7460f4d9f670d1cf661ecf25b2d6c466e707d730c21b5c4b360770a5a3f2b1`,
  `ev_fe76fcf56f21dde876f6ad5b702280d985737226b1ed693ec7c5966d91a2809b`,
  `ev_58bc2edc25112af50ecfcad0dea932da891540b9d36f4b9861e7861571f19aae`,
  and `ev_1e2a6eb5adcec9c208deeec8d15f7196facffd4befa1f70147b97a7dbc4caf9b`.
- `FUN_60076edc` reads the structured length, accepts only `0x2c`, reads that
  exact body into `block+0x370`, and calls `FUN_60076da8`. Evidence:
  `ev_af619496d9c7105fb749cee185241d9efd03e4adfc6e384017033d5ee4346073`.

The writer and loader are vtable-dispatched; neither has a direct block-specific
caller in the recovered reference graph. They prove that firmware can serialize
and restore shared reverb as structured state. They do not, by themselves,
prove a nonvolatile global scene, shutdown save, or cold-boot restore.

### Reconfiguration and root-state behavior

`FUN_6005e740` rebuilds the DSP buffers and finishes by sending a `Setu`
message to Voice FX block 201 and shared reverb block 202. For block 202 it
calls `FUN_60076d68` and then `FUN_60076e70`, which reconstructs and applies
the default state rather than invoking the structured-state loader. Evidence:
`ev_f28c53f21d3778beb61837e42ce8c7cd5a40cedd06756938b3407a199072ac27`.

Its only direct caller is `FUN_6005ef50`, a vtable-dispatched DSP/audio
configuration method that rebuilds and registers blocks 201 and 202 and uses
the sample-rate configuration supplied by its caller. It also resets block 202
through `Setu` on the applicable rate-change path. Evidence:
`ev_e9d66a4f383b42bfb4637a72c778fa3a1193e23b1c53c72565cb3df31a202011`
and `ev_cdd01d53247479cc01c15c5a67266b2a33ff590dbee605d3bc074e507309722f`.
Because invocation is indirect, this establishes DSP reconfiguration behavior,
not a boot-only call site.

The recovered root writers `FUN_6004f984` and `FUN_6005bda8` serialize version
3 and root-level parameters; they do not enumerate components or invoke block
202's structured writer. Evidence:
`ev_8c13572d4c21b3096c383b1c10f7cb675abd13509a15bd8a4391ebe1ec3e937b`
and `ev_a3ef5cc0b051ee86acd0ea48a4164af5c55771d2fa5bf3a917c6b02c0426a5ab`.

Therefore:

- Fat Channel plus compatible Voice FX can use the firmware-native channel
  preset path.
- Transformer's private reverb-like network persists with Transformer state.
- Shared device reverb can round-trip through its existing structured-state
  interface, but DSP/audio reconfiguration defaults it and the recovered root
  writer does not include it. Host/phone scene state must save and replay it.

## Remaining material REA work

1. Resolve the concrete nonvolatile backend below the virtual storage object,
   including medium, erase/write granularity, atomicity, wear behavior, and
   recovery after an interrupted write.
2. Trace the boot-time selection and the status bits that gate
   `FUN_6004f334`, so selection-time and power-on recall behavior are fully
   distinguished.
3. Treat a device-resident global container for block 202 as absent from the
   recovered application call graph unless new bytes or a live cold-boot trace
   establish one. The current lifecycle path defaults the block instead.
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
checksum-aware reader, conditional recall handler, Voice FX state loader, and
block-202 structured writer/loader pair, root-state writers, and DSP/audio
reconfiguration method. Their identifiers, sizes, and calls are internally
consistent: channel `Stat` owns Fat Channel plus compatible Voice FX, while
shared reverb owns a separate eleven-word state interface. No decoded path
places block 202 inside channel `Stat` or the recovered root-state writer, and
the reconfiguration lifecycle actively defaults it. The result is sufficient
to require Host/Android save and replay. The physical preset medium and actual
cold-boot behavior remain unproved without separately authorized hardware work.
