# UC 4.7.2 does not recall a channel preset through a device record

Status: `UC472_CHANNEL_PRESET_RECALL_IS_A_HOST_SIDE_MODEL_APPLY_NOT_A_DEVICE_RECORD_RECALL`

## Why this was run

Three live runs drove `MemP/Stat` plus selector recall and measured nothing, and
the direct-`SetP` positive control then proved the meter was not blind. The
route is genuinely inert. `NEXT.md` correctly forbade another speculative record
write, so the remaining move was static: find out what the vendor does instead.

## What the vendor's receiver actually accepts

`0x18003aef0` is the high-level preset request receiver. Its string compares
split cleanly by subject — a message name is compared against the request object
itself (`mov rcx, r14`), a parameter key against a member at `+0x48`. On that
discriminator the module understands exactly three incoming messages:

- `RestorePreset`
- `StorePreset`
- `GetPresetFileDescriptions`

and three keys: `presetTarget`, `presetFile`, `presetType`. `RenamedPreset` and
`PresetFileDescriptions` appear in the same body but are outgoing notification
names, not compares. **There is no assign, commit, apply, or activate message.**

## RestorePreset has two targets, and neither writes a record

`presetTarget` is compared against `channel` (`0x18003b112`) and `scene`
(`0x18003b20e`); there is no third branch. The `channel` branch:

```
18003b13c  call 0x18003c580              ; parse the index out of presetFile
18003b152  cmp  eax, [r13 + 0x160]       ; bound against the model's channel count
18003b161  lea  rbx, [rax + rax*8]
18003b165  shl  rbx, 5                   ; stride 0x120
18003b169  mov  rcx, [r13 + 0x158]       ; the host-side channel array
18003b170  add  rcx, 0xe8                ;   past its header
18003b17a  call 0x18003c8a0              ; guard
18003b19e  call 0x18002e690              ; apply the document to that channel
```

The applier `0x18002e690` brackets its work in the channel object's own `+0x8`
virtual — a begin/end suppression pair — and delegates to `0x18002e810`, which
builds a component-name filter (`voicefx`, `comp`, `opt`, `voicefxopt`) through
`0x18002ddf0` and then dispatches the document's own apply virtual. Everything
it touches is the host-side device model.

## The reachability test

Over the module's direct call/jmp graph, with call targets taken as function
starts, twelve functions materialise a `MemP`, `Stat`, or `PrsM` tag immediate.
The applier's entire 80-function subtree reaches **none** of them. The positive
control in the same run is `StorePreset`: its library sender `0x180037250`
reaches a record builder immediately, as it must.

Honest caveat, carried in the classification string: this is direct-call
evidence. 97 indirect call sites remain inside the applier subtree, including
the document's apply virtual. It is strong, not a proof.

## The one way a parameter reaches the wire

`0x1800541d0` is the module's only parameter-frame builder, and the module
contains exactly one `SetP` immediate (`0x18005423c`). It gates on
`[this+0x68] == 2` and prepends `GetP` or `SetP` for protocol version 2. It
lives at `+0xd8` of the same protocol-encoder vtable (`0x1804393e0`) whose
`+0x10` is the `MemP` fragmenter — so records and parameters are two slots of
one encoder class, not two transports.

## Consequence

UC's channel preset recall is a host-side model apply that replays ordinary
parameters. That is the same shape as the Linux Host's direct-setter preset
apply, which is therefore the UC-equivalent operation and not a workaround.

It also reframes the missing capability. Every one of our `MemP/Stat` nulls was
measuring a route the vendor never uses for recall, so those nulls say nothing
about whether the device can recall — only that we were pushing on the wrong
edge. And since UC's own recall is host-side, UC does not demonstrate
device-resident standalone recall over this route either. Whatever drives the
device's fast-access buttons is firmware-side and is not reached from these
three messages.

## What this does not settle

- What the device does with a `PrsM` library record once it has one.
- What the fast-access buttons do on the device, which stays firmware-side.
- The `scene` branch at `0x18003be50`, which opens a file and takes a different
  path; it was bounded here, not traced.
- Whether the applier's indirect apply virtual stays host-side. Confirming that
  would upgrade this from strong evidence to a closed result.

## Boundary

Static only. No device, USB, audio, Host, Wine, network, firmware, or Obsidian
action; no vendor code loaded or executed; nothing written to hardware. The
`NEXT.md` prohibition on a speculative `PrsM` write was respected.

Evidence: `route-report.json`, `re/cp34_uc472_restore_preset_route.py`,
`tests/test_cp34_uc472_restore_preset_route.py`.
