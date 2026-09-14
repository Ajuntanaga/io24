# Two dspusbdevice.dll builds are in play, and addresses are not portable

Status: `BUILD_PROVENANCE_HAZARD_IDENTIFIED_VOICEFX_MAPPING_VERIFIED_INTACT`

## The hazard

Two different `dspusbdevice.dll` builds are retained, and CP34 analysis has
been pinned to one while the block-201 / Voice FX analysis is pinned to the
other:

| build | size | sha256 (16) | location | used by |
|---|---|---|---|---|
| older | 4,974,080 | `c23c2867f02cf467` | `~/.cache/io24/re/` | `io24_fx.py`, block-201 model binding |
| UC 4.7.2 | 4,979,672 | `de685e89c88b191b` | `runs/20260906T001130-.../extracted/hwaccess/` | CP34 receiver/storage traces |

The same address means different things in each. `io24_fx.py` documents the
`VoFx` emit as block `0xc9` at `0x180049e4f` and the model store at
`0x180049e69`. In the older build those are exactly right. In UC 4.7.2,
`0x180049e4f` is a `ret` and `0x180049e69` is a `call`.

The 4.7.2 equivalents are:

```
0x180049752  mov qword [rsp+0x70], 0xc9        ; block 201
0x18004975b  mov dword [rsp+0x20], 0x566f4678  ; 'VoFx'
0x180049763  mov qword [rsp+0x24], 0x10        ; size 0x10
0x18004976c  mov dword [rsp+0x2c], r13d        ; model number
```

So old `0x180049e4f` -> 4.7.2 `0x180049752`, and old `0x180049e69` ->
4.7.2 `0x18004976c`.

Any future note that cross-references a block-201 address against a CP34
receiver/storage address is invalid unless both are re-derived in the same
build. This is the 13b failure mode at project scale.

## What is not affected

The Voice FX model binding is intact. Each of the six model tags occurs exactly
once in `.text` in both builds, in identical relative order:

| model | old | 4.7.2 |
|---|---|---|
| delay `vech` | 0x1800209d3 | 0x1800202b3 |
| transformer `godv` | 0x180022cb3 | 0x180022593 |
| vocoder `bota` | 0x1800232ba | 0x180022b9a |
| ringmod `botb` | 0x1800234cf | 0x180022daf |
| filters `botc` | 0x180023615 | 0x180022ef5 |
| detuner `may4` | 0x18002378e | 0x18002306e |

`io24_fx.py`'s model-to-class mapping therefore survives the build difference.
That was previously assumed; it is now checked.

## Method error, recorded

An earlier step in this run reported "zero immediate 201 sites in .text" and
that was wrong. It linearly swept `.text` with capstone; x86 linear sweep
desynchronises on embedded data and never decoded the real site, which stores
the block id as a QWORD (`mov qword [rsp+0x70], 0xc9`). The correct site was
found by disassembling from a known function offset instead. Do not trust a
linear-sweep negative over this binary.

## Boundary

Offline only. No device, audio, Wine, network, install or firmware operation,
and no vendor code executed.
