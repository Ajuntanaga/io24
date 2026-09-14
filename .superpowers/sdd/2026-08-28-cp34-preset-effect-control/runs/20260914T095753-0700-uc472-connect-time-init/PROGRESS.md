# UC 4.7.2 connect-time initialisation — partial trace

Status: `ENTRY_POINT_AND_TOOLING_ESTABLISHED_BLOCK201_INIT_PATH_UNRESOLVED`

## Why

Four established facts cannot all be true at once:

- 12S: block 201 does not respond to direct writes from a cold boot;
- 2026-08-31: only the native `Stat` load sets block 201's three gate flags;
- 2026-09-14: UC's recall replays ordinary parameters and never sends a `Stat`
  record, and that route is inert on this unit;
- the user confirms Voice FX were audible under UC.

So UC opens that gate by some route nobody has examined. Connect-time
initialisation is the obvious candidate, because it is the one thing UC does
that the Linux Host never reproduces.

## What is established

**The module is a plugin, and connect-time starts at a class factory.**
`dspusbdevice.dll` exports exactly one symbol, `CoreGetClassInfoBundle`
(`0x18004cc10`). Called with `0x64` it returns a bundle at `0x18049c948`:
count 4, class array at `0x18049c328`, vendor string `vendor=PreSonus`. All
four classes are category `HardwareDeviceFamilyManager`:

| class | GUID | factory |
|---|---|---|
| DSP USB Hardware Access | `{96552B05-DAAE-4334-B4E4-7E2A978FEEBB}` | `0x18004cf70` |
| DSP USB Hardware Access (Simulation) | `{D8FDB162-1888-49A0-BEB8-DBB7717D3600}` | `0x18004cc30` |
| DSP USB Hardware Access (MIDI Control) | `{F61B8BD1-6DB8-41AF-B8D4-72B76921D29A}` | `0x18004ce20` |
| DSP USB Hardware Access (Demo) | `{51F13B84-72E5-4709-BAFB-5BC23A561959}` | `0x18004cdc0` |

The real factory `0x18004cf70` answers interface FourCC `0x44464d67`, allocates
a 0x60-byte manager and a 0x40-byte sub-object, constructs the latter through
`0x180005b70`, installs its vtable, and calls `0x18006d3f0(0xa)` storing the
result at `+0x38`.

**Reliable tooling now exists.** `re/cp34_uc472_module_graph.py` builds the
function map from `.pdata` RUNTIME_FUNCTION entries -- 3452 exact bounds -- and
a direct call graph of 4050 edges, disassembling each function from a known
start. This replaces hand arithmetic and linear sweeps, both of which produced
false results earlier in this work.

**The block-201 emitter is isolated.** The `VoFx` emit site is inside function
`0x180049260..0x180049870`:

```
0x180049752  mov qword [rsp+0x70], 0xc9        ; block 201
0x18004975b  mov dword [rsp+0x20], 0x566f4678  ; 'VoFx'
0x180049763  mov qword [rsp+0x24], 0x10        ; size 0x10
0x18004976c  mov dword [rsp+0x2c], r13d        ; model number
```

It has exactly three direct callers -- `0x18003e6e3`, `0x18003e746`,
`0x1800491f0` -- and none of those has a direct caller of its own. The first two
are `.pdata` continuation chunks, not independent entries. Only `0x1800491f0`
is stored as a data pointer, at `0x180437bf8`.

That pointer is **slot 1 of the vtable based at `0x180437bf0`**, not slot 0 of a
vtable at `0x180437bf8`. An earlier revision of this record said the latter; it
walked backwards only while the preceding qword was a `.pdata` function start,
and stopped early at `0x18004c47c`, which is a chunk address rather than a
function begin. The base is confirmed by the three `lea` sites that install it.

## The owning class

Two functions install that vtable pair, and one destroys it:

| function | role |
|---|---|
| `0x18004b750` | allocating constructor: 0xE8 bytes, base ctor `0x180047fc0`, primary vtable at `+0x00`, secondary `0x180437bf0` at `+0x08`, `[obj+0xe0] = 0` |
| `0x180048ff0` | plain constructor, same two installs |
| `0x180049030` | destructor; queries interface FourCC `0x4a447370` (`JDsp`) and tail-jumps to `0x180063380` |

So the Voice FX component is a 0xE8-byte object with two vtables, the classic
MSVC multiple-inheritance layout, and its **secondary** interface at `+0x08`
carries the block-201 emitter at slot 1.

## Where the trace stops, and why

Neither constructor is called anywhere in the module. There is no direct
`call`, no raw `call rel32` anywhere in `.text` including outside `.pdata`
coverage, and neither address is stored as a 64-bit pointer. So the component
is instantiated through a mechanism this module does not express as a direct
reference, and resolving it needs indirect/virtual dispatch analysis.

A 32-bit RVA search looked briefly like a registration table and was a false
lead: the hits decode as the functions' own `.pdata` RUNTIME_FUNCTION entries
(`begin=0x18004b750 end=0x18004b7ad unwind=0x48c9a8`).

That false lead exposed a real defect in the tooling, now fixed and pinned by
regression tests: `.data` and `.pdata` **overlap in file space**, because a
section's virtual span can exceed its raw data. Mapping a file offset back to
an address by first match therefore attributed a `.pdata` entry to `.data`.
File-offset containment now uses raw extents only.

## What is NOT established

Whether connect-time initialisation emits block 201. It is not answerable by
direct-call reachability, because everything above `0x1800491f0` is virtual
dispatch. This is the same wall the `restore-preset-route` run hit with its 97
unresolved indirect sites. No claim either way should be recorded yet.

## Exact next step

1. Find where vtable `0x180437bf8` is installed -- search `.text` for the
   RIP-relative `lea` that loads it -- which names the owning class and its
   constructor.
2. From that constructor, walk up to whoever allocates the object, and
   determine whether the family manager's device-attach path reaches it before
   any user action.
3. Only then is a live test warranted, and the rig for it already exists: the
   positive control resolves a Channel-2 DSP change at about 28 dB, so an
   init-time block-201 effect would be unmissable.

## Boundary

Offline only. No device, audio, Wine, network, install or firmware operation,
and no vendor code executed.
