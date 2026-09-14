# Who instantiates the 0xE8 component: resolved

Status: `INSERT_FX_SELECTOR_COMPONENT_CREATED_BY_NAME_FROM_A_LOAD_TIME_REGISTRY`

## Answer

The 0xE8 object is **`InsertFXSelectorComponent`**. It is created by name
through a DSP component registry that a **CRT static initializer** populates at
DLL load, and it is instantiated during device-object construction.

```
DLL load
  -> CRT initializer table slot 0x1800e4898
     -> registry builder 0x180001990
        -> registry handle from 0x180026fd0
        -> appends 32-byte {name, creator, destroyer} records, capped at 100

device construction
  -> 0x180046350 -> device object ctor 0x1800303a0  (also 0x18002d8b0)
     -> looks the component up by name and calls its creator
        -> InsertFXSelectorComponent creator 0x18004b750
           -> allocates 0xE8, base ctor 0x180047fc0,
              primary vtable at +0x00, secondary 0x180437bf0 at +0x08
              (block-201 emitter is slot 1 of the secondary)
```

## The six registered components

| component | creator | destroyer |
|---|---|---|
| `EQCompSelectorComponent` | `0x18004b2e0` | `0x18004b350` |
| `FilterComponent` | `0x18004b420` | `0x18004b460` |
| `GateComponent` | `0x18004b530` | `0x18004b570` |
| `LimiterComponent` | `0x18004b640` | `0x18004b680` |
| **`InsertFXSelectorComponent`** | **`0x18004b750`** | `0x18004b7b0` |
| `VocalReverbComponent` | `0x18004b880` | `0x18004b8c0` |

This confirms in UC 4.7.2, with exact addresses, the class name PROTOCOL
previously carried from the older build.

## Why it was not found before

The creator is referenced by **neither a pointer nor a call**. It is not in any
vtable, appears nowhere as a 64-bit pointer, and is the target of no
`call rel32` anywhere in `.text`, including outside `.pdata` coverage. Earlier
searches therefore concluded, wrongly, that nothing instantiated it.

It is *loaded*, with a single RIP-relative `lea` at `0x180001ae0` inside the
static initializer, and written into the registry record. The general lesson,
worth carrying: **absence of pointers and calls is not absence of references.**
Search `lea` too.

Two techniques closed the remaining gaps:

- The emitter's other two "callers", `0x18003e6e3` and `0x18003e746`, are
  `.pdata` continuation chunks. Their `UNWIND_INFO` carries `UNW_FLAG_CHAININFO`,
  whose trailing RUNTIME_FUNCTION points at the primary, `0x18003e6c0`. That is
  the real calling function, and it queries interface FourCC `0x49467853`
  (`IFxS`) -- the Insert FX Selector.
- `0x180001990` has no callers but is stored at `0x1800e4898`, inside a dense
  run of consecutive function-start pointers: the CRT initializer table.

## Bearing on the open gate question

The Insert FX Selector component is constructed during **device construction**,
which is exactly the connect-time window. That is consistent with 13m, which
placed the block-201 gate opening "during chain construction, on heap nodes the
block resolver cannot address". It does not yet prove that construction emits
anything on the wire; the next step is what `0x1800303a0` and `0x180046350` do
after the component exists.

## Boundary

Offline only. No device, audio, Wine, network, install or firmware operation,
and no vendor code executed.

Evidence: `REGISTRY.json`, analyzer `re/cp34_uc472_component_registry.py`,
19 tests across it and the module graph.
