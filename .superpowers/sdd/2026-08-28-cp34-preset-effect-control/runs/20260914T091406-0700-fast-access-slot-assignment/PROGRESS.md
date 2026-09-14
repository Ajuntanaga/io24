# The fast-access slot assignment edge does not exist

Status: `ASSIGNMENT_EDGE_ABSENT_FROM_PRODUCT`

## What was asked

CP34 has repeatedly recorded `explicit_assign_frame_located: false` and named
"one UC 4.7.2 `sendToMixer` plus button-assignment sequence" as the next
acquisition. The implicit assumption was that the operation exists and had not
been found yet.

## Input availability

Four of the five pinned UC 4.7.2 modules are retained inside
`runs/20260906T010449-0700-uc472-save-assign-ui-route/extracted/` and verify
exactly: panel `52e48cb1...`, service `b8e97749...`, Universal Control
`27f9fe55...`, ucnet `61aeda72...`. Only `dspusbdevice.dll` (`de685e89...`) is
gone with the wiped `/tmp` extraction, and it is not needed here: `sendToMixer`
and the slot UI live in the panel and in the component model.

## Result

`re/cp34_uc472_fast_access_slot_assignment.py` enumerates, exhaustively, every
skin control naming a slot/store/assign/mixer/disk and every component-model
parameter naming a preset/slot/store/assign.

The entire set of such controls in UC's shipped skin is four:

| control | kind | what it does |
|---|---|---|
| `presetSlot` | RadioButton, values 1..4 | selects the active slot |
| `sendToMixer` | Button | local list -> device preset library |
| `sendToDisk` | Button | device preset library -> local list |
| `storeNamedRemotePreset` | Button | "Store" into the device library |

The relevant parameters and their declared flags:

| parameter | flags |
|---|---|
| `activePresetSlotIndex` (int 0..3) | **mutable** |
| `presetSlotTitle1..4` (string) | **readonly** |
| `presetHotKeyTitle` (string) | readonly |
| `presetButtonMode` (int 0..2) | storable mutable |
| `preset_name` (string) | storable |

`activePresetSlotIndex` is the only mutable slot parameter and it only chooses
which slot is active. The four slot contents are `readonly` in UC's own model,
so UC cannot write them. There is no control and no parameter that puts a
preset into a numbered fast-access slot.

`FastAccessPresetSlots` in the skin confirms it structurally: the form holds
only the momentary `presetHotKey`, the four `presetSlot` radio buttons gated by
`hasSlot[0..3]`, and `presetButtonMode` variants that grey out slots 2/3/4.
Selection and readback, nothing else.

## Consequence

The assignment edge was never missing from the analysis. It is absent from the
product. `sendToMixer` moves a preset into the twelve-entry device *library*
(`MemP/PrsM` 16..27), which prior work already established is a distinct
namespace from the four fast-access button slots. Populating those four slots
is not a host operation in UC.

This closes the stated next edge. It also means no capture of a UC session
would have revealed an assign frame, because UC never sends one, and it retires
the idea that a `PrsM` write might expose button assignment.

What the Linux Host already implements is therefore the whole of the host-side
model: `set_preset_slot` / `recall_device_slot` are `activePresetSlotIndex`,
and `presetButtonMode` is the Host's preset-blocks selector.

## Method note

The first revision of the scanner reported an assign control that does not
exist: its `name="..."` pattern also matched the `titlename="..."` attribute,
attributing a slot's label to the control. §13b records the same failure mode.
The pattern is now anchored and a regression test pins it.

## Boundary

Offline only. No device, audio, Wine, network, install or firmware operation,
and no vendor code executed. The conclusion is about UC's shipped definitions;
it does not claim anything about what the unit's own front panel can do, which
remains the plausible mechanism for populating those slots.

Evidence: `ANALYSIS.json`.
