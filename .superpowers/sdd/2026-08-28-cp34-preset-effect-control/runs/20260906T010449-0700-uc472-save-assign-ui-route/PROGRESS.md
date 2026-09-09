# UC 4.7.2 Save/Assign UI route - progress

Timestamp: 2026-09-06T03:45:30-07:00

Status:
`UC472_SAVE_ASSIGN_UI_ROUTE_SOURCE_BOUND_TO_EXISTING_DEVICE_LIBRARY_AND_SLOT_STATE_PATHS`

## Result

The exact UC 4.7.2 interface does not expose one additional low-level Assign
transaction. It exposes two distinct preset concepts:

- `Device Presets` is the twelve-record user library. UI actions
  `storeNamedRemotePreset` and `sendToMixer` feed a high-level UCNet/object
  route which corresponds to the exact DSP module's existing
  `StorePreset -> MemP/PrsM` path for indexes 16..27.
- `presetSlot` is the four-value fast-access control. The existing DSP state
  machine maintains active slots 0..3 through its settled-state
  `MemP/Stat` snapshot/send path. A separate Assign frame was not located.

This makes a strictly Linux-native replacement technically plausible, but it
does not yield a safe one-line Wine workaround. The smallest source-bound
direction is to reproduce the high-level preset/state-machine behavior after
resolving the remaining runtime format boundary. Copying a DLL, translating
one syscall, or sending one newly guessed packet is not supported by this
evidence.

## Embedded UI

`studiolivepanel.dll` contains RCDATA resource `DEFAULT.SKIN` at RVA
`0x1320348` / file offset `0x1305f48`, size 21,371,451. It is a `PACKAGEF`
container with 275 files. Its exact `uceasy/uceasy.xml` member is at package
offset `0x14579b5`, compressed size 5,918, raw size 39,057, SHA-256
`a710cf06425a48ff1bb0e9ae72ad74d15613b939e675d134b27f4441074d5dfa`.

The parsed XML binds:

- `presetSlot` radio values 1, 2, 3, and 4;
- `storeNamedRemotePreset`, titled `Store`;
- `remoteList`, labeled and tooltipped `Device Presets`;
- `sendToMixer` beside `Local Presets` and `Device Presets`.

## Panel and UCNet route

The exact panel registers `sendToMixer` as action `0x452` and dispatches its
event block at `0x1800f9178` to helper `0x1800fe080`. That helper calls generic
transfer helper `0x180113ba0` at `0x1800fe8bb`. The transfer validates a
`MixerPreset`, temporarily installs a capture dispatcher at the remote owner
`+0x298`, creates transferred items using `ZStr`, and inserts them into the
remote list model.

The panel registers `storeNamedRemotePreset` as action `0x45f`; event block
`0x1800f94a3` calls helper `0x180103ba0`. That helper's calls at
`0x180103e77` and `0x180103e82` resolve exactly to
`UCGetNetworkManager` and `UCGetFileTransferManager` in `ucnet.dll`.

Jackson's browser vtable maps `+0x220` to panel function `0x18006ef10`.
That function constructs the high-level message `StorePreset` with keys
`presets`, `presetFile`, and `presetTarget`, then dispatches through the object
at `+0x298`, vtable `+0x80`. It does not itself construct low-level
`MemP/Stat` bytes.

## Exact DSP endpoint

The exact UC 4.7.2 `dspusbdevice.dll` receiver at `0x18003aef0` compares
`RestorePreset` and `StorePreset`. Its Store branch:

1. calls exact serializer `0x18002e270` at `0x18003b5b3`;
2. updates the selected library record;
3. calls sender helper `0x180037250` at `0x18003b5dc`;
4. constructs `PrsM` plus `Appl` and reaches the existing `MemP` fragmenter
   `0x180050f10` through sender vtable `0x1804393e0 + 0x10`.

The independently source-bound active-slot writer uses the same fragmenter
with `Stat` 0..3. Its exact physical record byte zero is `0x7b`; it does not
insert native little-endian u32 value 2.

Across the exact panel, service, UC executable, UCNet DLL, and DSP DLL, the UI
and service-side modules contain no reversed-file-byte `MemP`, `Stat`, `PrsM`,
or `SetP` immediates. Those low-level builders occur in the DSP module. This is
bounded topology evidence, not a product-wide proof of absence.

## Boundary

`STATIC_UI_AND_HOST_MESSAGE_ROUTE_RESOLVED_RUNTIME_UCNET_DELIVERY_FORMAT_TRANSFORMATION_PHYSICAL_COMMIT_RECALL_AND_AUDIBILITY_UNOBSERVED`

The matching high-level panel message and DSP receiver are source-bound, but
their runtime cross-process delivery was not observed. No transform from the
panel's object/ZStr representation to a firmware-eligible native-u32-two
record was located. Device acceptance, physical storage, recall, power-cycle
survival, selected component, Voice FX activation, and audibility remain
unobserved.

## Safety

Only retained files were read. No vendor binary was loaded or executed. No
Wine prefix was accessed; no USB/device, interface, transfer, ALSA/audio,
front-panel, preset/effect, firmware-image, reset, DFU, flash, install,
network, or REAPER action occurred.
