# CP34 Hot Key and VoiceFX state-route result

Timestamp: 2026-09-06T09:03:17-07:00

Status: `UC472_HOTKEY_FULL_CHANNEL_OVERRIDE_AND_VOICEFX_SELECTION_ROUTE_SOURCE_BOUND`

## Result

The missing Hot Key path is real, but it is not another device preset slot or
another DSP effect engine. In UC 4.7.2, parameter 151 selects a complete cached
channel snapshot at channel-object offset `+0x180` while held. Releasing it
restores the active normal snapshot selected by parameter 150. Both states enter
the same generic channel deserializer and class-specific post-apply path.

The Hot Key snapshot is loaded and saved under the nested `hotkey` key. If it is
active while a channel is loaded, UC captures the effective full-channel state
with the same serializer used by `StorePreset`. This explains why the control
can make a saved VoiceFX choice effective even though it is not a seventh
device-resident preset slot.

## Active VoiceFX algorithm during save

UC does not detect the algorithm by reading a hidden DSP selector register.
Block 201 is write-only on this path. The source of truth is the current host
component tree:

- `voicefx.__classid` stores the selected model class;
- `voicefxopt/fxmodel`, parameter 450, holds model `-1` or `0..5`;
- `voicefx.on` is a separate storable enable value;
- only the selected mutable model child's state is serialized.

During apply, UC resolves `__classid`, creates/selects that model, emits
`SetP(block=201,index=0,tag=VoFx,size=16,u32=model)`, installs it as the mutable
`voicefx` child, and then applies the selected child's parameters. Model zero is
Transformer/Doubler, not bypass; `-1` means no model.

Therefore a Linux-host save must retain the model/class ID, `voicefx.on`, and
the selected model state. Apply must select/instantiate the model before its
parameters. Unknown attached-device VoiceFX state cannot be reconstructed from
block-201 readback; the host must use a complete known snapshot or explicitly
select a model.

## Exact channel-ownership branch

The channel decision is also explicit. Initial apply at `0x180040729` and the
parameter-change refresh at `0x18004193f` both read parameter 149 and call
`0x18003e6c0` with the predicate `processingChannel == 0`. The true branch
activates `voicefxopt/fxmodel` and selects its current model. The false branch
deactivates that selector and chooses host no-model sentinel `-1`. Parameter
149's change handler is `0x18004145e`.

This is an ownership layer, not a remapping of physical preset controls.
`set_preset_enabled(1|2)` and `set_preset_slot(1|2, ...)` continue to address
physical Channel 1 or Channel 2 respectively. The Linux-host order for an
explicit VoiceFX load is therefore: assign the requested physical input,
select its model, then apply `voicefx.on` and that model's fields.

## Per-channel storage versus runtime instances

Each Channel-1 or Channel-2 preset snapshot can contain its own VoiceFX class
and parameters. Recalling any one of those snapshots configures the same
singleton block-201 model object in stock firmware. Thus different model choices
can be stored per channel, but stock firmware does not provide two independently
running VoiceFX model instances.

The singleton is structurally two-input/two-output, and model zero's private
reverb binds lane indexes 0 and 1. That supports a possible shared algorithm and
shared parameter set on both lanes, but stock simultaneous routing/activation
is not yet proved. Shared block-202 reverb is a separate two-send architecture.

For genuinely different simultaneous VoiceFX algorithms, later custom firmware
would need an index-aware block-201 resolver, a second parent/model object, one
instance bound to each input lane, separate state per channel, and measured
RAM/code/DSP-budget headroom. Per user direction, that work is deferred until
after the initial GitHub publication. No firmware implementation belongs in the
current host-completion lane.

## Prior Channel-2 trial gap

The corrected Channel-2 slot-3 stage deliberately set
`direct_voicefx_parameter_write=false`. It therefore transferred and recalled a
tagged record but did not reproduce UC's explicit model-selection-before-state
transition. Its dry standalone result is not proof that the corrected full
VoiceFX apply route cannot work.

## Boundary

This is a hash-pinned static host-state result. Runtime event propagation,
physical device storage, power-cycle recall, the stock simultaneous-lane gate,
and audibility remain unobserved. No USB/device, Wine, audio, network, or
firmware action occurred.
